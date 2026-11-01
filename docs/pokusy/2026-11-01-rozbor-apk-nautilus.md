# P7 – rozbor APK: řada „nautilus/Axi“ = naše myčka, nastavení, statistiky, údržba (2026-11-01)

**Zdroj:** dekompilát APK 3.14.1 v `apk/src/` + resources v `apk/res-out/` (mimo git).
Třídy: `dishwasher/nautilus/**`, `dishwasher/hnautilus/**` (AxiDishwasher, příkazy), `CandyDishWasher` (společné čtení).

## Proč je naše myčka „nautilus“, ne stará `CandyDishWasher`

`CandyApplianceFactory`: connectivity `wifi` → `CandyDishWasher` (stará), jinak → `AxiDishwasher` (nautilus).
Naše data sedí na nautilus: stavy `StatoDWash` 2/3/5 = výběr/běh/konec a kódy `Program=P8/P19` = `cycleId`
(stará řada posílá `selector_position`). Hodnocení: 🟡 velmi pravděpodobné, potvrdí první start zápisem.

## Stavy `StatoDWash` (konstanty `DishWasher`)

0 bez stavu · 1 reset · **2 výběr** · **3 běh** · 4 pauza · **5 konec** · 6 chyba · 99 odložený start.
Checkup (`CheckUp`): 0 bez testu · 1 probíhá · 2 dokončen · 3 chyba. Fáze `r2`: navíc 9 = pauza „Good Night“.

## Příkazy (`http-write.json`, plaintext před XOR)

| Příkaz | Parametry | Třída |
|---|---|---|
| Start | `DelayStart=<d>&ExtraDry=<0/1>&OpenDoorOpt=<0/1>&TreinUno=<0/1>&Program=P<cycleId>&MetaCarico=<0/1>&OpzProg=<maska>&w1=<pozice>&StartStop=1&Eco=<0/1>` (+ `&w2=<název>` ; autoclean `&w3=H_<cycleId>`) | `Command.getParameterString` |
| Stop / zrušit odložený start | `Reset=1` | `StopCommand` |
| Pauza / pokračovat | `Pa=1` / `Pa=0` | `NautilusPauseWasherCommand` |
| Otevřít dvířka | `OpenDoorOpt=7` | `NautilusOpenDoorCommand` |
| Tvrdost vody | `HL=<index>` | `NautilusSetHardnessWasherCommand` |
| Zvuková signalizace | `BM=<0/1>` | `HNautilusBuzzerCommand` |
| Zapamatovat poslední cyklus | `LC=<0/1>` | `HNautilusLastCycleCommand` |
| Autodávkování | `SetDet=<0/1>&SetSoft=<0/1>` (jen modely s autodose) | `NautilusAutodoseWasherCommand` |
| Spustit kontrolu (checkup, ~8 min) | `StartCheckUp=<n>` | `CheckupCommand` |
| Reset kontroly | `Write=1` (lokálně) / `Write=1&StartStop=0&Program=11` (mapa) | `ResetCheckupCommand` |
| Tablety (počet / velikost balení) | `available_tabs`, `tabs_box_size` – posílá se **jen do cloudu** | `UpdateDataCommand` |

- **`DelayStart`**: výběr času krokuje po **půlhodinách** (max 48 = 24 h). Je-li `r15 > 0` (u nás 1),
  posílá se počet **půlhodin**, jinak celé hodiny (`delay / 2`). „Konec v …“ je jen výpočet appky
  (teď + program + odložení) → čas startu ujíždí s hodinami.
- `w1` = pozice programu (u nás odpovídá `r1`), `w2` = název programu pro displej, `w3`/`r9` = autoclean (`H_…`).
- Po příkazu appka hned znovu čte stav; polling lokálně á **15 s**, přes cloud á 30 s.

## Nastavení zrcadlená ve stavu

`r6` = buzzer (`BM`), `r7` = tvrdost vody (`HL`, index 0–5), `r8` = poslední cyklus (`LC`), `r15` = podpora
minut v odloženém startu / checkup. U nás: `r6=0`, `r7=2`, `r8=1`, `r15=1`.

## Statistiky a údržba

- Lokálně: **`GET /http-prepareStatistics.json?encrypted=1`**, počkat **15 s**, pak
  `GET /http-getStatistics.json?encrypted=1` → `{"statusCounters": {"s1"…"s24"}}`.
  `s1`–`s21` = počet spuštění programu podle `cycleId`, `s22`–`s24` = cykly podle teploty (0–30 / 40 / 60–90 °C).
  ⇒ Vysvětluje timeout v [P2]: chyběl krok `prepareStatistics`.
- Appka čte statistiky přednostně z cloudu, lokálně jen jako záloha; výsledek si ukládá v telefonu.
- **Čištění filtru**: každých **100 cyklů** (`filter_maintenance_cycle_limit`), počítáno ze součtu `s*`.
- **Odvápnění / autoclean**: po N cyklech podle tvrdosti `r7`: `hardness_values` = 110, 105, 100, 95, 90, 85
  (u nás `r7=2` → 100 cyklů). Počítadla „naposledy vyčištěno“ jsou **jen v telefonu**
  (`Preferences`: `LAST_LIMESTONE_CYCLE`, `NAUTILUS_TOTAL_CYCLE_FILTER`, `AVAILABLE_TABS`, …).
- **Sůl a leštidlo**: myčka dává jen příznak `MissSalt` / `MissRinse` (0/1), žádnou hladinu.
- 🟡 Hypotéza k „ztrátě nastavení po restartu“: údržba stojí na statistikách z cloudu nebo z
  `prepare/getStatistics`; když to selže, appka nemá z čeho počítat a stav v telefonu nesedí s myčkou.

## Další pole, která appka u nautilus zná (u nás v `http-read` nejsou – nejspíš jen ve statistikách/cloudu)

`FillR` plnění, `WaterHard`, `numF` počet napouštění, `NtcW`/`NtcD` teploty, `motS`, `PrCode`, `PrNm`,
`DryT`, `Det`/`Soft`, `rED`, `APSfreq`/`APSoff`, `DisTestOn`/`DisTestRes`, `Lang`.
