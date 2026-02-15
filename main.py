import microbit as mb

# Kitronik MAI-z / :MOVE style motor pin map.
# If your robot spins the wrong way, swap the *_FORWARD_PIN and *_REVERSE_PIN
# values for the side that is reversed.
LEFT_FORWARD_PIN = mb.pin8
LEFT_REVERSE_PIN = mb.pin12
RIGHT_FORWARD_PIN = mb.pin16
RIGHT_REVERSE_PIN = mb.pin0

PWM_MAX = 1023
TURN_SCALE = 0.92

CLAP_THRESHOLD = 170
CLAP_DEBOUNCE_MS = 450


def clamp(value, low, high):
	if value < low:
		return low
	if value > high:
		return high
	return value


def stop():
	LEFT_FORWARD_PIN.write_analog(0)
	LEFT_REVERSE_PIN.write_analog(0)
	RIGHT_FORWARD_PIN.write_analog(0)
	RIGHT_REVERSE_PIN.write_analog(0)


def set_motor(forward_pin, reverse_pin, speed_percent):
	speed_percent = clamp(speed_percent, -100, 100)
	pwm = int(abs(speed_percent) * PWM_MAX / 100)

	if speed_percent >= 0:
		forward_pin.write_analog(pwm)
		reverse_pin.write_analog(0)
	else:
		forward_pin.write_analog(0)
		reverse_pin.write_analog(pwm)


def drive(left_speed, right_speed, duration_ms):
	set_motor(LEFT_FORWARD_PIN, LEFT_REVERSE_PIN, left_speed)
	set_motor(RIGHT_FORWARD_PIN, RIGHT_REVERSE_PIN, right_speed)
	mb.sleep(duration_ms)
	stop()


def forward(speed=55, duration_ms=600):
	drive(speed, speed, duration_ms)


def pivot_left(speed=50, duration_ms=380):
	drive(-speed * TURN_SCALE, speed, duration_ms)


def polygon(sides, edge_ms, turn_ms, speed=55):
	for _ in range(sides):
		forward(speed, edge_ms)
		mb.sleep(120)
		pivot_left(50, turn_ms)
		mb.sleep(120)


def draw_square():
	polygon(sides=4, edge_ms=800, turn_ms=430, speed=56)


def draw_triangle():
	polygon(sides=3, edge_ms=900, turn_ms=560, speed=56)


def draw_circle():
	set_motor(LEFT_FORWARD_PIN, LEFT_REVERSE_PIN, 58)
	set_motor(RIGHT_FORWARD_PIN, RIGHT_REVERSE_PIN, 40)
	mb.sleep(4000)
	stop()


def draw_spiral():
	step = 320
	for _ in range(8):
		drive(58, 42, step)
		mb.sleep(80)
		step += 220


PATTERNS = [
	("square", mb.Image.SQUARE, draw_square),
	("triangle", mb.Image.TRIANGLE, draw_triangle),
	("circle", mb.Image.CLOCK3, draw_circle),
	("spiral", mb.Image.SNAKE, draw_spiral),
]


def show_pattern(index):
	_, icon, _ = PATTERNS[index]
	mb.display.show(icon)


def has_clap(last_clap_ms):
	try:
		level = mb.microphone.sound_level()
	except AttributeError:
		return mb.button_a.was_pressed(), last_clap_ms

	now = mb.running_time()
	if level >= CLAP_THRESHOLD and (now - last_clap_ms) > CLAP_DEBOUNCE_MS:
		return True, now
	return False, last_clap_ms


def main():
	pattern_index = 0
	last_clap_ms = -CLAP_DEBOUNCE_MS

	show_pattern(pattern_index)

	while True:
		if mb.button_b.was_pressed():
			pattern_index = (pattern_index + 1) % len(PATTERNS)
			show_pattern(pattern_index)

		clap, last_clap_ms = has_clap(last_clap_ms)
		if clap:
			pattern_index = (pattern_index + 1) % len(PATTERNS)
			show_pattern(pattern_index)
			mb.sleep(250)
			_, _, pattern_fn = PATTERNS[pattern_index]
			pattern_fn()
			show_pattern(pattern_index)

		mb.sleep(25)


main()

