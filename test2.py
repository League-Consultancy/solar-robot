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

    print("TX:", frame.decode().strip())

    ser.reset_input_buffer()
    ser.write(frame)
    ser.flush()

    response = ser.read_until(b"\n")

    print("RX:", response.decode(errors="replace").strip())


ser = serial.Serial(
    PORT,
    BAUD,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=1
)


print("Starting CCW test...")


# CCW enable
write_register(
    ser,
    2,
    0x0203
)

time.sleep(1)

print("Motor should now be rotating CCW.")

input("Press ENTER to stop...")


# CCW disable
write_register(
    ser,
    2,
    0x0208
)

ser.close()

print("Motor stopped.")
