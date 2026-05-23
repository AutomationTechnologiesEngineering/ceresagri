"""
Client pentru Sentinel Hub si Copernicus Data Space Ecosystem.

Acest modul incapsuleaza:
1. Autentificarea OAuth2 la Sentinel Hub (face automat refresh la token)
2. Interogarea catalogului STAC pentru a gasi scene Sentinel-2 disponibile
3. Filtrarea dupa zona geografica, perioada temporala si acoperire de nori

Restul codului va folosi acest modul ca interfata unica spre Copernicus.
"""

# --- Importuri standard Python ---
from datetime import datetime
from typing import Any

# --- Importuri din sentinelhub-py ---
# SHConfig: contine credentialele si setarile clientului
# SentinelHubCatalog: clientul pentru catalogul STAC
# DataCollection: enum cu toate misiunile suportate (Sentinel-1, 2, 3, etc.)
# BBox, CRS: pentru a defini o zona geografica
from sentinelhub import CRS, BBox, DataCollection, SentinelHubCatalog, SHConfig

# --- Importuri din modulele noastre ---
# Importam credentialele din modulul de configurare creat in Sesiunea 1.
# Asa avem un singur loc unde se citesc -- principiul "single source of truth".
from ceresagri import config


def get_sentinelhub_config() -> SHConfig:
    """
    Construieste obiectul SHConfig folosit de toate apelurile catre Sentinel Hub.

    Punct important: Copernicus Data Space Ecosystem (CDSE) foloseste URL-uri
    DIFERITE fata de Sentinel Hub-ul comercial istoric. Trebuie sa setam explicit
    aceste URL-uri, altfel clientul va incerca sa contacteze serverele vechi
    si vom primi erori obscure.
    """
    sh_config = SHConfig()
    sh_config.sh_client_id = config.SH_CLIENT_ID
    sh_config.sh_client_secret = config.SH_CLIENT_SECRET

    # URL-urile oficiale ale CDSE -- sunt diferite de cele Sentinel Hub clasic
    sh_config.sh_token_url = (
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    )
    sh_config.sh_base_url = "https://sh.dataspace.copernicus.eu"

    return sh_config


def search_sentinel2_scenes(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    max_cloud_cover: float = 100.0,
    buffer_degrees: float = 0.01,
) -> list[dict[str, Any]]:
    """
    Cauta scene Sentinel-2 L2A disponibile peste un punct geografic.

    Parametri:
        latitude: latitudinea punctului central (de ex. 46.22 pentru Jidvei)
        longitude: longitudinea punctului central (de ex. 24.13)
        start_date: data de inceput in format "YYYY-MM-DD"
        end_date: data de sfarsit in format "YYYY-MM-DD"
        max_cloud_cover: procentul maxim de nori acceptat (0-100). Default 100
                         inseamna "ia tot, filtram dupa".
        buffer_degrees: dimensiunea zonei de cautare in grade (cca 1 km = 0.01 grade).
                        Default 0.01 inseamna o zona de aprox. 1x1 km in jurul punctului.

    Intoarce:
        Lista de scene, fiecare ca dictionar cu metadate:
        - id, datetime, cloud_cover, bbox
    """
    # 1. Construim config-ul Sentinel Hub
    sh_config = get_sentinelhub_config()

    # 2. Definim zona geografica de cautare ca un dreptunghi (BBox)
    # CRS.WGS84 inseamna ca coordonatele sunt in latitudine/longitudine standard
    # (ce gasesti in Google Maps).
    bbox = BBox(
        bbox=(
            longitude - buffer_degrees,  # vest
            latitude - buffer_degrees,  # sud
            longitude + buffer_degrees,  # est
            latitude + buffer_degrees,  # nord
        ),
        crs=CRS.WGS84,
    )

    # 3. Construim clientul de catalog STAC
    catalog = SentinelHubCatalog(config=sh_config)

    # 4. Interogam catalogul.
    # Sentinel-2 L2A inseamna nivelul de procesare 2A (corectie atmosferica facuta).
    # Asta e ce vrem pentru aplicatii agricole -- date "gata de folosit".
    search_iterator = catalog.search(
        collection=DataCollection.SENTINEL2_L2A,
        bbox=bbox,
        time=(start_date, end_date),
        # Filtru pentru procentul de nori, folosind sintaxa CQL2 a STAC
        filter=f"eo:cloud_cover < {max_cloud_cover}",
        fields={
            # Cerem doar campurile care ne intereseaza, sa nu primim payload mare
            "include": [
                "id",
                "properties.datetime",
                "properties.eo:cloud_cover",
                "bbox",
            ],
            "exclude": [],
        },
    )

    # 5. Iteram prin rezultate si construim o lista usor de folosit
    scenes = []
    for item in search_iterator:
        scenes.append(
            {
                "id": item["id"],
                "datetime": item["properties"]["datetime"],
                "cloud_cover": item["properties"].get("eo:cloud_cover", -1),
                "bbox": item["bbox"],
            }
        )

    # 6. Sortam cronologic (cele mai recente primele)
    scenes.sort(key=lambda x: x["datetime"], reverse=True)

    return scenes


def print_scenes_summary(scenes: list[dict[str, Any]]) -> None:
    """Afiseaza o lista de scene intr-un format usor de citit."""
    if not scenes:
        print("Nicio scena gasita.")
        return

    print(f"\nGasite {len(scenes)} scene Sentinel-2 L2A:")
    print("-" * 80)
    print(f"{'#':<4} {'Data':<20} {'Nori (%)':<10} {'ID scena':<50}")
    print("-" * 80)

    for i, scene in enumerate(scenes, start=1):
        # Formatam data ca sa fie usor de citit
        dt = datetime.fromisoformat(scene["datetime"].replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d %H:%M")

        # Formatam procentul de nori
        cc = scene["cloud_cover"]
        cc_str = f"{cc:.1f}" if cc >= 0 else "N/A"

        print(f"{i:<4} {date_str:<20} {cc_str:<10} {scene['id']:<50}")

    print("-" * 80)


# --- Self-test cand rulam direct ---
if __name__ == "__main__":
    print("=" * 80)
    print("CeresAgri -- test interogare catalog Sentinel-2 pentru Jidvei")
    print("=" * 80)

    # Coordonatele podgoriei alese: lat 46.22, lon 24.13 (zona Jidvei, Transilvania)
    JIDVEI_LAT = 46.22
    JIDVEI_LON = 24.13

    # Cautam scenele din ultimul an (12 luni inapoi)
    print(f"\nLocatie: lat={JIDVEI_LAT}, lon={JIDVEI_LON}")
    print("Perioada: 2025-05-23 - 2026-05-23 (ultimul an)")
    print("Filtru nori: maxim 30%")
    print("\nInterogare in curs...")

    try:
        scenes = search_sentinel2_scenes(
            latitude=JIDVEI_LAT,
            longitude=JIDVEI_LON,
            start_date="2025-05-23",
            end_date="2026-05-23",
            max_cloud_cover=30.0,
        )

        print_scenes_summary(scenes)

        # Statistici simple
        if scenes:
            cloud_covers = [s["cloud_cover"] for s in scenes if s["cloud_cover"] >= 0]
            if cloud_covers:
                print(f"\nStatistici acoperire nori (din {len(cloud_covers)} scene):")
                print(f"  Minim:  {min(cloud_covers):.1f}%")
                print(f"  Maxim:  {max(cloud_covers):.1f}%")
                print(f"  Mediu:  {sum(cloud_covers) / len(cloud_covers):.1f}%")

    except Exception as e:
        print(f"\nEROARE: {e}")
        print(f"Tip eroare: {type(e).__name__}")
        import traceback

        traceback.print_exc()
