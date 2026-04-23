# APIgame — Project Context

**One-liner:** An ITP-showcase arcade game that teaches HTTP verbs (GET / POST / PUT / DELETE) by letting players drive real Google Calendar API calls from a handheld, with the consequences rendered on a big screen in real time.

**Audience:** Mixed kids/teens and adults at an NYU ITP open house. Short sessions (~90s incl. tutorial). Spectacle matters as much as pedagogy — onlookers watch the big screen over the player's shoulder.

---

## 1. Locked game spec

### Session structure (per player)

1. **Name entry** (~10s) — 3 letters, arcade style. Joystick up/down cycles the alphabet, button locks the letter.
2. **Tutorial** (~20s) — four scripted prompts, one per verb, in order GET → POST → PUT → DELETE. Tutorial performs the seeding of 3–5 events on the dummy calendar.
3. **Round** (60s) — tasks stream one at a time. +3 per correct verb, −2 per wrong.
4. **Results + Play Again** (10s) — big screen shows leaderboard; handheld shows "PLAY AGAIN?" with countdown. If player presses button within 10s:
   - Calendar resets (droplet seeds fresh events)
   - Name and score zeroed but **name persists** (tutorial skipped)
   - Only the GET box is lit on the handheld; pressing GET loads the new round
   - First real task appears, **60s timer starts now** (GET press does not eat the clock)
5. **Timeout** → leaderboard stays up, full reset for next player (name entry + tutorial).

### Verbs

| Box label | Semantic | Implementation | Notes |
|---|---|---|---|
| GET | "Refresh" | `events.list` on primary | Tutorial verb. After tutorial, pressing GET costs −2 (realistic: the UI polls, you don't need to). |
| POST | "Add an event" | `events.insert` with dummy payload | Body generated server-side (random title from pool, time = now+random offset). |
| PUT | "Update an event" | `events.patch` on a random existing event | Labelled PUT in UI (clean four-verb symmetry); implemented as PATCH because Calendar's PUT requires full resource replacement. This is a deliberate pedagogical simplification. |
| DELETE | "Remove an event" | `events.delete` on a random existing event | No confirmation. Fast. Risky by design. |

### Task generation rules

- Natural-language prompts, ≤4 words: `"Add an event"`, `"Update an event"`, `"Remove an event"`, `"Refresh calendar"` (tutorial only).
- **No color hints after level 1.** Tutorial + first 5 tasks may color-code; after that, box color is fixed (not matched to task).
- Task weighting during round: ~40% POST, ~30% PUT, ~30% DELETE, 0% GET (GET only in tutorial).
- If calendar state drops below 1 event, force next task to be POST (keeps PUT/DELETE meaningful).
- Never repeat the same verb three times in a row.

### Scoring

- Correct verb for current task: **+3**
- Wrong verb: **−2**. The action still executes against Google Calendar (wrong-but-real).
- Google API error response (4xx/5xx): **−2** and task advances. Player sees status code.
- Score can go negative.

### Handheld layout (ILI9341, 240×320 portrait)

```
┌────────────────────────┐
│ ABC     042    0:47    │  status bar: name, score, timer
├────────────────────────┤
│                        │
│   Add an event         │  current task (large font)
│                        │
├────────────────────────┤
│                        │
│  [GET][PUT][POST][DEL] │  four verb boxes (fixed colors after level 1)
│          🧍            │  player sprite, joystick moves horizontally
│                        │
├────────────────────────┤
│  POST 201 ✓   +3       │  last response: method, HTTP status, delta
└────────────────────────┘
```

### Big screen layout (1080p landscape, browser)

```
┌──────────────────────────────┬────────────────┐
│                              │  LIVE LOG      │
│   CALENDAR VIEW              │  POST /events  │
│   (today + tomorrow,         │    → 201       │
│    rendered from state)      │  GET /events   │
│                              │    → 200       │
│   Pushed via WebSocket       │  DELETE /ev/a3 │
│                              │    → 204       │
├──────────────────────────────┴────────────────┤
│  LEADERBOARD: ZAC 127 · BOB 89 · ANA 84 · ... │
└───────────────────────────────────────────────┘
```

Live log is the spectator teaching surface — watchers learn endpoint anatomy without playing.

---

## 2. Architecture

```
┌──────────────┐   MQTT/TLS    ┌────────────────────────────────────┐
│ ESP32 +      │ ◄────────────►│  DigitalOcean droplet              │
│ ILI9341 +    │   port 8883   │  (existing tinydrop.win)           │
│ joystick +   │               │                                    │
│ button       │               │  ┌──────────────────────────────┐  │
│              │               │  │ Mosquitto (shared w/ tinydrop)│ │
│ (handheld)   │               │  │  topic prefix: apigame/      │  │
└──────────────┘               │  └───────────────┬──────────────┘  │
                               │                  │                 │
                               │  ┌───────────────▼──────────────┐  │
                               │  │ apigame-agent (Python)       │  │
                               │  │  - MQTT subscriber           │  │
                               │  │  - Google Calendar client    │  │
                               │  │    (refresh token in .env)   │  │
                               │  │  - SQLite leaderboard        │  │
                               │  │  - Task state machine        │  │
                               │  └───────┬──────────────────┬───┘  │
                               │          │                  │      │
                               │          ▼                  ▼      │
                               │  ┌──────────────┐  ┌──────────────┐│
                               │  │ Google       │  │ apigame-web  ││
                               │  │ Calendar API │  │ (FastAPI +   ││
                               │  │              │  │  WebSocket)  ││
                               │  └──────────────┘  └──────┬───────┘│
                               │                           │        │
                               │                  ┌────────▼───────┐│
                               │                  │ Nginx          ││
                               │                  │ /apigame/  →   ││
                               │                  │ 127.0.0.1:8010 ││
                               │                  └────────┬───────┘│
                               └───────────────────────────┼────────┘
                                                           │ WSS
                                              ┌────────────▼───────────┐
                                              │ Mini PC under table    │
                                              │ Chromium kiosk mode    │
                                              │ → HDMI → big screen    │
                                              └────────────────────────┘
```

**Compartmentalization from tinydrop (preserve existing services):**

| Resource | tinydrop | apigame |
|---|---|---|
| Dir | `/opt/tinydrop/` | `/opt/apigame/` |
| Systemd | `tinydrop-agent`, `tinydrop-web` | `apigame-agent`, `apigame-web` |
| Web port (local) | 8000 | 8010 |
| MQTT topic prefix | `tinydrop/` | `apigame/` |
| Nginx | `tinydrop.win/` | `tinydrop.win/apigame/` (path-prefixed, same cert) |
| MQTT credentials | `esp32` user | **same user, same cert** (don't fragment broker config) |

Rationale for path prefix over subdomain: avoids re-running certbot, avoids DNS changes, works with existing cert.

---

## 3. MQTT topics

All topics use `apigame/` prefix. Device ID is assigned at flash time (e.g. `handheld-01`).

| Topic | Direction | Purpose |
|---|---|---|
| `apigame/device/<devid>/action` | ESP32 → agent | Player fired a verb |
| `apigame/device/<devid>/result` | agent → ESP32 | API response + scoring info |
| `apigame/device/<devid>/task` | agent → ESP32 | Next task to display |
| `apigame/device/<devid>/session` | ESP32 → agent | Name submitted, round start/end, play-again |
| `apigame/state` | agent → all | Calendar snapshot + last request (for big screen) |
| `apigame/leaderboard` | agent → all | Top 10 scores |
| `apigame/admin/reset` | any → agent | Force-reset the dummy calendar (ops) |

### Message schemas

**action** (ESP32 → agent):
```json
{"verb": "POST", "round_id": "r42", "ts": 1234567890}
```

**result** (agent → ESP32):
```json
{
  "round_id": "r42",
  "verb": "POST",
  "expected_verb": "POST",
  "status": 201,
  "correct": true,
  "points_delta": 3,
  "score_total": 42,
  "latency_ms": 180
}
```

**task** (agent → ESP32):
```json
{"round_id": "r42", "task_id": "t7", "text": "Add an event", "expected_verb": "POST"}
```

`expected_verb` is sent to the device for local scoring display, but server is source of truth. ESP32 does **not** decide correct/incorrect — it shows what the agent says.

**state** (agent → big screen):
```json
{
  "calendar": [
    {"id": "abc", "summary": "Dentist", "start": "2026-04-24T14:00:00-04:00"}
  ],
  "last_request": {
    "method": "POST",
    "path": "/calendar/v3/calendars/primary/events",
    "status": 201,
    "ts": 1234567890
  },
  "current_player": {"name": "ZAC", "score": 42, "time_left_s": 47}
}
```

---

## 4. Google Calendar integration

- **Auth:** OAuth2 refresh token stored in `/opt/apigame/config/.env`. Agent exchanges for access token on startup and on 401.
- **Calendar:** use `primary` calendar of the dummy account.
- **Timezone:** `America/New_York` (ITP is NYU Tisch).
- **Seeding:** on calendar reset, insert 3 events at now+30min, now+2hr, now+1day with titles from a pool (`"Coffee with Sam"`, `"Dentist"`, `"Standup"`, etc.).
- **Event targeting for PUT/DELETE:** agent keeps in-memory list of current event IDs, picks a random one per request. Refreshes list on 404.

**Quota awareness:** Calendar default is 500 requests / 100s per user. One player = ~30 requests over 90s. Two back-to-back players = safe. Seeding = ~5 requests. Headroom is adequate; don't optimize prematurely.

---

## 5. Hardware

**Already wired by user.** Assume generic ESP32 DevKit + standalone 2.2" ILI9341 240x320 SPI TFT + analog joystick + single tactile button.

Firmware targets (to be confirmed in PlatformIO setup):

- **Board:** ESP32 DevKit (board `esp32dev` in PlatformIO). Confirm with user at step 1.
- **Display:** `Bodmer/TFT_eSPI` library, `ILI9341_DRIVER`.
- **Joystick:** analog X on ADC pin (user to confirm wiring); Y unused or reserved.
- **Button:** single digital input with internal pullup.
- **MQTT:** `knolleary/PubSubClient` or `256dpi/arduino-mqtt` over TLS via `WiFiClientSecure`.

The PlatformIO setup step must produce a **cheatsheet** file (`esp32-firmware/README.md`) covering: how to build, how to flash, how to monitor serial, how `secrets.h` works, pin map, where game logic lives.

---

## 6. Build order (prioritized by risk)

1. **Droplet: Google Calendar wrapper service** (Python, local-only). Prove OAuth works, CRUD works.
2. **Droplet: MQTT bridge** adds MQTT subscriber around the wrapper. Test with `mosquitto_pub` from laptop.
3. **Droplet: FastAPI + WebSocket** for big screen. Minimal HTML renders state pushed from agent.
4. **ESP32: TFT + input** sanity. Draw four boxes, read joystick, read button, print to serial.
5. **ESP32: MQTT client.** Subscribe, publish, react.
6. **ESP32: game loop on device.** Name entry, tutorial, round, play-again.
7. **Big screen: polish** calendar view, live log, leaderboard.
8. **End-to-end rehearsal** + reset-between-players + error states.

Each step has its own test checklist (defined in the plan file Claude Code will produce).

---

## 7. Non-negotiables (things Claude Code must NOT do)

- Do not modify `/opt/tinydrop/*`, `tinydrop-agent`, `tinydrop-web`, `/etc/nginx/sites-available/tinydrop`, or `/etc/mosquitto/conf.d/tinydrop.conf`.
- Do not share MQTT topics with tinydrop (`tinydrop/` prefix is off-limits).
- Do not put OAuth on the ESP32. Refresh token lives on droplet only.
- Do not iframe `calendar.google.com`. Render the calendar view from agent state.
- Do not add a fifth verb box for PATCH. PUT labels the update action; PATCH is the wire implementation.
- Do not change SSL cert or DNS. Use path-prefix `/apigame/` on existing `tinydrop.win`.

---

## 8. Target repo layout

```
APIgame/
├── CLAUDE.md                            # created by Claude Code at step 1
├── docs/
│   ├── APIgame-context.md               # this file
│   ├── APIgame-build-plan.md            # Claude Code produces in plan mode
│   └── tinydrop-droplet-setup-guide.md  # reference (user drops in)
├── esp32-firmware/                      # PlatformIO project
│   ├── platformio.ini
│   ├── include/
│   │   └── secrets.h.example
│   ├── src/
│   │   └── main.cpp
│   └── README.md                        # hardware cheatsheet
├── server/
│   ├── agent/                           # MQTT ↔ Calendar bridge
│   │   ├── agent.py
│   │   ├── calendar_client.py
│   │   ├── task_engine.py
│   │   └── requirements.txt
│   └── web/                             # FastAPI + WebSocket
│       ├── app.py
│       └── requirements.txt
├── big-screen/                          # static, served by FastAPI
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── deploy/
    ├── systemd/
    │   ├── apigame-agent.service
    │   └── apigame-web.service
    ├── nginx/
    │   └── apigame.conf.snippet         # path-prefix block
    └── scripts/
        ├── deploy.sh                    # scp + restart
        └── reset-calendar.sh
```

---

## 9. Open questions Claude Code should resolve in plan mode

- Exact ESP32 pin assignments (user will confirm when prompted).
- Whether big-screen HTML lives in `big-screen/` served by FastAPI or packaged separately. Recommend served by FastAPI — one less moving part.
- Where leaderboard persistence lives. Recommend SQLite at `/opt/apigame/data/leaderboard.db`.
- Whether to add a `apigame/admin/*` auth token or leave admin topics open on local broker only.

---

## 10. Success criteria

A player walks up, types 3 letters, does a 20s tutorial, plays 60s, sees their score on the leaderboard, and walks away able to say: *"GET reads, POST creates, PUT updates, DELETE removes."* A spectator standing behind them learns the same from watching the big screen log.

If the player cannot answer that question unprompted after a round, the game failed its educational goal and the design needs revisiting.
