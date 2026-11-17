# Návod: myčka Candy simply-Fi bez appky a bez cloudu

> ⚠️ **Ověřeno jen na modelu Candy CDIN 2L360PB** (v appce simply-Fi řada *nautilus*).
> Jiné modely Candy/Hoover se simply-Fi mohou mít jiná pole stavu, kódy programů i příkazy.
> Čtení stavu je bezpečné vyzkoušet kdekoli; **příkazy (start/stop) na jiném modelu posílej opatrně**
> a jen když stojíš u myčky. Výsledek dej prosím vědět v issues.

Postup od nuly: najít myčku v síti, získat její klíč, přečíst stav a ovládat ji z prohlížeče.

## Co je potřeba

- Myčka už **připojená k domácí Wi-Fi**. Připojení se nastavuje jednou v appce simply-Fi
  a tyhle nástroje ho neřeší ani nemění (endpoint `http-config.json` záměrně nepoužívají).
- PC nebo telefon ve **stejné síti** jako myčka.
- Python 3.8+ pro nástroje. Webový ovladač potřebuje Python 3.12+ a [uv](https://docs.astral.sh/uv/),
  nebo Docker.
- Kopie tohoto repozitáře; všechny příkazy se spouští z jeho kořene.

## 1. Najdi IP adresu myčky

```bash
python -m candy_netscan
```

Vypíše zařízení v síti a označí kandidáty (výrobce Candy/Haier nebo Espressif, odpověď na
`/http-read.json`). Jistotu dá pokus: myčku vypni, zmizí ze seznamu; zapni, objeví se.
Když skript nevidí správnou síť, zadej ji ručně: `--subnet 192.168.1.0/24`.

V routeru pak myčce nastav **pevnou IP** (DHCP rezervace), jinak se po restartu může změnit.

## 2. Získej klíč

Komunikace je „šifrovaná“ XORem 16znakovým klíčem, který má každý modul vlastní. Jde ho dopočítat
z jedné odpovědi myčky (princip v [pokusu P13](pokusy/2026-11-01-ziskani-klice.md)):

```bash
python -m candy_netscan.find_key <ip>
```

## 3. Ulož IP a klíč do `.env`

Zkopíruj `.env.example` na `.env` a doplň `CANDY_IP` a `CANDY_KEY`. Soubor `.env` je v `.gitignore`;
**klíč nikam nepublikuj** – kdo ho zná a je ve tvé síti, může myčku ovládat.

## 4. Vyzkoušej čtení stavu

```bash
python candy_netscan/candy_watch.py --log data/watch/test.jsonl
```

Vypisuje změny stavu (program, zbývající čas, dvířka…). Ukončení Ctrl+C.

## 5. Ovládání

**Na myčce zapni režim dálkového ovládání** (tlačítko Wi-Fi na panelu). Bez něj myčka příkazy
ignoruje, i když odpoví „SUCCESS“. Při mačkání panelu se režim na ~5 s vypne – panel má přednost.

Z příkazové řádky (bez `--send` jen ukáže, co by se poslalo):

```bash
python -m candy_netscan.send start P12          # dry-run: vypíše plaintext příkazu
python -m candy_netscan.send start P12 --send   # ostře: předmytí (5 min)
python -m candy_netscan.send stop --send        # zastavení
```

Kódy programů jsou v [`protokol.md`](protokol.md#programy-p4-p5) – platí pro náš model, jinde se mohou lišit.

## 6. Webový ovladač

```bash
uv sync
uv run uvicorn ovladac.main:app --host 0.0.0.0 --port 8103
```

Stránka: http://127.0.0.1:8103, z mobilu `http://<IP počítače>:8103`. Výchozí je `DRY_RUN=true`
(nic se neposílá) – pro ostrý provoz nastav v `.env` `DRY_RUN=false`. Docker: [`nasazeni.md`](nasazeni.md).

## Řešení problémů

| Příznak | Příčina a řešení |
|---|---|
| Sken myčku nenajde | Myčka je vypnutá nebo v jiné síti (host Wi-Fi, VLAN). Zkus `--subnet` s rozsahem sítě, kde je myčka. |
| `find_key` klíč nenajde | Odpověď nezačíná známým textem – jiný firmware. Ulož hex přes `--hex` a založ issue (bez klíče!). |
| Čtení vrací timeout / „Remote end closed connection“ | Modul zvládne **jen jednoho klienta**: zavři appku simply-Fi, nespouštěj ovladač dvakrát (PC i Docker). |
| Modul nereaguje vůbec (ping jde, HTTP ne) | Zasekl se – pomůže jen vypnout myčku úplně (vypínač, případně ze zásuvky) a za chvíli zapnout. |
| Příkaz vrátí „SUCCESS“, ale nic se nestane | Modul hlásí úspěch i na ignorovaný příkaz. Zkontroluj režim dálkového ovládání a ověř efekt čtením stavu. Pauza (`Pa`) na našem modelu nefunguje vůbec. |
| Hned po startu stav „pauza“ | Normální rozběh na ~4 s, pak přejde do běhu. |
| Stav se mění pomalu | Ovladač čte á 15 s (`POLL_SECONDS`, minimum 3 s – modul nezahlcovat). |

Statistiky (počty cyklů) myčka lokálně nevydá, posílá je jen do cloudu – ovladač si historii vede sám.
