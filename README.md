# netscan_for_candy – lokální ovládání myčky Candy simply-Fi

![License: MIT](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.8%2B%20%7C%20ovlada%C4%8D%203.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-web%20UI-009688?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![Candy simply-Fi](https://img.shields.io/badge/Candy-simply--Fi-E30613)

> **In English:** Local control of a Candy **simply-Fi** dishwasher – read status, start/stop programs –
> straight over your LAN, **without the app and without the cloud**. Includes a tool that recovers the
> module's XOR key, a protocol description and a small web controller (FastAPI). Docs are in Czech, code
> and CLI are in English. MIT licensed – feel free to reuse it, e.g. for a Home Assistant integration.
> Quick path: `python -m candy_netscan` (find the IP) → `python -m candy_netscan.find_key <ip>` (get the key)
> → see [`candy_netscan/client.py`](candy_netscan/client.py) (~70 lines, standard library only).

Čtení stavu a ovládání myčky Candy s Wi-Fi modulem **simply-Fi** přímo v domácí síti –
**bez mobilní aplikace a bez cloudu**. Projekt vznikl jako reverzní inženýrství protokolu;
kromě nástrojů na pokusy obsahuje i webový ovladač, který běží na PC nebo v Dockeru.

> ⚠️ **Ověřeno jen na modelu Candy CDIN 2L360PB** (v appce simply-Fi řada *nautilus*). Jiné modely
> mohou mít odlišná pole stavu, kódy programů i příkazy – čtení stavu je bezpečné, příkazy zkoušej opatrně
> a u myčky. Postup krok za krokem: **[`docs/navod.md`](docs/navod.md)**.
>
> ⚠️ Neoficiální projekt, s firmou Candy/Haier nemá nic společného. Zápis příkazů do myčky je na vlastní
> riziko. Endpoint `http-config.json` (přenastavení Wi-Fi a klíče modulu) nástroje záměrně nepoužívají –
> hrozí ztráta spojení s modulem.

## Co umí

- **Webový ovladač** (`ovladac/`, FastAPI + vanilla JS, funguje bez internetu): stav a zbývající čas,
  start/stop programu, odložený start, čisticí cyklus, historie cyklů a hlídání údržby (filtr, odvápnění).
- **Sken sítě** – najde myčku v LAN (ARP + OUI výrobce + sonda na `/http-read.json`).
- **Získání klíče** – dopočítá XOR klíč modulu z jeho vlastní odpovědi (`find_key.py`).
- **Sledování stavu** do JSONL logu se změnami mezi čteními (`candy_watch.py`).
- **Příkazy z řádky** (`send.py`) – s výchozím dry-run, který jen ukáže plaintext příkazu.
- **Popis protokolu** v `docs/protokol.md` – endpointy, pole stavu, příkazy, u každého údaje zdroj
  a míra ověření.

Ověřeno na myčce **Candy CDIN 2L360PB** (v appce simply-Fi 3.14.1 řada *nautilus*). Jiné modely mohou mít odlišná pole i programy.

## Jak protokol funguje (zkráceně)

Modul je ESP s HTTP serverem na portu 80. Data jsou „šifrovaná“ jen XORem 16znakovým klíčem:

```text
GET http://<ip>/http-read.json?encrypted=1                 → hex → XOR klíč → {"statusDWash": {...}}
GET http://<ip>/http-write.json?encrypted=1&data=<hex>     ← XOR("StartStop=1&Program=P12&…")
```

Modul odpovídá „SUCCESS“ i na příkaz, který ignoruje → výsledek je nutné ověřit čtením stavu.
Podrobnosti v [`docs/protokol.md`](docs/protokol.md).

## Jak zjistit IP a klíč

1. **IP adresa:** `python -m candy_netscan` vypíše zařízení v síti a označí kandidáty (výrobce Candy/Haier
   nebo Espressif, odpověď na `/http-read.json`). Jistotu dá pokus: myčku vypni – zmizí ze seznamu,
   zapni – objeví se. V routeru jí pak nastav pevnou IP (DHCP rezervace).
2. **Klíč:** každý modul má vlastní 16znakový klíč a nikam ho neposílá. Jde ale dopočítat: XOR je
   symetrický (`klíč = šifra ⊕ text`) a zašifrovaný stav vždy začíná stejně (`{\r\n\t"statusDWash`,
   přesně 16 bajtů). Postup vychází z poznatků komunity Home Assistant:

   ```bash
   python -m candy_netscan.find_key <ip>          # jedno čtení stavu → vypíše klíč
   python -m candy_netscan.find_key --hex <hex>   # nebo z už staženého řetězce
   ```

Podrobný postup: [`docs/pokusy/2026-11-01-ziskani-klice.md`](docs/pokusy/2026-11-01-ziskani-klice.md).

## Rychlý start

Zkopíruj `.env.example` do `.env` a doplň `CANDY_IP` a `CANDY_KEY` (klíč do gitu nepatří).

### Nástroje (jen standardní knihovna, Python 3.8+, jde i v Pydroidu na telefonu)

Spouštět z kořene projektu:

```bash
python -m candy_netscan                                   # najdi myčku v síti
python candy_netscan/candy_watch.py --log data/watch/2026-01-01_test.jsonl   # sleduj stav
python -m candy_netscan.send start P12                    # dry-run: jen ukáže příkaz
python -m candy_netscan.send start P12 --send             # ostře
```

### Webový ovladač (Python 3.12+, [uv](https://docs.astral.sh/uv/))

```bash
uv sync
uv run uvicorn ovladac.main:app --host 0.0.0.0 --port 8103
```

Stránka běží na http://127.0.0.1:8103. Výchozí je `DRY_RUN=true` – nic se do myčky neposílá;
pro ostrý provoz nastav v `.env` `DRY_RUN=false`. Nasazení v Dockeru: [`docs/nasazeni.md`](docs/nasazeni.md).

**Myčka zvládá jen jednoho klienta** – nespouštěj ovladač dvakrát a appku simply-Fi nech zavřenou,
souběh spojení zasekává Wi-Fi modul. Stav se čte nejvýš 1× za 3 s (výchozí 15 s).

## Struktura

| Cesta | Obsah |
|---|---|
| `candy_netscan/` | sken sítě, `client.py` (XOR, čtení, zápis – sdílí ho všechno ostatní), `find_key.py`, `candy_watch.py`, `send.py` |
| `ovladac/` | webový ovladač: `services/` (model stavu, programy, historie), `routers/` (REST API), `static/` (UI) |
| `docs/navod.md` | návod krok za krokem a řešení problémů |
| `docs/protokol.md` | aktuální mapa protokolu |
| `docs/pokusy/` | zápisník pokusů, ze kterých poznatky vychází |
| `docs/specs/` | návrh ovladače |
| `data/watch/` | surové logy pokusů |
| `tests/` | testy (`uv run pytest`) |

## Převzetí do Home Assistant a jinam

Kód je pod licencí MIT – klidně ho převezmi a zkus zapojit do Home Assistant, Node-RED, ioBrokeru
nebo vlastní automatizace. Nejlepší výchozí bod:

- [`candy_netscan/client.py`](candy_netscan/client.py) – celá síťová vrstva (XOR, čtení, zápis)
  v ~70 řádcích bez závislostí, snadno přepsatelná do jiného jazyka.
- [`docs/protokol.md`](docs/protokol.md) – význam polí stavu a seznam příkazů včetně toho, co nefunguje.
- [`ovladac/services/model.py`](ovladac/services/model.py) a `programs.json` – převod surového stavu
  na srozumitelný (fáze, zbývající čas, programy).

Pozor na dvě věci, které platí pro každou integraci: myčka zvládne **jen jednoho klienta** (i appka
simply-Fi se počítá) a modul hlásí úspěch i na ignorovaný příkaz – efekt vždy ověř čtením stavu.
Pokud něco postavíš nebo ověříš na jiném modelu, dej vědět v issues.

## Licence

[MIT](LICENSE)

## Poděkování

Výchozí poznatky o formátu komunikace pochází z komunity –
[vlákno na Home Assistant Community](https://community.home-assistant.io/t/dishwasher-candy-simply-fi-cdi-6015-wifi/136543)
a integrace [ofalvai/home-assistant-candy](https://github.com/ofalvai/home-assistant-candy).
