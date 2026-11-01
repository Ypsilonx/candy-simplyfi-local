# Protokol myčky Candy simply-Fi (lokální HTTP API)

Aktuální stav poznání – přepisuje se. Legenda: ✅ ověřeno na naší myčce · 🟡 naše hypotéza ·
📚 z komunity, u nás neověřeno · ❓ neznámo. Zdroje: [P1] = `pokusy/2026-11-01-cyklus-P2.md`, [P2] = `pokusy/2026-11-01-statistiky.md`,
[P3] = `pokusy/2026-11-01-appka-soubeh.md`, [P4] = `pokusy/2026-11-01-mapa-programu.md`,
[P5] = `pokusy/2026-11-01-rozbor-apk-databaze.md`,
[HA] = vlákno [Home Assistant Community – Candy simply FI CDI 6015](https://community.home-assistant.io/t/dishwasher-candy-simply-fi-cdi-6015-wifi/136543),
[ofalvai] = [ofalvai/home-assistant-candy](https://github.com/ofalvai/home-assistant-candy) (`client/model.py`).

## Zařízení

- Wi-Fi modul na ESP (dle komunity ESP32), HTTP na portu 80, bez autentizace – jen XOR „šifra“. ✅
- Klíč: 16 ASCII znaků. Lze ho získat known-plaintext útokem, odpověď začíná `{"statusDWash":{"StatoWiFi`
  (nástroj CandySimplyFi-tool, MelvinGr). 📚 Náš klíč máme. ✅

## Endpointy

| Endpoint | Účel | Stav |
|---|---|---|
| `GET /http-read.json?encrypted=1` | stav myčky (hex, XOR) | ✅ |
| `GET /http-write.json?encrypted=1&data=<hex>` | příkaz (plaintext `k=v&k=v`, XOR, hex) | 📚 |
| `GET /http-getStatistics.json?encrypted=1` | statistiky (počty cyklů…?) – jen čtení | ❌ u nás neodpovídá (timeout 25 s), modul ale sám nezasekne [P2] |
| `/http-config.json` | přenastavení modulu (Wi-Fi, klíč) – **nesahat** bez plánu | 📚 |

## Pole stavu (`statusDWash`)

| Pole | Význam | Hodnoty | Stav |
|---|---|---|---|
| `StatoWiFi` | režim dálkového ovládání (zapíná se tlačítkem na myčce) – **ne stav sítě**; při mačkání panelu ~5 s 0 | 1 = zapnut | ✅ [P4] |
| `CodiceErrore` | chybový kód | `E0` = bez chyby | 🟡 |
| `StatoDWash` | stav stroje | 2 = klid/výběr, 3 = běží, 5 = dokončeno | 🟡 [P1, P2] |
| `Program` | interní kód programu | viz tabulka Programy | ✅ [P4] |
| `r1` | pozice programu na panelu (1–5) – odpovídá `w1` v zápisu; při přepínání krátce zaostává | | ✅ [P4] |
| `RemTime` | zbývající minuty; mimo běh = jmenovitá délka programu (P2+ExtraDry = 140, P12 = 5) | | ✅ [P1, P2] |
| `r2` | fáze cyklu | 0 nic, 2 mytí, 3 oplach, 4 sušení, 5 konec (1 = předmytí?) | 🟡 [P1, P2] |
| `r5` | ? (1→0 v 16. min cyklu – napouštění/ohřev?) | 0/1 | ❓ |
| `OpenDoor` | dvířka otevřená (projeví se okamžitě) | 1 = otevřeno | ✅ [P1, P3] |
| `OpenDoorOpt` | volba auto-otevření dvířek po sušení | 0/1 | 📚 |
| `ExtraDry`, `Eco`, `MetaCarico` (½ náplň), `TreinUno` (3v1), `DelayStart` (h) | volby programu | | 📚 |
| `MissSalt`, `MissRinse` | chybí sůl / leštidlo | 1 = chybí | 📚 [ofalvai] |
| `StartStop` | poslední start/stop – zůstává 1 i po konci | | 🟡 [P1] |
| `Reset`, `CheckUp` | reset programu / autodiagnostika | | ❓ |
| `r3`,`r4`,`r6`–`r9`,`r15` | ? konstantní v P1 i po restartu (`r9`=`NULL`) | | ❓ |

⚠️ Rozpor: [ofalvai] čte fázi (0 idle … 5 finished) ze `StatoDWash`. U naší myčky je `StatoDWash` po celý
cyklus 3 a fázi ukazuje `r2` → firmware/model se liší, mapování z HA nelze brát slepě.

## Programy [P4, P5]

`Program=P<n>`, kde `n` = `cycle_name` z databáze appky. Názvy z appky (italské klíče).

| `Program` | Název | Panel (`r1`) | Délka [min] naše / DB | Teplota (DB) |
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

Programy „jen appka“ jsou z DB 📚, na naší myčce neověřeny.

## Příkazy (`http-write.json`) – 📚 vše zatím neověřeno

Příklady z [HA] pro Hoover H-Dish 300 (plaintext před XOR):

```
DelayStart=0&ExtraDry=0&OpenDoorOpt=0&TreinUno=0&Program=P2&MetaCarico=0&OpzProg=0&w1=1&StartStop=1
Reset=1                      # stop / zrušení programu
```

- Programy u Hooveru: `P2`+`w1=1` Intensive 75 °C, `P5`+`w1=2` Universal 60 °C, `P8`+`w1=3` Eco 45 °C,
  `P12`+`w1=4` předmytí, `P13`+`w1=5` Total Care 50 °C.
- `OpzProg` (bitové volby?): 8 = 3v1, 9 = 3v1+ExtraDry, 10 = 3v1+½ náplň, 12 = 3v1+Eco.
- Bez správného `StartStop=1` modul odpoví „úspěch“, ale nic neudělá → ověřovat čtením stavu.
- Pravděpodobně vyžaduje `StatoWiFi=1` – režim dálkového ovládání zapnutý tlačítkem na myčce
  (v tom režimu panel nereaguje plně, uživatel ho pro ruční ovládání vypíná) [P4].
- Appka simply-Fi při pouhém výběru programu nic neposílá (stav myčky se nemění) [P3] – program jde
  zřejmě do myčky až se startem.

## Chování appky simply-Fi (pozorování uživatele, 2026-11-01)

- Ovládání z appky jen se zapnutým režimem dálkového ovládání (Wi-Fi tlačítko na myčce); může zůstat
  zapnutý libovolně dlouho. Bez něj jen panel a čtení stavu.
- Appka program do myčky pošle až se **startem** (výběr v appce se v myčce neprojeví) [P3].
- Odložený start „konec v“: program 140 min, konec 8:30 → appka ukázala start 7:20, který pak ujížděl
  (7:25 …). 🟡 Hypotéza: `DelayStart` je v **celých hodinách**, appka zobrazuje „teď + N h“, proto čas
  start ujíždí s hodinami. Ověřit: odložený start na panelu → hodnota `DelayStart`.
- „Resetovat čas“ v appce se ptá na přerušení programu a myčka udělala něco neočekávaného (program se
  nepřerušil) – co appka posílá, je neznámé → rozbor APK.

## Otevřené otázky

- Funguje lokální API, když je myčce v routeru zablokován internet?
- Co jsou `w1` vs. `r1…r15` (zápis vs. čtení stejných registrů?), jaký je seznam programů naší myčky?
