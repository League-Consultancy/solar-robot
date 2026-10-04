import serial
import time


PORT = "/dev/ttyAMA1"
BAUDRATE = 9600
SLAVE_ID = 7


def lrc(data):
    return (-sum(data)) & 0xFF


def frame(function, register, value):

    data = bytes([
        SLAVE_ID,
        function,
        (register >> 8) & 0xFF,
        register & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF
    ])

    checksum = lrc(data)

    return (
        b":"
        + data.hex().upper().encode()
        + f"{checksum:02X}".encode()
        + b"\r\n"
    )


def read_register(ser, register):

    data = bytes([
        SLAVE_ID,
        0x03,
        (register >> 8) & 0xFF,
        register & 0xFF,
        0x00,
        0x01
    ])

    checksum = lrc(data)

    request = (
        b":"
        + data.hex().upper().encode()
        + f"{checksum:02X}".encode()
        + b"\r\n"
    )

    ser.reset_input_buffer()
    ser.write(request)
    ser.flush()

    response = ser.read_until(b"\n")

    print("TX:", request.decode().strip())
    print("RX:", response.decode(errors="replace").strip())

    if not response:
        return None

    raw = bytes.fromhex(response.decode().strip()[1:-2])

    value = (raw[3] << 8) | raw[4]

    return value


ser = serial.Serial(
    PORT,
    BAUDRATE,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=1
)

print("================================")
print("RMCS-2304 MOTOR TEST")
print("================================")

# First verify current control
print("\nInitial control register:")
control = read_register(ser, 2)
print(f"Control = 0x{control:04X}")


# Enable Mode 2 + CW
print("\nEnabling Mode 2 CW...")

request = frame(
    0x06,
    2,
    0x0201
)

ser.reset_input_buffer()
ser.write(request)
ser.flush()

response = ser.read_until(b"\n")

print("TX:", request.decode().strip())
print("RX:", response.decode(errors="replace").strip())


# Wait
time.sleep(1)


# Read control register again
print("\nControl register AFTER enable:")

control = read_register(ser, 2)

print(f"Control = 0x{control:04X}")


print("\nMotor should now be commanded CW.")
print("Press ENTER to disable motor.")

input()


# Disable CW
print("\nDisabling motor...")

request = frame(
    0x06,
    2,
    0x0200
)

ser.reset_input_buffer()
ser.write(request)
ser.flush()

response = ser.read_until(b"\n")

print("TX:", request.decode().strip())
print("RX:", response.decode(errors="replace").strip())

ser.close()

print("\nMotor disabled.")
