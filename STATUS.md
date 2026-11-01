# Stav projektu

Aktualizováno: 2026-11-01

## Cíl

Hotovo = ze skriptu na PC umím číst stav a spustit/zastavit/nastavit program bez aplikace simply-Fi,
funguje to i s myčkou odříznutou od internetu, postup je sepsaný v `docs/`.

## Hotovo

- Sken LAN najde myčku (`candy_netscan`), čtení stavu přes `http-read.json` + XOR klíč (`candy_watch.py`).
- Pokus P1: celý cyklus P2 zalogován a rozebrán → `docs/pokusy/2026-11-01-cyklus-P2.md`.
- P2–P4: `getStatistics` nepoužitelný, appka výběr programu neposílá, mapa 5 programů panelu,
  `StatoWiFi` = režim dálkového ovládání.
- Průzkum komunity (HA vlákno, ofalvai) → formát zápisu `http-write.json` a příklady příkazů v `docs/protokol.md`.

## Další krok

0. Rozbor APK – kód (jadx 1.5.6; APK 3.14.1 je v `apk/`, mimo git): najít, jak appka skládá
   `http-write` pro myčku (start/stop/odložený start, bity `available_options`/`OpzProg`).
   Databáze appky už rozebrána (P5) → programy P2…P20.
1. Nástroj `send.py`: sestaví plaintext příkazu, ukáže ho, zašifruje; odeslání jen s `--send` (výchozí
   dry-run); před odesláním kontrola `StatoWiFi=1`.
2. Pokus P5 (u myčky, se souhlasem, dálkové ovládání zapnuté): přepnout program zápisem bez startu
   (`Program=P5&w1=2`) → ověřit čtením; pak start P12 (5 min) a `Reset=1`.
3. Pokus P6: zablokovat myčce internet v routeru → funguje čtení i zápis?
4. Až bude jasné, co dál: případně přestavět na `uv` projekt + `analyze.py` (rozbor logu jako v P1).

## Otevřené otázky / slepé uličky

- ❌ `http-getStatistics.json` – myčka neodpovídá (timeout), modul tím ale nezasekne. Nepoužívat.
- ⚠️ Ráno se HTTP server zasekl (ping ano, spojení zavírá), pomohl jen tvrdý restart myčky. Uživatel
  to zná i z běžného provozu appky. Hypotéza: souběh spojení appky a dalšího klienta.
- Nápad (poslední možnost): vlastní firmware do ESP modulu (ESPHome) – vyžaduje odposlech UART mezi
  modulem a deskou myčky, hardwarový zásah.

- `StatoDWash` u nás neodpovídá mapování z ofalvai (fáze je v `r2`) – viz protokol.
- Sdílené vlákno z Claude Desktop (claude.ai/share/…) nejde načíst – obsah se rekonstruoval z kódu a dat.
