# Plán: ovladač myčky (podle `docs/specs/ovladac-mycky.md`)

Postup: jeden task → ověření → zastávka. Práce ve větvi `feature/ovladac`, merge do `main` až po revizi.

## T1 – uv projekt a sdílený klient
- Soubory: `pyproject.toml`, `.python-version`, `.vscode/settings.json`, `candy_netscan/client.py` (nový),
  `candy_watch.py` a `send.py` (importují z `client.py`), `CLAUDE.md` (příkazy).
- Rozhraní: `xor_encrypt(text, key) -> str`, `xor_decrypt(hex, key) -> str`,
  `read_status(ip, key, timeout) -> dict[str, str]`, `send_params(ip, key, params, timeout) -> str` (dešifrovaná odpověď).
- Závislosti: `fastapi`, `uvicorn[standard]`, `pydantic-settings`; dev `pytest`, `httpx`.
- Ověřit: `uv run python -m candy_netscan.send start P12` (dry-run) a jedno čtení stavu projdou.

## T2 – model stavu a katalog programů
- Soubory: `ovladac/services/model.py`, `ovladac/services/programs.py`, `ovladac/services/programs.json`, `tests/`.
- Rozhraní: `interpret(raw: dict) -> Stav` (stav, fáze, program, zbývá, odložení, volby, nastavení, varování);
  `allowed_options(code) -> set[str]`, `validate_options(code, opts)` (maska + vylučující páry 3/5/6);
  `delay_for_end(now, konec, delka_min) -> (half_hours, odhad_konce)`; `start_params(code, opts, delay) -> str`.
- Ověřit: `uv run pytest tests/test_model.py tests/test_programs.py` (interpret na reálných řádcích z logů,
  výpočet „konec v“, vylučování voleb).

## T3 – historie cyklů a údržba
- Soubory: `ovladac/services/history.py`, `tests/test_history.py`.
- Rozhraní: `CycleTracker.update(stav, ts) -> Event | None` (start/konec/zrušeno), `History(path)` –
  `append(cycle)`, `list()`, `maintenance(hardness) -> {filtr_zbyva, odvapneni_zbyva}`, `mark(kind)`.
- Ověřit: přehrání `data/watch/2026-11-01_P2_extradry.jsonl` → přesně 1 dokončený cyklus P2 s délkou ~132 min.

## T4 – FastAPI server a správce myčky
- Soubory: `ovladac/config.py`, `ovladac/services/appliance.py`, `ovladac/routers/api.py`, `ovladac/main.py`,
  `.env.example` (doplnit `DRY_RUN`, `POLL_SECONDS`, `DATA_DIR`).
- Rozhraní: `GET /api/stav`, `GET /api/programy`, `POST /api/start {program, volby, delay|konec}`,
  `POST /api/stop`, `POST /api/nastaveni {zvuk|tvrdost|posledni_cyklus}`, `GET/POST /api/udrzba`.
- Ověřit: `uv run uvicorn ovladac.main:app` → `/api/stav` vrací živý stav; start s `DRY_RUN=true` nic nepošle.

## T5 – webové UI (lokální, bez internetu)
- Soubory: `ovladac/static/index.html`, `css/base.css` (proměnné barev/breakpointů), `css/app.css`,
  `js/api.js` (API_BASE_URL z `location`), `js/app.js`.
- Obsah: stav + průběh, výběr programu → nabídne jen povolené volby, „start teď / konec v“, stop,
  nastavení, údržba + historie.
- Ověřit: Playwright v Edge 390 px a 1440 px, konzole bez chyb, žádný požadavek mimo localhost.

## T6 – ostrý test a nasazení na Linux v Dockeru (později)
- Ostrý start z UI (P12 → stop) se souhlasem.
- `Dockerfile` (uv, `uvicorn ovladac.main:app --host 0.0.0.0`), `compose.yaml` (`env_file: .env`,
  volume pro `DATA_DIR=/data`, `TZ=Europe/Prague`, `restart: unless-stopped`), `docs/nasazeni-linux.md`.
- Do té doby běží ovladač na hlavním Windows PC (`uv run uvicorn …`).

## Body napojení

- **Myčka (HTTP, port 80)** – `GET /http-read.json?encrypted=1` → hex(XOR) JSON `statusDWash`;
  `GET /http-write.json?encrypted=1&data=<HEX>` → hex(XOR) `{"response":"SUCCESS"}`.
  Pozor: SUCCESS i na ignorovaný příkaz → vždy ověřit čtením; příkazy jen při `StatoWiFi=1`;
  jen jeden klient (server), čtení ne častěji než á 3 s (výchozí 15 s); ~4 s po startu krátce
  `StatoDWash=4` a `StatoWiFi=0`; po `Reset=1` ~1–8 s `StatoDWash=1`/`Program=P0`; `DelayStart`
  posílat v půlhodinách, číst v minutách; `r2` mimo běh drží starou fázi.
- **FastAPI lifespan** – poller jako `asyncio` task startovaný v `lifespan`, rušený při vypnutí;
  síťová volání myčky jsou synchronní (`urllib`) → `asyncio.to_thread`; příkazy a čtení přes jeden `asyncio.Lock`.
- **uvicorn** – Windows: `--host 0.0.0.0` jen pokud chceš z mobilu (firewall Windows se zeptá).
- **Docker (Linux)** – konfigurace jen z proměnných prostředí (`.env` nepovinný); historie ve volume
  (`DATA_DIR`); kontejner musí znát `TZ` (jinak časy v UTC) a mít `tzdata`; z bridge sítě je myčka
  na LAN dosažitelná přímo (`network_mode: host` netřeba); logy na stdout; SIGTERM → lifespan zruší poller.
- **Čas** – historie v ISO 8601 s offsetem (`datetime.now().astimezone()`), ne naivní čas.
