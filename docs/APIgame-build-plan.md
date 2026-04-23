# APIgame Build Plan

> Generated 2026-04-23.
> Reference docs: `docs/APIgame-context.md`, `docs/PIN_REFERNCE.md`, `docs/tinydrop-droplet-setup-guide.md`.

## Resolved design decisions

| Decision | Choice | Rationale |
|---|---|---|
| Display orientation | **Landscape 320×240** (`ROTATION 1`) | PIN_REFERENCE says tested at this setting; four verb boxes fit better horizontally |
| MQTT library (ESP32) | `knolleary/PubSubClient` with 512-byte buffer | Widely documented, sufficient for <500 byte JSON messages |
| JSON library (ESP32) | `bblanchon/ArduinoJson` v7 | De facto standard for Arduino JSON |
| Google API client (server) | `google-api-python-client` + `google-auth` + `google-auth-oauthlib` | Standard Google SDK, handles token refresh |
| OAuth scope | `https://www.googleapis.com/auth/calendar.events` | Events-only; narrowest sufficient scope |
| Leaderboard DB | SQLite at `/opt/apigame/data/leaderboard.db` | Simple, zero-config, adequate for showcase traffic |
| Admin MQTT auth | None beyond broker password | Port 1883 is localhost-only; adequate for a showcase |
| Big-screen HTML | Served by FastAPI as static files from `big-screen/` | One less moving part |
| MQTT credentials | Reuse existing `esp32` user | Per context doc; don't fragment broker config |
| Agent MQTT connection | `127.0.0.1:1883` (local, no TLS) | Agent runs on same host as broker |
| ESP32 MQTT connection | `mqtt.tinydrop.win:8883` (TLS) | Remote, uses Let's Encrypt cert already on broker |

## Important notes

**Nginx path-prefix requires one controlled modification to the tinydrop Nginx config.**
The context doc requires path-prefix `/apigame/` on the same domain (no subdomain, no DNS changes, no new cert). The only way to add a `location /apigame/` block to the existing HTTPS server block is to add a single `include` line to `/etc/nginx/sites-available/tinydrop`. Step 8 documents the exact change and rollback. This is the **only** modification to any tinydrop infrastructure file.

**Display orientation discrepancy.** The context doc says "240×320 portrait" but `PIN_REFERNCE.md` specifies `ROTATION 1` (landscape, 320×240) and is marked "all hardware tested and working." The UI mockup in the context doc is wider than tall and fits landscape naturally. This plan uses **landscape 320×240** throughout.

---

## Step 1 — Repo skeleton, CLAUDE.md, PlatformIO project, hardware cheatsheet

**Goal:** Create the full project structure, project-specific `CLAUDE.md`, PlatformIO project that compiles, and the ESP32 hardware cheatsheet README.

**Touches:**
- `CLAUDE.md`
- `.gitignore`
- `esp32-firmware/platformio.ini`
- `esp32-firmware/include/secrets.h.example`
- `esp32-firmware/src/main.cpp`
- `esp32-firmware/README.md`
- `server/agent/requirements.txt`
- `server/web/requirements.txt`
- Empty placeholder directories: `server/agent/`, `server/web/`, `big-screen/`, `deploy/systemd/`, `deploy/nginx/`, `deploy/scripts/`

**Prerequisites:** PlatformIO CLI installed locally (`pio --version` works). Repo cloned.

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 1).
>
> Create the full repo skeleton per context doc section 8:
>
> 1. **`CLAUDE.md`** — project-specific instructions. Include: project overview (one paragraph), architecture summary (ESP32 → MQTT → Python agent → Calendar API; agent → FastAPI/WS → big screen), key reference files (`docs/APIgame-context.md`, `docs/APIgame-build-plan.md`, `docs/PIN_REFERNCE.md`), the non-negotiables from context doc section 7 verbatim, file layout conventions (many small files, 200–400 lines, 800 max), key commands (pio build, flash, deploy, reset-calendar), and testing approach (server modules unit-tested locally, integration on droplet; ESP32 via serial+display; MQTT via mosquitto_pub/sub; web via curl+browser).
>
> 2. **`.gitignore`** — Python (`__pycache__/`, `*.pyc`, `.venv/`, `venv/`), PlatformIO (`.pio/`, `.vscode/`), secrets (`secrets.h`, `.env`), OS (`.DS_Store`), data (`*.db`).
>
> 3. **`esp32-firmware/platformio.ini`** — board `esp32dev`, framework `arduino`, monitor_speed 115200, lib_deps: `bodmer/TFT_eSPI@^2.5.0`, `knolleary/PubSubClient@^2.8`, `bblanchon/ArduinoJson@^7.0.0`. Use `build_flags` to configure TFT_eSPI pins from `docs/PIN_REFERNCE.md`: `-DUSER_SETUP_LOADED=1 -DILI9341_DRIVER=1 -DTFT_MOSI=23 -DTFT_MISO=19 -DTFT_SCLK=18 -DTFT_CS=5 -DTFT_DC=2 -DTFT_RST=4 -DSPI_FREQUENCY=40000000`.
>
> 4. **`esp32-firmware/include/secrets.h.example`** — template with `WIFI_SSID`, `WIFI_PASSWORD`, `MQTT_HOST` (`mqtt.tinydrop.win`), `MQTT_PORT` (8883), `MQTT_USER` (`esp32`), `MQTT_PASSWORD`, `DEVICE_ID` (`handheld-01`).
>
> 5. **`esp32-firmware/src/main.cpp`** — minimal: includes Arduino.h, setup() inits Serial at 115200 and prints "APIgame boot", loop() empty.
>
> 6. **`esp32-firmware/README.md`** — hardware cheatsheet covering: how to build (`pio run`), how to flash (`pio run -t upload`), how to monitor serial (`pio device monitor`), combined (`pio run -t upload -t monitor`), how `secrets.h` works (copy from example, fill in, gitignored), full pin map table from `docs/PIN_REFERNCE.md` with GPIO numbers and functions, display config (ILI9341, SPI, landscape 320×240, rotation 1), joystick config (analog X/Y on GPIO 34/35, button on GPIO 13, center 2048, deadzone 500), action button on GPIO 12, and a "where things will go" section mapping future source files to their purpose.
>
> 7. **`server/agent/requirements.txt`** — `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `paho-mqtt`, `python-dotenv`.
>
> 8. **`server/web/requirements.txt`** — `fastapi`, `uvicorn[standard]`, `websockets`, `aiofiles`, `python-dotenv`, `paho-mqtt`.
>
> 9. Create empty placeholder directories (with `.gitkeep` files): `big-screen/`, `deploy/systemd/`, `deploy/nginx/`, `deploy/scripts/`.
>
> Do NOT create any implementation files beyond what's listed above. The goal is a compilable skeleton.

### Test checklist (human performs, tick each)

- [ ] `cd esp32-firmware && pio run` — compiles with zero errors (warnings OK)
- [ ] `cat esp32-firmware/README.md` — pin map matches `docs/PIN_REFERNCE.md` exactly
- [ ] `cat esp32-firmware/include/secrets.h.example` — has all placeholders, no real credentials
- [ ] `cat CLAUDE.md` — contains non-negotiables, file layout, key commands
- [ ] `cat .gitignore` — includes `secrets.h`, `.env`, `.pio/`, `__pycache__/`
- [ ] Repo layout matches context doc section 8 (dirs exist, no extra files)

### Rollback / if it fails

Delete all generated files and re-run. If `pio run` fails, check that PlatformIO is installed and the board `esp32dev` platform is downloaded (`pio platform install espressif32`). If TFT_eSPI build errors mention User_Setup.h, confirm the build_flags include `-DUSER_SETUP_LOADED=1`.

---

## Step 2 — Droplet: directory tree, Python venv, .env template

**Goal:** Prepare the droplet filesystem for APIgame without disturbing tinydrop.

**Touches:**
- `/opt/apigame/` tree on droplet (agent/, web/, config/, data/, logs/)
- `/opt/apigame/venv/` — Python virtual environment
- `/opt/apigame/config/.env` — template with placeholders
- `deploy/scripts/setup-droplet.sh` (local, committed)

**Prerequisites:** SSH access to `root@162.243.231.61`. Step 1 complete.

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 2).
>
> Write a shell script `deploy/scripts/setup-droplet.sh` that, when run locally, SSHes into the droplet and sets up the apigame directory tree. The script must:
>
> 1. SSH to `root@162.243.231.61` and execute commands to:
>    - Create directories: `/opt/apigame/{agent,web,config,data,logs}`
>    - Create Python venv: `python3 -m venv /opt/apigame/venv`
>    - Install base pip packages in venv from `server/agent/requirements.txt` and `server/web/requirements.txt` (scp both files first, then pip install)
>    - Create `/opt/apigame/config/.env` with these placeholder values:
>      ```
>      GOOGLE_CLIENT_ID=
>      GOOGLE_CLIENT_SECRET=
>      GOOGLE_REFRESH_TOKEN=
>      MQTT_HOST=127.0.0.1
>      MQTT_PORT=1883
>      MQTT_USER=esp32
>      MQTT_PASS=
>      CALENDAR_ID=primary
>      TZ=America/New_York
>      ```
>    - `chmod 600 /opt/apigame/config/.env`
>
> 2. The script should be idempotent (safe to run twice).
> 3. The script must **never touch** `/opt/tinydrop/` or any tinydrop files.
> 4. Add `set -euo pipefail` and print each step for visibility.
>
> After writing the script, make it executable (`chmod +x`) and tell me to run it. Do NOT run it yourself — I'll execute it manually so I can watch SSH auth.

### Test checklist (human performs, tick each)

- [ ] Run `bash deploy/scripts/setup-droplet.sh` — completes without errors
- [ ] `ssh root@162.243.231.61 "ls -la /opt/apigame/"` — shows agent/, web/, config/, data/, logs/
- [ ] `ssh root@162.243.231.61 "/opt/apigame/venv/bin/pip list"` — shows google-api-python-client, paho-mqtt, fastapi, etc.
- [ ] `ssh root@162.243.231.61 "cat /opt/apigame/config/.env"` — shows placeholders
- [ ] `ssh root@162.243.231.61 "ls /opt/tinydrop/"` — unchanged, still has agent/, web/, config/, etc.

### Rollback / if it fails

`ssh root@162.243.231.61 "rm -rf /opt/apigame"` and re-run. If venv creation fails, check Python version on droplet (`python3 --version`, needs 3.10+). If pip install fails, check droplet has internet and `pip` can reach PyPI.

---

## Step 3 — Google OAuth2: GCP project, Calendar API, refresh token

**Goal:** Obtain a Google OAuth2 refresh token for Calendar API access and store it in the droplet's `.env`.

**Touches:**
- `scripts/get_refresh_token.py` (local helper, one-time use)
- `/opt/apigame/config/.env` on droplet (fill in real values)

**Prerequisites:** A Google account for the dummy calendar. Step 2 complete (`.env` template exists on droplet).

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 3).
>
> Write a helper script `scripts/get_refresh_token.py` that obtains a Google OAuth2 refresh token. The script should:
>
> 1. Require `google-auth-oauthlib` (user installs locally: `pip install google-auth-oauthlib`).
> 2. Look for `credentials.json` in the current directory (downloaded from Google Cloud Console).
> 3. Use `InstalledAppFlow.from_client_secrets_file` with scope `https://www.googleapis.com/auth/calendar.events`.
> 4. Run `flow.run_local_server(port=0)` to open browser for consent.
> 5. Print the `refresh_token`, `client_id`, and `client_secret` clearly labeled so the user can copy them into `.env`.
> 6. Include a docstring at the top with step-by-step instructions:
>    - Go to console.cloud.google.com
>    - Create a project (or select existing)
>    - Enable "Google Calendar API" (APIs & Services → Library)
>    - Create OAuth 2.0 Client ID (APIs & Services → Credentials → Create Credentials → OAuth client ID → Desktop app)
>    - Download the JSON → save as `credentials.json` in the repo root
>    - Run this script: `python scripts/get_refresh_token.py`
>    - Copy the printed values into `/opt/apigame/config/.env` on the droplet
>
> Also add `credentials.json` and `token.json` to `.gitignore` if not already there.
>
> Do NOT run the script or attempt OAuth — I will run it manually in a browser.

### Test checklist (human performs, tick each)

- [ ] Google Cloud project created, Calendar API enabled, OAuth client ID created
- [ ] `credentials.json` downloaded to repo root
- [ ] `python scripts/get_refresh_token.py` — browser opens, consent granted, refresh token printed
- [ ] Verify token works: `curl -s -X POST https://oauth2.googleapis.com/token -d "client_id=YOUR_ID&client_secret=YOUR_SECRET&refresh_token=YOUR_TOKEN&grant_type=refresh_token" | python3 -m json.tool` — returns JSON with `access_token`
- [ ] `ssh root@162.243.231.61 "nano /opt/apigame/config/.env"` — fill in `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `MQTT_PASS`

### Rollback / if it fails

**This is a risky step (first OAuth handshake).** If the script fails:
- Check `credentials.json` is valid JSON and has `installed.client_id` (not `web` type — must be Desktop app).
- If consent screen shows "unverified app" warning, click Advanced → Go to app (this is your own test project).
- If refresh_token is `None`, the consent was already granted previously. Go to myaccount.google.com/permissions, revoke the app, and re-run.
- If token exchange curl fails with `invalid_grant`, the refresh token may have expired (happens if GCP project is in "Testing" mode and >7 days old). Re-run the consent flow.

---

## Step 4 — calendar_client.py: token exchange + events.list

**Goal:** Write a standalone Python module that uses the refresh token to authenticate and list Google Calendar events. Prove the full OAuth → API call chain works before any game logic.

**Touches:**
- `server/agent/calendar_client.py`

**Prerequisites:** Step 3 complete (valid credentials in droplet `.env`).

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 4).
>
> Write `server/agent/calendar_client.py` — a standalone module that:
>
> 1. Loads credentials from environment variables (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`) using `python-dotenv`. Load path: `Path(__file__).parent.parent / 'config' / '.env'` (resolves to `/opt/apigame/config/.env` when deployed).
> 2. Builds `google.oauth2.credentials.Credentials` from the refresh token with token_uri `https://oauth2.googleapis.com/token` and scope `https://www.googleapis.com/auth/calendar.events`.
> 3. Builds the Calendar API service via `googleapiclient.discovery.build('calendar', 'v3', credentials=creds)`.
> 4. Exposes a `CalendarClient` class with one method for now: `list_events() -> list[dict]` — calls `events().list()` on the primary calendar, timeMin=now, timeMax=now+2days, singleEvents=True, orderBy='startTime', timeZone='America/New_York'. Returns the list of event dicts.
> 5. The class should handle token refresh automatically (google-auth does this) and log a warning on 401.
> 6. When run as `__main__`, call `list_events()` and pretty-print the results.
>
> Keep the module focused — no game logic, no MQTT. Just calendar CRUD foundation.
>
> After writing, scp to droplet and test:
> ```
> scp server/agent/calendar_client.py root@162.243.231.61:/opt/apigame/agent/
> ssh root@162.243.231.61 "/opt/apigame/venv/bin/python /opt/apigame/agent/calendar_client.py"
> ```

### Test checklist (human performs, tick each)

- [ ] `scp` succeeds
- [ ] `ssh root@... "/opt/apigame/venv/bin/python /opt/apigame/agent/calendar_client.py"` — prints event list (may be empty if dummy calendar is new, that's OK)
- [ ] No traceback, no auth errors
- [ ] If calendar has events, they appear with id, summary, start time
- [ ] Open Google Calendar in browser for the dummy account — matches what the script printed

### Rollback / if it fails

**This is a risky step (first real Google API call from droplet).**
- `invalid_grant` → refresh token is bad; re-run Step 3.
- `HttpError 403 (insufficient permissions)` → wrong OAuth scope; re-run consent with `calendar.events` scope.
- `HttpError 403 (Calendar API not enabled)` → go to GCP console, enable Calendar API.
- Connection timeout → droplet can't reach googleapis.com; check `curl https://www.googleapis.com` from droplet.
- Module not found → pip packages missing in venv; re-run `setup-droplet.sh`.

---

## Step 5 — Game operations: seed, list, insert-random, patch-random, delete-random

**Goal:** Extend the calendar client with the five operations the game needs. Each testable individually from CLI.

**Touches:**
- `server/agent/calendar_client.py` (extend `CalendarClient` class)
- `deploy/scripts/reset-calendar.sh` (convenience wrapper)

**Prerequisites:** Step 4 complete (list_events works).

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 5).
>
> Extend `server/agent/calendar_client.py` with these methods on `CalendarClient`:
>
> 1. **`seed(count=3) -> list[str]`** — Delete all events on the calendar first (clean slate). Then insert `count` events using titles from a pool (`"Coffee with Sam"`, `"Dentist"`, `"Standup"`, `"Lunch meeting"`, `"Team sync"`, `"1:1 with Jordan"`, `"Code review"`, `"Design crit"`, `"Office hours"`, `"Workshop"`), at times now+30min, now+2hr, now+1day (for 3 events). Return list of created event IDs. Store IDs in `self._event_ids`.
> 2. **`insert_random() -> dict`** — Insert an event with a random title from the pool, time = now + random 1–24hr offset. Return `{"status": 201, "event_id": ..., "summary": ..., "latency_ms": ...}`. Add new ID to `self._event_ids`.
> 3. **`patch_random() -> dict`** — Pick a random event from `self._event_ids`, PATCH its summary to a different random title. Return `{"status": 200, "event_id": ..., "summary": ..., "latency_ms": ...}`. If no events exist, return `{"status": 404, "error": "no events to patch"}`.
> 4. **`delete_random() -> dict`** — Pick a random event from `self._event_ids`, delete it. Return `{"status": 204, "event_id": ..., "latency_ms": ...}`. Remove from `self._event_ids`. On 404 (already deleted), refresh the event list and retry once.
> 5. **`refresh_event_ids() -> list[str]`** — Re-list events and update `self._event_ids`. Called internally on 404.
>
> Each method should measure latency (time.time before/after the API call, convert to ms).
>
> Add CLI subcommands when run as `__main__`: `python calendar_client.py seed`, `insert`, `patch`, `delete`, `list`. Each prints the result dict as JSON.
>
> Also write `deploy/scripts/reset-calendar.sh` — a one-liner that SSHes to the droplet and runs `seed`.
>
> scp the updated file and test each operation from the droplet CLI.

### Test checklist (human performs, tick each)

- [ ] `ssh root@... ".../python .../calendar_client.py seed"` — prints 3 event IDs, no errors
- [ ] Check Google Calendar in browser — exactly 3 new events visible
- [ ] `ssh root@... ".../python .../calendar_client.py insert"` — returns status 201
- [ ] Calendar now shows 4 events
- [ ] `ssh root@... ".../python .../calendar_client.py patch"` — returns status 200, different summary
- [ ] Calendar shows updated event title
- [ ] `ssh root@... ".../python .../calendar_client.py delete"` — returns status 204
- [ ] Calendar shows 3 events again
- [ ] `ssh root@... ".../python .../calendar_client.py list"` — shows current events

### Rollback / if it fails

Revert `calendar_client.py` to Step 4 version. Common issues:
- `events().insert()` returns 400 → check event body format (needs `summary`, `start.dateTime`, `end.dateTime` with timezone).
- `events().patch()` returns 404 → stale event ID; run `list` to refresh.
- Rate limiting (403 `rateLimitExceeded`) → you're calling too fast; wait 10 seconds.

---

## Step 6 — Task engine: state machine, scoring, task generator, leaderboard

**Goal:** Build the pure-logic game engine — task generation, scoring rules, session state machine, leaderboard persistence. Fully unit-testable with no I/O dependencies.

**Touches:**
- `server/agent/task_engine.py`
- `server/agent/test_task_engine.py`

**Prerequisites:** None (pure logic; can be built in parallel with Step 5 if desired).

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 6).
>
> Write `server/agent/task_engine.py` — the pure game logic module. Follow TDD: write `server/agent/test_task_engine.py` first, then implement to pass. Target 80%+ coverage.
>
> The module should contain:
>
> 1. **`TaskGenerator`** — generates tasks per context doc rules:
>    - Natural-language prompts ≤4 words: "Add an event" (POST), "Update an event" (PUT), "Remove an event" (DELETE), "Refresh calendar" (GET, tutorial only).
>    - Round weighting: ~40% POST, ~30% PUT, ~30% DELETE, 0% GET.
>    - Never repeat same verb 3 times in a row.
>    - If event count <1, force POST.
>    - Returns `{"task_id": "tN", "text": "...", "expected_verb": "POST/PUT/DELETE"}`.
>
> 2. **`SessionState`** — state machine per context doc section 1:
>    - States: `NAME_ENTRY`, `TUTORIAL`, `ROUND`, `RESULTS`, `IDLE`.
>    - Tracks: player name, score, round_id, current task, time_left, tutorial step (0–3), event_count.
>    - Methods: `start_session(name)`, `advance_tutorial(verb) -> bool`, `submit_action(verb) -> result_dict`, `tick(elapsed_s)`, `play_again()`, `timeout() -> reset to IDLE`.
>    - Scoring: +3 correct, −2 wrong, −2 on API error. Score can go negative.
>    - Tutorial: four prompts in order GET→POST→PUT→DELETE. Each waits for correct verb. Wrong verb during tutorial = no score penalty, just retry.
>    - Round: 60s timer. Tasks stream one at a time.
>    - Results: 10s play-again window.
>    - Play-again: skip tutorial, keep name, zero score, seed calendar, GET box starts round.
>
> 3. **`Leaderboard`** — SQLite persistence:
>    - Schema: `scores(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, score INTEGER, round_id TEXT, played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)`.
>    - Methods: `record(name, score, round_id)`, `top(n=10) -> list[dict]`.
>    - DB path: configurable, defaults to `/opt/apigame/data/leaderboard.db`.
>
> Tests should cover: task generation distribution, no-triple-repeat rule, force-POST-when-empty, scoring math, state transitions, tutorial flow, play-again flow, leaderboard ordering.
>
> Run tests locally: `cd server/agent && python -m pytest test_task_engine.py -v`.

### Test checklist (human performs, tick each)

- [ ] `cd server/agent && python -m pytest test_task_engine.py -v` — all tests pass
- [ ] Coverage check: `python -m pytest test_task_engine.py --cov=task_engine --cov-report=term` — 80%+
- [ ] Manual smoke test: `python -c "from task_engine import TaskGenerator; tg = TaskGenerator(); [print(tg.next(event_count=3)) for _ in range(20)]"` — no triple repeats, distribution looks ~40/30/30
- [ ] `python -c "from task_engine import Leaderboard; lb = Leaderboard('/tmp/test.db'); lb.record('TST', 42, 'r1'); print(lb.top())"` — returns the entry

### Rollback / if it fails

Delete `task_engine.py` and `test_task_engine.py` and re-run prompt. If SQLite errors on the droplet later, check that `/opt/apigame/data/` exists and is writable.

---

## Step 7 — MQTT subscriber glue: agent.py

**Goal:** Wire MQTT topics to the task engine and calendar client. The agent subscribes to device actions and session events, runs game logic, and publishes results, tasks, state, and leaderboard updates.

**Touches:**
- `server/agent/agent.py`

**Prerequisites:** Steps 5 and 6 complete (calendar_client and task_engine working). Mosquitto running on droplet (already is).

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 7).
>
> Write `server/agent/agent.py` — the MQTT↔game bridge:
>
> 1. Connect to MQTT at `127.0.0.1:1883` using credentials from `.env` (same dotenv path as calendar_client).
> 2. Subscribe to:
>    - `apigame/device/+/action` — player verb submissions
>    - `apigame/device/+/session` — name entry, round start/end, play-again
>    - `apigame/admin/reset` — ops: force calendar reset
> 3. On **session** message `{"type": "name", "name": "ZAC"}`:
>    - Create/retrieve SessionState for that device
>    - Call `start_session(name)`, seed calendar
>    - Publish first tutorial task to `apigame/device/<devid>/task`
> 4. On **action** message `{"verb": "POST", "round_id": "r42", "ts": ...}`:
>    - Route to SessionState.submit_action(verb) or advance_tutorial(verb)
>    - Execute the corresponding calendar operation (calendar_client.insert/patch/delete/list)
>    - Publish result to `apigame/device/<devid>/result` (per schema in context doc)
>    - Publish next task to `apigame/device/<devid>/task`
>    - Publish state to `apigame/state` (calendar snapshot + last request + current player)
>    - Publish leaderboard to `apigame/leaderboard` on round end
> 5. On **admin/reset**: seed calendar, publish state.
> 6. Maintain one SessionState per device_id (in a dict). Support multiple concurrent devices (future-proof but test with one).
> 7. Run a background timer (threading or asyncio) that ticks each session every second to count down the round timer. On timer expiry, transition to RESULTS. After 10s in RESULTS with no play-again, transition to IDLE.
>
> When run as `__main__`, start the MQTT loop. Log to stdout.
>
> scp to droplet and run as a script (not as a service yet):
> ```
> scp server/agent/agent.py root@162.243.231.61:/opt/apigame/agent/
> ssh root@162.243.231.61 "/opt/apigame/venv/bin/python /opt/apigame/agent/agent.py"
> ```

### Test checklist (human performs, tick each)

- [ ] Agent starts without errors, logs "Connected to MQTT"
- [ ] From local machine (or droplet second terminal), subscribe: `mosquitto_sub -h localhost -t 'apigame/#' -u esp32 -P '<password>'` (run on droplet)
- [ ] Publish a session start: `mosquitto_pub -h localhost -t 'apigame/device/test-01/session' -u esp32 -P '<password>' -m '{"type":"name","name":"TST"}'` — see task published to `apigame/device/test-01/task` in subscriber
- [ ] Publish a tutorial action: `mosquitto_pub -h localhost -t 'apigame/device/test-01/action' -u esp32 -P '<password>' -m '{"verb":"GET","round_id":"r0","ts":0}'` — see result on `apigame/device/test-01/result`
- [ ] Complete all 4 tutorial steps (GET, POST, PUT, DELETE) — agent logs each, advances to ROUND state
- [ ] Publish a round action (POST) — see result with score +3 or −2, next task published, state published to `apigame/state`
- [ ] Wait 60s (or set timer short for testing) — agent transitions to RESULTS, publishes leaderboard
- [ ] Check Google Calendar — events were actually created/modified/deleted during the round

### Rollback / if it fails

Kill the agent process (`Ctrl+C`). Check `journalctl` for Mosquitto errors. Common issues:
- "Connection refused" → Mosquitto not running; `systemctl status mosquitto`.
- "Not authorized" → wrong MQTT credentials in `.env`.
- Calendar errors → check `.env` has valid OAuth tokens (re-run Step 3 curl test).
- JSON decode errors → check message format matches schema in context doc section 3.

---

## Step 8 — FastAPI + WebSocket + deploy infrastructure

**Goal:** Stand up the web server for the big screen, create systemd units for both agent and web, configure Nginx path-prefix, write the deploy script, and get everything running as services. After this step, `https://tinydrop.win/apigame/` serves a placeholder page with live WebSocket state updates.

**Touches:**
- `server/web/app.py`
- `big-screen/index.html` (placeholder with WebSocket connection)
- `big-screen/styles.css` (minimal)
- `big-screen/app.js` (WebSocket client, renders raw state JSON)
- `deploy/systemd/apigame-agent.service`
- `deploy/systemd/apigame-web.service`
- `deploy/nginx/apigame.conf.snippet`
- `deploy/scripts/deploy.sh`
- `/etc/nginx/sites-available/tinydrop` on droplet (**one `include` line added** — see Important Notes at top of plan)

**Prerequisites:** Step 7 complete (agent runs as script). Steps 1–6 complete.

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 8).
>
> Create the web server, deployment infrastructure, and deploy everything. This step has many files but one goal: get `https://tinydrop.win/apigame/` serving a live page.
>
> **1. `server/web/app.py`** — FastAPI application:
> - Mount `big-screen/` as static files at `/` (these get deployed to `/opt/apigame/web/static/`).
> - WebSocket endpoint at `/ws`:
>   - On connect, add client to a set.
>   - Subscribe to MQTT topics `apigame/state` and `apigame/leaderboard` on `127.0.0.1:1883`.
>   - When MQTT message arrives on these topics, broadcast to all WebSocket clients as JSON `{"topic": "state"|"leaderboard", "data": <parsed payload>}`.
>   - On disconnect, remove client from set.
> - Health endpoint `GET /health` returning `{"status": "ok"}`.
> - Run with uvicorn on `127.0.0.1:8010`.
>
> **2. `big-screen/index.html`** — placeholder page:
> - Title: "APIgame — Big Screen"
> - Shows "Waiting for game data..." initially
> - Loads `app.js`
>
> **3. `big-screen/app.js`** — WebSocket client:
> - Connect to `wss://${window.location.host}/apigame/ws`
> - On message, parse JSON and dump formatted state to page (just `<pre>` for now — Step 15 will polish)
> - Show connection status indicator
>
> **4. `big-screen/styles.css`** — minimal reset, dark background, monospace font.
>
> **5. `deploy/systemd/apigame-agent.service`**:
> ```ini
> [Unit]
> Description=APIgame MQTT-Calendar Agent
> After=network.target mosquitto.service
>
> [Service]
> Type=simple
> User=root
> WorkingDirectory=/opt/apigame/agent
> EnvironmentFile=/opt/apigame/config/.env
> ExecStart=/opt/apigame/venv/bin/python /opt/apigame/agent/agent.py
> Restart=always
> RestartSec=5
>
> [Install]
> WantedBy=multi-user.target
> ```
>
> **6. `deploy/systemd/apigame-web.service`**:
> ```ini
> [Unit]
> Description=APIgame Web Dashboard
> After=network.target
>
> [Service]
> Type=simple
> User=root
> WorkingDirectory=/opt/apigame/web
> EnvironmentFile=/opt/apigame/config/.env
> ExecStart=/opt/apigame/venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8010
> Restart=always
> RestartSec=5
>
> [Install]
> WantedBy=multi-user.target
> ```
>
> **7. `deploy/nginx/apigame.conf.snippet`**:
> ```nginx
> # APIgame path-prefix — included from the tinydrop server block
> location /apigame/ {
>     proxy_pass http://127.0.0.1:8010/;
>     proxy_http_version 1.1;
>     proxy_set_header Upgrade $http_upgrade;
>     proxy_set_header Connection "upgrade";
>     proxy_set_header Host $host;
>     proxy_set_header X-Real-IP $remote_addr;
>     proxy_read_timeout 86400;
> }
> ```
>
> **8. `deploy/scripts/deploy.sh`** — deployment script that:
> - scps `server/agent/*.py` → `/opt/apigame/agent/`
> - scps `server/web/*.py` → `/opt/apigame/web/`
> - scps `big-screen/*` → `/opt/apigame/web/static/`
> - scps systemd units → `/etc/systemd/system/`
> - scps nginx snippet → `/etc/nginx/snippets/apigame.conf`
> - SSHes in to: `systemctl daemon-reload && systemctl enable --now apigame-agent apigame-web && systemctl reload nginx`
> - Uses `SERVER=root@162.243.231.61` as a variable at the top.
>
> **9. Nginx integration** (manual step, documented in deploy.sh output):
> The script should print a reminder that the user must **once** add this line inside the `server { listen 443 ... }` block in `/etc/nginx/sites-available/tinydrop`, just before the closing `}`:
> ```
> include /etc/nginx/snippets/apigame.conf;
> ```
> This is the only modification to a tinydrop file. The script should NOT do this automatically.
>
> After writing all files, tell me to run `deploy/scripts/deploy.sh` and the manual nginx include step.

### Test checklist (human performs, tick each)

- [ ] `bash deploy/scripts/deploy.sh` — completes without errors
- [ ] Add `include /etc/nginx/snippets/apigame.conf;` to tinydrop Nginx config, run `nginx -t` — syntax OK
- [ ] `systemctl reload nginx` — no errors
- [ ] `systemctl status apigame-agent apigame-web` — both `active (running)`
- [ ] `curl -s https://tinydrop.win/apigame/health` — returns `{"status":"ok"}`
- [ ] Open `https://tinydrop.win/apigame/` in browser — see placeholder page, "Waiting for game data..."
- [ ] Open browser DevTools → Network → WS — WebSocket connection established to `/apigame/ws`
- [ ] From droplet: `mosquitto_pub -h localhost -t 'apigame/state' -u esp32 -P '<pass>' -m '{"test":"hello"}'` — browser shows the JSON
- [ ] `https://tinydrop.win/` — tinydrop still works (not broken!)
- [ ] `journalctl -u apigame-agent -n 5 --no-pager` — agent logs look healthy
- [ ] `journalctl -u apigame-web -n 5 --no-pager` — web logs look healthy

### Rollback / if it fails

- **Nginx broken:** Remove the `include` line from tinydrop config, `nginx -t && systemctl reload nginx`. Tinydrop is restored.
- **Services won't start:** Check logs with `journalctl -u apigame-agent -e` and `journalctl -u apigame-web -e`. Common: wrong Python path, missing module, port already in use.
- **WebSocket won't connect:** Check Nginx snippet has `proxy_http_version 1.1` and `Upgrade`/`Connection` headers. Check browser console for errors.
- **502 Bad Gateway:** apigame-web not running or not listening on 8010. Check `ss -tlnp | grep 8010`.
- **To fully undo:** `systemctl disable --now apigame-agent apigame-web`, remove include line from Nginx, `systemctl reload nginx`, `rm /etc/systemd/system/apigame-*.service /etc/nginx/snippets/apigame.conf`.

---

## Step 9 — ESP32: TFT boot screen + joystick + button (no network)

**Goal:** Verify all hardware works: display renders, joystick reads, button registers. No WiFi or MQTT yet.

**Touches:**
- `esp32-firmware/src/main.cpp` (replace minimal with hardware test)
- `esp32-firmware/src/display.h` / `display.cpp`
- `esp32-firmware/src/input.h` / `input.cpp`

**Prerequisites:** Step 1 complete (PlatformIO compiles). ESP32 wired per `PIN_REFERNCE.md`. USB connected.

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md`, `docs/APIgame-build-plan.md` (locate Step 9), and `docs/PIN_REFERNCE.md`.
>
> Write the ESP32 hardware test firmware. Create three source files:
>
> **1. `esp32-firmware/src/display.h` / `display.cpp`** — TFT display module:
> - Initialize TFT_eSPI with rotation 1 (landscape 320×240).
> - `display_init()` — init SPI, clear screen to black.
> - `display_boot_screen()` — show "APIgame" in large white text centered, version text below, "Hardware test..." at bottom.
> - `display_text(x, y, text, color, size)` — convenience wrapper.
> - `display_clear()` — fill black.
>
> **2. `esp32-firmware/src/input.h` / `input.cpp`** — input module:
> - Pin definitions from PIN_REFERNCE: JOY_VRX=34, JOY_VRY=35, JOY_SW=13, BUTTON_PIN=12.
> - `input_init()` — configure pins (button and joystick switch with INPUT_PULLUP, analog pins as input).
> - `joy_direction()` — returns enum: NONE, LEFT, RIGHT, UP, DOWN. Use deadzone 500 from center 2048.
> - `button_pressed()` — returns true on rising edge (debounced, ~50ms).
> - `joy_button_pressed()` — same for joystick button.
>
> **3. `esp32-firmware/src/main.cpp`** — test harness:
> - setup(): Serial.begin(115200), display_init(), input_init(), display_boot_screen().
> - loop(): Read joystick direction and both buttons every 50ms. Print to Serial: `"JOY: LEFT"`, `"BTN: pressed"`, `"JOY_BTN: pressed"`. Also draw current direction and button state on the bottom portion of the display so it's visible without serial.
>
> This is a hardware validation step — keep it simple, no game logic.

### Test checklist (human performs, tick each)

- [ ] `cd esp32-firmware && pio run -t upload -t monitor` — compiles and flashes
- [ ] Display shows "APIgame" boot screen with "Hardware test..." text
- [ ] Move joystick left → serial prints `JOY: LEFT`, display updates
- [ ] Move joystick right → serial prints `JOY: RIGHT`
- [ ] Move joystick up/down → serial prints corresponding direction
- [ ] Press action button (GPIO 12) → serial prints `BTN: pressed`
- [ ] Press joystick button (GPIO 13) → serial prints `JOY_BTN: pressed`
- [ ] Release all inputs → serial prints `JOY: NONE`, no ghost presses

### Rollback / if it fails

- **Display blank/white:** Check SPI wiring matches PIN_REFERNCE. Check TFT_eSPI build flags in platformio.ini. Try different SPI_FREQUENCY (20000000 instead of 40000000).
- **Joystick reads wrong:** Check analog values in serial (`analogRead(34)` should be ~2048 at rest). If values are 0 or 4095, VRX/VRY wires may be swapped or disconnected.
- **Button doesn't register:** Check INPUT_PULLUP is set. Button should connect GPIO to GND when pressed. If it's active-high, flip the logic.
- **Upload fails:** Check USB cable is data-capable (not charge-only). Check correct port in platformio.ini or use `pio run -t upload --upload-port /dev/cu.usbserial-*`.

---

## Step 10 — ESP32: MQTT/TLS connection

**Goal:** Connect ESP32 to Mosquitto over TLS, subscribe to topics, publish a test message on button press.

**Touches:**
- `esp32-firmware/include/ca_cert.h` (Let's Encrypt ISRG Root X1)
- `esp32-firmware/src/mqtt_client.h` / `mqtt_client.cpp`
- `esp32-firmware/src/main.cpp` (add MQTT to loop)

**Prerequisites:** Step 9 complete (hardware works). `secrets.h` filled in with WiFi credentials and MQTT password. Droplet Mosquitto running.

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 10).
>
> Add MQTT/TLS connectivity to the ESP32 firmware:
>
> **1. `esp32-firmware/include/ca_cert.h`** — embed the ISRG Root X1 certificate (Let's Encrypt root CA) as a `const char*` PEM string. This cert is used by `WiFiClientSecure` to verify the Mosquitto broker's TLS certificate.
>
> **2. `esp32-firmware/src/mqtt_client.h` / `mqtt_client.cpp`** — MQTT module:
> - `mqtt_init(device_id)` — configure WiFiClientSecure with CA cert, configure PubSubClient with host/port/credentials from secrets.h. Set buffer size to 512.
> - `mqtt_connect()` — connect to WiFi (retry loop with serial output), then connect to MQTT broker (retry loop). Display connection status on TFT ("Connecting WiFi...", "Connecting MQTT...").
> - `mqtt_loop()` — call PubSubClient loop, handle reconnection if disconnected.
> - `mqtt_publish(topic, payload)` — publish a message.
> - `mqtt_subscribe(topic, callback)` — subscribe with callback.
> - `mqtt_connected()` — return connection status.
> - Subscribe to `apigame/device/<DEVICE_ID>/result` and `apigame/device/<DEVICE_ID>/task`. Log received messages to Serial.
>
> **3. Update `esp32-firmware/src/main.cpp`**:
> - setup(): After hardware init, call mqtt_init and mqtt_connect.
> - loop(): Call mqtt_loop(). On button press, publish a test message to `apigame/device/<DEVICE_ID>/action`: `{"verb":"GET","round_id":"test","ts":<millis>}`.
> - Display "WiFi: OK", "MQTT: OK" or "MQTT: DISCONNECTED" on screen.
>
> Reminder: DEVICE_ID comes from secrets.h (`handheld-01`). MQTT host is `mqtt.tinydrop.win`, port 8883.

### Test checklist (human performs, tick each)

- [ ] Flash and open serial monitor — see "Connecting WiFi..." then "WiFi connected: <IP>"
- [ ] See "Connecting MQTT..." then "MQTT connected"
- [ ] Display shows "WiFi: OK" and "MQTT: OK"
- [ ] On droplet, run: `mosquitto_sub -h localhost -t 'apigame/#' -u esp32 -P '<pass>'`
- [ ] Press button on ESP32 → see action message appear in mosquitto_sub
- [ ] From droplet: `mosquitto_pub -h localhost -t 'apigame/device/handheld-01/task' -u esp32 -P '<pass>' -m '{"round_id":"t0","task_id":"t0","text":"Test task","expected_verb":"GET"}'` → see message in ESP32 serial output

### Rollback / if it fails

**This is a risky step (first TLS handshake from embedded device).**
- **WiFi won't connect:** Check SSID/password in secrets.h. Check ESP32 is within range. Try a phone hotspot to isolate network issues.
- **MQTT connection refused:** Check MQTT host/port in secrets.h (`mqtt.tinydrop.win:8883`). Check `dig mqtt.tinydrop.win` resolves to `162.243.231.61`. Check Mosquitto is running on droplet.
- **TLS handshake fails:** The CA cert may be wrong. Verify: `openssl s_client -connect mqtt.tinydrop.win:8883 -CAfile /etc/ssl/certs/ca-certificates.crt` from any Linux machine. Check the cert chain — it should end with ISRG Root X1. If Let's Encrypt changed their chain, update `ca_cert.h`.
- **MQTT auth fails:** Check username/password match what's in `/etc/mosquitto/passwd`.
- **Messages too large:** If PubSubClient silently drops messages, increase buffer size beyond 512.

---

## Step 11 — ESP32: game UI + MQTT wire-up

**Goal:** Draw the game UI (four verb boxes, task text, status bar, response row) and wire incoming MQTT messages to display updates. Joystick moves selection between boxes, button publishes the selected verb.

**Touches:**
- `esp32-firmware/src/game_ui.h` / `game_ui.cpp`
- `esp32-firmware/src/main.cpp` (integrate game UI)

**Prerequisites:** Step 10 complete (MQTT works).

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 11).
>
> Create the game UI module and integrate it with MQTT:
>
> **`esp32-firmware/src/game_ui.h` / `game_ui.cpp`** — game screen rendering for landscape 320×240:
>
> Layout (adapt the context doc mockup to 320×240 landscape):
> ```
> ┌──────────────────────────────────┐
> │  ABC      042        0:47       │  Status bar: name(left), score(center), timer(right)
> ├──────────────────────────────────┤
> │                                  │
> │      Add an event               │  Task text (large, centered)
> │                                  │
> ├──────────────────────────────────┤
> │  [GET] [POST] [PUT]  [DEL]     │  Four verb boxes with fixed colors
> │              ▲                   │  Selection indicator under current box
> ├──────────────────────────────────┤
> │  POST 201 ✓  +3                │  Response row: verb, status code, delta
> └──────────────────────────────────┘
> ```
>
> - **Verb boxes:** GET=blue, POST=green, PUT=orange, DELETE=red. Fixed colors always (color hints only during tutorial+first 5 tasks, per context doc — implement the hint removal later in step 13).
> - **Selection:** Joystick left/right moves a highlight/underline between boxes. Wrap around.
> - **Task text:** Updated when MQTT `task` message arrives. Parse `{"text": "...", "expected_verb": "..."}`.
> - **Status bar:** Updated from MQTT `result` message (score) and internal timer.
> - **Response row:** Updated from MQTT `result` message: `{"verb": "POST", "status": 201, "correct": true, "points_delta": 3}`.
> - Functions: `game_ui_init()`, `game_ui_draw()`, `game_ui_set_task(text)`, `game_ui_set_result(verb, status, correct, delta)`, `game_ui_set_score(score)`, `game_ui_set_timer(seconds)`, `game_ui_set_name(name)`, `game_ui_move_selection(direction)`, `game_ui_get_selected_verb() -> String`.
>
> **Update `main.cpp`:**
> - On MQTT `task` message: parse JSON, call `game_ui_set_task`.
> - On MQTT `result` message: parse JSON, call `game_ui_set_result`, `game_ui_set_score`.
> - On joystick left/right: call `game_ui_move_selection`.
> - On button press: get selected verb, publish action message to MQTT.
> - Call `game_ui_draw()` in loop.
>
> This is a rendering and input step — no state machine yet. The game_ui module is "dumb": it draws what it's told.

### Test checklist (human performs, tick each)

- [ ] Flash — display shows game UI layout with four colored boxes
- [ ] Joystick left/right — selection indicator moves between boxes, wraps around
- [ ] From droplet, publish a task: `mosquitto_pub -h localhost -t 'apigame/device/handheld-01/task' -u esp32 -P '<pass>' -m '{"round_id":"r0","task_id":"t1","text":"Add an event","expected_verb":"POST"}'` — "Add an event" appears in task area
- [ ] Press button while "POST" box is selected → action message appears in `mosquitto_sub` on droplet
- [ ] From droplet, publish a result: `mosquitto_pub -h localhost -t 'apigame/device/handheld-01/result' -u esp32 -P '<pass>' -m '{"round_id":"r0","verb":"POST","expected_verb":"POST","status":201,"correct":true,"points_delta":3,"score_total":3,"latency_ms":150}'` — response row shows "POST 201 ✓ +3", score updates to 3
- [ ] All four boxes visible and distinctly colored

### Rollback / if it fails

Revert `main.cpp` to Step 10 version (MQTT test). If display layout is wrong (text overlapping, boxes off-screen), adjust pixel coordinates. The layout must fit in 320×240 — print `tft.width()` and `tft.height()` to confirm rotation is applied.

---

## Step 12 — ESP32: name entry screen

**Goal:** Implement the 3-letter arcade-style name entry. Joystick up/down cycles alphabet, button locks letter. After 3 letters, session message published to agent.

**Touches:**
- `esp32-firmware/src/name_entry.h` / `name_entry.cpp`
- `esp32-firmware/src/main.cpp` (add state management for name entry → game)

**Prerequisites:** Step 11 complete (game UI renders and MQTT works).

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 12).
>
> Create the name entry screen:
>
> **`esp32-firmware/src/name_entry.h` / `name_entry.cpp`**:
> - Display: "ENTER NAME" title, three letter slots rendered large and centered. Current slot has a cursor/highlight. Alphabet cycles A–Z (and wraps).
> - `name_entry_init()` — reset to first letter, all slots "A".
> - `name_entry_update(direction, button)` — on UP: next letter, on DOWN: prev letter, on BUTTON: lock current letter and move to next slot. After 3rd letter locked, return true (name complete).
> - `name_entry_draw()` — render the current state.
> - `name_entry_get_name() -> String` — returns the 3-letter name.
>
> **Update `main.cpp`** — add a simple state variable for the firmware:
> - States: `NAME_ENTRY`, `GAME` (more states added in later steps).
> - On boot, start in `NAME_ENTRY` state. Show name entry screen.
> - When name is complete, publish session message: `{"type":"name","name":"ABC"}` to `apigame/device/<DEVICE_ID>/session`.
> - Transition to `GAME` state (shows game UI from Step 11).
> - The transition to GAME is temporary — Step 13 will add TUTORIAL between them.

### Test checklist (human performs, tick each)

- [ ] Flash — see "ENTER NAME" screen with three letter slots showing "AAA"
- [ ] Joystick up — first letter cycles A→B→C...→Z→A
- [ ] Joystick down — first letter cycles A→Z→Y...
- [ ] Press button — first letter locks, cursor moves to second slot
- [ ] Enter all 3 letters — session message published (visible in `mosquitto_sub` on droplet)
- [ ] Screen transitions to game UI
- [ ] Serial shows: `"Name entered: XYZ"` and `"Published session: {"type":"name","name":"XYZ"}"`

### Rollback / if it fails

Revert to Step 11 main.cpp (skip name entry, go straight to game UI). If letters don't cycle smoothly, adjust the move delay (MOVE_DELAY in PIN_REFERNCE is 150ms — may need tuning for feel).

---

## Step 13 — ESP32: tutorial state machine

**Goal:** After name entry, run four scripted tutorial prompts (GET → POST → PUT → DELETE). Each waits for the correct verb press. Tutorial triggers calendar seeding via the agent. After tutorial, transition to round.

**Touches:**
- `esp32-firmware/src/tutorial.h` / `tutorial.cpp`
- `esp32-firmware/src/main.cpp` (add TUTORIAL state between NAME_ENTRY and GAME/ROUND)

**Prerequisites:** Step 12 complete. Agent running on droplet (Step 7/8).

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 13).
>
> Create the tutorial state machine on the ESP32:
>
> **`esp32-firmware/src/tutorial.h` / `tutorial.cpp`**:
> - Four steps, in order: GET ("Refresh calendar"), POST ("Add an event"), PUT ("Update an event"), DELETE ("Remove an event").
> - `tutorial_init()` — reset to step 0.
> - `tutorial_current_step() -> int` (0–3, or 4 = complete).
> - `tutorial_get_prompt() -> String` — returns current step's prompt text.
> - `tutorial_get_expected_verb() -> String` — returns "GET", "POST", "PUT", or "DELETE".
> - `tutorial_check_verb(verb) -> bool` — returns true if verb matches expected. Wrong verb = no penalty, just don't advance. Maybe flash the correct box or show a hint.
> - `tutorial_draw()` — render tutorial-specific UI: same game UI layout but with a tutorial instruction banner at top ("Tutorial 1/4: Press GET to refresh"), and maybe highlight/pulse the correct box as a hint.
>
> The tutorial doesn't directly call calendar APIs — it sends actions to the agent via MQTT, and the agent handles the calendar operations. The agent sees it's in tutorial state and seeds the calendar during the tutorial phase.
>
> **Update `main.cpp`** — states: `NAME_ENTRY → TUTORIAL → ROUND`:
> - After name entry, transition to TUTORIAL.
> - In TUTORIAL state: show tutorial_draw(), process joystick for box selection, on button press check verb via tutorial_check_verb.
> - On correct verb: publish action to MQTT (agent does the real API call), agent responds with result and next task. Advance tutorial step.
> - After step 4 (DELETE) completes, transition to ROUND state.
> - In ROUND state: show game UI, timer starts (handled in Step 14).
>
> The agent already handles tutorial logic server-side (Step 7). The ESP32 just needs to display tutorial prompts, enforce correct-verb-only advancement, and publish actions. The agent responds with results and tasks that drive the display.
>
> Note: during tutorial, wrong verb press should show a gentle hint (e.g., briefly highlight the correct box) but NOT publish to MQTT and NOT penalize score.

### Test checklist (human performs, tick each)

- [ ] Flash. Enter name. Tutorial starts: "Tutorial 1/4: Press GET to refresh"
- [ ] Press wrong verb (e.g., POST) — hint shown, no advancement, no MQTT message
- [ ] Press GET — action published, agent responds with result, tutorial advances to step 2
- [ ] Complete all 4 tutorial steps (GET → POST → PUT → DELETE)
- [ ] Check Google Calendar — events seeded during tutorial (3+ events visible)
- [ ] After tutorial, screen transitions to round UI (game UI with timer area — timer not running yet, that's Step 14)
- [ ] Serial log shows tutorial progression: "Tutorial step 1/4 complete", etc.

### Rollback / if it fails

Revert to Step 12 main.cpp (name entry → game UI directly). If tutorial doesn't advance, check that the agent is recognizing tutorial actions — look at agent logs on droplet (`journalctl -u apigame-agent -f`). If the agent isn't running, start it or use the script directly.

---

## Step 14 — ESP32: 60-second round + play-again flow

**Goal:** Complete the game loop: 60s timed round with streaming tasks, results screen with leaderboard, play-again with countdown, timeout to idle.

**Touches:**
- `esp32-firmware/src/game_loop.h` / `game_loop.cpp`
- `esp32-firmware/src/main.cpp` (full state machine)

**Prerequisites:** Step 13 complete. Agent running on droplet.

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 14).
>
> Implement the full game loop on ESP32:
>
> **`esp32-firmware/src/game_loop.h` / `game_loop.cpp`**:
> - `game_loop_start(round_id)` — start 60s countdown, init score to 0.
> - `game_loop_tick()` — decrement timer (call every second using millis()), update display timer. Return true when time expires.
> - `game_loop_on_result(result_json)` — parse result from agent, update score display, update response row.
> - `game_loop_get_time_left() -> int` — seconds remaining.
> - `game_loop_is_active() -> bool`.
>
> **Full state machine in `main.cpp`** — states: `IDLE → NAME_ENTRY → TUTORIAL → ROUND → RESULTS → (PLAY_AGAIN or IDLE)`:
>
> - **IDLE:** Display "APIgame" splash + "Press button to start". On button → NAME_ENTRY.
> - **NAME_ENTRY:** (from Step 12). On name complete → TUTORIAL.
> - **TUTORIAL:** (from Step 13). On tutorial complete → ROUND.
> - **ROUND:** 60s timer counting down. Tasks from agent displayed. Player selects verb + presses button → publish action. Agent responds with result + next task. On timer expire → RESULTS.
>   - GET press during round: publish action (agent scores −2 per context doc rules).
>   - Agent sends `round_id` with each task; ESP32 includes it in action messages.
> - **RESULTS:** Display final score, "PLAY AGAIN?" with 10s countdown. Show leaderboard (from MQTT `apigame/leaderboard`).
>   - If button pressed within 10s → PLAY_AGAIN transition.
>   - If 10s expires → IDLE.
> - **PLAY_AGAIN:** Per context doc: keep name, zero score, skip tutorial. Agent seeds fresh calendar. Only GET box lit. Player presses GET → agent responds, ROUND starts. The GET press does NOT start the timer or cost points — it triggers calendar load and first real task.
>
> The agent handles the server-side state transitions — the ESP32 publishes session messages:
> - `{"type":"name","name":"XYZ"}` — start session
> - `{"type":"round_start","round_id":"rN"}` — round begins (generated by ESP32, sequential)
> - `{"type":"round_end","round_id":"rN"}` — round time expired
> - `{"type":"play_again"}` — player wants another round
>
> The timer is managed on ESP32 (authoritative for countdown display), but the agent also tracks it (authoritative for scoring cutoff).

### Test checklist (human performs, tick each)

- [ ] Flash. See idle splash screen. Press button → name entry.
- [ ] Enter name → tutorial → complete tutorial → round starts.
- [ ] Timer counts down from 60. Score starts at 0.
- [ ] Press correct verb → score increases by 3, response shows ✓.
- [ ] Press wrong verb → score decreases by 2, response shows ✗.
- [ ] Play for 60s → timer hits 0 → results screen appears.
- [ ] Results screen shows final score, "PLAY AGAIN?" with countdown.
- [ ] Press button within 10s → play-again: same name, score reset, GET box only.
- [ ] Press GET → calendar reloads, first task appears, timer starts.
- [ ] Play another round. On results, wait 10s without pressing → idle splash.
- [ ] Press button → back to name entry (fresh start).
- [ ] Check leaderboard on droplet: `sqlite3 /opt/apigame/data/leaderboard.db "SELECT * FROM scores ORDER BY score DESC LIMIT 5;"` — scores recorded.

### Rollback / if it fails

Revert to Step 13 state machine (name → tutorial → game UI without timer). If timer drift is bad (e.g., 60s timer takes 65s), use `millis()` for timing, not `delay()`. If play-again doesn't work, check the agent handles `{"type":"play_again"}` session messages and re-seeds the calendar.

---

## Step 15 — Big screen: calendar view, live log, leaderboard

**Goal:** Replace the placeholder big-screen page with the real UI: rendered calendar view, scrolling live request log, and leaderboard. All driven by WebSocket state pushes from the agent.

**Touches:**
- `big-screen/index.html`
- `big-screen/styles.css`
- `big-screen/app.js`

**Prerequisites:** Step 8 complete (WebSocket relay works). Agent running and publishing state.

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 15).
>
> Build the full big-screen UI in `big-screen/`. This is a single-page web app driven entirely by WebSocket messages. No frameworks — vanilla HTML/CSS/JS. Target 1080p landscape on a TV/monitor in a dim room (think arcade aesthetic).
>
> **Layout** (from context doc):
> ```
> ┌──────────────────────────────┬────────────────┐
> │                              │  LIVE LOG      │
> │   CALENDAR VIEW              │  POST /events  │
> │   (today + tomorrow,         │    → 201       │
> │    rendered from state)      │  GET /events   │
> │                              │    → 200       │
> │                              │  DELETE /ev/a3 │
> │                              │    → 204       │
> ├──────────────────────────────┴────────────────┤
> │  LEADERBOARD: ZAC 127 · BOB 89 · ANA 84 · ... │
> └───────────────────────────────────────────────┘
> ```
>
> **`big-screen/index.html`:**
> - Three sections: calendar (left, ~65% width), live log (right, ~35% width), leaderboard (bottom strip).
> - Include current player info: name, score, time remaining (from state message).
>
> **`big-screen/styles.css`:**
> - Dark background (#1a1a2e or similar), bright text.
> - Calendar events as cards/blocks with time and title.
> - Live log as a scrolling monospace feed, newest at top. Color-code by HTTP method (green=POST, orange=PUT/PATCH, red=DELETE, blue=GET). Show method, path, → status code.
> - Leaderboard as a horizontal strip at the bottom, top 10 scores.
> - Smooth transitions when events are added/removed.
> - Large enough text to read from 10 feet away.
>
> **`big-screen/app.js`:**
> - Connect to `wss://${window.location.host}/apigame/ws`.
> - On `state` message: render calendar events (parse `calendar` array, show summary + start time, sorted by time), update live log (prepend `last_request`), update current player display.
> - On `leaderboard` message: render top 10 as `NAME SCORE` entries.
> - Handle reconnection (retry every 3s on disconnect).
> - On idle (no player), show leaderboard prominently and dim the calendar.
>
> After writing, deploy with `deploy/scripts/deploy.sh` (it scps big-screen/ to the droplet).

### Test checklist (human performs, tick each)

- [ ] Run `bash deploy/scripts/deploy.sh` — deploys updated big-screen files
- [ ] Open `https://tinydrop.win/apigame/` — see the full layout (calendar, log, leaderboard)
- [ ] WebSocket connects (check browser DevTools)
- [ ] Start a game on ESP32 → big screen shows current player name, score, timer
- [ ] Player performs actions → calendar view updates (events appear/change/disappear)
- [ ] Live log scrolls with each request: `POST /calendars/primary/events → 201`
- [ ] Round ends → leaderboard updates with new score
- [ ] Leaderboard shows top 10, sorted by score descending
- [ ] Text is readable from ~10 feet (adjust font sizes if needed)
- [ ] On idle (no active player), leaderboard is prominent

### Rollback / if it fails

Revert `big-screen/` files to Step 8 placeholder versions and redeploy. If WebSocket messages aren't arriving, check `journalctl -u apigame-web -f` on droplet for errors. If calendar view doesn't update, check the state message format in browser DevTools console.

---

## Step 16 — End-to-end: first real round

**Goal:** Play a complete game from start to finish with both screens and real Calendar API calls. Document and fix every bug found.

**Touches:** Whatever breaks. Keep a bug log.

**Prerequisites:** All previous steps complete. Agent and web services running. ESP32 flashed with full firmware. Big screen displaying in a browser.

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 16).
>
> This is an integration test step. I will play the game end-to-end and report bugs. For each bug I report, diagnose the root cause and fix it.
>
> Before I start playing, help me set up monitoring:
> 1. On the droplet, tail the agent log: `journalctl -u apigame-agent -f`
> 2. On the droplet, subscribe to all MQTT topics: `mosquitto_sub -h localhost -t 'apigame/#' -v -u esp32 -P '<pass>'`
> 3. ESP32 serial monitor open: `pio device monitor`
> 4. Big screen open in browser with DevTools console visible
>
> Then I'll play 3 rounds and report issues. For each issue, you should:
> 1. Identify which component is at fault (ESP32, agent, web, MQTT)
> 2. Read the relevant source file
> 3. Fix the bug
> 4. Deploy the fix (scp + restart for server, pio upload for ESP32)
> 5. Tell me to re-test
>
> Common issues to watch for:
> - Timing mismatches (ESP32 timer vs agent timer)
> - JSON parsing errors (field names, types)
> - MQTT message ordering (result arrives before task, or vice versa)
> - Calendar API rate limiting or errors
> - Display rendering glitches (text overflow, overlapping elements)
> - Score disagreements between ESP32 display and agent
> - Play-again flow not resetting properly
> - WebSocket drops during active game
>
> After all bugs are fixed, do a clean run and confirm everything works.

### Test checklist (human performs, tick each)

- [ ] **Round 1:** Name entry → tutorial → 60s round → results → timeout to idle. Note all bugs.
- [ ] **Round 2:** Name entry → tutorial → 60s round → play-again → second round → timeout. Note all bugs.
- [ ] **Round 3:** Quick back-to-back: play, play-again, play-again. Stress the calendar API.
- [ ] All bugs from rounds 1–3 fixed and re-tested
- [ ] Google Calendar shows correct state after each round (events match what was created/modified/deleted)
- [ ] Leaderboard in SQLite has entries for all rounds: `sqlite3 /opt/apigame/data/leaderboard.db "SELECT * FROM scores;"`
- [ ] Big screen showed live updates throughout all rounds
- [ ] No error tracebacks in agent logs
- [ ] No WebSocket disconnections during rounds
- [ ] ESP32 didn't crash or freeze at any point

### Rollback / if it fails

This step is iterative — bugs are expected and fixed in-place. If a fix breaks something else, use `git diff` to review changes and `git stash` to undo if needed. If the calendar gets into a bad state, run `deploy/scripts/reset-calendar.sh`.

---

## Step 17 — Presentation polish

**Goal:** Prepare for the ITP showcase: configure the mini PC for kiosk mode, handle player timeouts gracefully, clean up the physical setup.

**Touches:**
- Kiosk mode script/config for mini PC
- ESP32 firmware: idle timeout adjustments, attract screen
- Big screen: idle/attract mode styling
- Physical setup: cable management, display positioning

**Prerequisites:** Step 16 complete (all bugs fixed, clean runs work).

### Prompt to paste into Claude Code for this step

> Read `docs/APIgame-context.md` and `docs/APIgame-build-plan.md` (locate Step 17).
>
> Presentation polish for the ITP showcase. Help me with:
>
> **1. Chromium kiosk mode script** — write `deploy/scripts/kiosk.sh` for the mini PC (assume Linux, likely Ubuntu or Debian-based):
> - Start Chromium in kiosk mode (fullscreen, no address bar, no controls): `chromium-browser --kiosk --noerrdialogs --disable-infobars --disable-translate --no-first-run https://tinydrop.win/apigame/`
> - Disable screen blanking/screensaver: `xset s off -dpms`
> - Auto-start on boot: create a `.desktop` file in `~/.config/autostart/`.
> - Include a `kill-kiosk.sh` to exit kiosk mode.
>
> **2. ESP32 attract/idle screen** — when in IDLE state (no active player), display an "attract" screen:
> - Show "APIgame" title, animated or cycling text: "Learn HTTP verbs!", "Press button to play", "GET · POST · PUT · DELETE".
> - Auto-dim or cycle colors to catch attention.
>
> **3. Big screen idle mode** — when no player is active:
> - Show leaderboard prominently (full screen or large)
> - Show "Press button on controller to play" text
> - Maybe a subtle animation
>
> **4. Auto-reset safety** — if the ESP32 crashes or disconnects:
> - Agent should handle device reconnection gracefully (don't leave sessions hanging)
> - Add a watchdog: if no MQTT message from a device for 120s during a round, auto-end the session and publish leaderboard
>
> **5. Admin reset** — make `deploy/scripts/reset-calendar.sh` also publish `apigame/admin/reset` MQTT message so the agent resets its state too.
>
> Deploy all changes after writing.

### Test checklist (human performs, tick each)

- [ ] Kiosk mode: run `kiosk.sh` on mini PC → full-screen big screen display, no browser chrome
- [ ] Kill kiosk: `kill-kiosk.sh` → back to desktop
- [ ] Auto-start: reboot mini PC → kiosk starts automatically
- [ ] ESP32 idle attract screen: shows cycling text, eye-catching
- [ ] Big screen idle: leaderboard prominent, "press button to play" visible
- [ ] Play a round → both screens update live → round ends → back to idle/attract
- [ ] Unplug ESP32 during a round → agent times out after 120s → session ends cleanly
- [ ] Replug ESP32 → reconnects, idle screen, ready for new player
- [ ] `bash deploy/scripts/reset-calendar.sh` → calendar wiped, agent state reset, big screen shows empty calendar
- [ ] Physical setup: all cables hidden, displays positioned, controller accessible

### Rollback / if it fails

Kiosk mode issues: check Chromium is installed (`apt install chromium-browser`). If display doesn't work, check HDMI connection and resolution settings. If attract screen animation causes ESP32 performance issues, simplify or remove animation.

---

## Quick reference: step dependency graph

```
Step 1 (repo skeleton) ──────────────────────────────────────────────────────┐
  │                                                                          │
Step 2 (droplet setup)                                                Step 9 (ESP32 TFT+input)
  │                                                                          │
Step 3 (OAuth)                                                        Step 10 (ESP32 MQTT)
  │                                                                          │
Step 4 (calendar client)                                              Step 11 (ESP32 game UI)
  │                                                                          │
Step 5 (game operations)                                              Step 12 (ESP32 name entry)
  │                                                                          │
Step 6 (task engine) ─────────┐                                       Step 13 (ESP32 tutorial) ──┐
  │                           │                                              │                    │
Step 7 (MQTT glue) ──────────┤                                       Step 14 (ESP32 round) ─────┤
  │                           │                                              │                    │
Step 8 (FastAPI + deploy) ────┴── Step 15 (big screen) ──────────────────────┴────────────────────┤
                                      │                                                           │
                                Step 16 (end-to-end) ─────────────────────────────────────────────┘
                                      │
                                Step 17 (polish)
```

**Parallelism opportunities:**
- Steps 9–11 (ESP32 hardware) can run in parallel with Steps 2–8 (server-side) if two people are working.
- Step 6 (task engine) has no I/O dependencies and can be built any time after Step 1.
- Step 15 (big screen UI) can be started as soon as Step 8 is complete, even while ESP32 steps are in progress.

---

## Estimated total files created

| Directory | Files | Purpose |
|---|---|---|
| root | 2 | `CLAUDE.md`, `.gitignore` |
| `esp32-firmware/` | ~14 | platformio.ini, secrets.h.example, ca_cert.h, main.cpp, display.h/cpp, input.h/cpp, mqtt_client.h/cpp, game_ui.h/cpp, name_entry.h/cpp, tutorial.h/cpp, game_loop.h/cpp, README.md |
| `server/agent/` | 4 | calendar_client.py, task_engine.py, test_task_engine.py, agent.py, requirements.txt |
| `server/web/` | 2 | app.py, requirements.txt |
| `big-screen/` | 3 | index.html, styles.css, app.js |
| `deploy/` | 5 | apigame-agent.service, apigame-web.service, apigame.conf.snippet, deploy.sh, reset-calendar.sh, setup-droplet.sh |
| `scripts/` | 1 | get_refresh_token.py |
