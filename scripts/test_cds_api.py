"""Test rapid de conectivitate la CDS API."""

import os
from pathlib import Path

# Citim .env din radacina proiectului
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Verificam ca credentialele exista in mediul curent
cds_url = os.getenv("CDS_URL")
cds_key = os.getenv("CDS_KEY")

print(f"CDS_URL: {cds_url}")
print(f"CDS_KEY: {cds_key[:10]}..." if cds_key else "CDS_KEY: LIPSESTE!")

if not cds_url or not cds_key:
    print("\nEROARE: CDS_URL sau CDS_KEY lipsesc din .env")
    exit(1)

# Initializam clientul CDS
import cdsapi

# Cdsapi citeste credentialele dintr-un fisier .cdsapirc sau din variabile de mediu
# Le pasam explicit pentru claritate
client = cdsapi.Client(url=cds_url, key=cds_key)

print("\nClient CDS initializat cu succes.")
print("Pasul urmator: descarcam un mic test din ERA5-Land.")

# Descarcam doar o zi din ERA5-Land pentru zona Jidvei
# Doar variabila temperatura la 2m, ca test rapid
test_output = PROJECT_ROOT / "data" / "ecmwf" / "test_era5_land_jidvei.nc"
test_output.parent.mkdir(parents=True, exist_ok=True)

# Coordonatele parcelei Jidvei (lat, lon)
# Pentru ERA5-Land, definim un dreptunghi mic in jurul parcelei
# Format: [Nord, Vest, Sud, Est]
JIDVEI_LAT = 46.19
JIDVEI_LON = 24.10
buffer = 0.1  # ~11 km buffer

bbox = [
    JIDVEI_LAT + buffer,  # Nord
    JIDVEI_LON - buffer,  # Vest
    JIDVEI_LAT - buffer,  # Sud
    JIDVEI_LON + buffer,  # Est
]

print(f"\nDescarcare test ERA5-Land pentru bbox: {bbox}")
print("(o singura zi -- 1 august 2025 -- variabila 2m_temperature)")
print("Durata estimata: 1-3 minute")

try:
    client.retrieve(
        "reanalysis-era5-land",
        {
            "variable": "2m_temperature",
            "year": "2025",
            "month": "08",
            "day": "01",
            "time": ["00:00", "06:00", "12:00", "18:00"],
            "area": bbox,
            "format": "netcdf",
        },
        str(test_output),
    )

    file_size_mb = test_output.stat().st_size / (1024 * 1024)
    print(f"\nSUCCES! Fisier descarcat: {test_output}")
    print(f"Dimensiune: {file_size_mb:.2f} MB")

except Exception as e:
    print(f"\nEROARE: {e}")
    print("\nVerificari posibile:")
    print(
        "1. Ai acceptat termenii ERA5-Land la https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land"
    )
    print("2. UID si API key sunt corecte in .env")
    print("3. Format CDS_KEY: 'UID:KEY' (fara ghilimele, fara spatii)")
    import traceback

    traceback.print_exc()
