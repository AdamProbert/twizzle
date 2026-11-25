# Wiring

Everything runs on 5 V from the USB-C socket. There's no buck converter or level shifting, the ULN2003 is happy with 3.3 V on its inputs.

| From | To | Notes |
| --- | --- | --- |
| USB-C red | C3 5V and ULN2003 + | |
| USB-C black | C3 GND and ULN2003 - | All grounds joined |
| C3 GPIO4 | ULN2003 IN1 | |
| C3 GPIO5 | ULN2003 IN2 | |
| C3 GPIO6 | ULN2003 IN3 | |
| C3 GPIO7 | ULN2003 IN4 | |
| C3 GPIO10 | Button | Other side of the button to GND, internal pull-up |
| Motor plug | ULN2003 socket | Keyed, only goes one way |

GPIO3 is left free in case I want a status LED later.

Don't plug the C3's own USB in while the USB-C socket is powered. Unplug one or the other when flashing.

The wiring diagram is in the [sketchbook](design/sketchbook.html), section 4.
