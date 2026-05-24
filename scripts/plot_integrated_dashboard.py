"""
Grafic integrat final -- dashboard agro-climatic pentru parcela.

Combina toate componentele monitorizate intr-o singura figura cu 4 sub-paneluri:
1. NDVI (Sentinel-2) -- activitate vegetativa
2. VV radar (Sentinel-1) -- umiditate sol + structura
3. Precipitatii zilnice (ECMWF) -- input de apa
4. ET0 zilnic (Penman-Monteith) -- consum potential de apa
5. Balanta hidrica cumulativa -- starea sezonala

Aceasta este figura finala a prototipului TRL 3 CeresAgri.
"""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


def plot_integrated_dashboard(
    ndvi_csv: Path,
    s1_csv: Path,
    climate_et0_csv: Path,
    output_dir: Path,
    parcel_name: str = "Jidvei",
) -> None:
    """Genereaza dashboard-ul agro-climatic integrat."""

    # Citire date
    df_ndvi = pd.read_csv(ndvi_csv)
    df_ndvi["date"] = pd.to_datetime(df_ndvi["date"])

    df_s1 = pd.read_csv(s1_csv)
    df_s1["date"] = pd.to_datetime(df_s1["date"])

    df_climate = pd.read_csv(climate_et0_csv)
    df_climate["date"] = pd.to_datetime(df_climate["date"])

    print(f"NDVI:        {len(df_ndvi)} observatii")
    print(f"S1 radar:    {len(df_s1)} observatii")
    print(f"Climat+ET0:  {len(df_climate)} zile")

    # Figura cu 4 sub-paneluri verticale, axa X comuna
    fig, axes = plt.subplots(4, 1, figsize=(16, 14), sharex=True)
    fig.suptitle(
        f"CeresAgri -- dashboard integrat agro-climatic\n"
        f"Parcela viticola {parcel_name}, Podgoria Tarnave, Transilvania  |  "
        f"perioada {df_climate['date'].min().strftime('%d %b %Y')} - "
        f"{df_climate['date'].max().strftime('%d %b %Y')}",
        fontsize=15,
        fontweight="bold",
        y=0.995,
    )

    # --- Panel 1: NDVI ---
    ax = axes[0]
    ax.plot(
        df_ndvi["date"],
        df_ndvi["ndvi_mean"],
        marker="o",
        markersize=6,
        linewidth=1.8,
        color="#2D5F2D",
        label="NDVI mediu",
    )
    ax.fill_between(
        df_ndvi["date"],
        df_ndvi["ndvi_p25"],
        df_ndvi["ndvi_p75"],
        alpha=0.25,
        color="#2D5F2D",
    )
    ax.set_ylabel("NDVI\n(Sentinel-2)", fontsize=11, fontweight="bold")
    ax.set_ylim(-0.1, 1.0)
    ax.axhspan(0.6, 1.0, alpha=0.1, color="green")
    ax.axhspan(0.3, 0.6, alpha=0.1, color="yellow")
    ax.axhspan(-0.1, 0.3, alpha=0.1, color="orange")
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title("Activitate vegetativa (optic)", fontsize=11, loc="left", style="italic")

    # --- Panel 2: VV radar ---
    ax = axes[1]
    ax.plot(
        df_s1["date"],
        df_s1["vv_mean_db"],
        marker="s",
        markersize=4,
        linewidth=1.2,
        color="#1F4F9F",
        alpha=0.85,
        label="VV (dB)",
    )
    ax.set_ylabel("VV backscatter\n(Sentinel-1, dB)", fontsize=11, fontweight="bold")
    ax.set_ylim(-18, -6)
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title(
        "Umiditate sol + structura vegetatie (radar)", fontsize=11, loc="left", style="italic"
    )

    # --- Panel 3: Precipitatii ---
    ax = axes[2]
    ax.bar(
        df_climate["date"],
        df_climate["precipitation_mm"],
        width=1.0,
        color="#1F77B4",
        alpha=0.7,
        label="Precipitatii zilnice",
    )
    ax.set_ylabel("Precipitatii\n(mm/zi)", fontsize=11, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.3, axis="y")
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title("Input de apa (ECMWF ERA5-Land)", fontsize=11, loc="left", style="italic")

    # --- Panel 4: ET0 + balanta cumulativa ---
    ax = axes[3]
    ax.plot(
        df_climate["date"],
        df_climate["et0_mm"],
        color="#D62728",
        linewidth=1.2,
        alpha=0.6,
        label="ET0 zilnic (Penman-Monteith)",
    )
    ax.set_ylabel("ET0\n(mm/zi)", fontsize=11, fontweight="bold")
    ax.set_ylim(0, 8)
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.legend(loc="upper left", fontsize=9)

    # Axa secundara pentru balanta cumulativa
    ax2 = ax.twinx()
    ax2.plot(
        df_climate["date"],
        df_climate["water_balance_cumsum_mm"],
        color="#8B0000",
        linewidth=2.5,
        label="Balanta hidrica cumulativa",
    )
    ax2.axhline(y=0, color="black", linewidth=0.5, alpha=0.5)
    ax2.set_ylabel("Balanta cumulativa\n(mm)", fontsize=11, fontweight="bold", color="#8B0000")
    ax2.tick_params(axis="y", labelcolor="#8B0000")
    ax2.legend(loc="lower right", fontsize=9)

    ax.set_title(
        "Consum potential de apa + balanta hidrica cumulativa",
        fontsize=11,
        loc="left",
        style="italic",
    )

    # Formatare axa X (doar pe ultima axa, restul sunt shared)
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    axes[-1].set_xlabel("Data", fontsize=11, fontweight="bold")

    # Subscriere
    fig.text(
        0.5,
        0.005,
        "Contine date Copernicus Sentinel-1, Sentinel-2 si ECMWF ERA5-Land modificate, prelucrate de CeresAgri.  |  "
        "ET0 calculata prin FAO-56 Penman-Monteith.\n"
        "Proiect cofinantat prin POCIDIF 2021-2027 -- Automation Technologies Engineering S.R.L.",
        ha="center",
        fontsize=8,
        style="italic",
        color="gray",
    )

    plt.tight_layout(rect=[0, 0.02, 1, 0.99])

    # Salvare
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"dashboard_integrat_{parcel_name.lower()}.pdf"
    png_path = output_dir / f"dashboard_integrat_{parcel_name.lower()}.png"

    plt.savefig(pdf_path, dpi=200, bbox_inches="tight")
    plt.savefig(png_path, dpi=150, bbox_inches="tight")

    print("\nDashboard integrat salvat:")
    print(f"  PDF: {pdf_path}")
    print(f"  PNG: {png_path}")

    plt.show()


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).parent.parent

    ndvi_csv = PROJECT_ROOT / "data" / "ndvi" / "jidvei_ndvi_timeseries.csv"
    s1_csv = PROJECT_ROOT / "data" / "sentinel1" / "jidvei_s1_timeseries.csv"
    climate_et0_csv = PROJECT_ROOT / "data" / "ecmwf" / "jidvei_climate_et0.csv"
    figures_dir = PROJECT_ROOT / "data" / "figures"

    for csv in [ndvi_csv, s1_csv, climate_et0_csv]:
        if not csv.exists():
            print(f"EROARE: nu gasesc CSV-ul la {csv}")
            exit(1)

    plot_integrated_dashboard(ndvi_csv, s1_csv, climate_et0_csv, figures_dir, parcel_name="Jidvei")
