"""
Descarcare si procesare date meteorologice ECMWF ERA5-Land pentru o parcela.

Foloseste dataset-ul optimizat 'reanalysis-era5-land-timeseries' cu format
de output CSV -- mult mai simplu decat NetCDF si fara probleme de handles
pe Windows.

Variabile descarcate pentru calculul FAO-56 Penman-Monteith:
- 2m_temperature (t2m)               -- temperatura aerului la 2m (K)
- 2m_dewpoint_temperature (d2m)      -- punct de roua (pentru umiditate, K)
- 10m_u_component_of_wind (u10)      -- viteza vant N-S la 10m (m/s)
- 10m_v_component_of_wind (v10)      -- viteza vant E-V la 10m (m/s)
- surface_solar_radiation_downwards  -- radiatie solara (J/m2 orar)
- total_precipitation (tp)           -- precipitatii (m orar)

Rezolutie temporala: orara
Rezolutie spatiala: ~9 km
"""

import os
import zipfile
from pathlib import Path

import cdsapi
import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Incarcam .env din radacina proiectului
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_cds_client() -> cdsapi.Client:
    """Construieste clientul CDS folosind credentialele din .env."""
    cds_url = os.getenv("CDS_URL")
    cds_key = os.getenv("CDS_KEY")

    if not cds_url or not cds_key:
        raise RuntimeError(
            "CDS_URL sau CDS_KEY lipsesc din .env. "
            "Vezi instructiunile de inregistrare la "
            "https://cds.climate.copernicus.eu/"
        )

    return cdsapi.Client(url=cds_url, key=cds_key)


def download_era5_timeseries(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    output_path: Path,
) -> Path:
    """
    Descarca seria temporala ERA5-Land pentru un punct (format CSV).

    Endpoint-ul 'reanalysis-era5-land-timeseries' cu data_format='csv'
    returneaza un container ZIP cu unul sau mai multe fisiere CSV
    (cate unul per grup de variabile). Functia salveaza ZIP-ul brut --
    extragerea si combinarea se face in load_era5_csv_to_dataframe().

    Parametri:
        latitude, longitude: punctul de interes (centroidul parcelei)
        start_date, end_date: format "YYYY-MM-DD"
        output_path: unde salvam ZIP-ul descarcat

    Returneaza:
        Path catre fisierul ZIP descarcat.
    """
    client = get_cds_client()

    print("Descarcare ERA5-Land time-series (CSV):")
    print(f"  Punct: lat={latitude:.4f}, lon={longitude:.4f}")
    print(f"  Perioada: {start_date} -> {end_date}")
    print(f"  Output: {output_path}")
    print()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    client.retrieve(
        "reanalysis-era5-land-timeseries",
        {
            "variable": [
                "2m_temperature",
                "2m_dewpoint_temperature",
                "10m_u_component_of_wind",
                "10m_v_component_of_wind",
                "surface_solar_radiation_downwards",
                "total_precipitation",
            ],
            "location": {
                "latitude": latitude,
                "longitude": longitude,
            },
            "date": [f"{start_date}/{end_date}"],
            "data_format": "csv",
        },
        str(output_path),
    )

    return output_path


def load_era5_csv_to_dataframe(zip_path: Path) -> pd.DataFrame:
    """
    Incarca CSV-urile descarcate de CDS si le combina intr-un DataFrame.

    ECMWF returneaza un ZIP cu mai multe fisiere CSV, fiecare avand:
    - O coloana 'valid_time' (timestamp ISO)
    - Una sau mai multe coloane cu valorile variabilelor (in unitati SI)

    Functia detecteaza automat structura si combina totul pe axa temporala.
    """
    print(f"Citire fisier: {zip_path}")

    # Verificam ca este ZIP
    with open(zip_path, "rb") as f:
        first_bytes = f.read(4)

    if first_bytes != b"PK\x03\x04":
        # Nu este ZIP -- probabil este direct un CSV
        df = pd.read_csv(zip_path)
        df = _standardize_time_column(df)
        return df

    # Este ZIP -- extragem si combinam
    print("Fisierul este ZIP -- extragere si combinare CSV-uri...")

    all_data = {}

    with zipfile.ZipFile(zip_path, "r") as zf:
        csv_names = [name for name in zf.namelist() if name.endswith(".csv")]
        print(f"Fisiere CSV gasite in ZIP: {len(csv_names)}")

        for csv_name in csv_names:
            print(f"\n  Citire {csv_name}...")

            # pd.read_csv poate citi direct dintr-un ZIP via fileobj
            with zf.open(csv_name) as csv_file:
                df_part = pd.read_csv(csv_file)

            print(f"    Coloane: {list(df_part.columns)}")
            print(f"    Randuri: {len(df_part)}")

            # Standardizam numele coloanei de timp
            df_part = _standardize_time_column(df_part)

            # Setam timpul ca index pentru concatenare
            df_part = df_part.set_index("time")

            # Adaugam fiecare coloana de date in dict (excludem metadate)
            excluded = {
                "time",
                "valid_time",
                "latitude",
                "longitude",
                "lat",
                "lon",
                "number",
                "expver",
                "step",
            }
            for col in df_part.columns:
                if col not in excluded and col not in all_data:
                    all_data[col] = df_part[col]

    if not all_data:
        raise RuntimeError("Niciun camp de date gasit in CSV-urile extrase.")

    # Combinam toate seriile intr-un singur DataFrame
    df = pd.DataFrame(all_data).reset_index()
    df = df.rename(columns={"index": "time"})
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").reset_index(drop=True)

    print(f"\nDate orare incarcate: {len(df)} randuri")
    print(f"Coloane finale: {list(df.columns)}")

    # Verificare prezenta variabilelor necesare
    required = ["t2m", "d2m", "u10", "v10", "ssrd", "tp"]
    missing = [v for v in required if v not in df.columns]
    if missing:
        print(f"\nATENTIE: variabile lipsa: {missing}")
        print("Verifica structura CSV-urilor descarcate.")
    else:
        print("Toate variabilele necesare prezente.")

    return df


def _standardize_time_column(df: pd.DataFrame) -> pd.DataFrame:
    """Standardizeaza numele coloanei de timp la 'time'."""
    if "valid_time" in df.columns:
        df = df.rename(columns={"valid_time": "time"})
    elif "time" not in df.columns:
        # Cautam alta coloana de tip datetime
        for col in df.columns:
            if "time" in col.lower() or "date" in col.lower():
                df = df.rename(columns={col: "time"})
                break
    return df


def compute_daily_aggregates(df_hourly: pd.DataFrame) -> pd.DataFrame:
    """
    Agregam datele orare la nivel zilnic, in unitati agronomice.

    Conversii aplicate:
    - t2m si d2m: din Kelvin in Celsius (-273.15)
    - Temperaturi zilnice: min, max, medie
    - Umiditate relativa (RH): calculata din t2m si d2m
    - Vant: sqrt(u^2 + v^2), mediu zilnic
    - Radiatie solara: suma orara / 1e6 -> MJ/m2/zi
    - Precipitatii: suma orara * 1000 -> mm/zi
    """
    df = df_hourly.copy()

    # Convertire Kelvin -> Celsius
    df["t2m_C"] = df["t2m"] - 273.15
    df["d2m_C"] = df["d2m"] - 273.15

    # Magnitudinea vantului
    df["wind_speed"] = np.sqrt(df["u10"] ** 2 + df["v10"] ** 2)

    # Umiditate relativa din temperatura si punct de roua
    # Formula Magnus simplificata pentru presiunea de vapori (kPa)
    def vapor_pressure(t_celsius):
        return 0.6108 * np.exp(17.27 * t_celsius / (t_celsius + 237.3))

    es = vapor_pressure(df["t2m_C"])  # presiunea de saturatie
    ea = vapor_pressure(df["d2m_C"])  # presiunea actuala (la T_dew)
    df["RH"] = 100 * ea / es

    # Adaugam coloana de data (fara timp) pentru groupby
    df["date"] = pd.to_datetime(df["time"]).dt.date

    # Agregare zilnica
    daily = (
        df.groupby("date")
        .agg(
            t_min=("t2m_C", "min"),
            t_max=("t2m_C", "max"),
            t_mean=("t2m_C", "mean"),
            d_mean=("d2m_C", "mean"),
            rh_min=("RH", "min"),
            rh_max=("RH", "max"),
            rh_mean=("RH", "mean"),
            wind_mean=("wind_speed", "mean"),
            ssrd_total=("ssrd", "sum"),
            tp_total=("tp", "sum"),
        )
        .reset_index()
    )

    # Conversii finale
    # ssrd: J/m2 orar, sumat pe zi -> J/m2/zi. /1e6 -> MJ/m2/zi
    daily["solar_radiation_MJ"] = daily["ssrd_total"] / 1e6

    # tp: m orar, sumat pe zi -> m/zi. *1000 -> mm/zi
    daily["precipitation_mm"] = daily["tp_total"] * 1000

    # Datetime
    daily["date"] = pd.to_datetime(daily["date"])

    # Selectam coloanele finale utile pentru raport
    daily = daily[
        [
            "date",
            "t_min",
            "t_max",
            "t_mean",
            "d_mean",
            "rh_min",
            "rh_max",
            "rh_mean",
            "wind_mean",
            "solar_radiation_MJ",
            "precipitation_mm",
        ]
    ]

    print(f"Date agregate zilnic: {len(daily)} zile")
    return daily


# --- Self-test ---
if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).parent.parent

    # Coordonatele parcelei Jidvei
    JIDVEI_LAT = 46.19
    JIDVEI_LON = 24.10

    print("=" * 80)
    print("CeresAgri -- descarcare date meteo ERA5-Land pentru Jidvei (12 luni)")
    print("=" * 80)

    # Fisierul descarcat -- folosim extensia .zip ca sa fie clar ce e
    output_zip = PROJECT_ROOT / "data" / "ecmwf" / "jidvei_era5land_2025-05_2026-05.zip"

    if not output_zip.exists():
        download_era5_timeseries(
            latitude=JIDVEI_LAT,
            longitude=JIDVEI_LON,
            start_date="2025-05-23",
            end_date="2026-05-23",
            output_path=output_zip,
        )
    else:
        print(f"Fisier deja descarcat: {output_zip}")
        print("(daca vrei sa re-descarci, sterge fisierul si reruleaza)")

    # Procesare
    print("\nProcesare CSV-uri -> serie orara unificata...")
    df_hourly = load_era5_csv_to_dataframe(output_zip)

    print("\nAgregare orara -> zilnica...")
    df_daily = compute_daily_aggregates(df_hourly)

    # Salvam CSV-ul zilnic
    csv_path = PROJECT_ROOT / "data" / "ecmwf" / "jidvei_era5land_daily.csv"
    df_daily.to_csv(csv_path, index=False)
    print(f"\nDate zilnice salvate: {csv_path}")

    # Statistici de baza pentru verificare
    print("\nStatistici climatice anuale (Jidvei):")
    print(f"  Temperatura minima absoluta:    {df_daily['t_min'].min():.1f} C")
    print(f"  Temperatura maxima absoluta:    {df_daily['t_max'].max():.1f} C")
    print(f"  Temperatura medie anuala:       {df_daily['t_mean'].mean():.1f} C")
    print(f"  Precipitatii totale anuale:     {df_daily['precipitation_mm'].sum():.0f} mm")
    print(f"  Radiatie solara medie:          {df_daily['solar_radiation_MJ'].mean():.1f} MJ/m2/zi")
    print(f"  Vant mediu:                     {df_daily['wind_mean'].mean():.1f} m/s")
    print(f"  Umiditate relativa medie:       {df_daily['rh_mean'].mean():.0f}%")
