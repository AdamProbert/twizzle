# Twizzle

Twizzle is a little white puck that twists the tilt wand on my office venetian blind, so I can open and close it from Home Assistant and Google Assistant. It's a 28BYJ-48 stepper, its green ULN2003 driver board and an ESP32-C3 SuperMini in a 3D printed case, powered from USB-C.

The wand is a 7 mm clear acrylic hex. It goes straight through the puck, and a gear on the wand is driven 1:1 by a gear on the motor. A full open or close takes about 40 seconds, which is fine for a blind.

This repo has the ESPHome firmware, the Fusion 360 script that builds the case, the parts list, the wiring and the design sketches.

## Hardware

| Part | What it does | How it connects |
| --- | --- | --- |
| ESP32-C3 SuperMini | Wi-Fi, runs ESPHome | 5V pin from the USB-C socket |
| 28BYJ-48 5 V stepper | Turns the wand through a 20T to 20T spur gear pair | 5-wire plug into the driver board |
| ULN2003 driver board (green) | Drives the motor coils | IN1 to IN4 on GPIO 4, 5, 6 and 7, plus 5V and GND |
| 12 mm tactile switch, round cap | Tap, double tap and hold controls on the front | GPIO10 to GND |
| USB-C female pigtail socket | 5 V in | Red to 5V, black to GND |

The full parts list, including the screws, is in [docs/parts.md](docs/parts.md). Wiring is in [docs/wiring.md](docs/wiring.md).

## The button

| Press | What it does |
| --- | --- |
| Tap | Open or close (toggles) |
| Tap while moving | Stop |
| Double tap | Half open |
| Hold 3 s | Set the current position as closed |

## Mounting

The wand hangs about 5 cm off the wall and is pulled about 30° to the left. The puck sits on a single 90 mm mount, the same size as the puck, so the whole thing reads as one drum. The mount has 72 ridges round its rim that key into grooves on the back of the tray, and two M3 screws from the back of the mount go into inserts in the tray. The angle between the puck and the mount is `MOUNT_TWIST` in the script (30° now, in 5° steps); to change it, reprint just the mount. Two Command strips stick it to the wall, and the USB-C socket lives in the bottom of the mount, so the cable runs down the wall behind it.

To open it up, pull it off the wall (interlocking picture-hanging strips make that easy), take out the two mount screws, lift off the mount, and undo the three screws that hold the dome on.

## What's in here

- `firmware/` is the ESPHome config. See [Flashing the firmware](#flashing-the-firmware).
- `cad/fusion/Twizzle/` is the Fusion 360 script that builds every part. See [docs/printing.md](docs/printing.md) for how to run it, export the STLs and print them.
- `cad/check/` builds the same parts in CadQuery to check fits, overhangs and print orientation without Fusion.
- `docs/parts.md` is the parts list.
- `docs/wiring.md` is the wiring.
- `docs/printing.md` covers print orientation, settings and the measurements to check.
- `docs/design/sketchbook.html` has the concept sketches from designing it. Open it in a browser.
- `docs/build-log/` is for photos and notes as it gets built.

## Running the CAD script

1. In Fusion, open Utilities > Add-Ins > Scripts and Add-Ins.
2. On the Scripts tab, click the green + and pick the `cad/fusion/Twizzle` folder.
3. Select Twizzle and click Run.

It makes a new design with every part as its own component, in its assembled position. All the sizes are at the top of `Twizzle.py`. The ones marked `MEASURE` are guesses that should be checked before printing.

## Flashing the firmware

1. Copy `firmware/secrets.yaml.example` to `firmware/secrets.yaml` and fill it in. It's git-ignored.
2. Install ESPHome (`uv tool install esphome`). On Windows, set `ESPHOME_ESP_IDF_PREFIX` to a short path like `E:\espidf`, or the toolchain hits the 260-character path limit.
3. Plug in the C3's own USB (not the puck's USB-C socket) and run `esphome run firmware/twizzle.yaml`. After the first flash it updates over Wi-Fi.

`open_turns` at the top of `twizzle.yaml` is a guess. Count the wand turns from closed to open on your blind and set it.

## Build log

Photos and notes from the build go in [docs/build-log](docs/build-log/README.md).
