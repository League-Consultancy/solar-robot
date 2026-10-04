import serial
import time

PORT = "/dev/ttyAMA0"
BAUD = 9600
SLAVE = 7

SPEED_COMMAND = 320
RUN_TIME = 2.0


def lrc(data):
    return (-sum(data)) & 0xFF


def make_write(slave, address, value):
    data = [
        slave,
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


def make_read(slave, address, count=1):
    data = [
        slave,
        0x03,
        (address >> 8) & 0xFF,
        address & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF,
    ]

    return (
        ":"
        + "".join(f"{x:02X}" for x in data)
        + f"{lrc(data):02X}\r\n"
    )


def transaction(ser, frame):
    ser.reset_input_buffer()

    ser.write(frame.encode("ascii"))
    ser.flush()

    time.sleep(0.02)

    return ser.read_until(b"\n").decode("ascii", errors="ignore").strip()


def read_speed(ser):
    """
    Manufacturer register 24.
    """

    frame = make_read(SLAVE, 24, 1)
    response = transaction(ser, frame)

    if not response:
        return None

    # Example:
    # :0703021234XX
    #
    # Data starts after:
    # :07 03 02
    data_hex = response[7:11]

    if len(data_hex) != 4:
        return None

    value = int(data_hex, 16)

    # Speed feedback can be negative in reverse.
    if value >= 0x8000:
        value -= 0x10000

    return value


def read_position(ser):
    """
    Manufacturer registers 20 + 21.
    """

    frame = make_read(SLAVE, 20, 2)
    response = transaction(ser, frame)

    if not response:
        return None

    # Example response:
    # :07 03 04 AABBCCDD XX
    #
    # Extract the four data bytes.
    data_hex = response[7:15]

    if len(data_hex) != 8:
        return None

    # Manufacturer library swaps the two 16-bit words:
    #
    # AABBCCDD -> CCDDAABB
    #
    reordered = data_hex[4:8] + data_hex[0:4]

    value = int(reordered, 16)

    # Convert to signed 32-bit.
    if value >= 0x80000000:
        value -= 0x100000000

    return value


ser = serial.Serial(
    PORT,
    BAUD,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=0.3,
)

try:

    # --------------------------------------------------
    # Set speed
    # --------------------------------------------------

    print("Setting speed =", SPEED_COMMAND)

    frame = make_write(SLAVE, 14, SPEED_COMMAND)
    response = transaction(ser, frame)

    print("SET SPEED TX:", repr(frame))
    print("SET SPEED RX:", repr(response))

    # --------------------------------------------------
    # Enable CW
    # --------------------------------------------------

    print("\nENABLING CW...")

    frame = make_write(SLAVE, 2, 0x0101)
    response = transaction(ser, frame)

    print("ENABLE TX:", repr(frame))
    print("ENABLE RX:", repr(response))

    print("\nReading feedback...\n")

    start = time.monotonic()

    while time.monotonic() - start < RUN_TIME:

        elapsed = time.monotonic() - start

        speed = read_speed(ser)
        position = read_position(ser)

        print(
            f"t={elapsed:5.2f}s | "
            f"speed={speed!s:>6} | "
            f"position={position!s:>10}"
        )

        time.sleep(0.1)

finally:

    # --------------------------------------------------
    # ALWAYS disable motor
    # --------------------------------------------------

    print("\nDISABLING MOTOR...")

    frame = make_write(SLAVE, 2, 0x0100)
    response = transaction(ser, frame)

    print("DISABLE TX:", repr(frame))
    print("DISABLE RX:", repr(response))

    ser.close()

print("\nFeedback test complete.")
