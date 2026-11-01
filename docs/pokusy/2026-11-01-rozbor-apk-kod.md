# P6 – rozbor APK simply-Fi: kód příkazů a čtení stavu (2026-11-01)

> ⚠️ Částečně překonáno pokusem P7: naše myčka patří do řady **nautilus**, ne do staré `CandyDishWasher`.
> Platí formát startu s `Program=P<cycleId>&w1=…` a `DelayStart` v půlhodinách – viz `2026-11-01-rozbor-apk-nautilus.md`.

**Zdroj:** APK 3.14.1 dekompilované jadx 1.5.6 do `apk/src/` (mimo git, kód appky se nezveřejňuje).
Naše myčka používá „starou“ cestu `CandyDishWasher` / `CandyDishWasherCommand` / `CandyDishwasherStatus`
(klíč `statusDWash`). Řada `dishwasher/nautilus` a `hnautilus` je jiný (novější) protokol – nás se netýká.

## Odeslání (`CandyCommand`)

`http://<ip>/http-write.json?encrypted=1&data=<xorEncrypt(parametry, klíč)>`
(`encrypted=0&<parametry>` jen pro nešifrované modely). Jeden a týž XOR jako u čtení.

## Příkazy myčky (`CandyDishWasherCommand.getParameterString`) – doslova

| Akce v appce | Parametry |
|---|---|
| **Stop** (tlačítko stop, `stop()`) | `Reset=1` |
| **Start** | `StartStop=1&Program=P<selector_position>&DelayStart=<hodiny>&TreinUno=<b8>&Eco=<b4>&MetaCarico=<b2>&ExtraDry=<b1>&OpzProg=<p\|m\|0>` (+ `&OpenDoorOpt=0/1`, jen modely `*_OD`) |
| **Otevřít dvířka** (`getOpenDoor`) | `OpenDoorOpt=7` |
| **„Nový reset“** (`reset()`) | `StartStop=0&Program=P2&DelayStart=0&TreinUno=0&Eco=0&MetaCarico=0&ExtraDry=0&OpenDoor=0&OpzProg=m&OpenDoorOpt=0` |

- **Volby = bitová maska** (`getOptions`): 1 ExtraDry, 2 ½ náplň (`MetaCarico`), 4 Eco, 8 3v1 (`TreinUno`),
  16 Open door (jen `*_OD`). `available_options` programu říká, které bity jsou povolené (31 = vše).
- `OpzProg`: `p` = intenzita „+“, `m` = „−“, `0` = normál (z `default_soil_level` programu).
- `DelayStart` = **celé hodiny** (proměnná `delayHours`, výběr 0–23 h, minuty skryté) → potvrzuje hypotézu
  o „ujíždějícím“ času startu v appce.
- Žádný příkaz „jen nastav program bez startu“ – appka program posílá výhradně se `StartStop=1`.
- `Program=P<n>` bere `selector_position` z definice programu (seznam programů appka dostává pro konkrétní
  spotřebič; demo DB má jiné hodnoty než naše myčka) → u nás použít kódy, které myčka hlásí (P2, P5, P8, P12, P19).
- Po **stopu přes cloud** (mimo lokální síť) appka blokuje další příkazy na **70 s**
  (`disableCommandsTemporary`, `DishWasherRemotelyStoppedException`).
- Když myčka hlásí konec (`StatoDWash=5`), appka ukáže zprávu „mytí dokončeno“ s příznakem
  `sendResetWhenDismissed` – zavření zprávy myčce pošle reset.

## Čtení stavu (`CandyDishWasher.updateWithStatus`) – význam polí podle appky

| Pole | V appce |
|---|---|
| `StatoWiFi` | `readonly = !StatoWiFi` → 0 = jen čtení (dálkové ovládání vypnuté) |
| `StatoDWash` | `status`; 1 předmytí, 2 mytí, 3 oplach, 4 sušení (texty fází), 5 = mytí dokončeno |
| `StartStop` | `active` (program `P0` = neaktivní) |
| `r1` | `selectorPosition` (pozice voliče) |
| `r2` | `phase` |
| `r6` | `buzzer` (zvuková signalizace) |
| `r7` | `hardnessLevel` (tvrdost vody) |
| `r8` | `lastCycle` |
| `r9` | obsahuje `H_` → autoClean |
| `r15` | `isCheckupEnabled` (> 0) |
| `r4`, `r5` | čteny, význam v kódu nepojmenován |
| `CodiceErrore` | `E<n>`, n > 0 = chyba → číselník `error_code` v DB |
| `DelayStart` | hodiny (`getDelay` vrací ×60 min) |
| `Lang` | jazyk (naše myčka nehlásí) |

⚠️ Appka bere fázi ze `StatoDWash`, naše myčka ale celý cyklus hlásí `StatoDWash=3` a fázi v `r2` [P1] →
appka u nás pravděpodobně ukazuje celou dobu „oplach“. Pro nás platí: fáze = `r2`.
