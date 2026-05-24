"""
Script rapid pentru vizualizarea unui fisier NDVI TIFF.

Folosire:
    python scripts/quick_ndvi_view.py [calea_catre_tiff]

Daca nu e specificata calea, foloseste implicit fisierul nostru de test.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio


def visualize_ndvi(tiff_path: Path) -> None:
    """Vizualizeaza un fisier NDVI cu colormap specific."""

    # 1. Citim fisierul TIFF
    with rasterio.open(tiff_path) as src:
        ndvi = src.read(1)  # citim banda 1 (NDVI)
        bounds = src.bounds
        crs = src.crs

    # 2. Cream figura
    fig, ax = plt.subplots(figsize=(10, 9))

    # 3. Afisam harta cu colormap "RdYlGn" (Rosu-Galben-Verde)
    # vmin=-0.2, vmax=1.0 fixeaza scala intre valorile rezonabile pentru NDVI
    img = ax.imshow(
        ndvi,
        cmap="RdYlGn",
        vmin=-0.2,
        vmax=1.0,
        extent=[bounds.left, bounds.right, bounds.bottom, bounds.top],
    )

    # 4. Adaugam colorbar
    cbar = plt.colorbar(img, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("NDVI (Normalized Difference Vegetation Index)", fontsize=11)
    cbar.ax.tick_params(labelsize=10)

    # 5. Adaugam linii de referinta pe colorbar pentru interpretare
    for value, label in [(0.0, "sol gol"), (0.3, "moderat"), (0.6, "dens"), (0.8, "varf")]:
        cbar.ax.axhline(y=value, color="black", linewidth=0.5, alpha=0.5)

    # 6. Titlu si etichete
    date_str = tiff_path.stem.replace("jidvei_ndvi_", "")
    ax.set_title(
        f"NDVI parcela viticola Jidvei -- {date_str}",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("Longitudine (grade E)", fontsize=10)
    ax.set_ylabel("Latitudine (grade N)", fontsize=10)

    # 7. Subscriere obligatorie pentru atribuirea Copernicus
    fig.text(
        0.5,
        0.02,
        "Contine date Copernicus Sentinel modificate, prelucrate de CeresAgri.",
        ha="center",
        fontsize=8,
        style="italic",
        color="gray",
    )

    # 8. Statistici afisate ca text in figura
    valid_mask = ~np.isnan(ndvi)
    if valid_mask.any():
        mean = float(np.nanmean(ndvi))
        ax.text(
            0.02,
            0.98,
            f"NDVI mediu: {mean:.3f}\n"
            f"NDVI min:   {float(np.nanmin(ndvi)):.3f}\n"
            f"NDVI max:   {float(np.nanmax(ndvi)):.3f}",
            transform=ax.transAxes,
            verticalalignment="top",
            bbox=dict(facecolor="white", alpha=0.85, edgecolor="gray"),
            family="monospace",
            fontsize=10,
        )

    plt.tight_layout()

    # 9. Salvam ca PNG si afisam
    output_png = tiff_path.parent / f"{tiff_path.stem}_visualized.png"
    plt.savefig(output_png, dpi=150, bbox_inches="tight")
    print(f"Vizualizare salvata: {output_png}")

    plt.show()


if __name__ == "__main__":
    # Cale implicita -- daca utilizatorul nu specifica
    PROJECT_ROOT = Path(__file__).parent.parent
    default_path = PROJECT_ROOT / "data" / "ndvi" / "jidvei_ndvi_2025-08-30.tif"

    # Permitem si argument din linia de comanda
    if len(sys.argv) > 1:
        tiff_path = Path(sys.argv[1])
    else:
        tiff_path = default_path

    if not tiff_path.exists():
        print(f"EROARE: fisierul nu exista: {tiff_path}")
        sys.exit(1)

    print(f"Vizualizare: {tiff_path}")
    visualize_ndvi(tiff_path)
