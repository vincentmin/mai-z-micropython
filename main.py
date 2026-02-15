import microbit as mb
import mai_z


def run_demo_once():
    mai_z.init()
    mai_z.units_select(mai_z.SelectUnits.CENTIMETRES)

    mai_z.set_led_brightness(30)
    mai_z.set_leds(65280)
    mai_z.sound_buzzer()

    mai_z.move(mai_z.MoveDirection.FORWARDS, 50, mai_z.MoveDistance.TEN_UNITS)
    mai_z.rotate_angle(90, 40)
    mai_z.move(mai_z.MoveDirection.BACKWARDS, 40, mai_z.MoveDistance.FIVE_UNITS)

    mai_z.stop()
    mai_z.set_leds(0)


def main():
    mb.display.scroll("A=RUN")

    while True:
        if mb.button_a.was_pressed():
            mb.display.show(mb.Image.HAPPY)
            run_demo_once()
            mb.display.show(mb.Image.YES)

        mb.sleep(25)


main()
