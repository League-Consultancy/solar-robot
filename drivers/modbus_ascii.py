# drivers/modbus_ascii.py

import serial
import threading


class ModbusASCII:
    """
    Modbus ASCII master.

    One instance = one physical UART connection.

    Example:
        uart = ModbusASCII("/dev/ttyAMA10", slave_id=1)
    """

    def __init__(
        self,
        port,
        slave_id,
        baudrate=9600,
        timeout=0.3
    ):
        self.port = port
        self.slave_id = slave_id

        self.serial = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout
        )

        self.lock = threading.Lock()

    # ---------------------------------------------------------
    # LRC
    # ---------------------------------------------------------

    @staticmethod
    def calculate_lrc(data):
        """
        Calculate Modbus ASCII LRC.

        data = bytes excluding ':' and LRC itself
        """

        total = sum(data) & 0xFF

        lrc = ((-total) & 0xFF)

        return lrc

    # ---------------------------------------------------------
    # Build frame
    # ---------------------------------------------------------

    def build_frame(self, function_code, data=b""):
        """
        Build Modbus ASCII frame.

        Format:

        :SLAVE FUNCTION DATA LRC CR LF
        """

        payload = bytes([
            self.slave_id,
            function_code
        ]) + data

        lrc = self.calculate_lrc(payload)

        message = payload + bytes([lrc])

        return b":" + message.hex().upper().encode() + b"\r\n"

    # ---------------------------------------------------------
    # Send / Receive
    # ---------------------------------------------------------

    def _transact(self, function_code, data=b""):
        """
        Send request and receive response.
        """

        frame = self.build_frame(function_code, data)

        with self.lock:

            self.serial.reset_input_buffer()

            self.serial.write(frame)
            self.serial.flush()

            response = self.serial.readline()

        if not response:
            raise TimeoutError(
                f"No response from slave {self.slave_id} "
                f"on {self.port}"
            )

        return self._parse_response(response, function_code)

    # ---------------------------------------------------------
    # Parse response
    # ---------------------------------------------------------

    def _parse_response(self, response, expected_function):
        """
        Validate Modbus ASCII response.

        Returns:
            payload without slave ID/function/LRC
        """

        response = response.strip()

        if not response.startswith(b":"):
            raise ValueError(
                f"Invalid Modbus ASCII response: {response!r}"
            )

        try:
            raw = bytes.fromhex(
                response[1:].decode()
            )
        except ValueError:
            raise ValueError(
                f"Invalid hexadecimal response: {response!r}"
            )

        if len(raw) < 4:
            raise ValueError(
                f"Response too short: {response!r}"
            )

        slave_id = raw[0]
        function_code = raw[1]

        # Check slave
        if slave_id != self.slave_id:
            raise ValueError(
                f"Wrong slave ID. "
                f"Expected {self.slave_id}, "
                f"received {slave_id}"
            )

        # Modbus exception
        if function_code & 0x80:

            exception_code = raw[2]

            raise RuntimeError(
                f"Modbus exception from slave "
                f"{self.slave_id}: "
                f"code 0x{exception_code:02X}"
            )

        if function_code != expected_function:
            raise ValueError(
                f"Wrong function code. "
                f"Expected 0x{expected_function:02X}, "
                f"received 0x{function_code:02X}"
            )

        # Check LRC
        received_lrc = raw[-1]

        calculated_lrc = self.calculate_lrc(
            raw[:-1]
        )

        if received_lrc != calculated_lrc:
            raise ValueError(
                f"LRC error. "
                f"Received 0x{received_lrc:02X}, "
                f"calculated 0x{calculated_lrc:02X}"
            )

        return raw[2:-1]

    # ---------------------------------------------------------
    # Write register - Function 06
    # ---------------------------------------------------------

    def write_register(self, register, value):
        """
        Write one 16-bit register.

        Modbus function:
            06 - Write Single Register
        """

        data = (
            register.to_bytes(2, "big") +
            value.to_bytes(2, "big")
        )

        response = self._transact(
            function_code=0x06,
            data=data
        )

        # Normal response should echo:
        #
        # REGISTER + VALUE
        #

        if len(response) != 4:
            raise ValueError(
                f"Invalid write response: {response.hex()}"
            )

        returned_register = int.from_bytes(
            response[0:2],
            "big"
        )

        returned_value = int.from_bytes(
            response[2:4],
            "big"
        )

        if returned_register != register:
            raise ValueError(
                "Write response register mismatch"
            )

        if returned_value != value:
            raise ValueError(
                "Write response value mismatch"
            )

        return True

    # ---------------------------------------------------------
    # Read registers - Function 03
    # ---------------------------------------------------------

    def read_registers(self, register, count=1):
        """
        Read holding registers.

        Modbus function:
            03 - Read Holding Registers
        """

        data = (
            register.to_bytes(2, "big") +
            count.to_bytes(2, "big")
        )

        response = self._transact(
            function_code=0x03,
            data=data
        )

        if len(response) < 1:
            raise ValueError(
                "Invalid read response"
            )

        byte_count = response[0]

        register_data = response[1:]

        if byte_count != len(register_data):
            raise ValueError(
                "Byte count mismatch"
            )

        if byte_count != count * 2:
            raise ValueError(
                "Unexpected register data length"
            )

        registers = []

        for i in range(count):

            start = i * 2

            value = int.from_bytes(
                register_data[start:start + 2],
                "big"
            )

            registers.append(value)

        return registers

    # ---------------------------------------------------------
    # Close
    # ---------------------------------------------------------

    def close(self):

        if self.serial.is_open:
            self.serial.close()

    # ---------------------------------------------------------

    def __enter__(self):
        return self

    # ---------------------------------------------------------

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()