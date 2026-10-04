import serial
import time

PORT = "/dev/ttyAMA0"
BAUD = 9600
SLAVE = 7


def lrc(data):
    return (-sum(data)) & 0xFF


def make_write(slave, address, value):
    """
    Manufacturer-compatible Modbus ASCII Write Single Register.
    Function code 06.
    """
    data = [
        slave,
        0x06,
        (address >> 8) & 0xFF,
        address & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF,
    ]

    checksum = lrc(data)

    return (
        ":"
        + "".join(f"{b:02X}" for b in data)
        + f"{checksum:02X}\r\n"
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

    checksum = lrc(data)

    return (
        ":"
        + "".join(f"{b:02X}" for b in data)
        + f"{checksum:02X}\r\n"
    )


ser = serial.Serial(
    PORT,
    BAUD,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=0.5,
)


# --------------------------------------------------
# 1. Configure Digital Speed Mode, but KEEP MOTOR OFF
# --------------------------------------------------

address = 2
value = 256       # 0x0100
write_frame = make_write(SLAVE, address, value)

print("Writing Digital Mode (disabled)...")
print("TX:", repr(write_frame))

ser.reset_input_buffer()
ser.write(write_frame.encode("ascii"))
ser.flush()

time.sleep(0.1)

response = ser.read_until(b"\n")

print("RX:", repr(response))


# --------------------------------------------------
# 2. Read register 2 back
# --------------------------------------------------

read_frame = make_read(SLAVE, 2, 1)

print("\nReading control register...")
print("TX:", repr(read_frame))

ser.reset_input_buffer()
ser.write(read_frame.encode("ascii"))
ser.flush()

time.sleep(0.1)

response = ser.read_until(b"\n")

print("RX:", repr(response))

ser.close()

