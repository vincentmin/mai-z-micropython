# MAI-z Shape Drawer (interactive clap mode)

This project makes a Kitronik MAI-z robot draw pen shapes with a Sharpie in the center.

## Controls

- Clap once: switch to next pattern, then draw it.
- Press button B: preview/select next pattern without drawing.
- If your board has no microphone support in firmware, button A is used as clap fallback.

Patterns cycle in this order:

1. Square
2. Triangle
3. Circle
4. Spiral

## Calibration

Open [main.py](main.py) and tune:

- Motor pins: `LEFT_FORWARD_PIN`, `LEFT_REVERSE_PIN`, `RIGHT_FORWARD_PIN`, `RIGHT_REVERSE_PIN`
- Turn accuracy: `TURN_SCALE`
- Clap sensitivity: `CLAP_THRESHOLD`

Tip: if the robot drives backward or spins the wrong way, swap forward/reverse pins for that motor side.
