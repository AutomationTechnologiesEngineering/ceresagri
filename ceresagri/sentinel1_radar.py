"""
Descarcare si procesare date radar Sentinel-1 pentru o parcela.

Sentinel-1 este un radar cu deschidere sintetica (SAR) care functioneaza la
~5.4 GHz (banda C). Trimite un puls de microunda spre sol si masoara cat se
intoarce inapoi (backscatter), in decibeli (dB).

Avantaj fata de optic (Sentinel-2):
- Functioneaza noaptea si prin nori
- Sensibil la umiditatea solului si structura vegetatiei

Pentru CeresAgri folosim:
- VV (Vertical-Vertical) -- proxy de umiditate sol + rugozitate
- VH (Vertical-Horizontal) -- proxy de structura vegetatie
- Indice VH/VV -- raport util pentru detectia tipului de cultura
"""

# --- Importuri ---
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_bounds
from sentinelhub import (
    CRS,
    BBox,
    DataCollection,
    MimeType,
    SentinelHubCatalog,
    SentinelHubRequest,
    bbox_to_dimensions,
)
from shapely.geometry import Polygon
from tqdm import tqdm

from ceresagri.sentinel_client import get_sentinelhub_config

# --- Constante ---
# Sentinel-1 are rezolutie nativa ~10m in modul IW (Interferometric Wide swath)
# Folosim aceeasi rezolutie ca pentru Sentinel-2 ca sa putem suprapune imaginile
RESOLUTION_M = 10


# --- Evalscripts ---
# Acest evalscript calculeaza VV si VH in decibeli (dB)
# Conversia din unitati liniare in dB: dB = 10 * log10(linear)
# Adaugam un mic offset (1e-10) ca sa evitam log10(0) care da -infinit
EVALSCRIPT_S1_VV_VH = """
//VERSION=3
function setup() {
    return {
        input: ["VV", "VH", "dataMask"],
        output: {
            bands: 3,
            sampleType: "FLOAT32"
        }
    };
}

function evaluatePixel(sample) {
    // Conversie liniara -> decibeli
    // Adaugam 1e-10 ca protectie la log(0)
    let vv_db = 10 * Math.log10(sample.VV + 1e-10);
    let vh_db = 10 * Math.log10(sample.VH + 1e-10);

    return [vv_db, vh_db, sample.dataMask];
}
"""


def search_sentinel1_scenes(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    buffer_degrees: float = 0.01,
) -> list[dict]:
    """
    Cauta scene Sentinel-1 GRD disponibile peste un punct geografic.

    Sentinel-1 nu are conceptul de "cloud cover" (este radar, nu vede nori).
    In schimb, are conceptul de "orbit direction":
    - ASCENDING: satelit se misca spre nord (de obicei seara)
    - DESCENDING: satelit se misca spre sud (de obicei dimineata)
    Cele doua au geometrii diferite si rezultate usor diferite.
    Pentru analiza temporala consistenta, ne fixam pe una (ASCENDING e mai comun).
    """
    sh_config = get_sentinelhub_config()

    bbox = BBox(
        bbox=(
            longitude - buffer_degrees,
            latitude - buffer_degrees,
            longitude + buffer_degrees,
            latitude + buffer_degrees,
        ),
        crs=CRS.WGS84,
    )

    catalog = SentinelHubCatalog(config=sh_config)

    search_iterator = catalog.search(
        collection=DataCollection.SENTINEL1_IW,
        bbox=bbox,
        time=(start_date, end_date),
        # Filtru pentru orbita ASCENDING (vrem date consistente in timp)
        filter="sat:orbit_state = 'ascending'",
        fields={
            "include": [
                "id",
                "properties.datetime",
                "properties.sat:orbit_state",
                "bbox",
            ],
            "exclude": [],
        },
    )

    scenes = []
    for item in search_iterator:
        scenes.append(
            {
                "id": item["id"],
                "datetime": item["properties"]["datetime"],
                "orbit": item["properties"].get("sat:orbit_state", "unknown"),
                "bbox": item["bbox"],
            }
        )

    scenes.sort(key=lambda x: x["datetime"], reverse=True)
    return scenes


def download_sentinel1_data(
    parcel_polygon: Polygon,
    date: str,
    output_path: Path,
    buffer_m: int = 200,
) -> dict:
    """
    Descarca VV + VH (in dB) pentru parcela la data specificata.

    Salveaza un TIFF cu 3 benzi: VV, VH, dataMask.
    """
    minx, miny, maxx, maxy = parcel_polygon.bounds
    buffer_lat = buffer_m / 111000
    buffer_lon = buffer_m / (111000 * np.cos(np.radians((miny + maxy) / 2)))

    bbox = BBox(
        bbox=(
            minx - buffer_lon,
            miny - buffer_lat,
            maxx + buffer_lon,
            maxy + buffer_lat,
        ),
        crs=CRS.WGS84,
    )
    size = bbox_to_dimensions(bbox, resolution=RESOLUTION_M)

    sh_config = get_sentinelhub_config()
    time_interval = (f"{date}T00:00:00", f"{date}T23:59:59")

    request = SentinelHubRequest(
        evalscript=EVALSCRIPT_S1_VV_VH,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL1_IW.define_from(
                    "s1iw", service_url="https://sh.dataspace.copernicus.eu"
                ),
                time_interval=time_interval,
                other_args={
                    "dataFilter": {
                        "orbitDirection": "ASCENDING",
                    },
                    "processing": {
                        # Aplicare automata a corectiei radiometrice si terrain correction
                        "backCoeff": "SIGMA0_ELLIPSOID",
                        "orthorectify": True,
                    },
                },
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=size,
        config=sh_config,
    )

    print(f"  Cerere Sentinel-1 catre Sentinel Hub pentru {date}...")
    response = request.get_data(save_data=False)

    if not response:
        raise RuntimeError(f"Niciun raspuns primit pentru data {date}")

    s1_data = response[0]
    print(f"  S1 primit: shape={s1_data.shape}, dtype={s1_data.dtype}")

    # Separam canalele
    vv_db = s1_data[:, :, 0]
    vh_db = s1_data[:, :, 1]
    data_mask = s1_data[:, :, 2]

    # Aplicam masca: pixelii cu mask=0 devin NaN
    vv_masked = np.where(data_mask > 0, vv_db, np.nan)
    vh_masked = np.where(data_mask > 0, vh_db, np.nan)

    # Salvam ca TIFF cu 2 benzi (VV si VH)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    transform = from_bounds(bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y, size[0], size[1])

    with rasterio.open(
        output_path,
        "w",
        driver="GTiff",
        height=vv_masked.shape[0],
        width=vv_masked.shape[1],
        count=2,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=np.nan,
    ) as dst:
        dst.write(vv_masked.astype("float32"), 1)
        dst.write(vh_masked.astype("float32"), 2)
        dst.set_band_description(1, "VV_dB")
        dst.set_band_description(2, "VH_dB")

    # Statistici
    valid_vv = vv_masked[~np.isnan(vv_masked)]
    valid_vh = vh_masked[~np.isnan(vh_masked)]

    if len(valid_vv) > 0:
        stats = {
            "vv_mean_db": float(np.mean(valid_vv)),
            "vv_min_db": float(np.min(valid_vv)),
            "vv_max_db": float(np.max(valid_vv)),
            "vv_std_db": float(np.std(valid_vv)),
            "vh_mean_db": float(np.mean(valid_vh)),
            "vh_min_db": float(np.min(valid_vh)),
            "vh_max_db": float(np.max(valid_vh)),
            "vh_std_db": float(np.std(valid_vh)),
            "vh_vv_ratio_db": float(np.mean(valid_vh) - np.mean(valid_vv)),
            "valid_fraction": len(valid_vv) / vv_masked.size,
        }
    else:
        stats = dict.fromkeys(
            [
                "vv_mean_db",
                "vv_min_db",
                "vv_max_db",
                "vv_std_db",
                "vh_mean_db",
                "vh_min_db",
                "vh_max_db",
                "vh_std_db",
                "vh_vv_ratio_db",
            ]
        )
        stats["valid_fraction"] = 0.0

    return {
        "path": str(output_path),
        "shape": vv_masked.shape,
        "date": date,
        "stats": stats,
    }


def compute_s1_timeseries(
    parcel_polygon: Polygon,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    output_dir: Path,
    skip_existing: bool = True,
) -> pd.DataFrame:
    """
    Construieste serie temporala Sentinel-1 pentru parcela (12 luni).
    """
    print(f"Cautare scene Sentinel-1 in perioada {start_date} -> {end_date}")
    scenes = search_sentinel1_scenes(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
    )

    if not scenes:
        print("Nicio scena Sentinel-1 gasita.")
        return pd.DataFrame()

    print(f"Gasite {len(scenes)} scene Sentinel-1 (ASCENDING).\n")

    records = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for scene in tqdm(scenes, desc="Procesare S1 per scena"):
        scene_datetime = scene["datetime"]
        date_str = scene_datetime.split("T")[0]

        s1_tiff_path = output_dir / f"jidvei_s1_{date_str}.tif"

        if skip_existing and s1_tiff_path.exists():
            stats = _read_s1_stats_from_tiff(s1_tiff_path)
        else:
            try:
                result = download_sentinel1_data(
                    parcel_polygon=parcel_polygon,
                    date=date_str,
                    output_path=s1_tiff_path,
                    buffer_m=200,
                )
                stats = result["stats"]
            except Exception as e:
                print(f"\nEROARE la {date_str}: {e}")
                continue

        records.append(
            {
                "date": date_str,
                "orbit": scene["orbit"],
                **stats,
                "scene_id": scene["id"],
            }
        )

    df = pd.DataFrame(records)
    if len(df) > 0:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

    return df


def _read_s1_stats_from_tiff(tiff_path: Path) -> dict:
    """Recalculeaza statistici din TIFF deja descarcat."""
    with rasterio.open(tiff_path) as src:
        vv = src.read(1)
        vh = src.read(2)

    valid_vv = vv[~np.isnan(vv)]
    valid_vh = vh[~np.isnan(vh)]

    if len(valid_vv) == 0:
        return {
            "vv_mean_db": None,
            "vv_min_db": None,
            "vv_max_db": None,
            "vv_std_db": None,
            "vh_mean_db": None,
            "vh_min_db": None,
            "vh_max_db": None,
            "vh_std_db": None,
            "vh_vv_ratio_db": None,
            "valid_fraction": 0.0,
        }

    return {
        "vv_mean_db": float(np.mean(valid_vv)),
        "vv_min_db": float(np.min(valid_vv)),
        "vv_max_db": float(np.max(valid_vv)),
        "vv_std_db": float(np.std(valid_vv)),
        "vh_mean_db": float(np.mean(valid_vh)),
        "vh_min_db": float(np.min(valid_vh)),
        "vh_max_db": float(np.max(valid_vh)),
        "vh_std_db": float(np.std(valid_vh)),
        "vh_vv_ratio_db": float(np.mean(valid_vh) - np.mean(valid_vv)),
        "valid_fraction": len(valid_vv) / vv.size,
    }


# --- Self-test ---
if __name__ == "__main__":
    from ceresagri.sentinel_download import load_parcel_geojson

    PROJECT_ROOT = Path(__file__).parent.parent
    parcel_path = PROJECT_ROOT / "data" / "parcels" / "jidvei_test_parcel.geojson"
    output_dir = PROJECT_ROOT / "data" / "sentinel1"

    polygon = load_parcel_geojson(parcel_path)
    centroid = polygon.centroid

    print("=" * 80)
    print("CeresAgri -- serie temporala Sentinel-1 SAR pentru parcela Jidvei")
    print("=" * 80)
    print(f"Centroid: lat={centroid.y:.5f}, lon={centroid.x:.5f}")
    print(f"Output: {output_dir}\n")

    df = compute_s1_timeseries(
        parcel_polygon=polygon,
        latitude=centroid.y,
        longitude=centroid.x,
        start_date="2025-05-23",
        end_date="2026-05-23",
        output_dir=output_dir,
        skip_existing=True,
    )

    print(f"\n\nSerie temporala Sentinel-1: {len(df)} puncte")

    if len(df) > 0:
        # Afisam doar coloanele cheie pentru un summary lizibil
        print("\nPrimele 10 randuri:")
        print(
            df[["date", "vv_mean_db", "vh_mean_db", "vh_vv_ratio_db"]]
            .head(10)
            .to_string(index=False)
        )
        print("\nUltimele 10 randuri:")
        print(
            df[["date", "vv_mean_db", "vh_mean_db", "vh_vv_ratio_db"]]
            .tail(10)
            .to_string(index=False)
        )

    # Salvam CSV
    csv_path = PROJECT_ROOT / "data" / "sentinel1" / "jidvei_s1_timeseries.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSerie salvata: {csv_path}")
