import serial
import time

PORT = "/dev/ttyAMA4"
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


def transaction(ser, frame):
    ser.reset_input_buffer()
    ser.write(frame.encode())
    ser.flush()

    time.sleep(0.05)

    return ser.read_until(b"\n")


ser = serial.Serial(
    PORT,
    9600,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=0.5,
)

try:

    # Enable CW
    frame = make_write(2, 0x0101)

    print("ENABLING MOTOR 2 CW...")
    print("TX:", repr(frame))

    rx = transaction(ser, frame)

    print("RX:", repr(rx))

    print("\nMotor 2 should now be running.")
    print("Running for 2 seconds...")

    time.sleep(2)

finally:

    # Always disable
    frame = make_write(2, 0x0100)

    print("\nDISABLING MOTOR 2...")
    print("TX:", repr(frame))

    try:
        rx = transaction(ser, frame)
        print("RX:", repr(rx))
    except Exception as e:
        print("Disable error:", e)

    ser.close()

print("\nMotor 2 test complete.")
