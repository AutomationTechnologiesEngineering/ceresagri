"""
Calcul serii temporale NDVI pentru o parcela.

Acest modul:
1. Itereaza prin toate scenele Sentinel-2 disponibile intr-o perioada
2. Descarca NDVI pentru fiecare
3. Calculeaza statistici per-parcela (medie, min, max, std, percentile)
4. Construieste un DataFrame pandas cu serie temporala curata
5. Salveaza ca CSV pentru reproductibilitate
"""

# --- Importuri ---
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import Polygon
from tqdm import tqdm

from ceresagri.sentinel_client import search_sentinel2_scenes
from ceresagri.vegetation_indices import download_ndvi


def compute_ndvi_timeseries(
    parcel_polygon: Polygon,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    output_dir: Path,
    max_cloud_cover: float = 30.0,
    skip_existing: bool = True,
) -> pd.DataFrame:
    """
    Construieste o serie temporala NDVI pentru o parcela.

    Parametri:
        parcel_polygon: poligonul parcelei (shapely)
        latitude, longitude: punctul central pentru cautare in catalog
        start_date, end_date: perioada in format "YYYY-MM-DD"
        output_dir: unde se salveaza fisierele NDVI TIFF (cache local)
        max_cloud_cover: filtru pentru scene (procent maxim de nori)
        skip_existing: daca True, nu re-descarca scenele deja prelucrate

    Returneaza:
        DataFrame pandas cu coloanele:
        - date: data scenei
        - cloud_cover: procentul de nori al scenei
        - ndvi_mean, ndvi_min, ndvi_max, ndvi_std: statistici per parcela
        - ndvi_p25, ndvi_p75: percentile (utile pentru detectia anomaliilor)
        - valid_fraction: procent pixeli validi (dupa masking)
        - scene_id: ID Sentinel-2
    """
    # 1. Cautam toate scenele disponibile in perioada
    print(f"Cautare scene Sentinel-2 in perioada {start_date} -> {end_date}")
    print(f"Filtru nori: maxim {max_cloud_cover}%")

    scenes = search_sentinel2_scenes(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        max_cloud_cover=max_cloud_cover,
    )

    if not scenes:
        print("Nicio scena gasita.")
        return pd.DataFrame()

    print(f"Gasite {len(scenes)} scene.\n")

    # 2. Descarcam NDVI pentru fiecare scena si extragem statistici
    records = []
    output_dir.mkdir(parents=True, exist_ok=True)

    # tqdm imbraca iteratia intr-o bara de progres -- foarte util pentru
    # operatiuni lungi unde vrei sa stii la cat ai ramas
    for scene in tqdm(scenes, desc="Procesare NDVI per scena"):
        # Extragem doar data (fara timp) din timestamp-ul scenei
        scene_datetime = scene["datetime"]
        date_str = scene_datetime.split("T")[0]  # "2025-08-30T09:27:00Z" -> "2025-08-30"

        # Calea unde salvam fisierul NDVI pentru aceasta scena
        ndvi_tiff_path = output_dir / f"jidvei_ndvi_{date_str}.tif"

        # Daca exista deja si skip_existing, sarim cu calcul rapid din TIFF
        if skip_existing and ndvi_tiff_path.exists():
            stats = _read_stats_from_tiff(ndvi_tiff_path)
        else:
            try:
                result = download_ndvi(
                    parcel_polygon=parcel_polygon,
                    date=date_str,
                    output_path=ndvi_tiff_path,
                    buffer_m=200,
                )
                stats = result["stats"]
            except Exception as e:
                print(f"\nEROARE la {date_str}: {e}")
                continue

        # Pastram inregistrarea
        # Calculam si percentilele 25 si 75 prin re-citirea TIFF-ului
        # (ar fi putut fi facut in download_ndvi, dar separarea responsabilitatilor
        # este mai curata asa)
        percentiles = _read_percentiles_from_tiff(ndvi_tiff_path)

        records.append(
            {
                "date": date_str,
                "cloud_cover": scene["cloud_cover"],
                "ndvi_mean": stats["mean"],
                "ndvi_min": stats["min"],
                "ndvi_max": stats["max"],
                "ndvi_std": stats["std"],
                "ndvi_p25": percentiles["p25"],
                "ndvi_p75": percentiles["p75"],
                "valid_fraction": stats["valid_fraction"],
                "scene_id": scene["id"],
            }
        )

    # 3. Construim DataFrame-ul
    df = pd.DataFrame(records)

    if len(df) > 0:
        # Convertim coloana date la tipul datetime al pandas pentru filtrare ulterioara
        df["date"] = pd.to_datetime(df["date"])
        # Sortam cronologic (cele mai vechi primele)
        df = df.sort_values("date").reset_index(drop=True)

    return df


def _read_stats_from_tiff(tiff_path: Path) -> dict:
    """Recalculeaza statistici NDVI dintr-un fisier TIFF deja descarcat."""
    import rasterio

    with rasterio.open(tiff_path) as src:
        ndvi = src.read(1)

    valid = ndvi[~np.isnan(ndvi)]

    if len(valid) == 0:
        return {"mean": None, "min": None, "max": None, "std": None, "valid_fraction": 0.0}

    return {
        "mean": float(np.mean(valid)),
        "min": float(np.min(valid)),
        "max": float(np.max(valid)),
        "std": float(np.std(valid)),
        "valid_fraction": len(valid) / ndvi.size,
    }


def _read_percentiles_from_tiff(tiff_path: Path) -> dict:
    """Calculeaza percentilele 25 si 75 ale NDVI."""
    import rasterio

    with rasterio.open(tiff_path) as src:
        ndvi = src.read(1)

    valid = ndvi[~np.isnan(ndvi)]

    if len(valid) == 0:
        return {"p25": None, "p75": None}

    return {
        "p25": float(np.percentile(valid, 25)),
        "p75": float(np.percentile(valid, 75)),
    }


# --- Self-test ---
if __name__ == "__main__":
    from ceresagri.sentinel_download import load_parcel_geojson

    PROJECT_ROOT = Path(__file__).parent.parent
    parcel_path = PROJECT_ROOT / "data" / "parcels" / "jidvei_test_parcel.geojson"
    output_dir = PROJECT_ROOT / "data" / "ndvi"

    polygon = load_parcel_geojson(parcel_path)

    # Centroid pentru cautare in catalog
    centroid = polygon.centroid
    lat = centroid.y
    lon = centroid.x

    print("=" * 80)
    print("CeresAgri -- serie temporala NDVI pentru parcela Jidvei (12 luni)")
    print("=" * 80)
    print(f"Centroid parcela: lat={lat:.5f}, lon={lon:.5f}")
    print()

    df = compute_ndvi_timeseries(
        parcel_polygon=polygon,
        latitude=lat,
        longitude=lon,
        start_date="2025-05-23",
        end_date="2026-05-23",
        output_dir=output_dir,
        max_cloud_cover=30.0,
        skip_existing=True,
    )

    print(f"\n\nSerie temporala completa: {len(df)} puncte\n")
    print(df.to_string(index=False))

    # Salvam ca CSV pentru analiza ulterioara
    csv_path = PROJECT_ROOT / "data" / "ndvi" / "jidvei_ndvi_timeseries.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSerie salvata: {csv_path}")
