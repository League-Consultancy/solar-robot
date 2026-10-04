import serial
import time

PORT = "/dev/ttyAMA0"
BAUD = 9600
SLAVE = 7

SPEED = 320
RUN_TIME = 2.0


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

    return ":" + "".join(f"{x:02X}" for x in data) + f"{lrc(data):02X}\r\n"


def make_read(address, count=1):
    data = [
        SLAVE,
        0x03,
        (address >> 8) & 0xFF,
        address & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF,
    ]

    return ":" + "".join(f"{x:02X}" for x in data) + f"{lrc(data):02X}\r\n"


def transaction(ser, frame):
    ser.reset_input_buffer()
    ser.write(frame.encode())
    ser.flush()
    time.sleep(0.02)
    return ser.read_until(b"\n").decode(errors="ignore").strip()


def read_position(ser):
    response = transaction(ser, make_read(20, 2))

    if not response:
        return None

    data = response[7:15]

    if len(data) != 8:
        return None

    # Same word swap used by manufacturer's library
    value = int(data[4:8] + data[0:4], 16)

    if value >= 0x80000000:
        value -= 0x100000000

    return value


ser = serial.Serial(
    PORT,
    BAUD,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=0.3
)

try:
    # Set speed
    print("Setting speed:", SPEED)
    print(transaction(ser, make_write(14, SPEED)))

    # Enable CCW
    print("Enabling CCW...")
    print(transaction(ser, make_write(2, 0x0109)))

    start = time.monotonic()

    while time.monotonic() - start < RUN_TIME:
        position = read_position(ser)

        print(
            f"t={time.monotonic() - start:.2f}s "
            f"position={position}"
        )

        time.sleep(0.1)

finally:
    # Disable
    print("Disabling motor...")
    print(transaction(ser, make_write(2, 0x0100)))

    ser.close()

print("CCW test complete.")
