import microbit as mb

I2C_ADDRESS = 23
INCHES_CONSTANT = 2.54
DISTANCE_CONSTANT = 100
MAX_RETRIES = 3
COMMAND_OUTSTANDING = 0x01


class CommandID:
    MOVE = 0x01
    SPIN = 0x02
    STOP = 0x03
    GRADUAL_STOP = 0x04
    TURN_ROVER = 0x05

    TURN_ALL_ZIP_LEDS = 0x10
    SET_ZIP_LED = 0x11
    SET_ZIP_LED_BRIGHTNESS = 0x12
    INDICATOR_LIGHT = 0x13
    BREAK_LIGHT = 0x14

    LINE_FOLLOWING_DETECT = 0x20
    MEASURE_DISTANCE_FRONT = 0x21
    AUTO_CLIFF_DETECT = 0x22

    SOUND_HORN = 0x30

    ERROR_READ = 0x40
    COMMAND_FINISHED_READ = 0x41

    COMMS_RESET = 0x50
    START_KEY = 0x60

    SOFTWARE_VERSION = 0x80


class CommandType:
    TX = 0x00
    RX = 0x01


class ErrorCode:
    NO_ERROR = 0x00
    TIMEOUT_ERROR = 0x01
    TX_CHECK_BYTE_ERROR = 0x02
    UNKNOWN_COMMAND_ERROR = 0x03
    INVALID_DATA_ERROR = 0x04
    READ_ERROR = 0x05
    START_KEY_ERROR = 0x06
    CLIFF_DETECTED = 0x07

    RX_CHECKBYTE_ERROR = 0x08
    RX_COMMAND_ERROR = 0x09


class MoveDirection:
    FORWARDS = 0x01
    BACKWARDS = 0x02


class MoveDistance:
    CONTINUOUS = 0x00
    ONE_UNIT = 0x01
    TWO_UNITS = 0x02
    THREE_UNITS = 0x03
    FOUR_UNITS = 0x04
    FIVE_UNITS = 0x05
    TEN_UNITS = 0x0A
    FIFTEEN_UNITS = 0x0F
    TWENTY_UNITS = 0x14
    TWENTY_FIVE_UNITS = 0x19
    FIFTY_UNITS = 0x32
    ONE_HUNDRED_UNITS = 0x64
    TWO_HUNDRED_UNITS = 0xC8
    FIVE_HUNDRED_UNITS = 0x01F4
    ONE_THOUSAND_UNITS = 0x03E8


class RotateDirection:
    CLOCKWISE = 0x01
    ANTICLOCKWISE = 0x02


class LedID:
    LED_ONE = 0x00
    LED_TWO = 0x01
    LED_THREE = 0x02
    LED_FOUR = 0x03


class IndicatorStatus:
    OFF = 0x00
    LEFT = 0x01
    RIGHT = 0x02
    HAZARDS = 0x03


class BrakeStatus:
    OFF = 0x00
    ON = 0x01


class LineFollowSensor:
    RIGHT = 0x01
    CENTRE = 0x02
    LEFT = 0x04


class AutoCliffStatus:
    ENABLED = 0x01
    DISABLED = 0x00


class MoveXTiles:
    ONE = 0x01
    TWO = 0x02
    THREE = 0x03
    FOUR = 0x04
    FIVE = 0x05
    SIX = 0x06
    SEVEN = 0x07
    EIGHT = 0x08
    NINE = 0x09
    TEN = 0x0A
    ELEVEN = 0x0B
    TWELVE = 0x0C


class TurnTiles:
    RIGHT = 0x01
    LEFT = 0x02


class SelectUnits:
    CENTIMETRES = 0x00
    INCHES = 0x01


# MakeCode color picker decimal value -> Mai-Z color code.
COLOUR_ID = {
    16711680: 0x01,  # red
    16744448: 0x02,  # orange
    16776960: 0x03,  # yellow
    16752037: 0x04,  # light pink
    65280: 0x05,  # green
    11575039: 0x06,  # lilac
    65535: 0x07,  # cyan
    32767: 0x08,  # light blue
    6637343: 0x09,  # brown
    255: 0x0A,  # blue
    8323327: 0x0B,  # violet
    16711808: 0x0C,  # pink
    16711935: 0x0D,  # magenta
    16777215: 0x0E,  # white
    10066329: 0x0F,  # gray
    0: 0x00,  # off/black
}


# -----------------------------------------------------------------------------
# Mutable module state
# -----------------------------------------------------------------------------

_distance_value: int = 0
_line_follow_value: int = 0x00
_front_distance_value: float = 0
_auto_cliff_enabled: bool = False
_false_cliff_counter: int = 0
_current_cliff_status: bool = False
_error_status: int = 0x00
_command_completed_status: int = 0x00
_inches_flag: bool = False
_successful_comms_reset: bool = False
_software_version: int = 0


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _clamp(value: int, low: int, high: int) -> int:
    """Clamp value to the inclusive range [low, high]"""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _colour_id_mapper(colour: int) -> int:
    """Map MakeCode RGB decimal color to Mai-Z LED color id"""
    return COLOUR_ID.get(colour, 0x00)


def _int_to_bytes(value: int) -> list:
    """Convert a positive integer to little-endian byte list"""
    arr: list = []
    while value > 0:
        arr.append(value & 0xFF)
        value >>= 8
    return arr


def _calculate_check_byte(message: list) -> int:
    """Calculate protocol check byte for a message payload"""
    check_byte = 0
    for b in message:
        check_byte += b
    return (~check_byte) & 0xFF


def _is_enodev(err: OSError) -> bool:
    return bool(getattr(err, "args", None)) and err.args[0] == 19


def is_connected() -> bool:
    try:
        return I2C_ADDRESS in mb.i2c.scan()
    except OSError:
        return False


def _tx_message(command_id: int, params: list) -> None:
    """Send one protocol message to Mai-Z over I2C"""
    message_len = len(params) + 2
    message = [message_len, command_id]
    for p in params:
        message.append(p)
    message.append(_calculate_check_byte(message))
    mb.i2c.write(I2C_ADDRESS, bytes(message))


def _rx_message(read_id: int) -> None:
    """Issue a read command and store decoded response in module state"""
    global _line_follow_value
    global _front_distance_value
    global _error_status
    global _command_completed_status
    global _successful_comms_reset
    global _software_version

    _tx_message(read_id, [])

    if read_id == CommandID.MEASURE_DISTANCE_FRONT:
        rx = mb.i2c.read(I2C_ADDRESS, 5)
    else:
        rx = mb.i2c.read(I2C_ADDRESS, 4)

    rx_data = list(rx)
    if len(rx_data) < 4:
        _error_status = ErrorCode.READ_ERROR
        return

    check_data = rx_data[:-1]
    rx_check = _calculate_check_byte(check_data)
    if rx_check != rx_data[-1]:
        _error_status = ErrorCode.RX_CHECKBYTE_ERROR
        return

    rx_command_id = rx_data[1]
    if rx_command_id != read_id:
        _error_status = ErrorCode.RX_COMMAND_ERROR
        return

    if rx_command_id == CommandID.LINE_FOLLOWING_DETECT:
        _line_follow_value = rx_data[2]
        return

    if rx_command_id == CommandID.MEASURE_DISTANCE_FRONT:
        raw = (rx_data[3] << 8) | rx_data[2]
        _front_distance_value = (raw / 100) - 2
        return

    if rx_command_id == CommandID.ERROR_READ:
        _error_status = rx_data[2]
        return

    if rx_command_id == CommandID.COMMAND_FINISHED_READ:
        _command_completed_status = rx_data[2]
        return

    if rx_command_id == CommandID.COMMS_RESET:
        if rx_data[2] == 0x02:
            _successful_comms_reset = True
        return

    if rx_command_id == CommandID.SOFTWARE_VERSION:
        _software_version = rx_data[2]


def _comms_retries(
    command_id: int, command_params: list, comms_type: CommandType
) -> None:
    """Execute TX/RX command with retry and built-in error polling"""
    global _error_status

    retries = 0
    while retries <= MAX_RETRIES:
        try:
            if comms_type == CommandType.TX:
                _tx_message(command_id, command_params)
            else:
                _rx_message(command_id)

            _rx_message(CommandID.ERROR_READ)
        except OSError as err:
            if _is_enodev(err):
                retries += 1
                mb.sleep(20)
                continue
            raise

        if _error_status == ErrorCode.NO_ERROR:
            return

        if _error_status == ErrorCode.START_KEY_ERROR:
            _error_status = ErrorCode.NO_ERROR
            mb.reset()

        if _error_status == ErrorCode.CLIFF_DETECTED:
            while _error_status == ErrorCode.CLIFF_DETECTED:
                mb.sleep(5)
                _rx_message(CommandID.ERROR_READ)
            mb.sleep(500)
            retries = 0
            continue

        retries += 1
        mb.sleep(5)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def init() -> bool:
    """Initialise Mai-Z communication.

    Returns True when Mai-Z is detected and START_KEY is sent, otherwise False.
    """
    return init_with_retries()


def init_with_retries(retries: int = 8, delay_ms: int = 120) -> bool:
    for _ in range(retries):
        if is_connected():
            try:
                _tx_message(CommandID.START_KEY, [])
                return True
            except OSError as err:
                if not _is_enodev(err):
                    raise
        mb.sleep(delay_ms)
    return False


def move(move_direction: MoveDirection, speed: int, distance: MoveDistance) -> None:
    """Move forwards/backwards at speed (%) for selected distance units"""
    global _distance_value

    capped_speed = int(_clamp(round(speed), 1, 100))
    _distance_value = int(distance * DISTANCE_CONSTANT)

    if _distance_value == MoveDistance.CONTINUOUS:
        _comms_retries(
            CommandID.MOVE,
            [move_direction, capped_speed, _distance_value],
            CommandType.TX,
        )
    else:
        if _inches_flag:
            _distance_value = int(_distance_value * INCHES_CONSTANT)

        distance_arr = _int_to_bytes(_distance_value)
        _comms_retries(
            CommandID.MOVE,
            [move_direction, capped_speed] + distance_arr,
            CommandType.TX,
        )
        _comms_retries(CommandID.COMMAND_FINISHED_READ, [], CommandType.RX)
        mb.sleep(10)

        while _command_completed_status == COMMAND_OUTSTANDING:
            _comms_retries(CommandID.COMMAND_FINISHED_READ, [], CommandType.RX)
            mb.sleep(10)

    mb.sleep(100)


def rotate_continuous(rotate_direction: RotateDirection, speed: int) -> None:
    """Rotate continuously clockwise or anticlockwise at speed (%)"""
    capped_speed = int(_clamp(round(speed), 1, 100))
    _comms_retries(
        CommandID.SPIN,
        [rotate_direction, capped_speed, MoveDistance.CONTINUOUS],
        CommandType.TX,
    )
    mb.sleep(100)


def rotate_angle(rotate_ratio: int, speed: int) -> None:
    """Rotate by angle in degrees at speed (%)"""
    capped_speed = int(_clamp(round(speed), 1, 100))
    rotate_direction = (
        RotateDirection.CLOCKWISE if rotate_ratio > 0 else RotateDirection.ANTICLOCKWISE
    )

    distance_value = int(abs(rotate_ratio) * DISTANCE_CONSTANT)
    distance_arr = _int_to_bytes(distance_value)

    _comms_retries(
        CommandID.SPIN, [rotate_direction, capped_speed] + distance_arr, CommandType.TX
    )
    _comms_retries(CommandID.COMMAND_FINISHED_READ, [], CommandType.RX)
    mb.sleep(10)

    while _command_completed_status == COMMAND_OUTSTANDING:
        _comms_retries(CommandID.COMMAND_FINISHED_READ, [], CommandType.RX)
        mb.sleep(10)

    mb.sleep(100)


def rotate_360(rotate_direction: RotateDirection, speed: int) -> None:
    """Rotate one full turn (360°) in selected direction at speed (%)"""
    capped_speed = int(_clamp(round(speed), 1, 100))
    _comms_retries(
        CommandID.SPIN, [rotate_direction, capped_speed, 0xA0, 0x8C], CommandType.TX
    )
    _comms_retries(CommandID.COMMAND_FINISHED_READ, [], CommandType.RX)
    mb.sleep(10)

    while _command_completed_status == COMMAND_OUTSTANDING:
        _comms_retries(CommandID.COMMAND_FINISHED_READ, [], CommandType.RX)
        mb.sleep(10)

    mb.sleep(100)


def stop() -> None:
    """Stop Mai-Z motors immediately"""
    _comms_retries(CommandID.STOP, [], CommandType.TX)
    mb.sleep(100)


def gradual_stop() -> None:
    """Gradually decelerate Mai-Z to a stop"""
    _comms_retries(CommandID.GRADUAL_STOP, [], CommandType.TX)
    _comms_retries(CommandID.COMMAND_FINISHED_READ, [], CommandType.RX)
    mb.sleep(10)

    while _command_completed_status == COMMAND_OUTSTANDING:
        _comms_retries(CommandID.COMMAND_FINISHED_READ, [], CommandType.RX)
        mb.sleep(10)

    mb.sleep(100)


def move_tiles(move_x_tiles: MoveXTiles, speed: int) -> None:
    """Move forwards by selected number of tiles at speed (%)"""
    capped_speed = int(_clamp(round(speed), 1, 100))
    distance_value = int(move_x_tiles * 13.5 * DISTANCE_CONSTANT)
    distance_arr = _int_to_bytes(distance_value)

    _comms_retries(
        CommandID.MOVE,
        [MoveDirection.FORWARDS, capped_speed] + distance_arr,
        CommandType.TX,
    )
    _comms_retries(CommandID.COMMAND_FINISHED_READ, [], CommandType.RX)
    mb.sleep(10)

    while _command_completed_status == COMMAND_OUTSTANDING:
        _comms_retries(CommandID.COMMAND_FINISHED_READ, [], CommandType.RX)
        mb.sleep(10)

    mb.sleep(100)


def turn_tiles(tile_turn_direction: TurnTiles) -> None:
    """Turn 90° left or right for tile movement routines"""
    _comms_retries(
        CommandID.SPIN, [tile_turn_direction, 50, 0x28, 0x23], CommandType.TX
    )
    _comms_retries(CommandID.COMMAND_FINISHED_READ, [], CommandType.RX)
    mb.sleep(10)

    while _command_completed_status == COMMAND_OUTSTANDING:
        _comms_retries(CommandID.COMMAND_FINISHED_READ, [], CommandType.RX)
        mb.sleep(10)

    mb.sleep(100)


def u_turn() -> None:
    """Turn 180° for tile movement routines"""
    _comms_retries(
        CommandID.SPIN, [RotateDirection.CLOCKWISE, 50, 0x50, 0x46], CommandType.TX
    )
    _comms_retries(CommandID.COMMAND_FINISHED_READ, [], CommandType.RX)
    mb.sleep(10)

    while _command_completed_status == COMMAND_OUTSTANDING:
        _comms_retries(CommandID.COMMAND_FINISHED_READ, [], CommandType.RX)
        mb.sleep(10)

    mb.sleep(100)


def set_leds(colour: int) -> None:
    """Set all Mai-Z LEDs to one color picker value"""
    _comms_retries(
        CommandID.TURN_ALL_ZIP_LEDS, [_colour_id_mapper(colour)], CommandType.TX
    )


def set_led(led_id: LedID, colour: int) -> None:
    """Set one Mai-Z LED to one color picker value"""
    _comms_retries(
        CommandID.SET_ZIP_LED, [led_id, _colour_id_mapper(colour)], CommandType.TX
    )


def set_led_brightness(led_brightness: int) -> None:
    """Set global LED brightness as percentage"""
    mapped = int((led_brightness * 128) / 100)
    _comms_retries(CommandID.SET_ZIP_LED_BRIGHTNESS, [mapped], CommandType.TX)


def set_indicator_lights(indicator_status: IndicatorStatus) -> None:
    """Set indicator light state"""
    _comms_retries(CommandID.INDICATOR_LIGHT, [indicator_status], CommandType.TX)


def set_brake_lights(brake_status: BrakeStatus) -> None:
    """Set brake light state"""
    _comms_retries(CommandID.BREAK_LIGHT, [brake_status], CommandType.TX)


def sound_buzzer() -> None:
    """Play Mai-Z horn beep pattern"""
    _comms_retries(CommandID.SOUND_HORN, [], CommandType.TX)


def line_follow_status(line_follow_sensor: LineFollowSensor) -> bool:
    """Return selected line-follow sensor state. True if selected sensor detects the line; otherwise False"""
    _comms_retries(CommandID.LINE_FOLLOWING_DETECT, [], CommandType.RX)
    sensor_state = _line_follow_value & line_follow_sensor
    return bool(sensor_state)


def cliff_detection_status() -> bool:
    """Return filtered cliff detection state"""
    global _false_cliff_counter
    global _current_cliff_status

    _comms_retries(CommandID.LINE_FOLLOWING_DETECT, [], CommandType.RX)
    cliff_detect_state = (_line_follow_value >> 3) & 0x01

    if cliff_detect_state:
        _false_cliff_counter = 0
        _current_cliff_status = True
    else:
        _false_cliff_counter += 1
        if _false_cliff_counter >= 3:
            _current_cliff_status = False

    return _current_cliff_status


def auto_cliff_detection(auto_cliff_status: AutoCliffStatus) -> None:
    """Enable or disable onboard auto-cliff stop behavior"""
    global _auto_cliff_enabled

    _comms_retries(CommandID.AUTO_CLIFF_DETECT, [auto_cliff_status], CommandType.TX)
    _auto_cliff_enabled = auto_cliff_status == AutoCliffStatus.ENABLED


def measure_front_distance() -> int:
    """Measure front distance in selected units"""
    _comms_retries(CommandID.MEASURE_DISTANCE_FRONT, [], CommandType.RX)
    if _inches_flag:
        return int(_front_distance_value / INCHES_CONSTANT)
    return int(_front_distance_value)


def units_select(select_units: SelectUnits) -> None:
    """Select distance units for movement and distance reads"""
    global _inches_flag

    _inches_flag = bool(select_units)


def software_version() -> int:
    """Return Mai-Z backend firmware version number"""
    _comms_retries(CommandID.SOFTWARE_VERSION, [], CommandType.RX)
    return _software_version


# Optional MakeCode-like aliases
maizMove = move
maizRotateContinuous = rotate_continuous
maizRotateAngle = rotate_angle
maiz360Rotation = rotate_360
maizStop = stop
maizGradualStop = gradual_stop
maizMoveTiles = move_tiles
maizTurnTiles = turn_tiles
maizUTurn = u_turn
setLEDs = set_leds
setLED = set_led
setLEDBrightness = set_led_brightness
setIndicatorLights = set_indicator_lights
setBrakeLights = set_brake_lights
lineFollowStatus = line_follow_status
cliffDetectionStatus = cliff_detection_status
autoCliffDetection = auto_cliff_detection
measureFrontDistance = measure_front_distance
unitsSelect = units_select
returnSoftwareVersion = software_version
