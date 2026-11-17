# Guide: Candy simply-Fi dishwasher without the app and without the cloud

[🇨🇿 Česky](navod.md) | 🇬🇧 English

> ⚠️ **Tested only on the Candy CDIN 2L360PB** (in the simply-Fi app it belongs to the *nautilus* family).
> Other Candy/Hoover models with simply-Fi may use different status fields, program codes and commands.
> Reading the status is safe to try anywhere; **send commands (start/stop) to another model carefully**
> and only while standing at the dishwasher. Please report the result in the issues.

From scratch: find the dishwasher on the network, get its key, read the status and control it from a browser.

## Requirements

- The dishwasher is already **connected to your home Wi-Fi**. That is set up once in the simply-Fi app;
  these tools neither handle nor change it (the `http-config.json` endpoint is deliberately not used).
- A PC or phone on the **same network** as the dishwasher.
- Python 3.8+ for the tools. The web controller needs Python 3.12+ and [uv](https://docs.astral.sh/uv/),
  or Docker.
- A copy of this repository; all commands are run from its root.

## 1. Find the dishwasher's IP address

```bash
python -m candy_netscan
```

Lists devices on the network and flags candidates (vendor Candy/Haier or Espressif, answers
`/http-read.json`). To be sure: switch the dishwasher off, it disappears from the list; switch it on,
it comes back. If the script picks the wrong network, set it manually: `--subnet 192.168.1.0/24`.

Then give the dishwasher a **fixed IP** in your router (DHCP reservation), otherwise it may change.

## 2. Get the key

Communication is "encrypted" by XOR with a 16-character key unique to each module. It can be computed
from a single answer of the dishwasher:

```bash
python -m candy_netscan.find_key <ip>
```

## 3. Save the IP and key to `.env`

Copy `.env.example` to `.env` and fill in `CANDY_IP` and `CANDY_KEY`. `.env` is in `.gitignore`;
**never publish the key** – anyone who knows it and is on your network can control the dishwasher.

## 4. Try reading the status

```bash
python candy_netscan/candy_watch.py --log data/watch/test.jsonl
```

Prints status changes (program, remaining time, door…). Stop with Ctrl+C.

## 5. Control

**Turn on remote control mode on the dishwasher** (Wi-Fi button on the panel). Without it the dishwasher
ignores commands even though it answers "SUCCESS". Pressing panel buttons turns the mode off for ~5 s –
the panel has priority.

From the command line (without `--send` it only shows what would be sent):

```bash
python -m candy_netscan.send start P12          # dry-run: prints the plaintext command
python -m candy_netscan.send start P12 --send   # for real: pre-wash (5 min)
python -m candy_netscan.send stop --send        # stop
```

## 6. Web controller

```bash
uv sync
uv run uvicorn ovladac.main:app --host 0.0.0.0 --port 8103
```

Page: http://127.0.0.1:8103, from a phone `http://<PC IP>:8103`. The default is `DRY_RUN=true`
(nothing is sent) – set `DRY_RUN=false` in `.env` for real use. The UI is in Czech.
Docker: `docker compose up -d --build`, details in [`nasazeni.md`](nasazeni.md) (Czech).

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Scan does not find the dishwasher | It is off or on another network (guest Wi-Fi, VLAN). Try `--subnet` with the dishwasher's network range. |
| `find_key` finds no key | The answer does not start with the known text – different firmware. Save the hex via `--hex` and open an issue (without the key!). |
| Reads time out / "Remote end closed connection" | The module handles **only one client**: close the simply-Fi app, don't run the controller twice (PC and Docker). |
| Module does not respond at all (ping works, HTTP doesn't) | It hung – only switching the dishwasher fully off (power switch, or unplug) and on again helps. |
| Command returns "SUCCESS" but nothing happens | The module reports success even for ignored commands. Check remote control mode and verify the effect by reading the status. Pause (`Pa`) does not work on our model at all. |
| "Pause" right after start | Normal ~4 s spin-up, then it switches to running. |
| Status changes slowly | The controller reads every 15 s (`POLL_SECONDS`, minimum 3 s – don't flood the module). |

The dishwasher does not provide statistics (cycle counts) locally, it sends them only to the cloud –
the controller keeps its own history.

## Protocol summary

Verified on the CDIN 2L360PB unless marked otherwise; full Czech version with sources:
[`protokol.md`](protokol.md). All status values are strings.

### Commands (`http-write.json`, plaintext before XOR)

| Action | Parameters | Works |
|---|---|---|
| Start | `DelayStart=<d>&ExtraDry=<0/1>&OpenDoorOpt=<0/1>&TreinUno=<0/1>&Program=P<n>&MetaCarico=<0/1>&OpzProg=<mask>&w1=<position>&StartStop=1&Eco=<0/1>` | ✅ |
| Stop / cancel delayed start | `Reset=1` | ✅ |
| Pause / resume | `Pa=1` / `Pa=0` | ❌ answers SUCCESS, does nothing |
| Water hardness | `HL=<0–5>` → `r7` | ✅ |
| Sound | `BM=<0/1>` → `r6` | ✅ |
| Remember last cycle | `LC=<0/1>` → `r8` | ✅ |
| Cleaning cycle | start `P2` with an empty dishwasher + `w3=H_2` | ✅ |

- `DelayStart` in the command = number of **half-hours** (0–48); the status returns **remaining minutes**.
- `w1` = program position on the panel (= `r1`). `OpzProg` mask: 1 ExtraDry, 2 half load, 4 Eco, 8 3-in-1,
  16 open door (from the app's code, unverified).
- There is no "just select a program" command – the program reaches the dishwasher only with a start.

### Status fields (`statusDWash`)

| Field | Meaning |
|---|---|
| `StatoWiFi` | 1 = remote control enabled, 0 = read only |
| `StatoDWash` | 1 reset, 2 selection, 3 running (also waiting delayed start), 4 pause (door open), 5 finished, 6 error |
| `r2` | phase: 0 none, 1 pre-wash, 2 wash, 3 rinse, 4 drying, 5 end, 9 pause |
| `Program` / `r1` | internal program code `P<n>` / position on the panel (1–5) |
| `RemTime` | remaining minutes; when idle the nominal duration |
| `StartStop` | program active (stays 1 after the end until a reset) |
| `DelayStart` | minutes until delayed start |
| `OpenDoor` | door open; while running → pause, resumes ~3 s after closing |
| `MissSalt`, `MissRinse` | salt / rinse aid missing (flag only) |
| `CodiceErrore` | `E<n>`, n > 0 = error |
| `r6` / `r7` / `r8` | sound / water hardness / remember last cycle – stored in the dishwasher |
| `r9` | echo of `w3` from the last start (`H_2` = cleaning) – firmware does not escape `\`, may break strict JSON |

### Programs (CDIN 2L360PB)

| `Program` | Name (app) | Panel (`r1`) | Duration [min] |
|---|---|---|---|
| P2 | Intensive 73 °C | 1 | 130 (+10 ExtraDry) |
| P5 | Universal 57 °C | 2 | 120 |
| P8 | Eco 55 °C | 3 | 230 |
| P12 | Pre-wash (default after power-on) | 4 | 5 |
| P19 | Zoom 39 | 5 | 39 |
| P9, P16, P17, P20 | Delicate, Auto daily, Night, Rapid 24 – app only, not verified | – | – |
