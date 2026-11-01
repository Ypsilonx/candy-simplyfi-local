# P5 – rozbor APK simply-Fi: přibalená databáze (2026-11-01)

**Zdroj:** APK `it.candy.simplyfi` 3.14.1 (versionCode 226) stažené z telefonu uživatele přes `adb pull`
do `apk/` (mimo git). Appka je nativní Java/Kotlin (5× dex, Realm, okhttp) → vhodná pro jadx.
**Soubor:** `assets/candy_database.sql` – ve skutečnosti SQLite DB (demo spotřebiče + definice programů).

## Programy myček „DW_WIFI_*“ (tabulky `programs` + `parameters_for_programs` + `parameters`)

| `cycle_name` | Název (klíč) | `selector_position` | `duration_timing` | `temp` | `available_options` |
|---|---|---|---|---|---|
| 8 | ECO | 1 | 180 | 55 | 31 |
| 2 | INTENSIVO | 2 | 130 | 73 | 31 |
| 17 | NOTTE | 3 | 240 | 55 | 28 |
| 5 | UNIVERSALE | 4 | 120 | 57 | 31 |
| 16 | AUTO_GIORNALIERO_NO_TORBI | 5 | 95 | 60 | 31 |
| 9 | DELICATO | 6 | 85 | 48 | 31 |
| 19 | ZOOM_39 | 7 | 39 | 57 | 28 |
| 20 | RAPIDO_24 | 8 | 24 | 50 | 8 |
| 12 | PRELAVAGGIO | 9 | 5 | 0 | 8 |

- `cycle_name` = číslo v `Program=P<n>` – sedí s měřením P4 (P2 130, P5 120, P12 5, P19 39).
  P8 má v DB 180 min, naše myčka hlásí 230 → délky se mezi modely liší.
- `selector_position` v DB ≠ pozice na našem panelu (`r1`) → pořadí je pro demo/jiný model.
- Parametry s prázdnou hodnotou (`eco_opt`, `extradry_opt`, `halfload_opt`, `open_door`, `tab`) = volby
  programu; `available_options` je zřejmě bitová maska povolených voleb (31 = všech 5, 8 = jen jedna).
  Přiřazení bitů zatím neznámé → jadx.

## Další nálezy

- `nfc_dw_storable_prog`: stahovatelné programy (Turbo Power 90 min, Super Wash 130, Extra Hygiene 140 …)
  s příznaky eco/xd/hl/opendoor – pro NFC modely, u Wi-Fi zatím nevíme.
- `configured_appliances`: demo spotřebiče; myčka CDPM 95390XF s `interface_type=DishwasherInterfaceTypeFSTouch`
  (jiný typ rozhraní než naše „Program=Pxx“ – má programy `P_1_PLUS` … se `soil_level`).
- `error_code` (405 řádků) + `error_suggestion`: číselník chybových kódů – k dohledání `CodiceErrore`.
