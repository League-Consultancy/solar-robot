import serial
import time


PORT = "/dev/ttyAMA4"
BAUD = 9600
SLAVE = 7

LPR = 2262


def lrc(data):
    return (-sum(data)) & 0xFF


def make_frame(slave, function, address, value):
    payload = bytes([
        slave,
        function,
        (address >> 8) & 0xFF,
        address & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF,
    ])

    checksum = lrc(payload)

    return (
        ":"
        + payload.hex().upper()
        + f"{checksum:02X}"
        + "\r\n"
    ).encode("ascii")


def write_register(ser, address, value):

    frame = make_frame(
        SLAVE,
        6,
        address,
        value
    )

    print("TX:", frame.decode().strip())

    ser.reset_input_buffer()

    ser.write(frame)
    ser.flush()

    response = ser.read_until(b"\n")

    print("RX:", response.decode(errors="replace").strip())


def read_register(ser, address):

    frame = make_frame(
        SLAVE,
        3,
        address,
        1
    )

    print("TX:", frame.decode().strip())

    ser.reset_input_buffer()

    ser.write(frame)
    ser.flush()

    response = ser.read_until(b"\n")

    print("RX:", response.decode(errors="replace").strip())

    text = response.decode(errors="replace").strip()

    if not text.startswith(":"):
        return None

    raw = bytes.fromhex(text[1:-2])

    value = (raw[3] << 8) | raw[4]

    return value


ser = serial.Serial(
    PORT,
    BAUD,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=1
)

try:

    print("=" * 60)
    print("RMCS-5031 / RMCS-2303 LPR CONFIGURATION")
    print("=" * 60)

    print("\nCurrent LPR:")

    current = read_register(ser, 10)

    print("Current LPR =", current)

    print("\nSetting LPR =", LPR)

    write_register(
        ser,
        10,
        LPR
    )

    time.sleep(0.5)

    print("\nReading LPR again:")

    new_lpr = read_register(
        ser,
        10
    )

    print("New LPR =", new_lpr)

finally:

    ser.close()
