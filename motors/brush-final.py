import serial
import time


class RMCS2304Motor:
    """
    RMCS-2304 single-direction motor controller

    Hardware:
        Driver : RMCS-2304
        Motor  : RKI-1148
        UART   : /dev/ttyAMA4
        Slave  : 7
        Baud   : 9600

    Control:
        start()     -> motor ON
        stop()      -> motor OFF
        set_speed() -> change speed

    Motor direction is fixed to CW.
    """

    def __init__(
        self,
        port="/dev/ttyAMA1",
        slave_id=7,
        baudrate=9600,
        timeout=0.5
    ):
        self.port = port
        self.slave_id = slave_id
        self.baudrate = baudrate
        self.timeout = timeout

        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=8,
            parity=serial.PARITY_NONE,
            stopbits=1,
            timeout=self.timeout
        )

        # Current speed setting used by the motor
        self.speed = None

    # ---------------------------------------------------------
    # Modbus ASCII
    # ---------------------------------------------------------

    @staticmethod
    def lrc(data):
        """
        Calculate Modbus ASCII LRC.
        """
        total = sum(data) & 0xFF
        return (-total) & 0xFF

    def send_command(self, function, address, value):
        """
        Send Modbus ASCII Write Single Register command.

        Function  : 06
        Address   : register address
        Value     : 16-bit value
        """

        frame = bytes([
            self.slave_id,
            function,
            (address >> 8) & 0xFF,
            address & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF
        ])

        checksum = self.lrc(frame)

        message = (
            b":"
            + frame.hex().upper().encode()
            + f"{checksum:02X}".encode()
            + b"\r\n"
        )

        self.ser.reset_input_buffer()
        self.ser.write(message)

        response = self.ser.readline()

        if not response:
            raise TimeoutError(
                f"No response from RMCS-2304 on {self.port}"
            )

        response = response.decode(errors="ignore").strip()

        return response

    def read_register(self, address):
        """
        Read one holding register.

        Function = 03
        """

        frame = bytes([
            self.slave_id,
            0x03,
            (address >> 8) & 0xFF,
            address & 0xFF,
            0x00,
            0x01
        ])

        checksum = self.lrc(frame)

        message = (
            b":"
            + frame.hex().upper().encode()
            + f"{checksum:02X}".encode()
            + b"\r\n"
        )

        self.ser.reset_input_buffer()
        self.ser.write(message)

        response = self.ser.readline()

        if not response:
            raise TimeoutError(
                f"No response from RMCS-2304 on {self.port}"
            )

        response = response.decode(errors="ignore").strip()

        # Expected:
        # :07 03 02 XX XX LRC

        if not response.startswith(":"):
            raise ValueError(f"Invalid response: {response}")

        raw = bytes.fromhex(response[1:])

        # Data starts at byte 3
        value = (raw[3] << 8) | raw[4]

        return value

    # ---------------------------------------------------------
    # Motor functions
    # ---------------------------------------------------------

    def set_speed(self, speed):
        """
        Set motor speed.

        RMCS-2304 speed register:
            Address = 0x0E
            Range   = 0 - 2048

        This function does NOT start the motor.
        """

        if not 0 <= speed <= 2048:
            raise ValueError(
                "Speed must be between 0 and 2048"
            )

        self.send_command(
            function=0x06,
            address=0x000E,
            value=speed
        )

        self.speed = speed

    def start(self):
        """
        Start motor in CW direction.

        0x0201 = Mode 2 CW Enable
        """

        self.send_command(
            function=0x06,
            address=0x0002,
            value=0x0201
        )

    def stop(self):
        """
        Stop motor.

        0x0200 = Mode 2 CW Disable
        """

        self.send_command(
            function=0x06,
            address=0x0002,
            value=0x0200
        )

    def get_speed(self):
        """
        Read currently configured speed from driver.
        """

        return self.read_register(0x000E)

    def close(self):
        """
        Stop motor and close UART.
        """

        try:
            self.stop()
        except Exception:
            pass

        self.ser.close()


# =============================================================
# Example
# =============================================================

if __name__ == "__main__":

    motor = RMCS2304Motor(
        port="/dev/ttyAMA1",
        slave_id=7,
        baudrate=9600
    )

    try:

        # -----------------------------------------------------
        # Set speed ONCE
        # -----------------------------------------------------

        motor.set_speed(2048)

        print("Speed set to:", motor.get_speed())

        # -----------------------------------------------------
        # Start motor
        # -----------------------------------------------------

        print("Starting motor...")
        motor.start()

        time.sleep(5)

        # -----------------------------------------------------
        # Stop motor
        # -----------------------------------------------------

        print("Stopping motor...")
        motor.stop()

        time.sleep(2)

        # -----------------------------------------------------
        # Start again at SAME speed
        # -----------------------------------------------------

        print("Starting again...")
        motor.start()

        time.sleep(5)

        print("Stopping...")
        motor.stop()

    except KeyboardInterrupt:

        print("\nInterrupted.")

    finally:

        motor.close()
        print("Motor controller closed.")
