# Stav projektu

Aktualizováno: 2026-11-01

## Cíl

Hotovo = ze skriptu na PC umím číst stav a spustit/zastavit/nastavit program bez aplikace simply-Fi,
funguje to i s myčkou odříznutou od internetu, postup je sepsaný v `docs/`.

## Hotovo

- ✅ P8: **lokální zápis funguje** – start P12 a `Reset=1` přes `candy_netscan/send.py`.

- Sken LAN najde myčku (`candy_netscan`), čtení stavu přes `http-read.json` + XOR klíč (`candy_watch.py`).
- Pokus P1: celý cyklus P2 zalogován a rozebrán → `docs/pokusy/2026-11-01-cyklus-P2.md`.
- P2–P4: `getStatistics` nepoužitelný, appka výběr programu neposílá, mapa 5 programů panelu,
  `StatoWiFi` = režim dálkového ovládání.
- P5–P7: rozbor APK 3.14.1 (DB + jadx + resources, vše v `apk/` mimo git) → naše myčka = řada
  nautilus; kompletní sada příkazů (start/stop/pauza/dvířka/tvrdost/zvuk/checkup), stavy, statistiky
  (prepare → 15 s → get), pravidla údržby (filtr 100 cyklů, odvápnění dle tvrdosti).
- Průzkum komunity (HA vlákno, ofalvai) → formát zápisu `http-write.json` a příklady příkazů v `docs/protokol.md`.

## Další krok

1. Ověřit zbytek příkazů (u myčky, se souhlasem): pauza `Pa`, odložený start + zrušení, `BM`/`HL`/`LC`.
2. Pokus: zablokovat myčce internet v routeru → funguje čtení i zápis bez cloudu?
3. Vlastní nástroj místo appky (návrh A: Python + jednoduchá webová stránka): stav, start/stop/pauza,
   odložený start „konec v“, počítání cyklů pro údržbu (filtr 100, odvápnění dle `r7`).

## Otevřené otázky / slepé uličky

- ❌ Statistiky lokálně: `prepareStatistics` → 15 s → `getStatistics` = obojí timeout (P7). Myčka je dává
  jen do cloudu. Neopakovat; údržbu počítat sami z logu cyklů.
- ⚠️ Ráno se HTTP server zasekl (ping ano, spojení zavírá), pomohl jen tvrdý restart myčky. Uživatel
  to zná i z běžného provozu appky. Hypotéza: souběh spojení appky a dalšího klienta.
- Nápad (poslední možnost): vlastní firmware do ESP modulu (ESPHome) – vyžaduje odposlech UART mezi
  modulem a deskou myčky, hardwarový zásah.

- `StatoDWash` u nás neodpovídá mapování z ofalvai (fáze je v `r2`) – viz protokol.
- Sdílené vlákno z Claude Desktop (claude.ai/share/…) nejde načíst – obsah se rekonstruoval z kódu a dat.
