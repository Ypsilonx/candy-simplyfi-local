# P13 – Získání IP adresy a XOR klíče myčky

Cíl: popsat postup, jak se k myčce dostat bez appky simply-Fi – najít její IP a klíč, kterým modul
„šifruje“ komunikaci. Postup byl proveden na začátku projektu, tady je sepsaný zpětně a dnes ověřený
nástrojem `candy_netscan/find_key.py`.

## 1. IP adresa

1. Skript na sledování sítě (dnes `python -m candy_netscan`) vypíše zařízení v LAN (ARP tabulka,
   výrobce podle OUI, sonda na `/http-read.json`).
2. Ověření: myčka vypnutá → zařízení v seznamu chybí; zapnutá → objeví se. Tím je IP jistá.
   Modul je ESP (v OUI často „Espressif“), sonda na `/http-read.json` odpoví hex řetězcem.

Doporučení: v routeru myčce nastavit pevnou IP (DHCP rezervace), jinak se po restartu může změnit.

## 2. Klíč

1. `GET http://<ip>/http-read.json?encrypted=1` vrátí dlouhý hex řetězec – zašifrovaný stav.
2. Z komunity Home Assistant ([HA]) je známo, že jde o XOR s 16znakovým ASCII klíčem opakovaným
   přes celou zprávu a že plaintext je JSON `{"statusDWash": {...}}`.
3. XOR je symetrický: `šifra = text ⊕ klíč` ⇒ `klíč = šifra ⊕ text`. Stačí tedy znát prvních 16 znaků
   textu. Naše myčka posílá na začátku vždy `{\r\n\t"statusDWash` – to je přesně 16 bajtů.
4. Skript XORne prvních 16 bajtů šifry se známým začátkem → klíč. Kontrola: s tímto klíčem se dešifruje
   celá zpráva na platný JSON.

Příklad principu (smyšlená čísla): šifra začíná bajtem `0x3A`, text znakem `{` (`0x7B`) →
první znak klíče `0x3A ⊕ 0x7B = 0x41` = `A`. Tak dál pro všech 16 pozic.

Každý modul má **vlastní** klíč, myčka ho sama neposílá – jde jen dopočítat z její odpovědi.

## Výsledek

- ✅ `python -m candy_netscan.find_key <ip>` (nebo `--hex <řetězec>`) vrátí klíč; na naší myčce shoda
  s klíčem v `.env` (2026-11-01).
- Nástroj zkouší několik variant začátku (`\r\n` / `\n` / bez odsazení) pro případ, že jiný firmware
  formátuje JSON jinak; přijme jen klíč, se kterým se celá zpráva rozparsuje.

[HA]: https://community.home-assistant.io/t/dishwasher-candy-simply-fi-cdi-6015-wifi/136543
