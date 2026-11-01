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
- P5–P7: rozbor APK 3.14.1 (DB + jadx + resources, vše v `apk/` mimo git) → naše myčka = řada
  nautilus; kompletní sada příkazů (start/stop/pauza/dvířka/tvrdost/zvuk/checkup), stavy, statistiky
  (prepare → 15 s → get), pravidla údržby (filtr 100 cyklů, odvápnění dle tvrdosti).
- Průzkum komunity (HA vlákno, ofalvai) → formát zápisu `http-write.json` a příklady příkazů v `docs/protokol.md`.

## Další krok

0. Bezpečné čtení statistik: `prepareStatistics` → 15 s → `getStatistics` (P7).
1. Nástroj `send.py` podle příkazů z kódu appky (P6, P7): `start`/`stop`; sestaví plaintext, ukáže ho,
   zašifruje; odeslání jen s `--send` (výchozí dry-run); před odesláním kontrola `StatoWiFi=1`.
2. Pokus P7 (u myčky, se souhlasem, dálkové ovládání zapnuté): start `P12` (5 min) → ověřit čtením → `Reset=1`.
3. Pokus P8: zablokovat myčce internet v routeru → funguje čtení i zápis?
4. Až bude jasné, co dál: případně přestavět na `uv` projekt + `analyze.py` (rozbor logu jako v P1).

## Otevřené otázky / slepé uličky

- `http-getStatistics.json` samotný = timeout; appka nejdřív volá `http-prepareStatistics.json` a čeká 15 s (P7).
- ⚠️ Ráno se HTTP server zasekl (ping ano, spojení zavírá), pomohl jen tvrdý restart myčky. Uživatel
  to zná i z běžného provozu appky. Hypotéza: souběh spojení appky a dalšího klienta.
- Nápad (poslední možnost): vlastní firmware do ESP modulu (ESPHome) – vyžaduje odposlech UART mezi
  modulem a deskou myčky, hardwarový zásah.

- `StatoDWash` u nás neodpovídá mapování z ofalvai (fáze je v `r2`) – viz protokol.
- Sdílené vlákno z Claude Desktop (claude.ai/share/…) nejde načíst – obsah se rekonstruoval z kódu a dat.
