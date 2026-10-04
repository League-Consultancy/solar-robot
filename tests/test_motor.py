import serial
import time

PORT = "/dev/ttyAMA0"
BAUD = 9600
SLAVE = 7


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


def write_register(ser, address, value):
    frame = make_write(SLAVE, address, value)

    print("TX:", repr(frame))

    ser.reset_input_buffer()
    ser.write(frame.encode("ascii"))
    ser.flush()

    time.sleep(0.1)

    response = ser.read_until(b"\n")

    print("RX:", repr(response))

    return response


ser = serial.Serial(
    PORT,
    BAUD,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=0.5,
)

try:
    # Enable Digital Mode, CW
    print("ENABLING MOTOR CW...")
    write_register(ser, 2, 0x0101)

    print("\nMotor should now be running.")
    print("Running for 2 seconds...")

    time.sleep(2)

    # Disable motor
    print("\nDISABLING MOTOR...")
    write_register(ser, 2, 0x0100)

finally:
    # Make sure we leave the driver disabled
    try:
        write_register(ser, 2, 0x0100)
    except Exception:
        pass

    ser.close()

print("\nTest complete.")
