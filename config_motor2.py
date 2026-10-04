import serial
import time

PORT = "/dev/ttyAMA4"
BAUD = 9600
SLAVE = 7


def lrc(data):
    return (-sum(data)) & 0xFF


def make_write(address, value):
    data = [
        SLAVE,
        0x06,
        (address >> 8) & 0xFF,
        address & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF,
    ]

    return (
        ":"
        + "".join(f"{x:02X}" for x in data)
        + f"{lrc(data):02X}\r\n"
    )


def make_read(address):
    data = [
        SLAVE,
        0x03,
        (address >> 8) & 0xFF,
        address & 0xFF,
        0,
        1,
    ]

    return (
        ":"
        + "".join(f"{x:02X}" for x in data)
        + f"{lrc(data):02X}\r\n"
    )


def transaction(ser, frame):
    ser.reset_input_buffer()
    ser.write(frame.encode())
    ser.flush()

    time.sleep(0.05)

    return ser.read_until(b"\n")


ser = serial.Serial(
    PORT,
    BAUD,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=0.5,
)

try:
    # -----------------------------------------
    # Digital mode, CW, DISABLED
    # -----------------------------------------

    frame = make_write(2, 0x0100)

    print("CONFIGURE DIGITAL MODE")
    print("TX:", repr(frame))

    rx = transaction(ser, frame)

    print("RX:", repr(rx))

    # -----------------------------------------
    # Set safe test speed = 320
    # -----------------------------------------

    frame = make_write(14, 320)

    print("\nSET SPEED = 320")
    print("TX:", repr(frame))

    rx = transaction(ser, frame)

    print("RX:", repr(rx))

    # -----------------------------------------
    # Read control back
    # -----------------------------------------

    frame = make_read(2)

    print("\nREAD CONTROL")
    print("TX:", repr(frame))

    rx = transaction(ser, frame)

    print("RX:", repr(rx))

    # -----------------------------------------
    # Read speed back
    # -----------------------------------------

    frame = make_read(14)

    print("\nREAD SPEED")
    print("TX:", repr(frame))

    rx = transaction(ser, frame)

    print("RX:", repr(rx))

finally:
    # Leave motor disabled
    try:
        transaction(ser, make_write(2, 0x0100))
    except Exception:
        pass

    ser.close()

