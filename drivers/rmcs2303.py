import serial
import time


class RMCS2303:
    """
    Python driver for RMCS-2303.

    Protocol:
        Modbus ASCII
        9600 8N1
        Function 03 = Read Holding Registers
        Function 06 = Write Single Register
    """

    # RMCS registers used by this driver
    REG_MODBUS_ID = 1
    REG_CONTROL = 2
    REG_MODE = 3
    REG_P_GAIN = 4
    REG_I_GAIN = 6
    REG_VF_GAIN = 8
    REG_LPR = 10
    REG_ACCELERATION = 12
    REG_SPEED = 14

    REG_POSITION = 20       # 2 registers: 20 + 21
    REG_SPEED_FEEDBACK = 24

    # Control values from manufacturer library
    DIGITAL_CW_DISABLED = 0x0100
    DIGITAL_CW_ENABLED = 0x0101

    DIGITAL_CCW_DISABLED = 0x0108
    DIGITAL_CCW_ENABLED = 0x0109

    BRAKE_CW = 0x0104
    BRAKE_CCW = 0x010C

    ESTOP = 0x0700
    STOP = 0x0701
    SET_HOME = 0x0800
    RESTART = 0x0900

    def __init__(
        self,
        port,
        slave_id=7,
        baudrate=9600,
        timeout=0.5,
    ):
        self.port_name = port
        self.slave_id = slave_id

        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )

    # ---------------------------------------------------------
    # Protocol
    # ---------------------------------------------------------

    @staticmethod
    def _lrc(data):
        """Modbus ASCII LRC."""
        return (-sum(data)) & 0xFF

    def _make_frame(self, function, address, value):
        """
        Build the same frame used by the manufacturer library.

        :ID FC ADDRESS_HI ADDRESS_LO DATA_HI DATA_LO LRC CR LF
        """

        data = [
            self.slave_id,
            function,
            (address >> 8) & 0xFF,
            address & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF,
        ]

        checksum = self._lrc(data)

        return (
            ":"
            + "".join(f"{byte:02X}" for byte in data)
            + f"{checksum:02X}\r\n"
        )

    def _transaction(self, frame):
        """Send one frame and return the response string."""

        self.ser.reset_input_buffer()

        self.ser.write(frame.encode("ascii"))
        self.ser.flush()

        time.sleep(0.02)

        response = self.ser.read_until(b"\n")

        if not response:
            raise TimeoutError(
                f"No response from RMCS ID {self.slave_id} "
                f"on {self.port_name}"
            )

        response = response.decode(
            "ascii",
            errors="ignore",
        ).strip()

        return response

    # ---------------------------------------------------------
    # Write / Read
    # ---------------------------------------------------------

    def write_register(self, address, value):
        """
        Write one 16-bit register.

        Manufacturer uses function code 06.
        """

        if not 0 <= value <= 0xFFFF:
            raise ValueError("Register value must be 0..65535")

        frame = self._make_frame(
            0x06,
            address,
            value,
        )

        response = self._transaction(frame)

        # Manufacturer controller echoes the write frame.
        if response != frame.strip():
            raise IOError(
                f"Unexpected write response.\n"
                f"TX: {frame.strip()}\n"
                f"RX: {response}"
            )

        return True

    def read_register(self, address, count=1):
        """
        Read one or more registers.

        Manufacturer uses function code 03.
        """

        frame = self._make_frame(
            0x03,
            address,
            count,
        )

        response = self._transaction(frame)

        # Expected response:
        #
        # :ID 03 BYTE_COUNT DATA... LRC
        #
        # Example one register:
        # :0703020140B3

        if not response.startswith(":"):
            raise IOError(f"Invalid response: {response}")

        # Remove ':'
        hex_data = response[1:]

        # Convert ASCII hex into bytes.
        try:
            raw = bytes.fromhex(hex_data)
        except ValueError:
            raise IOError(
                f"Invalid hexadecimal response: {response}"
            )

        # Minimum:
        # ID + FC + byte_count + LRC
        if len(raw) < 4:
            raise IOError(
                f"Response too short: {response}"
            )

        # Verify LRC.
        received_lrc = raw[-1]
        calculated_lrc = self._lrc(raw[:-1])

        if received_lrc != calculated_lrc:
            raise IOError(
                f"LRC error.\n"
                f"Response: {response}\n"
                f"Received: {received_lrc:02X}\n"
                f"Calculated: {calculated_lrc:02X}"
            )

        # Verify slave ID.
        if raw[0] != self.slave_id:
            raise IOError(
                f"Unexpected slave ID: {raw[0]}"
            )

        # Verify function.
        if raw[1] != 0x03:
            raise IOError(
                f"Unexpected function: {raw[1]:02X}"
            )

        byte_count = raw[2]

        expected_byte_count = count * 2

        if byte_count != expected_byte_count:
            raise IOError(
                f"Expected {expected_byte_count} data bytes, "
                f"got {byte_count}"
            )

        data = raw[3:3 + byte_count]

        values = []

        for i in range(0, len(data), 2):
            value = (data[i] << 8) | data[i + 1]
            values.append(value)

        return values

    # ---------------------------------------------------------
    # Configuration
    # ---------------------------------------------------------

    def get_id(self):
        return self.read_register(
            self.REG_MODBUS_ID
        )[0]

    def get_control(self):
        return self.read_register(
            self.REG_CONTROL
        )[0]

    def get_mode(self):
        return self.read_register(
            self.REG_MODE
        )[0]

    def get_lpr(self):
        return self.read_register(
            self.REG_LPR
        )[0]

    def get_acceleration(self):
        return self.read_register(
            self.REG_ACCELERATION
        )[0]

    def get_speed_command(self):
        return self.read_register(
            self.REG_SPEED
        )[0]

    def set_speed(self, speed):
        """
        Set digital speed command.

        Does NOT enable the motor.
        """

        if not 0 <= speed <= 65535:
            raise ValueError(
                "Speed must be between 0 and 65535"
            )

        return self.write_register(
            self.REG_SPEED,
            speed,
        )

    # ---------------------------------------------------------
    # Digital mode
    # ---------------------------------------------------------

    def digital_cw(self):
        """Enable digital mode and run CW."""

        return self.write_register(
            self.REG_CONTROL,
            self.DIGITAL_CW_ENABLED,
        )

    def digital_ccw(self):
        """Enable digital mode and run CCW."""

        return self.write_register(
            self.REG_CONTROL,
            self.DIGITAL_CCW_ENABLED,
        )

    def disable_cw(self):
        """Disable digital mode in CW direction."""
        self.write_register(2, 0x0100)


    def disable_ccw(self):
        """Disable digital mode in CCW direction."""
        self.write_register(2, 0x0108)


    def disable(self):
        """Legacy/default disable. Prefer disable_cw() or disable_ccw()."""
        self.disable_cw()

    def brake_cw(self):
        return self.write_register(
            self.REG_CONTROL,
            self.BRAKE_CW,
        )

    def brake_ccw(self):
        return self.write_register(
            self.REG_CONTROL,
            self.BRAKE_CCW,
        )

    def stop(self):
        """
        Manufacturer STOP command.
        """

        return self.write_register(
            self.REG_CONTROL,
            self.STOP,
        )

    def estop(self):
        """
        Manufacturer emergency-stop command.
        """

        return self.write_register(
            self.REG_CONTROL,
            self.ESTOP,
        )

    # ---------------------------------------------------------
    # Encoder / feedback
    # ---------------------------------------------------------

    def get_speed_feedback(self):
        """
        Read manufacturer speed-feedback register.

        Returns signed 16-bit value according to
        manufacturer's Speed_Feedback() implementation.
        """

        value = self.read_register(
            self.REG_SPEED_FEEDBACK
        )[0]

        if value > 32765:
            value -= 65535

        return value

    def get_position(self):
        """
        Read 32-bit encoder position.

        Matches the word ordering used by the
        manufacturer's Position_Feedback().
        """

        registers = self.read_register(
            self.REG_POSITION,
            2,
        )

        high_word = registers[0]
        low_word = registers[1]

        # Manufacturer swaps the two 16-bit words.
        value = (low_word << 16) | high_word

        if value >= 0x80000000:
            value -= 0x100000000

        return value

    def set_position(self, position):
        """
        Command an absolute 32-bit position.

        RMCS-2303:
            Register 16 = LSB
            Register 18 = MSB

        The drive executes the position command
        when register 18 is written.
        """
        if position < 0:
            position &= 0xFFFFFFFF

        lsb = position & 0xFFFF
        msb = (position >> 16) & 0xFFFF

        self.write_register(16, lsb)
        self.write_register(18, msb)


    def position_enable(self):
        """Enable position control mode."""
        self.write_register(2, 0x0201)


    def position_disable(self):
        """Disable position control mode."""
        self.write_register(2, 0x0200)

    def set_home(self):
        return self.write_register(
            0,
            self.SET_HOME,
        )

    # ---------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------

    def close(self):
        if self.ser.is_open:
            self.ser.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Always leave motor disabled when the object closes.
        try:
            self.disable()
        except Exception:
            pass

        self.close()
