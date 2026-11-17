# netscan_for_candy – local control of a Candy simply-Fi dishwasher

[🇨🇿 Česky](README.md) | 🇬🇧 English

![License: MIT](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.8%2B%20%7C%20controller%203.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-web%20UI-009688?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![Candy simply-Fi](https://img.shields.io/badge/Candy-simply--Fi-E30613)

Read the status of a Candy dishwasher with the **simply-Fi** Wi-Fi module and control it straight
over your home network – **without the mobile app and without the cloud**. The project started as
reverse engineering of the protocol; besides the research tools it contains a web controller that runs
on a PC or in Docker.

> ⚠️ **Tested only on the Candy CDIN 2L360PB** (in the simply-Fi app it belongs to the *nautilus* family).
> Other models may use different status fields, program codes and commands – reading the status is safe,
> try commands carefully and only while standing at the dishwasher. Step-by-step guide:
> **[`docs/guide.md`](docs/guide.md)**.
>
> ⚠️ Unofficial project, not affiliated with Candy/Haier. Sending commands to the dishwasher is at your
> own risk. The `http-config.json` endpoint (changes the module's Wi-Fi and key) is deliberately never
> used – it could cut the module off your network.

**Language note:** code, CLI and this README are in English; the detailed docs (`docs/protokol.md`,
experiment notes in `docs/pokusy/`) and the web UI are in Czech. The English guide contains a summary
of the protocol.

## Features

- **Web controller** (`ovladac/`, FastAPI + vanilla JS, works offline): status and remaining time,
  start/stop a program, delayed start, cleaning cycle, cycle history and maintenance reminders
  (filter, descaling).
- **Network scan** – finds the dishwasher on the LAN (ARP + vendor OUI + probe of `/http-read.json`).
- **Key recovery** – computes the module's XOR key from its own answer (`find_key.py`).
- **Status watch** into a JSONL log with changes between reads (`candy_watch.py`).
- **Command line** (`send.py`) – dry-run by default, shows the plaintext command first.
- **Protocol description** in `docs/protokol.md` (Czech) – endpoints, status fields, commands, each with
  its source and how well it is verified.

## How the protocol works (short)

The module is an ESP with an HTTP server on port 80. Data is "encrypted" only by XOR with a
16-character key:

```text
GET http://<ip>/http-read.json?encrypted=1                 → hex → XOR key → {"statusDWash": {...}}
GET http://<ip>/http-write.json?encrypted=1&data=<hex>     ← XOR("StartStop=1&Program=P12&…")
```

The module answers "SUCCESS" even to a command it ignores → always verify the result by reading the
status. Field and command summary: [`docs/guide.md`](docs/guide.md#protocol-summary).

## Finding the IP and the key

1. **IP address:** `python -m candy_netscan` lists devices on the network and flags candidates
   (vendor Candy/Haier or Espressif, answers `/http-read.json`). To be sure, switch the dishwasher off –
   it disappears; switch it on – it comes back. Then give it a fixed IP in your router (DHCP reservation).
2. **Key:** every module has its own 16-character key and never sends it anywhere. It can be computed,
   though: XOR is symmetric (`key = cipher ⊕ text`) and the encrypted status always starts the same way
   (`{\r\n\t"statusDWash` – exactly 16 bytes). The approach builds on findings of the Home Assistant
   community:

   ```bash
   python -m candy_netscan.find_key <ip>          # one status read → prints the key
   python -m candy_netscan.find_key --hex <hex>   # or from an already downloaded payload
   ```

## Quick start

Copy `.env.example` to `.env` and fill in `CANDY_IP` and `CANDY_KEY` (the key must never go into git).

### Tools (standard library only, Python 3.8+, runs even in Pydroid on a phone)

Run from the project root:

```bash
python -m candy_netscan                                   # find the dishwasher
python candy_netscan/candy_watch.py --log data/watch/2026-01-01_test.jsonl   # watch the status
python -m candy_netscan.send start P12                    # dry-run: only shows the command
python -m candy_netscan.send start P12 --send             # for real
```

### Web controller (Python 3.12+, [uv](https://docs.astral.sh/uv/))

```bash
uv sync
uv run uvicorn ovladac.main:app --host 0.0.0.0 --port 8103
```

The page runs at http://127.0.0.1:8103. The default is `DRY_RUN=true` – nothing is sent to the
dishwasher; set `DRY_RUN=false` in `.env` for real use. Docker deployment: [`docs/nasazeni.md`](docs/nasazeni.md)
(Czech; in short `docker compose up -d --build`, host port `MYCKA_HOST_PORT`, default 8103).

**The dishwasher handles only one client** – don't run the controller twice and keep the simply-Fi app
closed; concurrent connections hang the Wi-Fi module. Status is read at most once per 3 s (default 15 s).

## Structure

| Path | Contents |
|---|---|
| `candy_netscan/` | network scan, `client.py` (XOR, read, write – shared by everything else), `find_key.py`, `candy_watch.py`, `send.py` |
| `ovladac/` | web controller: `services/` (status model, programs, history), `routers/` (REST API), `static/` (UI) |
| `docs/guide.md` / `docs/navod.md` | step-by-step guide and troubleshooting (EN / CZ) |
| `docs/protokol.md` | current protocol map (CZ) |
| `docs/pokusy/` | experiment notebook the findings come from (CZ) |
| `docs/specs/` | controller design (CZ) |
| `data/watch/` | raw logs of the experiments |
| `tests/` | tests (`uv run pytest`) |

## Reuse in Home Assistant and elsewhere

The code is MIT licensed – feel free to take it into Home Assistant, Node-RED, ioBroker or your own
automation. Best starting points:

- [`candy_netscan/client.py`](candy_netscan/client.py) – the whole network layer (XOR, read, write)
  in ~70 lines without dependencies, easy to port to another language.
- [`docs/guide.md`](docs/guide.md#protocol-summary) – meaning of the status fields and the commands,
  including what does not work.
- [`ovladac/services/model.py`](ovladac/services/model.py) and `programs.json` – turning the raw status
  into something readable (phase, remaining time, programs).

Two things apply to any integration: the dishwasher handles **only one client** (the simply-Fi app counts
too) and the module reports success even for an ignored command – always verify the effect by reading
the status. If you build something or test it on another model, please let us know in the issues.

## License

[MIT](LICENSE)

## Acknowledgements

The initial knowledge of the message format comes from the community –
[thread on Home Assistant Community](https://community.home-assistant.io/t/dishwasher-candy-simply-fi-cdi-6015-wifi/136543)
and the [ofalvai/home-assistant-candy](https://github.com/ofalvai/home-assistant-candy) integration.
