"""
Configurarea centralizata a proiectului CeresAgri.

Acest modul incarca credentialele si setarile din fisierul .env
si le pune la dispozitia restului codului intr-un mod sigur si tipat.

Toate celelalte module vor importa de aici, NU vor citi .env direct.
Asa avem un singur loc unde verificam credentialele si tratam erorile.
"""

# --- Importuri ---
# os ne lasa sa citim variabile de mediu (PATH, USER, etc.)
import os

# Path este o varianta moderna a "string-ului de cale" -- ne ajuta sa
# scriem cod care merge la fel pe Windows si Linux fara modificari.
from pathlib import Path

# load_dotenv citeste fisierul .env si pune valorile in variabilele de mediu
# ale procesului curent Python.
from dotenv import load_dotenv

# --- Localizarea fisierului .env ---
# __file__ este o variabila magica Python care contine calea fisierului curent.
# .parent.parent urca doua niveluri (config.py -> ceresagri/ -> radacina/).
# Asa gasim .env din radacina proiectului indiferent de unde am rulat scriptul.
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


# --- Incarcarea variabilelor de mediu din .env ---
# Apelam load_dotenv() o singura data, la import. Dupa aceea, os.getenv()
# va sti despre toate variabilele din .env.
load_dotenv(dotenv_path=ENV_FILE)


# --- Citirea credentialelor Sentinel Hub ---
# os.getenv("X") returneaza valoarea variabilei "X" sau None daca nu exista.
SH_CLIENT_ID = os.getenv("SH_CLIENT_ID")
SH_CLIENT_SECRET = os.getenv("SH_CLIENT_SECRET")

# CDS_API_KEY este pentru Copernicus Climate Data Store (folosit in Saptamana 4).
# Acum poate fi gol -- doar il pregatim.
CDS_API_KEY = os.getenv("CDS_API_KEY")


# --- Functie de verificare ---
def verify_config() -> dict:
    """
    Verifica daca toate credentialele necesare sunt prezente.

    Intoarce un dict cu statusul fiecarei credentiale.
    Daca lipseste ceva critic, ridica o exceptie.
    """
    status = {
        "project_root": str(PROJECT_ROOT),
        "env_file_exists": ENV_FILE.exists(),
        "sh_client_id_set": bool(SH_CLIENT_ID),
        "sh_client_secret_set": bool(SH_CLIENT_SECRET),
        "cds_api_key_set": bool(CDS_API_KEY),
    }

    # Verificari critice: daca lipsesc, ridicam exceptie ca sa stim imediat.
    if not ENV_FILE.exists():
        raise FileNotFoundError(
            f"Fisierul .env nu exista la {ENV_FILE}. "
            f"Copiaza .env.example ca .env si completeaza credentialele."
        )

    if not SH_CLIENT_ID or not SH_CLIENT_SECRET:
        raise ValueError(
            "SH_CLIENT_ID sau SH_CLIENT_SECRET lipsesc din .env. "
            "Obtine-le de la https://shapps.dataspace.copernicus.eu/dashboard/"
        )

    return status


# --- Cand rulam acest fisier direct (nu importat), face un self-test ---
# Aceasta sintaxa "if __name__ == '__main__'" inseamna:
# "executa codul de mai jos doar daca cineva ruleaza acest fisier direct,
# NU cand cineva il importa". E o conventie Python standard.
if __name__ == "__main__":
    print("=" * 60)
    print("CeresAgri -- verificare configuratie")
    print("=" * 60)

    try:
        status = verify_config()
        print("\nStatus configuratie:")
        for key, value in status.items():
            # Afisam credentialele ca True/False pentru a nu expune secretele
            print(f"  {key:.<40} {value}")
        print("\nToate credentialele necesare sunt prezente.")
    except (FileNotFoundError, ValueError) as e:
        print(f"\nEROARE: {e}")
        print("\nVerifica fisierul .env si reincearca.")
