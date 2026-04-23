# ESP32 Firmware — Hardware Cheatsheet

## Quick start

```bash
# Build
pio run

# Flash
pio run -t upload

# Serial monitor (115200 baud)
pio device monitor

# Flash + monitor (combined)
pio run -t upload -t monitor
```

## secrets.h

The file `include/secrets.h` holds WiFi and MQTT credentials. It is gitignored.

```bash
cp include/secrets.h.example include/secrets.h
# Edit secrets.h with your values
```

Fields:
- `WIFI_SSID` / `WIFI_PASSWORD` — local WiFi network
- `MQTT_HOST` — `mqtt.tinydrop.win`
- `MQTT_PORT` — `8883` (TLS)
- `MQTT_USER` — `esp32`
- `MQTT_PASSWORD` — Mosquitto password for the esp32 user
- `DEVICE_ID` — `handheld-01` (or unique per device)

## Pin map

| Function       | GPIO | Notes                              |
|----------------|------|------------------------------------|
| TFT_MOSI       | 23   | SPI data out                       |
| TFT_MISO       | 19   | SPI data in                        |
| TFT_SCLK       | 18   | SPI clock                          |
| TFT_CS         | 5    | TFT chip select                    |
| TFT_DC         | 2    | TFT data/command                   |
| TFT_RST        | 4    | TFT reset                          |
| TFT_BL         | —    | Hardwired to 3.3V                  |
| JOY_VRX        | 34   | Joystick X-axis (analog)           |
| JOY_VRY        | 35   | Joystick Y-axis (analog)           |
| JOY_SW         | 13   | Joystick button (INPUT_PULLUP)     |
| BUTTON_PIN     | 12   | Action button (INPUT_PULLUP)       |

## Display config

- **Controller:** ILI9341
- **Interface:** SPI at 40 MHz
- **Resolution:** 320x240 landscape (rotation 1)
- **Library:** `Bodmer/TFT_eSPI` — pins configured via `build_flags` in `platformio.ini` (no `User_Setup.h` needed)

## Joystick config

- **X-axis:** GPIO 34 (analog, 0–4095)
- **Y-axis:** GPIO 35 (analog, 0–4095)
- **Button:** GPIO 13 (digital, INPUT_PULLUP, active LOW)
- **Center value:** 2048
- **Deadzone:** 500 (values 1548–2548 = no movement)
- **Control mode:** binary/digital 4-direction (LEFT, RIGHT, UP, DOWN)
- **Move delay:** 150ms between repeated moves

## Action button

- **GPIO 12**, INPUT_PULLUP, active LOW
- Used to confirm verb selection during gameplay and lock letters during name entry

## Where things will go

| File                    | Purpose                                      |
|-------------------------|----------------------------------------------|
| `src/main.cpp`          | Entry point, state machine, main loop        |
| `src/display.h/.cpp`    | TFT init, drawing helpers                    |
| `src/input.h/.cpp`      | Joystick + button reading, debounce          |
| `src/mqtt_client.h/.cpp`| WiFi + MQTT/TLS connection, pub/sub          |
| `src/game_ui.h/.cpp`    | Game screen: verb boxes, task, score, timer  |
| `src/name_entry.h/.cpp` | 3-letter arcade name entry screen            |
| `src/tutorial.h/.cpp`   | 4-step tutorial state machine                |
| `src/game_loop.h/.cpp`  | 60s round timer, scoring display             |
| `include/secrets.h`     | WiFi/MQTT credentials (gitignored)           |
| `include/ca_cert.h`     | Let's Encrypt ISRG Root X1 CA cert for TLS   |
