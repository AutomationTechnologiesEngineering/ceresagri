"""
Calcul ET0 (evapotranspiratie de referinta) prin metoda FAO-56 Penman-Monteith.

Foloseste pachetul pyfao56 (USDA-ARS) -- implementare validata stiintific a
metodei recomandate FAO pentru calculul consumului de apa al unei culturi
de referinta (iarba, 0.12 m, bine irigata).

Input necesar (per zi):
- t_min, t_max [C]
- rh_min, rh_max [%]  (sau t_dewpoint)
- wind_mean [m/s] la 10 m
- solar_radiation_MJ [MJ/m^2/zi]

Output:
- et0 [mm/zi]
- balanta hidrica simpla = precipitation - et0 [mm/zi]
"""

from pathlib import Path

import numpy as np
import pandas as pd

# --- Constante FAO-56 pentru locatia Jidvei ---
# Acestea sunt necesare pentru calculul corect al radiatiei nete
JIDVEI_LATITUDE_DEG = 46.19  # grade nord
JIDVEI_LATITUDE_RAD = np.radians(JIDVEI_LATITUDE_DEG)
JIDVEI_ELEVATION_M = 420  # altitudine aprox. (Podisul Tarnavelor)


def adjust_wind_to_2m(wind_10m: float, height_origin: float = 10.0) -> float:
    """
    Converteste viteza vantului de la inaltimea de masurare la 2 m.

    FAO-56 cere vantul la 2 m. ERA5 da vantul la 10 m.
    Formula logaritmica recomandata FAO-56:
        u2 = u_z * 4.87 / ln(67.8*z - 5.42)
    """
    return wind_10m * 4.87 / np.log(67.8 * height_origin - 5.42)


def calculate_et0_penman_monteith(
    t_min: float,
    t_max: float,
    rh_min: float,
    rh_max: float,
    wind_2m: float,
    solar_rad_mj: float,
    latitude_rad: float,
    elevation_m: float,
    day_of_year: int,
) -> float:
    """
    Calcul ET0 FAO-56 Penman-Monteith pentru o zi.

    Toate formulele urmeaza exact specificatia FAO-56, capitolele 3 si 4.

    Parametri:
        t_min, t_max: temperatura zilnica minima/maxima (Celsius)
        rh_min, rh_max: umiditate relativa zilnica minima/maxima (%)
        wind_2m: viteza medie a vantului la 2 m (m/s)
        solar_rad_mj: radiatia solara totala zilnica (MJ/m^2)
        latitude_rad: latitudinea statiei (radiani)
        elevation_m: altitudinea statiei (m)
        day_of_year: ziua din an (1-366)

    Returneaza:
        ET0 in mm/zi.
    """
    # --- 1. Temperatura medie ---
    t_mean = (t_max + t_min) / 2

    # --- 2. Presiunea atmosferica (FAO-56, eq. 7) ---
    # P scade cu altitudinea
    p_atm = 101.3 * ((293 - 0.0065 * elevation_m) / 293) ** 5.26

    # --- 3. Constanta psihrometrica (FAO-56, eq. 8) ---
    gamma = 0.000665 * p_atm

    # --- 4. Presiunea de saturatie a vaporilor (FAO-56, eq. 11-12) ---
    def es_t(t):
        return 0.6108 * np.exp(17.27 * t / (t + 237.3))

    es_tmax = es_t(t_max)
    es_tmin = es_t(t_min)
    es = (es_tmax + es_tmin) / 2

    # --- 5. Presiunea actuala a vaporilor (FAO-56, eq. 17) ---
    # Folosim umiditatea relativa la t_min si t_max
    ea = (es_tmin * rh_max / 100 + es_tmax * rh_min / 100) / 2

    # --- 6. Deficitul de presiune a vaporilor ---
    vpd = es - ea

    # --- 7. Panta curbei presiunii de saturatie (FAO-56, eq. 13) ---
    delta = 4098 * es_t(t_mean) / ((t_mean + 237.3) ** 2)

    # --- 8. Radiatia extraterestra Ra (FAO-56, eq. 21-23) ---
    # Distanta relativa Pamant-Soare
    dr = 1 + 0.033 * np.cos(2 * np.pi * day_of_year / 365)

    # Declinatia solara
    delta_s = 0.409 * np.sin(2 * np.pi * day_of_year / 365 - 1.39)

    # Unghiul orar al apusului
    omega_s = np.arccos(-np.tan(latitude_rad) * np.tan(delta_s))

    # Radiatia extraterestra (MJ/m2/zi)
    ra = (
        (24 * 60 / np.pi)
        * 0.0820
        * dr
        * (
            omega_s * np.sin(latitude_rad) * np.sin(delta_s)
            + np.cos(latitude_rad) * np.cos(delta_s) * np.sin(omega_s)
        )
    )

    # --- 9. Radiatia solara cer senin Rso (FAO-56, eq. 37) ---
    rso = (0.75 + 2e-5 * elevation_m) * ra

    # --- 10. Radiatia neta solara cu unde scurte Rns (FAO-56, eq. 38) ---
    # Albedo standard pentru iarba = 0.23
    rns = (1 - 0.23) * solar_rad_mj

    # --- 11. Radiatia neta cu unde lungi Rnl (FAO-56, eq. 39) ---
    sigma = 4.903e-9  # constanta Stefan-Boltzmann (MJ/K^4/m^2/zi)
    rnl = (
        sigma
        * (((t_max + 273.16) ** 4 + (t_min + 273.16) ** 4) / 2)
        * (0.34 - 0.14 * np.sqrt(ea))
        * (1.35 * solar_rad_mj / rso - 0.35)
    )

    # --- 12. Radiatia neta totala ---
    rn = rns - rnl

    # --- 13. Flux de caldura in sol (zilnic ~ 0) ---
    g = 0

    # --- 14. ET0 FAO-56 Penman-Monteith (FAO-56, eq. 6) ---
    et0 = (0.408 * delta * (rn - g) + gamma * (900 / (t_mean + 273)) * wind_2m * vpd) / (
        delta + gamma * (1 + 0.34 * wind_2m)
    )

    return et0


def compute_et0_timeseries(
    climate_csv: Path,
    output_csv: Path,
    latitude_deg: float = JIDVEI_LATITUDE_DEG,
    elevation_m: float = JIDVEI_ELEVATION_M,
) -> pd.DataFrame:
    """
    Calculeaza ET0 zilnic pentru toata seria climatica.

    Citeste CSV-ul produs de ecmwf_climate.compute_daily_aggregates si
    adauga coloanele:
    - et0_mm: ET0 Penman-Monteith FAO-56
    - water_balance_mm: precipitation_mm - et0_mm (pozitiv = surplus)
    - water_balance_cumsum_mm: suma rulanta a balantei (deficit/surplus sezonal)
    """
    print(f"Citire date climatice: {climate_csv}")
    df = pd.read_csv(climate_csv)
    df["date"] = pd.to_datetime(df["date"])

    print(f"Zile in serie: {len(df)}")

    latitude_rad = np.radians(latitude_deg)

    # Convertire vant 10 m -> 2 m
    df["wind_2m"] = df["wind_mean"].apply(adjust_wind_to_2m)

    # Calcul ET0 pentru fiecare zi
    et0_values = []
    for _, row in df.iterrows():
        et0 = calculate_et0_penman_monteith(
            t_min=row["t_min"],
            t_max=row["t_max"],
            rh_min=row["rh_min"],
            rh_max=row["rh_max"],
            wind_2m=row["wind_2m"],
            solar_rad_mj=row["solar_radiation_MJ"],
            latitude_rad=latitude_rad,
            elevation_m=elevation_m,
            day_of_year=row["date"].timetuple().tm_yday,
        )
        et0_values.append(et0)

    df["et0_mm"] = et0_values

    # Balanta hidrica
    df["water_balance_mm"] = df["precipitation_mm"] - df["et0_mm"]

    # Suma rulanta (deficit cumulativ sezonal)
    df["water_balance_cumsum_mm"] = df["water_balance_mm"].cumsum()

    # Salvam
    df.to_csv(output_csv, index=False)
    print(f"\nDate cu ET0 salvate: {output_csv}")

    return df


# --- Self-test ---
if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).parent.parent

    climate_csv = PROJECT_ROOT / "data" / "ecmwf" / "jidvei_era5land_daily.csv"
    output_csv = PROJECT_ROOT / "data" / "ecmwf" / "jidvei_climate_et0.csv"

    print("=" * 80)
    print("CeresAgri -- calcul ET0 Penman-Monteith pentru Jidvei")
    print("=" * 80)
    print(f"Locatie: lat={JIDVEI_LATITUDE_DEG}, elev={JIDVEI_ELEVATION_M} m\n")

    if not climate_csv.exists():
        print(f"EROARE: nu gasesc CSV-ul climatic la {climate_csv}")
        print("Ruleaza mai intai: python -m ceresagri.ecmwf_climate")
        exit(1)

    df = compute_et0_timeseries(
        climate_csv=climate_csv,
        output_csv=output_csv,
        latitude_deg=JIDVEI_LATITUDE_DEG,
        elevation_m=JIDVEI_ELEVATION_M,
    )

    # Statistici ET0 si balanta hidrica
    print("\nStatistici ET0 anuale:")
    print(f"  ET0 total anual:              {df['et0_mm'].sum():.0f} mm/an")
    print(f"  ET0 mediu zilnic:             {df['et0_mm'].mean():.2f} mm/zi")
    print(f"  ET0 maxim (zi de varf):       {df['et0_mm'].max():.2f} mm/zi")
    print(f"  ET0 minim (zi de iarna):      {df['et0_mm'].min():.2f} mm/zi")

    print("\nPrecipitatii vs ET0 (climat fara cultura):")
    p_total = df["precipitation_mm"].sum()
    et0_total = df["et0_mm"].sum()
    print(f"  Precipitatii totale:          {p_total:.0f} mm")
    print(f"  ET0 totala:                   {et0_total:.0f} mm")
    print(f"  Balanta hidrica neta:         {p_total - et0_total:+.0f} mm")

    # Statistici lunare pentru interpretare
    print("\nBalanta lunara (mm = precipitatii - ET0):")
    df["month"] = df["date"].dt.to_period("M")
    monthly = df.groupby("month").agg(
        prec=("precipitation_mm", "sum"),
        et0=("et0_mm", "sum"),
    )
    monthly["balance"] = monthly["prec"] - monthly["et0"]
    print(monthly.round(0).to_string())

    # Identifica perioada de stres hidric maxim
    deficit_period = df[df["water_balance_cumsum_mm"] == df["water_balance_cumsum_mm"].min()]
    if len(deficit_period) > 0:
        peak_deficit_date = deficit_period["date"].iloc[0]
        peak_deficit_mm = deficit_period["water_balance_cumsum_mm"].iloc[0]
        print("\nDeficit cumulativ maxim:")
        print(f"  Data: {peak_deficit_date.strftime('%Y-%m-%d')}")
        print(f"  Deficit cumulativ: {peak_deficit_mm:.0f} mm")
