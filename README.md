# CeresAgri

Platformă de monitorizare agricolă prin Earth Observation, dezvoltată în România
pentru conformitate PAC și sprijin decizional în viticultură și culturi de câmp.

**Status:** Prototip TRL 3 — validare componentă.
**Solicitant POCIDIF 2.1:** Automation Technologies Engineering S.R.L.

> **Pentru audiență non-tehnică:** vezi [README-public.md](README-public.md) —
> o introducere pedagogică în ce face și de ce contează platforma CeresAgri.

---

## Despre proiect

CeresAgri integrează date din trei surse independente — sateliți optici
(Sentinel-2), radar (Sentinel-1) și reanaliza meteo (ECMWF ERA5-Land) — pentru
a produce indicatori cantitativi de stare a parcelelor agricole. Indicatorii
sunt corelați cu modele agronomice (FAO-56 Penman-Monteith pentru
evapotranspirație) pentru a oferi sprijin decizional în:

- Conformitate cu Politica Agricolă Comună (PAC) și raportare APIA
- Decizii de irigare bazate pe balanță hidrică
- Detectarea precoce a stresului hidric și termic
- Trasabilitate pentru produse cu denumire de origine (PDO/PGI)

Prototipul actual a fost dezvoltat și validat pe o parcelă viticolă de
~33 hectare în Podgoria Jidvei (Transilvania), pe perioada mai 2025 – mai 2026.

---

## Ce face acest prototip

Pipeline-ul TRL 3 implementează capăt-la-capăt:

1. **Ingestie Sentinel-2 (optic)** — interogare catalog STAC al Copernicus Data
   Space Ecosystem, autentificare OAuth2, descărcare imagini procesate prin
   evalscripts.
2. **Calcul indici vegetativi** — NDVI per scenă, salvare ca GeoTIFF
   georeferențiat, agregare statistică per parcelă (medie, min, max, P25, P75).
3. **Serie temporală NDVI** — 32 de observații curate (sub 30% nori) pe 12 luni,
   afișate ca grafic fenologic anual.
4. **Ingestie Sentinel-1 (radar SAR)** — 64 de observații VV/VH în polarizare
   ASCENDING, conversie liniară în decibeli, complementaritate cu optic în
   perioadele cu acoperire de nori.
5. **Ingestie meteo ECMWF ERA5-Land** — date orare pentru 6 variabile
   (temperatură, punct de rouă, vânt N-S și V-E, radiație solară, precipitații),
   agregate la nivel zilnic.
6. **Calcul evapotranspirație FAO-56 Penman-Monteith** — implementare conformă
   capitolele 3-4 ale FAO Irrigation and Drainage Paper No. 56 (Allen et al. 1998).
7. **Balanță hidrică zilnică și cumulativă** — precipitații minus ET₀, suma
   rulantă pentru identificarea perioadelor de deficit.
8. **Dashboard integrat** — vizualizare cu patru paneluri (NDVI, VV radar,
   precipitații, ET₀ + balanță cumulativă) pe aceeași axă temporală.

---

## Rezultate principale (parcela Jidvei, mai 2025 – mai 2026)

| Indicator | Valoare măsurată |
|---|---|
| Observații Sentinel-2 utilizabile | 32 (sub 30% nori) |
| Observații Sentinel-1 SAR | 64 (orbit ASCENDING) |
| NDVI mediu de vârf | 0.77 (16 octombrie 2025) |
| NDVI minim | -0.02 (17 ianuarie 2026, zăpadă) |
| Temperatura medie anuală | 11.1 °C |
| Precipitații anuale | 624 mm |
| ET₀ total anual | 832 mm |
| Balanța hidrică anuală | -208 mm |
| Deficit cumulativ maxim | -275 mm (28 septembrie 2025) |

Detalii și interpretarea agronomică în [`docs/raport_tehnic_trl3.md`](docs/raport_tehnic_trl3.md).

---

## Structura repository-ului

```text
ceresagri/
│
├── ceresagri/                       Pachet Python - cod reutilizabil
│   ├── config.py                    Incarcare credentiale din .env
│   ├── sentinel_client.py           Client OAuth2 + catalog STAC pentru CDSE
│   ├── sentinel_download.py         Descarcare imagini RGB Sentinel-2
│   ├── vegetation_indices.py        Calcul NDVI per scena
│   ├── time_series.py               Constructie serii temporale NDVI
│   ├── sentinel1_radar.py           Pipeline Sentinel-1 SAR
│   ├── ecmwf_climate.py             Descarcare ERA5-Land + agregare zilnica
│   └── evapotranspiration.py        FAO-56 Penman-Monteith
│
├── scripts/                         Scripturi de un singur scop
│   ├── plot_ndvi_timeseries.py
│   ├── plot_fusion_optic_radar.py
│   └── plot_integrated_dashboard.py
│
├── notebooks/                       Notebook-uri Jupyter de validare
│   └── 01_sentinel2_first_steps.ipynb
│
├── data/
│   ├── parcels/                     Geometrii parcele (GeoJSON) - versionate
│   ├── ndvi/                        Serii temporale NDVI (CSV) - versionate
│   ├── sentinel1/                   Serii temporale S1 (CSV) - versionate
│   ├── ecmwf/                       Serii climatice + ET0 (CSV) - versionate
│   └── figures/                     Figuri finale (PDF + PNG) - versionate
│
├── docs/
│   └── raport_tehnic_trl3.md        Raport tehnic complet
│
├── notes/                           Observatii de dezvoltare
├── pyproject.toml                   Manifest Python (uv)
└── README.md                        Acest fisier
```

---

## Cum se rulează

### Cerințe

- Python 3.13 (`uv python install 3.13`)
- Cont și credențiale Copernicus Data Space Ecosystem (Sentinel-1, Sentinel-2)
- Cont și API key Copernicus Climate Data Store (ECMWF ERA5-Land)
- ~5 GB spațiu liber pe disc pentru date intermediare

### Instalare

```bash
git clone https://github.com/AutomationTechnologiesEngineering/ceresagri.git
cd ceresagri
uv sync
```

### Configurare credențiale

# Copernicus Data Space Ecosystem - Sentinel Hub credentials

SH_CLIENT_ID=sh
SH_CLIENT_SECRET=

# Copernicus Climate Data Store (pentru ECMWF data) - vom completa in Saptamana 4

CDS_API_KEY=
CDS_URL=https://cds.climate.copernicus.eu/api
CDS_KEY=

### Rulare pipeline complet

```bash
# 1. Verificare configurare
python -m ceresagri.config

# 2. Descărcare Sentinel-2 (RGB sezonier)
python -m ceresagri.sentinel_download

# 3. Calcul NDVI per scenă
python -m ceresagri.vegetation_indices

# 4. Serie temporală NDVI (12 luni, durata ~5-10 min)
python -m ceresagri.time_series

# 5. Sentinel-1 SAR (durata ~10-15 min)
python -m ceresagri.sentinel1_radar

# 6. Descărcare meteo ECMWF (durata ~2-3 min)
python -m ceresagri.ecmwf_climate

# 7. Calcul ET₀ Penman-Monteith
python -m ceresagri.evapotranspiration

# 8. Dashboard integrat final
python scripts/plot_integrated_dashboard.py
```

---

## Limitări cunoscute

Prototipul TRL 3 prezintă următoarele limitări, asumate explicit, ce vor fi
adresate în implementarea POCIDIF:

- **Detectare zăpadă lipsă** — scenele cu acoperire de zăpadă produc NDVI
  apropiat de zero, fals interpretabil ca "vegetație inexistentă". Soluție în
  proiect: masking SWIR pe banda B11.
- **Validare in-situ inexistentă** — VV radar este interpretat ca proxy de
  umiditate sol fără calibrare prin senzori in-situ. Soluție în proiect:
  parteneriat cu stație meteorologică automată dintr-o exploatație reală.
- **O singură parcelă-test** — prototipul a fost dezvoltat și validat pe o
  parcelă reprezentativă, nu pe o populație de parcele. Generalizarea este în
  scopul proiectului.
- **Lipsa integrării APIA / SIGPAC** — prototipul folosește GeoJSON manual.
  Integrarea cu sursele oficiale de date administrative este obiectiv POCIDIF.
- **Fără front-end** — la TRL 3, validarea se face prin notebook-uri și
  figuri. Interfața web pentru utilizatori finali este obiectiv ulterior.

---

## Surse de date

Toate datele provin din surse Copernicus, gratuite și deschise:

- **Sentinel-2 L2A** (optic, 10 m, 5 zile revisit) — Copernicus Data Space Ecosystem
- **Sentinel-1 IW GRD** (SAR, 10 m, 6 zile revisit) — Copernicus Data Space Ecosystem
- **ERA5-Land** (reanaliza meteo, 9 km, orară) — Copernicus Climate Data Store

Conține date Copernicus Sentinel modificate (2025-2026).

---

## Finanțare

Acest prototip a fost dezvoltat ca parte din pregătirea cererii de finanțare
prin **Programul Operațional Creștere Inteligentă, Digitalizare și
Instrumente Financiare 2021-2027 (POCIDIF), Acțiunea 2.1** — Dezvoltarea
capacității de cercetare-dezvoltare a întreprinderilor.

---

## Licență

**Proprietary - All Rights Reserved.**

Copyright © 2026 Automation Technologies Engineering S.R.L.

Utilizarea, copierea, modificarea sau distribuția codului din acest repository
sunt interzise fără acord scris prealabil. Pentru solicitări de licențiere
academică sau necomercială, contactați autorul.

---

## Contact

**Automation Technologies Engineering S.R.L.**
Traian Conchi — traian.conchi@atc-e.com
+40 741 298 818

---

*Conține date Copernicus Sentinel-1, Sentinel-2 și ECMWF ERA5-Land modificate,
prelucrate de CeresAgri. Sursa: Copernicus Data Space Ecosystem și Copernicus
Climate Data Store — ESA Copernicus Programme.*
