import serial
import time


PORT = "/dev/ttyAMA0"
BAUD = 9600


def lrc(data):
    """
    Modbus ASCII LRC.
    data = list of binary bytes
    """
    return (-sum(data)) & 0xFF


def make_read_frame(slave_id, address, count=1):
    """
    Manufacturer-compatible Modbus ASCII read frame.
    Function code 03.
    """

    data = [
        slave_id,
        0x03,
        (address >> 8) & 0xFF,
        address & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF,
    ]

    checksum = lrc(data)

    frame = ":" + "".join(f"{b:02X}" for b in data) + f"{checksum:02X}\r\n"

    return frame


ser = serial.Serial(
    PORT,
    BAUD,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1,
)

# Clear anything left in the UART buffer
ser.reset_input_buffer()

frame = make_read_frame(
    slave_id=11,
    address=0,
    count=1,
)

print("TX:", repr(frame))

ser.write(frame.encode("ascii"))
ser.flush()

time.sleep(0.2)

response = ser.read_until(b"\n")

print("RX:", repr(response))

ser.close()
