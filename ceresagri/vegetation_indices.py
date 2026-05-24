"""
Calculul indicilor vegetativi din imagini Sentinel-2.

Acest modul defineste evalscripts pentru calculul indicilor pe serverul
Sentinel Hub si functii de descarcare a rezultatelor.

Indicii implementati (Ziua 2):
- NDVI: Normalized Difference Vegetation Index -- vigoarea vegetatiei

Indicii planificati (zilele urmatoare):
- NDRE: Normalized Difference Red Edge -- mai sensibil pentru culturi mature
- NDWI: Normalized Difference Water Index -- umiditatea vegetatiei
- EVI:  Enhanced Vegetation Index -- mai bun in conditii dense
"""

# --- Importuri ---
from pathlib import Path

import numpy as np
from sentinelhub import (
    CRS,
    BBox,
    DataCollection,
    MimeType,
    SentinelHubRequest,
    bbox_to_dimensions,
)
from shapely.geometry import Polygon

from ceresagri.sentinel_client import get_sentinelhub_config

# --- Constante ---
RESOLUTION_M = 10  # rezolutie pixel in metri (banzile B04, B08 sunt nativ 10m)


# --- Evalscripts ---

# Calcul NDVI cu output float (valori reale -1 la +1)
# Folosim sampleType FLOAT32 pentru a pastra precizia matematica.
# Output-ul va fi un TIFF cu valori reale, nu o imagine PNG colorata.
EVALSCRIPT_NDVI = """
//VERSION=3
function setup() {
    return {
        input: ["B04", "B08", "dataMask"],
        output: {
            bands: 2,
            sampleType: "FLOAT32"
        }
    };
}

function evaluatePixel(sample) {
    // Calculam NDVI = (NIR - RED) / (NIR + RED)
    // B08 = NIR (842nm), B04 = RED (665nm)
    let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);

    // Intoarcem doua benzi:
    // banda 1: valoarea NDVI
    // banda 2: dataMask (1 = pixel valid, 0 = pixel invalid - nor, umbra)
    return [ndvi, sample.dataMask];
}
"""


def download_ndvi(
    parcel_polygon: Polygon,
    date: str,
    output_path: Path,
    buffer_m: int = 200,
) -> dict:
    """
    Descarca o harta NDVI pentru parcela la data specificata.

    Spre deosebire de RGB (care intoarce 3 canale uint8 0-255), NDVI
    intoarce 2 canale float32: valoarea NDVI propriu-zisa si masca de validitate.

    Output este salvat ca TIFF (pastreaza precizia float, spre deosebire de PNG).
    """
    # 1. Bounding box cu buffer
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

    # 2. Cererea Sentinel Hub
    sh_config = get_sentinelhub_config()
    time_interval = (f"{date}T00:00:00", f"{date}T23:59:59")

    request = SentinelHubRequest(
        evalscript=EVALSCRIPT_NDVI,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A.define_from(
                    "s2l2a", service_url="https://sh.dataspace.copernicus.eu"
                ),
                time_interval=time_interval,
                mosaicking_order="leastCC",
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=size,
        config=sh_config,
    )

    # 3. Descarcam
    print(f"  Cerere NDVI catre Sentinel Hub pentru {date}...")
    response = request.get_data(save_data=False)

    if not response:
        raise RuntimeError(f"Niciun raspuns primit pentru data {date}")

    # response[0] este un array numpy de shape (H, W, 2)
    # canal 0 = NDVI, canal 1 = dataMask
    ndvi_data = response[0]
    print(f"  NDVI primit: shape={ndvi_data.shape}, dtype={ndvi_data.dtype}")

    # Separam canalele
    ndvi_values = ndvi_data[:, :, 0]  # valorile NDVI
    data_mask = ndvi_data[:, :, 1]  # masca de validitate

    # Aplicam masca: pixelii cu mask=0 devin NaN (Not a Number)
    # Astfel statisticile (medie, min, max) nu vor lua in calcul pixelii invalizi
    ndvi_masked = np.where(data_mask > 0, ndvi_values, np.nan)

    # 4. Salvam ca TIFF float32
    # Pentru asta folosim rasterio (citire/scriere fisiere geospatiale)
    import rasterio
    from rasterio.transform import from_bounds

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Calculam transformata geografica (pixeli -> coordonate)
    transform = from_bounds(bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y, size[0], size[1])

    with rasterio.open(
        output_path,
        "w",
        driver="GTiff",
        height=ndvi_masked.shape[0],
        width=ndvi_masked.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:4326",  # WGS84
        transform=transform,
        nodata=np.nan,
    ) as dst:
        dst.write(ndvi_masked.astype("float32"), 1)

    # 5. Statistici de baza pentru raport
    valid_pixels = np.sum(~np.isnan(ndvi_masked))
    total_pixels = ndvi_masked.size

    if valid_pixels > 0:
        stats = {
            "mean": float(np.nanmean(ndvi_masked)),
            "min": float(np.nanmin(ndvi_masked)),
            "max": float(np.nanmax(ndvi_masked)),
            "std": float(np.nanstd(ndvi_masked)),
            "valid_fraction": valid_pixels / total_pixels,
        }
    else:
        stats = {"mean": None, "min": None, "max": None, "std": None, "valid_fraction": 0.0}

    return {
        "path": str(output_path),
        "shape": ndvi_masked.shape,
        "date": date,
        "stats": stats,
        "bbox_wgs84": (bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y),
    }


# --- Self-test ---
if __name__ == "__main__":
    print("=" * 80)
    print("CeresAgri -- Calcul NDVI pentru parcela Jidvei (test pe o scena)")
    print("=" * 80)

    # Calea catre parcela
    PROJECT_ROOT = Path(__file__).parent.parent
    parcel_path = PROJECT_ROOT / "data" / "parcels" / "jidvei_test_parcel.geojson"

    # Incarcam parcela
    from ceresagri.sentinel_download import load_parcel_geojson

    polygon = load_parcel_geojson(parcel_path)

    # Scena de vara (varf vegetativ) -- ne asteptam NDVI ridicat
    target_date = "2025-08-30"
    output_path = PROJECT_ROOT / "data" / "ndvi" / f"jidvei_ndvi_{target_date}.tif"

    print(f"\nParcela: {parcel_path.name}")
    print(f"Data: {target_date} (vara, varf vegetativ - asteptam NDVI ridicat)")
    print(f"Output: {output_path}")
    print()

    try:
        result = download_ndvi(
            parcel_polygon=polygon,
            date=target_date,
            output_path=output_path,
            buffer_m=200,
        )

        print(f"\nSUCCES! NDVI salvat la: {result['path']}")
        print(f"Dimensiuni: {result['shape']}")
        print("\nStatistici NDVI:")
        print(f"  Medie:               {result['stats']['mean']:.3f}")
        print(f"  Minim:               {result['stats']['min']:.3f}")
        print(f"  Maxim:               {result['stats']['max']:.3f}")
        print(f"  Deviatie standard:   {result['stats']['std']:.3f}")
        print(f"  Pixeli validi:       {result['stats']['valid_fraction'] * 100:.1f}%")

        # Interpretare automata simpla
        mean = result["stats"]["mean"]
        if mean < 0.1:
            interpretare = "sol gol / zapada / urban"
        elif mean < 0.3:
            interpretare = "vegetatie rara sau uscata"
        elif mean < 0.6:
            interpretare = "vegetatie moderata (cultura in crestere)"
        elif mean < 0.8:
            interpretare = "vegetatie densa, sanatoasa"
        else:
            interpretare = "varf vegetativ"

        print(f"\nInterpretare agronomica: {interpretare}")

    except Exception as e:
        print(f"\nEROARE: {e}")
        import traceback

        traceback.print_exc()
