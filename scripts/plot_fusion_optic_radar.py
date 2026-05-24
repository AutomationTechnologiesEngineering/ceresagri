"""
Grafic combinat NDVI (Sentinel-2 optic) si VV (Sentinel-1 radar).

Demonstreaza fuziunea celor doua surse de date independente pentru
monitorizarea agricola complementara:
- NDVI: vegetatie verde / activitate fotosintetica
- VV (radar): umiditate sol + structura vegetatie + rugozitate

Cele doua surse au:
- Frecvente diferite de revisit (NDVI rar in iarna, radar constant)
- Sensibilitati diferite (NDVI pentru frunze, radar pentru sol+structura)
- Limitari complementare (NDVI eșueaza la nori, radar are zgomot speckle)
"""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


def plot_optic_radar_fusion(
    ndvi_csv: Path,
    s1_csv: Path,
    output_dir: Path,
    parcel_name: str = "Jidvei",
) -> None:
    """Genereaza grafic combinat NDVI + VV pentru aceeasi parcela."""

    # 1. Citim datele
    df_ndvi = pd.read_csv(ndvi_csv)
    df_ndvi["date"] = pd.to_datetime(df_ndvi["date"])

    df_s1 = pd.read_csv(s1_csv)
    df_s1["date"] = pd.to_datetime(df_s1["date"])

    print(f"NDVI: {len(df_ndvi)} observatii")
    print(f"S1:   {len(df_s1)} observatii")

    # 2. Cream figura cu doua axe Y suprapuse
    # (NDVI in stanga, VV in dreapta, scale diferite)
    fig, ax_ndvi = plt.subplots(figsize=(15, 8))

    # 3. Plotam NDVI pe axa Y stanga (verde)
    color_ndvi = "#2D5F2D"  # verde inchis
    ax_ndvi.set_xlabel("Data observatiei", fontsize=12, fontweight="bold")
    ax_ndvi.set_ylabel(
        "NDVI (Sentinel-2)",
        fontsize=12,
        color=color_ndvi,
        fontweight="bold",
    )
    ax_ndvi.plot(
        df_ndvi["date"],
        df_ndvi["ndvi_mean"],
        marker="o",
        markersize=7,
        linewidth=2,
        color=color_ndvi,
        label="NDVI mediu (optic, S2)",
        zorder=3,
    )
    ax_ndvi.fill_between(
        df_ndvi["date"],
        df_ndvi["ndvi_p25"],
        df_ndvi["ndvi_p75"],
        alpha=0.2,
        color=color_ndvi,
        zorder=2,
    )
    ax_ndvi.tick_params(axis="y", labelcolor=color_ndvi)
    ax_ndvi.set_ylim(-0.1, 1.0)
    ax_ndvi.grid(True, linestyle="--", alpha=0.3)

    # 4. Cream axa Y dreapta (radar)
    ax_s1 = ax_ndvi.twinx()
    color_s1 = "#1F4F9F"  # albastru inchis

    ax_s1.set_ylabel(
        "VV backscatter (Sentinel-1, dB)",
        fontsize=12,
        color=color_s1,
        fontweight="bold",
    )
    ax_s1.plot(
        df_s1["date"],
        df_s1["vv_mean_db"],
        marker="s",  # patrate pentru a diferentia vizual
        markersize=5,
        linewidth=1.5,
        color=color_s1,
        alpha=0.85,
        label="VV mediu (radar, S1)",
        zorder=3,
    )
    ax_s1.tick_params(axis="y", labelcolor=color_s1)
    ax_s1.set_ylim(-18, -6)  # plaja tipica pentru sol agricol

    # 5. Formatare axa X (datele)
    ax_ndvi.xaxis.set_major_locator(mdates.MonthLocator())
    ax_ndvi.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))

    # 6. Titlu
    plt.title(
        f"Fuziune optic + radar -- parcela viticola {parcel_name}\n"
        f"NDVI (verde, {len(df_ndvi)} obs.) suprapus peste VV (albastru, {len(df_s1)} obs.)  |  "
        f"perioada {df_ndvi['date'].min().strftime('%d %b %Y')} - "
        f"{df_ndvi['date'].max().strftime('%d %b %Y')}",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )

    # 7. Legenda combinata din ambele axe
    lines_ndvi, labels_ndvi = ax_ndvi.get_legend_handles_labels()
    lines_s1, labels_s1 = ax_s1.get_legend_handles_labels()
    ax_ndvi.legend(
        lines_ndvi + lines_s1,
        labels_ndvi + labels_s1,
        loc="upper right",
        fontsize=10,
        framealpha=0.95,
    )

    # 8. Subscriere obligatorie
    fig.text(
        0.5,
        0.01,
        "Contine date Copernicus Sentinel-1 si Sentinel-2 modificate, "
        "prelucrate de CeresAgri.\n"
        "Proiect cofinantat prin POCIDIF 2021-2027 -- "
        "Automation Technologies Engineering S.R.L.",
        ha="center",
        fontsize=9,
        style="italic",
        color="gray",
    )

    plt.tight_layout(rect=[0, 0.04, 1, 1])

    # 9. Salvam
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"fusion_optic_radar_{parcel_name.lower()}.pdf"
    png_path = output_dir / f"fusion_optic_radar_{parcel_name.lower()}.png"

    plt.savefig(pdf_path, dpi=200, bbox_inches="tight")
    plt.savefig(png_path, dpi=150, bbox_inches="tight")

    print("\nGrafic salvat:")
    print(f"  PDF: {pdf_path}")
    print(f"  PNG: {png_path}")

    plt.show()


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).parent.parent

    ndvi_csv = PROJECT_ROOT / "data" / "ndvi" / "jidvei_ndvi_timeseries.csv"
    s1_csv = PROJECT_ROOT / "data" / "sentinel1" / "jidvei_s1_timeseries.csv"
    figures_dir = PROJECT_ROOT / "data" / "figures"

    if not ndvi_csv.exists():
        print(f"EROARE: nu gasesc CSV-ul NDVI la {ndvi_csv}")
        exit(1)

    if not s1_csv.exists():
        print(f"EROARE: nu gasesc CSV-ul Sentinel-1 la {s1_csv}")
        exit(1)

    plot_optic_radar_fusion(ndvi_csv, s1_csv, figures_dir, parcel_name="Jidvei")
