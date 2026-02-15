import microbit as mb

A = 23
K = 100
INCH = 2.54
RET = 3
OUT = 1


class CommandID:
    MOVE = 0x01
    SPIN = 0x02
    STOP = 0x03
    SET_ALL = 0x10
    SET_BRIGHT = 0x12
    AUTO_CLIFF = 0x22
    HORN = 0x30
    ERROR = 0x40
    DONE = 0x41
    START = 0x60


class CommandType:
    TX = 0
    RX = 1


class ErrorCode:
    NO = 0
    START_KEY = 6
    CLIFF = 7


class MoveDirection:
    FORWARDS = 1
    BACKWARDS = 2


class MoveDistance:
    CONTINUOUS = 0
    ONE_UNITS = 1
    TWO_UNITS = 2
    THREE_UNITS = 3
    FOUR_UNITS = 4
    FIVE_UNITS = 5
    TEN_UNITS = 10
    FIFTEEN_UNITS = 15
    TWENTY_UNITS = 20
    TWENTY_FIVE_UNITS = 25


class SelectUnits:
    CENTIMETRES = 0
    INCHES = 1


class AutoCliffStatus:
    DISABLED = 0
    ENABLED = 1


C = {65280: 5, 16776960: 3, 65535: 7, 255: 10, 16711935: 13, 0: 0}

_err = 0
_done = 0
_inches = False


def _enodev(e):
    return bool(getattr(e, "args", None)) and e.args[0] == 19


def is_connected():
    try:
        return A in mb.i2c.scan()
    except OSError:
        return False


def _chk(m):
    s = 0
    for b in m:
        s += b
    return (~s) & 0xFF


def _b(v):
    r = []
    while v > 0:
        r.append(v & 0xFF)
        v >>= 8
    return r


def _tx(cmd, p):
    m = [len(p) + 2, cmd]
    for x in p:
        m.append(x)
    m.append(_chk(m))
    mb.i2c.write(A, bytes(m))


def _rx(cmd):
    global _err, _done
    _tx(cmd, [])
    n = 4
    d = list(mb.i2c.read(A, n))
    if len(d) < 4:
        return
    if _chk(d[:-1]) != d[-1]:
        return
    if d[1] != cmd:
        return
    if cmd == CommandID.ERROR:
        _err = d[2]
    elif cmd == CommandID.DONE:
        _done = d[2]


def _comms(cmd, p, t):
    global _err
    i = 0
    while i <= RET:
        try:
            if t == CommandType.TX:
                _tx(cmd, p)
            else:
                _rx(cmd)
            _rx(CommandID.ERROR)
        except OSError as e:
            if _enodev(e):
                i += 1
                mb.sleep(20)
                continue
            raise

        if _err == ErrorCode.NO:
            return True
        if _err == ErrorCode.START_KEY:
            mb.reset()
        if _err == ErrorCode.CLIFF:
            while _err == ErrorCode.CLIFF:
                mb.sleep(5)
                _rx(CommandID.ERROR)
            i = 0
            continue
        i += 1
        mb.sleep(5)
    return False


def init_with_retries(retries=8, delay_ms=120):
    for _ in range(retries):
        if is_connected():
            try:
                _tx(CommandID.START, [])
                return True
            except OSError as e:
                if not _enodev(e):
                    raise
        mb.sleep(delay_ms)
    return False


def init():
    return init_with_retries()


def units_select(select_units):
    global _inches
    _inches = bool(select_units)


def set_led_brightness(led_brightness):
    if led_brightness < 1:
        led_brightness = 1
    elif led_brightness > 100:
        led_brightness = 100
    _comms(CommandID.SET_BRIGHT, [int((led_brightness * 128) / 100)], CommandType.TX)


def set_leds(colour):
    _comms(CommandID.SET_ALL, [C.get(colour, 0)], CommandType.TX)


def auto_cliff_detection(auto_cliff_status):
    _comms(CommandID.AUTO_CLIFF, [auto_cliff_status], CommandType.TX)


def sound_buzzer():
    _comms(CommandID.HORN, [], CommandType.TX)


def _wait_done():
    global _done
    _comms(CommandID.DONE, [], CommandType.RX)
    mb.sleep(10)
    while _done == OUT:
        _comms(CommandID.DONE, [], CommandType.RX)
        mb.sleep(10)


def move(move_direction, speed, distance):
    if speed < 1:
        speed = 1
    elif speed > 100:
        speed = 100

    dv = int(distance * K)
    if dv == MoveDistance.CONTINUOUS:
        _comms(CommandID.MOVE, [move_direction, int(speed), dv], CommandType.TX)
    else:
        if _inches:
            dv = int(dv * INCH)
        _comms(CommandID.MOVE, [move_direction, int(speed)] + _b(dv), CommandType.TX)
        _wait_done()
    mb.sleep(100)


def rotate_angle(rotate_ratio, speed):
    if speed < 1:
        speed = 1
    elif speed > 100:
        speed = 100

    rd = 1 if rotate_ratio > 0 else 2
    dv = int(abs(rotate_ratio) * K)
    _comms(CommandID.SPIN, [rd, int(speed)] + _b(dv), CommandType.TX)
    _wait_done()
    mb.sleep(100)


def stop():
    _comms(CommandID.STOP, [], CommandType.TX)
    mb.sleep(100)
