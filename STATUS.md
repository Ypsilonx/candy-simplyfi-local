# Stav projektu

Aktualizováno: 2026-11-01

## Cíl

Hotovo = ze skriptu na PC umím číst stav a spustit/zastavit/nastavit program bez aplikace simply-Fi
(lokálně, přímo na IP myčky), postup je sepsaný v `docs/`.

## Hotovo

- ✅ Ovladač (FastAPI + web UI, Docker soubory) mergnutý do `main`; provoz zatím na Windows PC
  (`uv run uvicorn … --host 0.0.0.0`), Docker na Linuxu nesestaven.
- ✅ Ovladač ukládá surový log čtení (`data/raw/`, jen změny, všechna pole – nic se nefiltruje).
- ✅ P12: **čisticí cyklus naostro** – P2 + `w3=H_2` z UI, po dokončení se samo zapsalo odvápnění.
- ✅ P11: **ovladač naostro z webového UI** – start P12, stop, zápis cyklu do historie (větev `feature/ovladac`).
- ✅ P8: **lokální zápis funguje** – start P12 a `Reset=1` přes `candy_netscan/send.py`.
- ✅ P9: dvířka během běhu = pauza (`StatoDWash=4`) a samo pokračuje; odložený start (příkaz v půlhodinách,
  stav v minutách) i jeho zrušení `Reset=1` fungují.
- ✅ P10: nastavení zvuk `BM`→`r6`, poslední cyklus `LC`→`r8`, tvrdost `HL`→`r7` zápisem fungují
  a přežijí restart myčky (ztrácí se jen údaje appky/cloudu – údržba, tablety).
- Sken LAN najde myčku (`candy_netscan`), čtení stavu přes `http-read.json` + XOR klíč (`candy_watch.py`).
- Pokus P1: celý cyklus P2 zalogován a rozebrán → `docs/pokusy/2026-11-01-cyklus-P2.md`.
- P2–P4: `getStatistics` nepoužitelný, appka výběr programu neposílá, mapa 5 programů panelu,
  `StatoWiFi` = režim dálkového ovládání.
- P5–P7: rozbor APK 3.14.1 (DB + jadx + resources, vše v `apk/` mimo git) → naše myčka = řada
  nautilus; kompletní sada příkazů (start/stop/pauza/dvířka/tvrdost/zvuk/checkup), stavy, statistiky
  (prepare → 15 s → get), pravidla údržby (filtr 100 cyklů, odvápnění dle tvrdosti).
- Průzkum komunity (HA vlákno, ofalvai) → formát zápisu `http-write.json` a příklady příkazů v `docs/protokol.md`.

## Další krok

1. **Příprava na publikaci** (GitHub): ✅ README (česky + anglický úvod, sekce pro převzetí do HA),
   ✅ LICENSE (MIT), ✅ kontrola úniků (klíč/IP/MAC v gitu ani historii nejsou),
   ✅ P13 získání klíče + `candy_netscan/find_key.py` (ověřeno naživo). Zbývá: název repozitáře na GitHubu.
2. **Vizuál webového UI** – barvy, výraznější styl stránek ovladače (`ovladac/static/css/`).
3. „Statistiky a údržba v2“ – počáteční stav údržby, učení délek programů z historie, přehled statistik.
4. Za provozu doladit: pípání na konci (r6=0 a stejně pípá), délky programů s volbami, programy jen z appky.

## Otevřené otázky / slepé uličky

- ❌ Pauza `Pa=1/0` – myčka odpoví SUCCESS, ale běží dál (P8, 2× ověřeno). Nepodporuje.

- ❌ Statistiky lokálně: `prepareStatistics` → 15 s → `getStatistics` = obojí timeout (P7). Myčka je dává
  jen do cloudu. Neopakovat; údržbu počítat sami z logu cyklů.
- ⚠️ Ráno se HTTP server zasekl (ping ano, spojení zavírá), pomohl jen tvrdý restart myčky. Uživatel
  to zná i z běžného provozu appky. Hypotéza: souběh spojení appky a dalšího klienta.
- Nápad (poslední možnost): vlastní firmware do ESP modulu (ESPHome) – vyžaduje odposlech UART mezi
  modulem a deskou myčky, hardwarový zásah.

- `StatoDWash` u nás neodpovídá mapování z ofalvai (fáze je v `r2`) – viz protokol.
- Sdílené vlákno z Claude Desktop (claude.ai/share/…) nejde načíst – obsah se rekonstruoval z kódu a dat.
