"""
Generare grafic serie temporala NDVI pentru parcela.

Output:
- PDF de inalta rezolutie pentru anexa POCIDIF
- PNG pentru afisare web
"""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


def plot_ndvi_timeseries(csv_path: Path, output_dir: Path, parcel_name: str = "Jidvei") -> None:
    """Genereaza graficul fenologic anual al unei parcele."""

    # 1. Citim datele
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])

    # 2. Pregatim figura
    fig, ax = plt.subplots(figsize=(14, 8))

    # 3. Adaugam zonele de interpretare ca benzi colorate de fundal
    # (vegetatie densa = verde, moderata = galben, sol = portocaliu, etc.)
    zones = [
        (-0.2, 0.1, "#FFE4D4", "Sol gol / zapada"),
        (0.1, 0.3, "#FFD4A8", "Vegetatie rara"),
        (0.3, 0.6, "#FFF4B8", "Vegetatie moderata"),
        (0.6, 0.8, "#D4F4D4", "Vegetatie densa"),
        (0.8, 1.0, "#A8E4A8", "Varf vegetativ"),
    ]
    for ymin, ymax, color, _label in zones:
        ax.axhspan(ymin, ymax, facecolor=color, alpha=0.4, zorder=0)

    # 4. Plotam intervalul interquartilic (intre P25 si P75) ca banda
    # Asta arata variabilitatea SPATIALA in cadrul parcelei
    ax.fill_between(
        df["date"],
        df["ndvi_p25"],
        df["ndvi_p75"],
        alpha=0.3,
        color="darkgreen",
        label="Interval interquartilic (P25-P75)",
        zorder=2,
    )

    # 5. Plotam media NDVI ca linie continua cu puncte
    ax.plot(
        df["date"],
        df["ndvi_mean"],
        marker="o",
        markersize=8,
        markerfacecolor="darkgreen",
        markeredgecolor="white",
        markeredgewidth=1.5,
        linewidth=2,
        color="darkgreen",
        label="NDVI mediu per parcela",
        zorder=3,
    )

    # 6. Adnotam scena cu zapada (NDVI minim)
    min_idx = df["ndvi_mean"].idxmin()
    min_row = df.iloc[min_idx]
    ax.annotate(
        f"NDVI min: {min_row['ndvi_mean']:.2f}\n(zapada -- {min_row['date'].strftime('%d %b %Y')})",
        xy=(min_row["date"], min_row["ndvi_mean"]),
        xytext=(20, 30),
        textcoords="offset points",
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="gray"),
        arrowprops=dict(arrowstyle="->", color="gray"),
    )

    # 7. Adnotam scena cu varf vegetativ (NDVI maxim)
    max_idx = df["ndvi_mean"].idxmax()
    max_row = df.iloc[max_idx]
    ax.annotate(
        f"NDVI max: {max_row['ndvi_mean']:.2f}\n(varf -- {max_row['date'].strftime('%d %b %Y')})",
        xy=(max_row["date"], max_row["ndvi_mean"]),
        xytext=(-100, -50),
        textcoords="offset points",
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="gray"),
        arrowprops=dict(arrowstyle="->", color="gray"),
    )

    # 8. Formatare axe
    ax.set_xlabel("Data observatiei", fontsize=12, fontweight="bold")
    ax.set_ylabel("NDVI (Normalized Difference Vegetation Index)", fontsize=12, fontweight="bold")
    ax.set_title(
        f"Dinamica fenologica anuala -- parcela viticola {parcel_name}\n"
        f"Sursa: Sentinel-2 L2A prin Copernicus Data Space Ecosystem  |  "
        f"{len(df)} observatii peste 12 luni",
        fontsize=14,
        fontweight="bold",
        pad=15,
    )

    # Formatare axa X (datele) -- afisam cate o eticheta pe luna
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.set_ylim(-0.1, 1.0)

    # Grila pentru lizibilitate
    ax.grid(True, linestyle="--", alpha=0.3, zorder=1)
    ax.set_axisbelow(True)

    # Legenda
    ax.legend(loc="upper left", fontsize=10, framealpha=0.95)

    # 9. Subscriere obligatorie (atribuire Copernicus)
    fig.text(
        0.5,
        0.01,
        "Contine date Copernicus Sentinel modificate, prelucrate de CeresAgri.\n"
        "Proiect cofinantat prin POCIDIF 2021-2027 -- Automation Technologies Engineering S.R.L.",
        ha="center",
        fontsize=9,
        style="italic",
        color="gray",
    )

    plt.tight_layout(rect=[0, 0.04, 1, 1])

    # 10. Salvam
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"ndvi_timeseries_{parcel_name.lower()}.pdf"
    png_path = output_dir / f"ndvi_timeseries_{parcel_name.lower()}.png"

    plt.savefig(pdf_path, dpi=200, bbox_inches="tight")
    plt.savefig(png_path, dpi=150, bbox_inches="tight")

    print("Grafic salvat:")
    print(f"  PDF: {pdf_path}")
    print(f"  PNG: {png_path}")

    plt.show()


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).parent.parent
    csv_path = PROJECT_ROOT / "data" / "ndvi" / "jidvei_ndvi_timeseries.csv"
    figures_dir = PROJECT_ROOT / "data" / "figures"

    if not csv_path.exists():
        print(f"EROARE: nu gasesc CSV-ul la {csv_path}")
        exit(1)

    plot_ndvi_timeseries(csv_path, figures_dir, parcel_name="Jidvei")
