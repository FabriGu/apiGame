# CLAUDE.md — APIgame

## Project overview

APIgame is an ITP-showcase arcade game that teaches HTTP verbs (GET / POST / PUT / DELETE) by letting players drive real Google Calendar API calls from a handheld ESP32 controller, with consequences rendered on a big screen in real time. Players enter a 3-letter name, complete a 4-step tutorial, then play a 60-second timed round where they match natural-language task prompts to the correct HTTP verb.

## Architecture

```
ESP32 + ILI9341 + joystick + button
    │
    │ MQTT/TLS (port 8883)
    ▼
Mosquitto (on tinydrop.win droplet, topic prefix: apigame/)
    │
    ▼
apigame-agent (Python)
    ├── Google Calendar API (OAuth2 refresh token)
    ├── SQLite leaderboard
    └── Task state machine
    │
    ▼
apigame-web (FastAPI + WebSocket, port 8010)
    │
    │ WSS via Nginx path-prefix /apigame/
    ▼
Big screen (Chromium kiosk on mini PC → HDMI → monitor)
```

## Key reference files

- `docs/APIgame-context.md` — full project spec, game rules, MQTT topics, architecture
- `docs/APIgame-build-plan.md` — step-by-step build plan with test checklists
- `docs/PIN_REFERNCE.md` — ESP32 pin assignments (all hardware tested and working)

## Non-negotiables

- Do not modify `/opt/tinydrop/*`, `tinydrop-agent`, `tinydrop-web`, `/etc/nginx/sites-available/tinydrop`, or `/etc/mosquitto/conf.d/tinydrop.conf`.
- Do not share MQTT topics with tinydrop (`tinydrop/` prefix is off-limits).
- Do not put OAuth on the ESP32. Refresh token lives on droplet only.
- Do not iframe `calendar.google.com`. Render the calendar view from agent state.
- Do not add a fifth verb box for PATCH. PUT labels the update action; PATCH is the wire implementation.
- Do not change SSL cert or DNS. Use path-prefix `/apigame/` on existing `tinydrop.win`.

## File layout conventions

- Many small files over few large ones.
- 200–400 lines typical, 800 lines max per file.
- ESP32 firmware: one `.h`/`.cpp` pair per module (display, input, mqtt_client, game_ui, etc.).
- Server: one `.py` per concern (calendar_client, task_engine, agent, app).

## Key commands

### ESP32 firmware (from `esp32-firmware/`)
```bash
pio run                          # build
pio run -t upload                # flash
pio device monitor               # serial monitor (115200 baud)
pio run -t upload -t monitor     # flash + monitor
```

### Server deployment
```bash
bash deploy/scripts/deploy.sh          # scp + restart services on droplet
bash deploy/scripts/reset-calendar.sh  # wipe and re-seed dummy calendar
bash deploy/scripts/setup-droplet.sh   # initial droplet directory setup
```

## Testing approach

| Component | How to test |
|---|---|
| Server modules (calendar_client, task_engine) | Unit tests locally: `cd server/agent && python -m pytest` |
| Server integration | On droplet: run agent as script, test with `mosquitto_pub`/`mosquitto_sub` |
| ESP32 firmware | Flash and verify via serial monitor + display output |
| MQTT messaging | `mosquitto_pub` / `mosquitto_sub` from droplet or laptop |
| Web / big screen | `curl` for health endpoint; browser for WebSocket + UI |
