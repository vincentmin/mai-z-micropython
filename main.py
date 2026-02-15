import microbit as mb
import mai_z


CLAP_THRESHOLD = 170
CLAP_DEBOUNCE_MS = 450


def draw_polygon(sides: int, side_distance: int, speed: int, turn_speed: int) -> None:
    exterior_angle = int(360 / sides)
    for _ in range(sides):
        mai_z.move(mai_z.MoveDirection.FORWARDS, speed, side_distance)
        mb.sleep(80)
        mai_z.rotate_angle(exterior_angle, turn_speed)
        mb.sleep(80)


def draw_square() -> None:
    draw_polygon(
        sides=4,
        side_distance=mai_z.MoveDistance.TWENTY_UNITS,
        speed=48,
        turn_speed=38,
    )


def draw_triangle() -> None:
    draw_polygon(
        sides=3,
        side_distance=mai_z.MoveDistance.TWENTY_FIVE_UNITS,
        speed=48,
        turn_speed=38,
    )


def draw_hexagon() -> None:
    draw_polygon(
        sides=6,
        side_distance=mai_z.MoveDistance.TEN_UNITS,
        speed=44,
        turn_speed=34,
    )


def draw_circle() -> None:
    for _ in range(24):
        mai_z.move(
            mai_z.MoveDirection.FORWARDS,
            42,
            mai_z.MoveDistance.FIVE_UNITS,
        )
        mai_z.rotate_angle(15, 34)
        mb.sleep(40)


def draw_spiral() -> None:
    distances = [
        mai_z.MoveDistance.FIVE_UNITS,
        mai_z.MoveDistance.TEN_UNITS,
        mai_z.MoveDistance.FIFTEEN_UNITS,
        mai_z.MoveDistance.TWENTY_UNITS,
        mai_z.MoveDistance.TWENTY_FIVE_UNITS,
    ]
    for distance in distances:
        mai_z.move(mai_z.MoveDirection.FORWARDS, 45, distance)
        mai_z.rotate_angle(40, 35)
        mb.sleep(60)


PATTERNS = [
    ("square", mb.Image.SQUARE, draw_square, 65280),
    ("triangle", mb.Image.TRIANGLE, draw_triangle, 16776960),
    ("hexagon", mb.Image.DIAMOND, draw_hexagon, 65535),
    ("circle", mb.Image.CLOCK3, draw_circle, 255),
    ("spiral", mb.Image.SNAKE, draw_spiral, 16711935),
]


def show_pattern(index: int) -> None:
    _, icon, _, colour = PATTERNS[index]
    mb.display.show(icon)
    mai_z.set_leds(colour)


def clap_pressed(last_clap_ms: int) -> tuple:
    try:
        level = mb.microphone.sound_level()
    except AttributeError:
        return mb.button_a.was_pressed(), last_clap_ms

    now = mb.running_time()
    if level >= CLAP_THRESHOLD and (now - last_clap_ms) > CLAP_DEBOUNCE_MS:
        return True, now
    return False, last_clap_ms


def run_selected_pattern(index: int) -> None:
    _, _, pattern_fn, _ = PATTERNS[index]
    mai_z.sound_buzzer()
    mb.sleep(120)
    pattern_fn()
    mai_z.stop()


def setup() -> None:
    while not mai_z.init_with_retries(retries=3, delay_ms=150):
        mb.display.show(mb.Image.NO)
        mb.sleep(250)

    mb.display.show(mb.Image.YES)
    mb.sleep(150)
    mai_z.units_select(mai_z.SelectUnits.CENTIMETRES)
    mai_z.set_led_brightness(35)
    mai_z.auto_cliff_detection(mai_z.AutoCliffStatus.ENABLED)


def main():
    setup()
    pattern_index = 0
    last_clap_ms = -CLAP_DEBOUNCE_MS

    mb.display.scroll("CLAP OR A")
    show_pattern(pattern_index)

    while True:
        if mb.button_b.was_pressed():
            pattern_index = (pattern_index + 1) % len(PATTERNS)
            show_pattern(pattern_index)

        clap, last_clap_ms = clap_pressed(last_clap_ms)
        if clap:
            pattern_index = (pattern_index + 1) % len(PATTERNS)
            show_pattern(pattern_index)
            mb.display.show(mb.Image.HAPPY)
            run_selected_pattern(pattern_index)
            show_pattern(pattern_index)

        mb.sleep(25)


main()
