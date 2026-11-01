# Candy simply-Fi – reverzní inženýrství myčky

Výzkumný projekt: zjistit, jak lokálně (bez mobilní aplikace simply-Fi a ideálně bez cloudu) číst stav
a ovládat myčku Candy. Výstupem jsou hlavně **poznatky v `docs/`** a malé nástroje na pokusy, ne aplikace.
Velikost: M.

Doména: python-uv (scripts-data, http-clients) + smart-home-api (šetrný polling, opatrné příkazy) –
obecná pravidla jsou ve skillech, tady se neopakují.

## Spuštění

Jen standardní knihovna Pythonu 3.8+ (kvůli běhu i na telefonu – Pydroid). Spouštět z kořene projektu:

- Sken sítě: `python -m candy_netscan`
- Sledování stavu: `python candy_netscan/candy_watch.py --log data/watch/<datum>_<popis>.jsonl`
  (IP a klíč z `.env`, viz `.env.example`)

## Mapa projektu

- `candy_netscan/` – sken LAN (ARP + OUI + sonda `/http-read.json`) a `candy_watch.py` (polling + diff + log)
- `data/watch/` – surové logy pokusů (`<YYYY-MM-DD>_<popis>.jsonl`), commitují se
- `docs/protokol.md` – **živá mapa protokolu**: endpointy, pole, příkazy; u každého údaje stav
  (✅ ověřeno / 🟡 hypotéza / 📚 z komunity) a zdroj
- `docs/pokusy/` – zápisník pokusů, jeden soubor na pokus (`<YYYY-MM-DD>-<popis>.md`)

## Pravidla tohoto projektu

- Nový poznatek → nejdřív zápis pokusu v `docs/pokusy/`, pak aktualizace `docs/protokol.md` s odkazem na pokus.
  `protokol.md` se přepisuje na aktuální stav poznání, není to deník.
- **Zápis do myčky (`http-write.json`, `http-config.json`) jen se souhlasem uživatele a když je u myčky.**
  Před odesláním vždy ukázat plaintext příkazu. `http-config.json` (přenastavení Wi-Fi/klíče) zatím vůbec –
  hrozí ztráta spojení s modulem.
- Polling ne častěji než 1× za 3 s (modul je ESP, nezahlcovat).
- Klíč a IP jen v `.env`, nikdy v kódu ani v dokumentaci.
- Kód zůstává v angličtině (existující moduly jsou anglicky, případně pro sdílení s komunitou); dokumentace česky.

## Body napojení

- `GET http://<ip>/http-read.json?encrypted=1` → hex řetězec; `bytes.fromhex` XOR klíč (16 ASCII znaků,
  opakovaně) → JSON `{"statusDWash": {...}}`, všechny hodnoty jsou stringy.
- `GET http://<ip>/http-write.json?encrypted=1&data=<hex>` – plaintext `klíč=hodnota&…` zašifrovaný stejně.
  Pozor: modul vrací „úspěch“ i na příkaz, který ignoruje → výsledek ověřovat čtením stavu, ne odpovědí.

Stav práce: viz `STATUS.md`.
