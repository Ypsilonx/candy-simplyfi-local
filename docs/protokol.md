# Protokol myčky Candy simply-Fi (lokální HTTP API)

Aktuální stav poznání – přepisuje se. Legenda: ✅ ověřeno na naší myčce · 🔍 z kódu appky simply-Fi
3.14.1 · 🟡 naše hypotéza · 📚 z komunity · ❓ neznámo.
Zdroje: [P1] `pokusy/2026-11-01-cyklus-P2.md` · [P2] `pokusy/2026-11-01-statistiky.md` ·
[P3] `pokusy/2026-11-01-appka-soubeh.md` · [P4] `pokusy/2026-11-01-mapa-programu.md` ·
[P5] `pokusy/2026-11-01-rozbor-apk-databaze.md` · [P6] `pokusy/2026-11-01-rozbor-apk-kod.md` ·
[P7] `pokusy/2026-11-01-rozbor-apk-nautilus.md` · [P8] `pokusy/2026-11-01-prvni-zapis.md` · [P9] `pokusy/2026-11-01-dvirka-odlozeny-start.md` ·
[HA] [Home Assistant Community – Candy simply FI CDI 6015](https://community.home-assistant.io/t/dishwasher-candy-simply-fi-cdi-6015-wifi/136543).

## Zařízení

- Wi-Fi modul na ESP, HTTP port 80, bez autentizace – jen XOR klíčem (16 ASCII znaků). ✅
- V appce řada **nautilus/Axi** (ne stará `CandyDishWasher`). ✅ [P7, P8]
- Ovládání jen v **režimu dálkového ovládání** (Wi-Fi tlačítko, `StatoWiFi=1`); při mačkání panelu ~5 s 0. ✅ [P4]

## Endpointy

| Endpoint | Účel | Stav |
|---|---|---|
| `GET /http-read.json?encrypted=1` | stav (hex, XOR) | ✅ |
| `GET /http-write.json?encrypted=1&data=<HEX(xor(parametry))>` | příkaz → odpověď šifrovaně `{"response":"SUCCESS"}` | ✅ [P8] |
| `GET /http-prepareStatistics.json?encrypted=1` → 15 s → `GET /http-getStatistics.json?encrypted=1` | statistiky (`statusCounters` s1–s24) | ❌ u nás obě timeout i ve správném pořadí [P7] – jen cloud |
| `/http-config.json` | přenastavení modulu (Wi-Fi, klíč) – **nesahat** | 📚 |

Modul odpoví „úspěch“ i na ignorovaný příkaz → výsledek vždy ověřit čtením stavu. 📚
Appka čte stav lokálně á 15 s.

## Příkazy (`http-write.json`) 🔍 [P6, P7]

| Akce | Parametry (plaintext před XOR) |
|---|---|
| Start ✅ [P8] | `DelayStart=<d>&ExtraDry=<0/1>&OpenDoorOpt=<0/1>&TreinUno=<0/1>&Program=P<n>&MetaCarico=<0/1>&OpzProg=<maska>&w1=<pozice>&StartStop=1&Eco=<0/1>` |
| Stop / zrušit odložený start ✅ [P8] (stop) | `Reset=1` |
| ~~Pauza / pokračovat~~ ❌ [P8] | `Pa=1` / `Pa=0` – odpoví SUCCESS, ale nic neudělá |
| Otevřít dvířka | `OpenDoorOpt=7` |
| Tvrdost vody | `HL=<0–5>` |
| Zvuk | `BM=<0/1>` |
| Pamatovat poslední cyklus | `LC=<0/1>` |
| Kontrola (checkup, ~8 min) / reset kontroly | `StartCheckUp=<n>` / `Write=1` |

- `DelayStart` v příkazu = počet **půlhodin** (0–48); ve stavu se vrací **zbývající minuty** (1 → 30, odpočítává). ✅ [P9]
- Zrušení odloženého startu: `Reset=1`. ✅ [P9]
- Volby (`OpzProg` maska): 1 ExtraDry, 2 ½ náplň, 4 Eco, 8 3v1, 16 Open door. 🔍
- `w1` = pozice programu (= `r1`), volitelně `w2` = název pro displej. 🔍
- „Jen nastav program“ neexistuje – program jde do myčky jen se startem. 🔍✅ [P3]
- Počet tablet / velikost balení appka posílá jen do cloudu, ne do myčky. 🔍

## Pole stavu (`statusDWash`)

| Pole | Význam | Stav |
|---|---|---|
| `StatoWiFi` | 1 = dálkové ovládání zapnuté, 0 = jen čtení | ✅ 🔍 |
| `StatoDWash` | 0 –, **1 reset** (~1–8 s po `Reset=1`), **2 výběr**, **3 běh** (i čekající odložený start), **4 pauza** (otevřená dvířka, ~4 s po startu), **5 konec**, 6 chyba, 99 odložený start (u nás nepozorováno) | ✅ (1–5) [P9] 🔍 |
| `r2` | fáze: 0 nic, (1 předmytí), 2 mytí, 3 oplach, 4 sušení, 5 konec, 9 pauza | ✅ [P1] 🔍 |
| `Program` | kód programu `P<cycleId>`, viz Programy | ✅ |
| `r1` | pozice programu na panelu (1–5) | ✅ [P4] 🔍 |
| `RemTime` | zbývající minuty; mimo běh jmenovitá délka | ✅ [P1] |
| `StartStop` | aktivní program (zůstává 1 i po konci, dokud nepřijde reset) | ✅ 🔍 |
| `DelayStart` | zbývající minuty do odloženého startu | ✅ [P9] |
| `TreinUno`, `Eco`, `MetaCarico`, `ExtraDry`, `OpenDoorOpt` | volby 3v1, Eco, ½ náplň, ExtraDry, auto-otevření | 🔍 |
| `OpenDoor` | dvířka otevřená; během běhu → pauza (`StatoDWash=4`), po zavření ~3 s pokračuje | ✅ [P3, P9] |
| `MissSalt`, `MissRinse` | chybí sůl / leštidlo (jen příznak, žádná hladina) | 🔍 |
| `CodiceErrore` | `E<n>`, n > 0 = chyba (číselník v DB appky) | 🔍 |
| `CheckUp` | kontrola: 0 –, 1 probíhá, 2 hotovo, 3 chyba | 🔍 |
| `r6` zvuk (`BM`) · `r7` tvrdost vody (`HL`, u nás 2) · `r8` poslední cyklus (`LC`) | nastavení myčky | 🔍 |
| `r9` | `H_<cycleId>` = autoclean, jinak `NULL` | 🔍 |
| `r15` | > 0 = odložení v půlhodinách + checkup | 🔍 |
| `r5` | 🟡 1 = neběží/připraveno: 1→0 při startu, 0→1 po stopu (v P1 1→0 až v 16. min – log začal po startu) | [P1, P8] |
| `r3`, `r4`, `Reset` | nepojmenováno | ❓ |

## Údržba (počítá appka, ne myčka) 🔍 [P7]

- **Filtr**: upozornění každých **100 cyklů** (součet `s1`–`s21` ze statistik).
- **Odvápnění / autoclean**: po 110/105/100/95/90/85 cyklech podle tvrdosti `r7` (u nás 100).
- „Naposledy vyčištěno“ a tablety si appka pamatuje jen v telefonu.

## Programy [P4, P5]

| `Program` | Název (appka) | Panel (`r1`) | Délka [min] naše / DB appky | Teplota (DB) |
|---|---|---|---|---|
| P2 | Intensivo | 1 | 130 (+10 ExtraDry) / 130 | 73 °C |
| P5 | Universale | 2 | 120 / 120 | 57 °C |
| P8 | Eco | 3 | 230 / 180 | 55 °C |
| P12 | Prelavaggio (předmytí), výchozí po zapnutí | 4 | 5 / 5 | – |
| P19 | Zoom 39 | 5 | 39 / 39 | 57 °C |
| P9 | Delicato | jen appka | – / 85 | 48 °C |
| P16 | Auto Giornaliero | jen appka | – / 95 | 60 °C |
| P17 | Notte (noční) | jen appka | – / 240 | 55 °C |
| P20 | Rapido 24 | jen appka | – / 24 | 50 °C |

## Otevřené otázky

- Ověřit: nastavení `BM`/`HL`/`LC`, programy jen z appky (P9, P16, P17, P20 – neznámé `w1`), volby
  (ExtraDry, Eco, ½ náplň, 3v1) ve startu.
