# CeresAgri — pe înțelesul tuturor

**Cum vede un satelit o podgorie din Transilvania, și de ce contează asta
pentru viticultură, pentru fermieri și pentru piața vinurilor românești.**

---

> **Document pentru audiență generală.** Pentru detalii tehnice, cod și
> referințe științifice, vezi [README.md](README.md). Pentru raportul
> complet de cercetare, vezi [docs/raport_tehnic_trl3.md](docs/raport_tehnic_trl3.md).

---

## De ce am construit CeresAgri

Agricultura modernă se confruntă cu o întrebare aparent simplă, dar greu de
răspuns onest: **ce se întâmplă, chiar acum, pe parcela mea?**

Un viticultor care are 50 de hectare de viță-de-vie nu poate inspecta personal
fiecare rând în fiecare zi. Un agronom care consiliază 20 de exploatații nu
poate fi simultan în toate. Un inspector APIA care verifică conformitatea
Politicii Agricole Comune (PAC) la mii de parcele anual nu are timp fizic să
le viziteze pe toate.

În același timp, Europa a investit zeci de miliarde de euro într-un sistem
spațial de observare a Pământului, **Programul Copernicus**, care fotografiază
și măsoară fiecare metru pătrat al Europei la fiecare 3-6 zile. Datele sunt
**gratuite și disponibile public** pentru oricine știe să le citească.

Problema: aceste date sunt brute, voluminoase și greu accesibile pentru
agricultori. Un fișier Sentinel-2 acoperă 110 × 110 km în 13 benzi spectrale,
ocupă 1-2 gigabytes și necesită cunoștințe tehnice avansate pentru a-l
transforma în informație utilă.

**CeresAgri este puntea dintre infrastructura spațială europeană și fermierul care gestioneaza pamantul.**
 Sau, mai precis, dintre satelitul Sentinel-2 aflat la 786
de kilometri altitudine și viticultorul din Jidvei care vrea să știe dacă să
irigheze sau să aștepte ploaia.

---

## Ce face platforma, concret

Platforma CeresAgri integrează automat **trei surse independente de date**
despre o parcelă agricolă, fiecare măsurând ceva diferit:

### 1. Sateliți optici — "ochii" platformei

Sateliții **Sentinel-2** ai Agenției Spațiale Europene fotografiază Europa la
fiecare 3-5 zile, în 13 culori spectrale (de la albastru ultraviolet la
infraroșu apropiat și mijlociu). Fiecare pixel din imagine corespunde cu o
suprafață de 10 × 10 metri pe sol.

Din aceste imagini, platforma calculează **NDVI** — un indice numeric care
măsoară cât de "verde" și fotosintetic activă este vegetația pe fiecare pixel.

De ce funcționează NDVI: frunzele verzi sănătoase absorb intens lumina roșie
vizibilă (pentru fotosinteză) dar reflectă puternic radiația infraroșie
apropiată — invizibilă pentru ochiul uman, dar perfect detectabilă de satelit.
Diferența dintre cele două lumini, normalizată, dă un număr între -1 și +1
care spune dacă pixelul respectiv conține:

- Apă (NDVI negativ)
- Sol gol, drumuri, beton (NDVI aproape de zero)
- Vegetație rară sau uscată (NDVI 0.1 – 0.3)
- Cultură în creștere normală (NDVI 0.3 – 0.6)
- Vegetație densă, sănătoasă (NDVI 0.6 – 0.8)

Pentru parcela noastră-test din Jidvei, am obținut **32 de măsurători NDVI
curate** (fără nori) pe parcursul unui an întreg. Acest set permite trasarea
"curbei fenologice" a viei — o reprezentare grafică a felului în care
plantele cresc, înfloresc, dau rod și intră în dormanță.

### 2. Sateliți radar — "atingerea" platformei

Sateliții **Sentinel-1** funcționează diferit: nu fotografiază lumina solară
reflectată, ci trimit ei înșiși un puls de microunde spre Pământ și măsoară
cât revine înapoi.

Acest sistem are două avantaje uriașe față de satelitul optic:

- **Funcționează și noaptea** (nu depinde de soare)
- **Trece prin nori** (microundele nu sunt blocate de nori)

În Transilvania, unde iarna avem 80% acoperire de nori, satelitul optic este
practic orb pentru luni întregi. Radarul, în schimb, oferă date continue,
indiferent de vreme.

Ce ne spune radarul: cât de **umed** este solul (apa reflectă puternic
radarul) și cât de complexă este structura vegetației (frunzișul, lemnul,
sârmele de la viță împrăștie diferit semnalul).

Pentru parcela Jidvei, radarul ne-a dat **64 de măsurători** într-un an — de
două ori mai multe decât satelitul optic, exact pentru că nu este oprit de
nori.

### 3. Reanaliza meteorologică — "memoria climatică"

A treia sursă de date vine de la **Centrul European pentru Prognoze
Meteorologice pe Termen Mediu (ECMWF)** din Reading, UK. Acesta produce
**ERA5-Land** — o "reanaliză" globală a vremii: o reconstrucție matematică a
condițiilor meteorologice pe fiecare 9 × 9 km de Europa, pentru fiecare oră
din ultimii 70 de ani.

Pentru fiecare zi, platforma noastră obține de aici:

- Temperatura aerului (minimă, maximă, medie)
- Umiditatea aerului
- Precipitațiile (mm de ploaie sau echivalent zăpadă)
- Radiația solară primită
- Viteza vântului

Aceste date sunt baza pentru a calcula **câtă apă pierde parcela pe zi prin
evapotranspirație** — adică prin evaporarea apei din sol și transpirația
plantelor. Este o componentă critică a bilanțului hidric al unei culturi.

---

## Ce poate spune CeresAgri despre o parcelă

Punând împreună aceste trei surse, platforma construiește o imagine
multi-dimensională a parcelei pe care un singur instrument nu o poate da:

**"Pe 16 octombrie 2025, parcela viticolă din Jidvei a avut NDVI maxim al
sezonului — 0.77. În același timp, balanța hidrică cumulativă era de -275 mm,
indicând un deficit de apă acumulat din vară. Sezonul anterior a avut iunie
deosebit de uscat (-133 mm deficit lunar), însă viile au rezistat datorită
rezervelor de apă din sol și ploilor compensatorii din august. Recolta 2025
este așteptată să aibă struguri mai mici dar mai concentrați aromatic."**

Acest paragraf nu este o speculație. Este reconstrucția cantitativă, bazată
pe date măsurate prin satelit și model meteo, a realității unei parcele
agricole reale, pe parcursul unui an întreg, fără ca cineva să fi pus piciorul
fizic acolo.

---

## Pentru cine este utilă platforma

### Viticultori și fermieri

- **Decizii de irigare** bazate pe balanța hidrică reală, nu pe intuiție
- **Detectarea precoce a stresului hidric** înainte ca el să devină vizibil
  cu ochiul liber
- **Optimizarea momentului de recoltă** prin urmărirea maturării
- **Documentație obiectivă** a anului agricol pentru asiguratori, parteneri
  comerciali, autorități

### Cooperative agricole și consultanți agronomici

- **Monitorizarea simultană a zecilor sau sutelor de parcele** dintr-o zonă
- **Comparații obiective** între parcele cu management diferit
- **Rapoarte standardizate** pentru toți membrii cooperativei

### Producători de vinuri cu denumire de origine (PDO/PGI)

- **Trasabilitate completă** a sezonului agricol pentru fiecare lot
- **Dovezi cantitative** pentru caracteristicile recoltei (concentrație,
  stres hidric, condiții termice) — utile pentru marketing premium

### Autorități și organisme de control (APIA, agenții PAC)

- **Verificare automată a conformității** declarațiilor de cultură
- **Detectarea anomaliilor** (parcele neîntreținute, schimbări de cultură,
  pârloagă nedeclarată)
- **Reducerea costurilor de inspecție** prin pre-filtrarea inteligentă

---

## De ce este momentul potrivit acum

Trei tendințe converg către aceeași oportunitate, fix acum, în 2026:

**1. Infrastructura spațială europeană s-a maturizat.** Constelația Copernicus
include acum patru sateliți operaționali (Sentinel-1A, Sentinel-2A, 2B și 2C)
plus servicii ECMWF, oferind date continue, gratuite, garantate pe termen
lung. Acum 5 ani, această infrastructură era încă în construcție.

**2. Politica Agricolă Comună (PAC) 2023-2027** introduce obligații noi de
monitorizare obiectivă a parcelelor pentru toate cele 27 de state membre
UE. Verificarea prin satelit devine de la "opțiune utilă" la "obligație
operațională".

**3. Schimbările climatice fac monitorizarea hidrică critică.** Anii cu
secete extreme sau ploi neuniforme nu mai sunt excepții, ci normă. Decizia
"udăm sau așteptăm" se ia acum cu marja mai mică de eroare, și are nevoie de
suport cantitativ.

Pentru România în special, unde agricultura reprezintă cca 4% din PIB și
unde marile cooperative agricole (Cooperative cerealiere, asociațiile
viticultorilor) sunt în plină consolidare, momentul este excelent pentru o
platformă **construită pentru piața românească, vorbind limba românească,
integrată cu sistemele APIA**.

---

## Status actual și pași următori

CeresAgri se află în acest moment la **TRL 3** (Technology Readiness Level 3)
— validare experimentală a componentelor critice. Toate cele trei pipeline-uri
tehnice (optic, radar, meteo) funcționează și au fost demonstrate pe o
parcelă reală.

Pașii următori, în cadrul proiectului propus pentru finanțare prin
**Programul Operațional Creștere Inteligentă, Digitalizare și Instrumente
Financiare 2021-2027 (POCIDIF), Acțiunea 2.1**:

- Generalizarea pe sute de parcele de tipuri diferite (viță-de-vie, porumb,
  grâu, livezi, pășuni)
- Integrarea cu sistemul APIA pentru ingestare automată a geometriei
  parcelelor
- Dezvoltarea unei interfețe web pentru utilizatori non-tehnici
- Calibrarea radarului prin senzori in-situ în 3-5 exploatații pilot
- Validarea cu fermierii reali, prin parteneriate cu cooperative locale

Ținta este o **platformă operațională, multi-tenant, gata pentru
comercializare** la sfârșitul proiectului, în 2027.

---

## Contact

Dacă sunteți fermier, consultant agronomic, cooperative sau pur și simplu
curios, ne-ar plăcea să auzim de la dumneavoastră.

**Automation Technologies Engineering S.R.L.**
Traian Conchi — traian.conchi@atc-e.com
+40 741 298 818

---

*CeresAgri folosește date Copernicus Sentinel-1, Sentinel-2 și ECMWF
ERA5-Land — programul european de observare a Pământului, finanțat din
contribuțiile statelor membre UE și ale Agenției Spațiale Europene (ESA).*
