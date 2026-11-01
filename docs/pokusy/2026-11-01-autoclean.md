# P12 – rozbor APK: čisticí cyklus „Automatické čištění“ (2026-11-01)

**Cíl:** zjistit, jaký program appka spouští pro odvápnění/čištění myčky naší řady (nautilus).
**Zdroj:** dekompilát simply-Fi 3.14.1 v `apk/` (mimo git) – `NautilusWasherHomeActivity.autoclean()`,
`Command.getAutoCleanCommand`, `NautilusDownloadProgramManager.getByOuput`, asset
`assisted/dishwasher_output_cycles.json`, texty `DW_STATISTICS_AUTO_CLEAN_*`.

## Zjištění

- Appka nemá zvláštní program – vezme **první dostupný** program myčky s `Output=4` podle priority:
  Universale Plus → Auto Famiglia → Universale Plus → Famiglia → **Intensivo** → Vapore → Igienizzante → Igiene Plus.
  Naše myčka má z nich jen Intensivo → **Automatické čištění = P2 Intenzivní 75 °C**. 🔍
- Příkaz = běžný start P2 + `w3=H_2` (příznak autoclean); stav pak v `r9` ukazuje `H_2`. 🔍 (neověřeno zápisem)
- Před startem si appka uloží celkový počet cyklů → počítadlo odvápnění se nuluje startem čištění.
- Text appky: „Speciální cyklus určený k čištění myčky a odstraňování vodního kamene. Spusťte ho
  s použitím speciálního čisticího prostředku (řiďte se pokyny na obalu). Spotřebič musí být prázdný.“
- Interval: podle tvrdosti vody (110…85 cyklů, u nás 100) – viz P7, P10.

## Důsledky pro ovladač

- Odvápnění = ručně spustit P2 s prázdnou myčkou a čističem, pak v UI „Odvápněno“.
- Implementováno: tlačítko „Spustit čištění“ (`POST /api/cisteni`) = P2 + `w3=H_2`; cyklus se pozná podle
  `r9=H_` nebo podle toho, že ho spustil ovladač, a po dokončení se sám zapíše jako odvápnění.

## Ostrý test (12:33, z UI ovladače)

- Myčka příkaz s `w3=H_2` **přijala** ✅: běží P2, `StatoDWash=3`, `r2=2`, `RemTime` 130→…, `r9` = `H_2 \`.
- Firmware **neescapuje zpětné lomítko** – `"r9":"H_2 \"` rozbije striktní JSON („Invalid control character“),
  ovladač přestal číst stav (příkaz ohlásil „odešel, ale nešlo ověřit“ – pojistka z revize zafungovala).
  Opraveno v `candy_netscan/client.parse_status` (lomítka se berou doslova) + regresní test `tests/test_client.py`.
- Server byl kvůli opravě restartován uprostřed čištění → cyklus v historii začíná až v 12:47 (kratší délka);
  čištění rozpoznáno podle `r9`.
- `r7` (tvrdost) = 4 – nastavil uživatel záměrně přes UI (na panelu ta volba není) → interval odvápnění 90 cyklů.
- **Konec 14:33** ✅: `StatoDWash=5`, cyklus v historii `cisteni: true`, `vysledek: dokonceno`, fáze Mytí 37 /
  Oplach 38 / Sušení 31 min (od 12:47); ovladač sám zapsal `udrzba odvapneni` → `odvapneni_zbyva` = 90.
  Celková délka od startu 12:33 ≈ 2 h (myčka na startu hlásila 117–130 min).
- Po konci `r9` dál drží `H_2 \` a `RemTime` ukazuje 130 (výchozí délka P2) – `r9` je příznak posledního
  spuštění, ne „právě běží čištění“. Appka to ví: `CandyDishWasher` nastaví `autoClean` při `r9` obsahujícím
  `H_`, ale název „Automatické čištění“ ukáže jen když `isAutoClean() && isRunning()`. Běžný start appky `w3`
  neposílá (jen `w2` = název programu), takže jestli firmware `r9` při dalším startu vynuluje, nevíme.
- **Rozhodnutí:** ovladač bere jako čištění jen cyklus spuštěný jeho tlačítkem; P2 jinak = běžné mytí, `r9` se
  ignoruje. Daň: restart serveru během čištění příznak ztratí → odvápnění pak zapsat ručně tlačítkem „Odvápněno“.
