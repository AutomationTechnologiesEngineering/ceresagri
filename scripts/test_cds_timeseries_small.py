"""
Test minimal pentru ERA5-Land Time-series.
Cerem doar 1 luna pentru a verifica daca endpoint-ul si parametrii sunt corecti.
"""

import os
from pathlib import Path

import cdsapi
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

cds_url = os.getenv("CDS_URL")
cds_key = os.getenv("CDS_KEY")

client = cdsapi.Client(url=cds_url, key=cds_key)

output_path = PROJECT_ROOT / "data" / "ecmwf" / "test_timeseries_july2025.nc"
output_path.parent.mkdir(parents=True, exist_ok=True)

print("Test ERA5-Land Time-series pentru iulie 2025 (o luna)")
print("Variabila: doar 2m_temperature")
print("Locatie: Jidvei (46.19, 24.10)")
print()

try:
    client.retrieve(
        "reanalysis-era5-land-timeseries",
        {
            "variable": ["2m_temperature"],
            "location": {
                "latitude": 46.19,
                "longitude": 24.10,
            },
            "year": ["2025"],
            "month": ["07"],
            "day": [f"{d:02d}" for d in range(1, 32)],
            "time": [f"{h:02d}:00" for h in range(24)],
            "data_format": "netcdf",
        },
        str(output_path),
    )
    print(f"\nSUCCES! Fisier descarcat: {output_path}")
    print(f"Dimensiune: {output_path.stat().st_size / 1024:.1f} KB")
except Exception as e:
    print(f"\nEROARE: {type(e).__name__}: {e}")
