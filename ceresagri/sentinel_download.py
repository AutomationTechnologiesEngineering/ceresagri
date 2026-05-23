"""
Descarcare imagini Sentinel-2 procesate prin Sentinel Hub Process API.

Modulul cere serverului Sentinel Hub sa proceseze pixelii pentru o zona
(definita ca poligon GeoJSON) si o data specifica, si sa intoarca rezultatul
ca fisier GeoTIFF gata de afisare/analiza.

Spre deosebire de catalogul STAC (care intoarce doar metadate), aici primim
DATE PROPRIU-ZISE.
"""

# --- Importuri standard ---
import json
from pathlib import Path

# --- Importuri terta parte ---
# numpy: lucram cu pixeli ca matrici de numere
import numpy as np

# sentinelhub: API client
from sentinelhub import (
    CRS,
    BBox,
    DataCollection,
    MimeType,
    SentinelHubRequest,
    bbox_to_dimensions,
)

# shapely: pentru operatii pe poligoane (validare, reordonare colturi)
from shapely.geometry import Polygon, shape

# --- Importuri din modulele noastre ---
from ceresagri.sentinel_client import get_sentinelhub_config

# --- Constante ---
# Rezolutia pixelilor in metri.
# Sentinel-2 are benzi de 10m, 20m si 60m. Pentru RGB folosim 10m
# (rezolutia nativa a B02, B03, B04).
RESOLUTION_M = 10


# --- Evalscripts ---
# Acestea sunt mici programe JavaScript care ruleaza pe serverul Sentinel Hub.
# Triple-quote string permite multi-line in Python.

EVALSCRIPT_TRUE_COLOR_RGB = """
//VERSION=3
// Imagine color natural (ce vezi cu ochii).
// Benzile B04, B03, B02 = rosu, verde, albastru.
// Valorile sunt scalate intre 0 si 1 si apoi convertite la 0-255 pentru afisare.

function setup() {
    return {
        input: ["B04", "B03", "B02"],
        output: { bands: 3, sampleType: "UINT8" }
    };
}

function evaluatePixel(sample) {
    // Factor de "luminozitate" -- valorile Sentinel-2 sunt foarte mici,
    // le multiplicam ca sa vedem ceva.
    let gain = 2.5;
    return [
        Math.min(255, sample.B04 * 255 * gain),
        Math.min(255, sample.B03 * 255 * gain),
        Math.min(255, sample.B02 * 255 * gain)
    ];
}
"""


def load_parcel_geojson(geojson_path: Path) -> Polygon:
    """
    Incarca un fisier GeoJSON si intoarce primul poligon valid.

    Foloseste shapely pentru a valida si curata poligonul (de exemplu,
    reordoneaza colturile in sens antiorar daca e nevoie).
    """
    with open(geojson_path, encoding="utf-8") as f:
        data = json.load(f)

    # Luam prima geometrie din FeatureCollection
    if data.get("type") == "FeatureCollection":
        geometry_dict = data["features"][0]["geometry"]
    elif data.get("type") == "Feature":
        geometry_dict = data["geometry"]
    else:
        geometry_dict = data

    # Construim un obiect Polygon din shapely.
    # shapely face validare automata.
    polygon = shape(geometry_dict)

    # Daca colturile au fost date in sens gresit sau au incrucisari,
    # convex_hull le rearanjeaza intr-un poligon valid convex.
    # Pentru parcelele agricole reale, asta este aproape intotdeauna corect.
    polygon_clean = polygon.convex_hull

    return polygon_clean


def download_rgb_image(
    parcel_polygon: Polygon,
    date: str,
    output_path: Path,
    buffer_m: int = 200,
) -> dict:
    """
    Descarca o imagine RGB Sentinel-2 pentru parcela la data specificata.

    Parametri:
        parcel_polygon: poligonul parcelei (shapely Polygon, WGS84)
        date: data tinta in format "YYYY-MM-DD"
        output_path: unde sa salvam fisierul GeoTIFF
        buffer_m: cati metri sa adaugam in jurul parcelei (pentru context vizual)

    Intoarce dict cu metadate: path, dimensiuni, data.
    """
    # 1. Calculam bounding box-ul (dreptunghiul de inglobare) cu buffer
    # bounds intoarce (minx, miny, maxx, maxy) = (vest, sud, est, nord)
    minx, miny, maxx, maxy = parcel_polygon.bounds

    # Adaugam buffer in grade.
    # 1 grad latitudine ~ 111 km, deci 200 m = 0.0018 grade
    # 1 grad longitudine la lat 46 ~ 77 km, deci 200 m = 0.0026 grade
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

    # 2. Calculam dimensiunile imaginii in pixeli, in functie de rezolutie
    # Daca avem 1 km x 1 km la rezolutie 10m -> 100 x 100 pixeli
    size = bbox_to_dimensions(bbox, resolution=RESOLUTION_M)

    # 3. Configurarea cererii catre Sentinel Hub
    sh_config = get_sentinelhub_config()

    # Definim o fereastra temporala de +/- 1 zi in jurul datei tinta,
    # ca sa fim siguri ca prindem scena (orarele de pe satelit pot varia)
    time_interval = (f"{date}T00:00:00", f"{date}T23:59:59")

    request = SentinelHubRequest(
        evalscript=EVALSCRIPT_TRUE_COLOR_RGB,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A.define_from(
                    "s2l2a", service_url="https://sh.dataspace.copernicus.eu"
                ),
                time_interval=time_interval,
                # mosaicking_order: "leastCC" alege scena cu cele mai putine nori
                # daca exista mai multe in intervalul de timp
                mosaicking_order="leastCC",
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=size,
        config=sh_config,
    )

    # 4. Trimitem cererea si primim datele
    # get_data() intoarce o lista cu numpy arrays (de obicei 1 element)
    print(f"  Cerere catre Sentinel Hub pentru {date}...")
    response = request.get_data(save_data=False)

    if not response:
        raise RuntimeError(f"Niciun raspuns primit pentru data {date}")

    image_array = response[0]
    print(f"  Imagine primita: shape={image_array.shape}, dtype={image_array.dtype}")

    # 5. Salvam imaginea ca fisier
    # Pentru moment salvam ca PNG simplu (mai usor de afisat in notebook-uri)
    # In sesiunile urmatoare vom salva ca GeoTIFF cu georeferentiere
    from PIL import Image

    img = Image.fromarray(image_array)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)

    return {
        "path": str(output_path),
        "shape": image_array.shape,
        "date": date,
        "bbox_wgs84": bbox.geometry.bounds,
    }


# --- Self-test ---
if __name__ == "__main__":
    print("=" * 80)
    print("CeresAgri -- descarcare prima imagine RGB pentru parcela Jidvei")
    print("=" * 80)

    # Calea catre parcela noastra de test
    PROJECT_ROOT = Path(__file__).parent.parent
    parcel_path = PROJECT_ROOT / "data" / "parcels" / "jidvei_test_parcel.geojson"

    # Verificam ca exista
    if not parcel_path.exists():
        print(f"EROARE: nu gasesc parcela la {parcel_path}")
        exit(1)

    # Incarcam parcela
    print(f"\nIncarc parcela din: {parcel_path}")
    polygon = load_parcel_geojson(parcel_path)
    print(f"Poligon valid: {polygon.is_valid}")
    print(f"Suprafata aproximativa: {polygon.area * 111000 * 111000:.0f} mp")
    print(f"Bounds: {polygon.bounds}")

    # Alegem o scena -- una din lista ta din sesiunea precedenta
    # Scena #15 din lista ta: 2025-08-30, 0% nori (vara, varf vegetativ)
    target_date = "2025-08-30"

    output_path = PROJECT_ROOT / "data" / "images" / f"jidvei_rgb_{target_date}.png"

    print(f"\nData tinta: {target_date}")
    print(f"Output: {output_path}")

    try:
        result = download_rgb_image(
            parcel_polygon=polygon,
            date=target_date,
            output_path=output_path,
            buffer_m=200,
        )

        print(f"\nSUCCES! Imagine salvata la: {result['path']}")
        print(f"Dimensiuni: {result['shape']}")
        print("\nDeschide imaginea in VS Code (dublu-click pe fisier) ca sa o vezi.")

    except Exception as e:
        print(f"\nEROARE: {e}")
        import traceback

        traceback.print_exc()
