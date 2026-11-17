# Nasazení ovladače myčky

Ovladač je jediný klient myčky – **nespouštěj ho na dvou místech zároveň** (Windows i Docker) a appku
simply-Fi nech zavřenou. Souběh spojení zasekává Wi-Fi modul myčky.

## Teď: Windows PC

1. `.env` v kořeni projektu (vzor `.env.example`): `CANDY_IP`, `CANDY_KEY`, pro ostrý provoz `DRY_RUN=false`.
2. Spuštění z kořene projektu:

   ```powershell
   uv run uvicorn ovladac.main:app --host 0.0.0.0 --port 8103
   ```

   - PC: http://127.0.0.1:8103, mobil v domácí Wi-Fi: `http://<IP tohoto PC>:8103`
     (IP zjistíš `ipconfig`). Při prvním spuštění se Windows firewall zeptá – povolit pro **soukromé** sítě.
   - Jen pro PC bez mobilu stačí vynechat `--host 0.0.0.0` (pak firewall neřeší nic).
   - Ukončení Ctrl+C. Historie zůstává v `data/historie.jsonl`, surový log čtení v `data/raw/<datum>.jsonl`.
3. Server běží jen dokud je PC zapnuté a okno otevřené – cykly mimo tu dobu se do historie nezapíšou.

## Později: Docker na Linux serveru

Soubory: `Dockerfile`, `compose.yaml`, `.dockerignore` v kořeni projektu.

1. Na server zkopírovat projekt (stačí `git clone` – `apk/` a `.env` v gitu nejsou) a vytvořit `.env`.
2. Složka pro historii: `mkdir -p data && sudo chown 1000 data` (kontejner běží jako UID 1000).
   Historii z Windows přeneseš zkopírováním `data/historie.jsonl`.
3. Varianty spuštění:
   - **Samostatně:** `docker compose up -d --build` ve složce projektu.
   - **Do existujícího compose:** v něm přidat
     ```yaml
     include:
       - /cesta/k/netscan_for_candy/compose.yaml
     ```
     (Compose 2.20+; cesty `build: .` a `./data` se berou relativně ke složce projektu), nebo blok
     `mycka:` zkopírovat do `services:` a `build:`/`volumes:` přepsat na absolutní cesty.
4. Ověření: `docker compose ps` (stav `healthy`), `docker logs mycka-ovladac`, stránka `http://<server>:8103`.
5. Aktualizace: `git pull && docker compose up -d --build`.

### Na co dát pozor

- **Časová zóna:** `TZ=Europe/Prague` (už v `compose.yaml`) – „konec v“ a historie se počítají v ní.
  Databázi zón dodává Python balíček `tzdata`; logy uvicornu mohou být v UTC (slim obraz nemá systémová data zón).
- **Síť:** z výchozí bridge sítě je myčka v LAN dosažitelná napřímo, `network_mode: host` netřeba.
- **Port:** výchozí host port je 8103; jiný lze nastavit `MYCKA_HOST_PORT` v `.env`.
- **Restart:** `restart: unless-stopped`; zastavení (`docker compose down`) korektně ukončí čtení myčky.
