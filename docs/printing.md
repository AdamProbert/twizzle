# Printing

## Making the STLs

Run the script (see the [README](../README.md#running-the-cad-script)). Each part is its own component, placed where it sits in the assembly. Right-click a body and pick Save As Mesh, then STL, and rotate it in the slicer as below. The "Reference parts" component (wand, motor, boards, socket, screws, inserts, wall) is only there to check fit, don't print it.

`cad/check/check.py` builds the same parts in CadQuery and writes STLs already in print orientation, plus an interference and overhang report. See [Checking the model](#checking-the-model).

## Orientation

| Part | Print it | Supports | Notes |
| --- | --- | --- | --- |
| Tray | Back face down | None | The index grooves, the three screw counterbores and the centre insert pocket are on the bed side. Counterbore ceilings are short bridges. |
| Dome | Front face down | None | Front bevel is 45°. The lip has a 45° shoulder. Insert pockets, bearing caps and the motor cap all open upwards. |
| Wand gear | Standing on either hub | None | Tooth ends are chamfered 45° so there's no flat overhang. 100 % infill. |
| Motor pinion | Flat | None | 100 % infill. |
| Switch plug | Flat | None | |
| Mount | Back face down | None | The Command strip pockets are 1 mm deep on the bed side, so their ceilings are 20 mm bridges. The index ridges and USB pocket are on top. |

## Settings

PLA, 0.4 mm nozzle, 0.2 mm layers. 3 walls and 20 % infill is plenty. Gears at 100 %. Fuzzy skin on the dome's outer wall only, if you want the chalk look. Use 4 walls round the insert bosses if your slicer lets you set it per part.

## Heat-set inserts

Six M3 inserts, all in 4.2 mm pockets (the PokePi coupon size that fitted perfectly):

- 3 in the dome bosses, pressed in from the seam face
- 1 in the centre of the tray, pressed in from the back
- 2 in the board standoffs, pressed in from the top

The pockets are `INSERT_L + 1` deep. `INSERT_L` defaults to 5.7 mm; change it if yours are longer.

## Fits

All the fits come from `CLEAR` (0.2 mm per side) and a few others at the top of the script: `JOURNAL_CLEAR` for the wand gear in its bearings, `PINION_FIT` for the D bore, `WAND_FIT` for the hex bore, `MOTOR_CLEAR` round the motor can, `LIP_CLEAR` for the dome lip, and `USB_PINCH` for how hard the tray presses the USB socket.

## Measurements to check

These are marked `MEASURE` in the script.

| Parameter | Default | What to measure |
| --- | --- | --- |
| `WAND_AF` | 7.0 | Wand across the flats |
| `INSERT_L` | 5.7 | Heat-set insert length |
| `MOTOR_SHAFT_LEN`, `MOTOR_FLAT_LEN` | 9, 6 | Motor face to shaft tip, and length of the flats. Listings say 8 to 10 mm. The motor moves so the pinion always sits on the flats. |
| `MOTOR_COVER_W`, `MOTOR_COVER_R`, `MOTOR_COVER_LEN` | 16, 17, 17 | The blue wire cover on the motor: width, can centre to its outside, and length. It keys the motor in its cradle. |
| `BOARD_W`, `BOARD_H` | 35 x 32 | Green ULN2003 board outline |
| `BOARD_HOLE_DX`, `BOARD_HOLE_DY`, `BOARD_HOLE_D` | 30 x 27, 3.0 | Hole spacing, and hole size. An M3 needs about 3.2 mm, so the two screw holes may need opening up with a drill. |
| `BOARD_COMP_H` | 9 | Tallest part on the board |
| `SW_TOTAL_H`, `SW_CAP_D` | 11, 12 | Switch body bottom to the top of the cap, and cap diameter |
| `STRIP_T`, `STRIP_L` | 2, 70 | Command strip pair thickness when pressed, and length |

The mount height is worked out from `WAND_WALL_GAP`: the wand ends up `STRIP_T - STRIP_RECESS + MOUNT_H + WAND_Z` = 50 mm off the wall.

## Checking the model

```
pip install cadquery
python cad/check/check.py
```

It runs the same part code as the Fusion script, then reports parts that overlap each other or the bought parts, printed parts that come out in more than one piece, and down-facing faces in each part's print orientation. STLs and a few renders go in `cad/check/out/`. The expected overlaps are the board pins and screws (the reference board has no holes) and the USB socket's 0.2 mm pinch.
