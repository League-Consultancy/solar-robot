import serial
import time


PORT = "/dev/ttyAMA4"
BAUD = 9600
SLAVE = 7

LPR = 2262
P_GAIN = 32
I_GAIN = 16
VF_GAIN = 32
ACCELERATION = 20000
SPEED = 320


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


def write_register(ser, address, value, name):

    frame = make_frame(
        SLAVE,
        6,
        address,
        value
    )

    print(f"\n{name}")
    print(f"  Address : {address}")
    print(f"  Value   : {value}")
    print(f"  TX      : {frame.decode().strip()}")

    ser.reset_input_buffer()

    ser.write(frame)
    ser.flush()

    response = ser.read_until(b"\n")

    print(
        f"  RX      : "
        f"{response.decode(errors='replace').strip()}"
    )


def read_register(ser, address, name):

    frame = make_frame(
        SLAVE,
        3,
        address,
        1
    )

    ser.reset_input_buffer()

    ser.write(frame)
    ser.flush()

    response = ser.read_until(b"\n")

    text = response.decode(errors="replace").strip()

    if not text.startswith(":"):
        print(f"{name}: READ ERROR")
        return None

    try:

        raw = bytes.fromhex(text[1:-2])

        value = (raw[3] << 8) | raw[4]

        print(f"{name}: {value}")

        return value

    except Exception as e:

        print(f"{name}: PARSE ERROR: {e}")

        return None


ser = serial.Serial(
    PORT,
    BAUD,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=1
)

try:

    print()
    print("=" * 60)
    print("RMCS-5031 / RMCS-2303 MOTOR CONFIGURATION")
    print("=" * 60)

    # --------------------------------------------------------
    # Make sure motor is disabled
    # --------------------------------------------------------

    write_register(
        ser,
        2,
        0x0100,
        "DISABLE MOTOR"
    )

    time.sleep(0.5)

    # --------------------------------------------------------
    # LPR
    # --------------------------------------------------------

    write_register(
        ser,
        10,
        LPR,
        "SET LPR"
    )

    # --------------------------------------------------------
    # P gain
    # --------------------------------------------------------

    write_register(
        ser,
        4,
        P_GAIN,
        "SET P GAIN"
    )

    # --------------------------------------------------------
    # I gain
    # --------------------------------------------------------

    write_register(
        ser,
        6,
        I_GAIN,
        "SET I GAIN"
    )

    # --------------------------------------------------------
    # VF gain
    # --------------------------------------------------------

    write_register(
        ser,
        8,
        VF_GAIN,
        "SET VF GAIN"
    )

    # --------------------------------------------------------
    # Acceleration
    # --------------------------------------------------------

    write_register(
        ser,
        12,
        ACCELERATION,
        "SET ACCELERATION"
    )

    # --------------------------------------------------------
    # Speed
    # --------------------------------------------------------

    write_register(
        ser,
        14,
        SPEED,
        "SET SPEED"
    )

    time.sleep(0.5)

    # --------------------------------------------------------
    # Verify everything
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("VERIFYING CONFIGURATION")
    print("=" * 60)

    read_register(
        ser,
        10,
        "LPR"
    )

    read_register(
        ser,
        4,
        "P GAIN"
    )

    read_register(
        ser,
        6,
        "I GAIN"
    )

    read_register(
        ser,
        8,
        "VF GAIN"
    )

    read_register(
        ser,
        12,
        "ACCELERATION"
    )

    read_register(
        ser,
        14,
        "SPEED"
    )

    # --------------------------------------------------------
    # Final disabled state
    # --------------------------------------------------------

    write_register(
        ser,
        2,
        0x0100,
        "FINAL DISABLE"
    )

    print()
    print("=" * 60)
    print("CONFIGURATION COMPLETE")
    print("=" * 60)

finally:

    ser.close()
