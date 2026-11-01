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
  Ostrý test (zda myčka `w3` přijme a ukáže `r9=H_2`) čeká na první skutečné čištění.
