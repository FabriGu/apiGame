ESP32 PIN ASSIGNMENTS - QUICK REFERENCE
========================================

DISPLAY (SPI - ILI9341)
-----------------------
#define TFT_MOSI 23
#define TFT_MISO 19
#define TFT_SCLK 18
#define TFT_CS   5
#define TFT_DC   2
#define TFT_RST  4
// TFT_BL hardwired to 3.3V

JOYSTICK (Analog)
-----------------
#define JOY_VRX  34  // X-axis
#define JOY_VRY  35  // Y-axis
#define JOY_SW   13  // Button

BUTTONS
-------
#define BUTTON_PIN 12

CONFIG VALUES
-------------
#define SPI_FREQUENCY  40000000
#define SCREEN_WIDTH   320
#define SCREEN_HEIGHT  240
#define ROTATION       1  // Landscape

#define JOY_CENTER     2048
#define JOY_DEADZONE   500
#define MOVE_STEP      10
#define MOVE_DELAY     150

CONTROL MODE: Binary/Digital (4-direction)
STATUS: All hardware tested and working
