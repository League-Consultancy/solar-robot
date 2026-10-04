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


def make_read(slave, address):
    data = [
        slave,
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


ser = serial.Serial(
    PORT,
    BAUD,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=0.5,
)

# Set speed register 14 = 320 RPM command
write_frame = make_write(SLAVE, 14, 320)

print("Setting test speed...")
print("TX:", repr(write_frame))

ser.reset_input_buffer()
ser.write(write_frame.encode())
ser.flush()

time.sleep(0.1)

print("RX:", repr(ser.read_until(b"\n")))

# Read speed register back
read_frame = make_read(SLAVE, 14)

print("\nReading speed register...")
print("TX:", repr(read_frame))

ser.reset_input_buffer()
ser.write(read_frame.encode())
ser.flush()

time.sleep(0.1)

print("RX:", repr(ser.read_until(b"\n")))

ser.close()
