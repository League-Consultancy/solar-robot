import serial
import time


PORT = "/dev/ttyAMA1"
BAUDRATE = 9600
SLAVE_ID = 7


def calculate_lrc(data):
    total = sum(data) & 0xFF
    return (-total) & 0xFF


def make_read_request(slave_id, register, quantity=1):

    data = bytes([
        slave_id,
        0x03,
        (register >> 8) & 0xFF,
        register & 0xFF,
        (quantity >> 8) & 0xFF,
        quantity & 0xFF
    ])

    lrc = calculate_lrc(data)

    return (
        b":"
        + data.hex().upper().encode()
        + f"{lrc:02X}".encode()
        + b"\r\n"
    )


def read_register(ser, register):

    frame = make_read_request(
        SLAVE_ID,
        register,
        1
    )

    ser.reset_input_buffer()

    print(f"\nRegister {register}:")
    print("TX:", frame.decode().strip())

    ser.write(frame)
    ser.flush()

    time.sleep(0.1)

    response = ser.read_until(b"\n")

    if not response:
        print("RX: NO RESPONSE")
        return None

    response = response.strip()

    print("RX:", response.decode(errors="replace"))
    print("HEX:", response.hex(" "))

    # Expected response:
    # :07 03 02 XX XX LRC

    try:
        text = response.decode()

        if text[0] != ":":
            print("Invalid ASCII Modbus response")
            return None

        # Remove ':' and LRC
        raw = bytes.fromhex(text[1:-2])

        slave = raw[0]
        function = raw[1]
        byte_count = raw[2]

        if slave != SLAVE_ID:
            print(f"Unexpected slave ID: {slave}")
            return None

        if function != 0x03:
            print(f"Unexpected function: {function:02X}")
            return None

        if byte_count != 2:
            print(f"Unexpected byte count: {byte_count}")
            return None

        value = (raw[3] << 8) | raw[4]

        print(f"VALUE: {value} decimal")
        print(f"HEX  : 0x{value:04X}")

        return value

    except Exception as e:
        print("Parsing error:", e)
        return None


def main():

    ser = serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1
    )

    print("================================")
    print("RMCS-2304 Configuration Read")
    print("================================")
    print(f"Port     : {PORT}")
    print(f"Baudrate : {BAUDRATE}")
    print(f"Slave ID : {SLAVE_ID}")

    # 40003 -> address 2
    control = read_register(ser, 2)

    # 40013 -> address 12
    acceleration = read_register(ser, 12)

    # 40015 -> address 14
    speed = read_register(ser, 14)

    ser.close()

    print("\n================================")
    print("CURRENT CONFIGURATION")
    print("================================")

    print(f"Control      : {control} (0x{control:04X})")
    print(f"Acceleration : {acceleration}")
    print(f"Speed        : {speed}")


if __name__ == "__main__":
    main()
