# Printing

## Making the STLs

Run the script (see the [README](../README.md#running-the-cad-script)). Each part is its own component. Right-click a body and pick Save As Mesh, then STL. The "Reference parts" component (wand, motor, boards, wall) is only there to check fit, don't print it.

## Orientation

| Part | Print it | Supports |
| --- | --- | --- |
| Tray | Back face down | None |
| Dome | Front face down | None. The 45° bevel and the button socket print without them. |
| Wand gear | Flat | None |
| Motor pinion | Flat | None |
| Switch plug | Flat | None |
| Spacers | Flat, teeth up | None |
| Base | Flat, teeth up | None |

The half-round wand notches in the tray and dome rims face up when printed, so they print clean.

## Settings

PLA, 0.4 mm nozzle, 0.2 mm layers. 3 walls and 20 % infill is plenty. The gears are better at 100 % infill. Fuzzy skin on the dome's outer wall only, if you want the chalk look.

## Fits

All the fits come from `CLEAR` (0.2 mm per side) and a few others at the top of the script. If the pinion is loose on the shaft, drop the 0.1 mm added to the D bore. If the dome lip is too tight in the tray, raise the 0.15 mm in the `lip_lo` line of `build_dome` or sand it.

## Measurements to check

These are marked `MEASURE` in the script. They're from datasheets and listings, so check them with calipers before printing the tray and dome.

| Parameter | Default | What to measure |
| --- | --- | --- |
| `WAND_AF` | 7.0 | Wand across the flats |
| `WAND_AC` | 8.08 | Wand across the corners |
| `BOARD_W`, `BOARD_H` | 35 x 32 | Green ULN2003 board outline |
| `BOARD_HOLE_DX`, `BOARD_HOLE_DY` | 30 x 27 | Hole spacing, centre to centre |
| `SW_TOTAL_H` | 11 | Switch body bottom to the top of the cap |
| `SW_CAP_D` | 12 | Cap diameter |
| `STRIP_T` | 2 | Command strip thickness, squashed |

The wand ends up `WAND_Z + 5 x SPACER_T + BASE_T + STRIP_T` = 51 mm off the wall. Change `WAND_WALL_GAP` and the script works out how many spacers you need.
