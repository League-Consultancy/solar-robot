import serial
import time

PORT = "/dev/ttyAMA1"
BAUD = 9600
SLAVE = 7


def lrc(data):
    return (-sum(data)) & 0xFF


def write_register(ser, register, value):

    data = bytes([
        SLAVE,
        0x06,
        (register >> 8) & 0xFF,
        register & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF
    ])

    checksum = lrc(data)

    frame = (
        b":"
        + data.hex().upper().encode()
        + f"{checksum:02X}".encode()
        + b"\r\n"
    )

    ser.reset_input_buffer()
    ser.write(frame)
    ser.flush()

    response = ser.read_until(b"\n")

    print("WRITE TX:", frame.decode().strip())
    print("WRITE RX:", response.decode(errors="replace").strip())


def read_register(ser, register):

    data = bytes([
        SLAVE,
        0x03,
        (register >> 8) & 0xFF,
        register & 0xFF,
        0x00,
        0x01
    ])

    checksum = lrc(data)

    frame = (
        b":"
        + data.hex().upper().encode()
        + f"{checksum:02X}".encode()
        + b"\r\n"
    )

    ser.reset_input_buffer()
    ser.write(frame)
    ser.flush()

    response = ser.read_until(b"\n")

    print("READ TX:", frame.decode().strip())
    print("READ RX:", response.decode(errors="replace").strip())

    raw = bytes.fromhex(
        response.decode().strip()[1:-2]
    )

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

print("Current speed:")
print(read_register(ser, 14))

print("\nWriting speed = 120")
write_register(ser, 14, 400)

time.sleep(0.2)

print("\nReading speed back:")
speed = read_register(ser, 14)

print(f"\nFINAL SPEED = {speed}")

ser.close()
