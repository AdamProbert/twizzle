# Twizzle

Twizzle is a little white puck that twists the tilt wand on my office venetian blind, so I can open and close it from Home Assistant and Google Assistant. It's a 28BYJ-48 stepper, its green ULN2003 driver board and an ESP32-C3 SuperMini in a 3D printed case, powered from USB-C.

The wand is a 7 mm clear acrylic hex. It goes straight through the puck, and a gear on the wand is driven 1:1 by a gear on the motor. A full open or close takes about 40 seconds, which is fine for a blind.

This repo has the Fusion 360 script that builds the case, the parts list, the wiring and the design sketches. The firmware isn't in here yet.

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

The wand hangs about 5 cm off the wall and is pulled about 30° to the left. The puck sits on a 60 mm round plinth made of a base and five 5 mm spacers. The spacers have 72 teeth (5° steps), so the puck can be turned to match the wand's angle on the bench, then clamped with one M4 screw through the middle and stuck to the wall with Command strips.

## What's in here

- `cad/fusion/Twizzle/` is the Fusion 360 script that builds every part. See [docs/printing.md](docs/printing.md) for how to run it, export the STLs and print them.
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

## Build log

Photos and notes from the build go in [docs/build-log](docs/build-log/README.md).
