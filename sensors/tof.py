import time
from smbus2 import SMBus


class ToF:
    ADDRESS = 0x29

    # Registers
    SYSRANGE_START = 0x00
    SYSTEM_SEQUENCE_CONFIG = 0x01
    SYSTEM_INTERRUPT_CLEAR = 0x0B

    RESULT_INTERRUPT_STATUS = 0x13
    RESULT_RANGE_STATUS = 0x14

    SYSTEM_INTERMEASUREMENT_PERIOD = 0x04

    GPIO_HV_MUX_ACTIVE_HIGH = 0x84
    MSRC_CONFIG_CONTROL = 0x60

    PRE_RANGE_CONFIG_VCSEL_PERIOD = 0x50
    FINAL_RANGE_CONFIG_VCSEL_PERIOD = 0x70

    IDENTIFICATION_MODEL_ID = 0xC0

    def __init__(self, bus_number=2):

        self.bus_number = bus_number
        self.bus = SMBus(bus_number)

        print(f"Opening VL53L0X on /dev/i2c-{bus_number}")

        # Verify device
        try:
            self.bus.write_quick(self.ADDRESS)
        except Exception as e:
            self.bus.close()
            raise RuntimeError(
                f"VL53L0X not responding at 0x29: {e}"
            )

        print("VL53L0X detected at 0x29")

        self._initialize()

        print("VL53L0X initialized successfully")

    # ---------------------------------------------------------
    # Basic I2C register functions
    # ---------------------------------------------------------

    def _write8(self, register, value):
        self.bus.write_byte_data(
            self.ADDRESS,
            register,
            value
        )

    def _read8(self, register):
        return self.bus.read_byte_data(
            self.ADDRESS,
            register
        )

    def _write16(self, register, value):
        self.bus.write_word_data(
            self.ADDRESS,
            register,
            value
        )

    def _read16(self, register):
        return self.bus.read_word_data(
            self.ADDRESS,
            register
        )

    def _write_multi(self, register, data):
        self.bus.write_i2c_block_data(
            self.ADDRESS,
            register,
            list(data)
        )

    # ---------------------------------------------------------
    # VL53L0X initialization
    # Based on the standard ST/Pololu initialization sequence.
    # ---------------------------------------------------------

    def _initialize(self):

        # Stop any previous measurement
        self._write8(self.SYSRANGE_START, 0x00)

        # Recommended initialization sequence
        init_data = [
            (0x88, 0x00),
            (0x80, 0x01),
            (0xFF, 0x01),
            (0x00, 0x00),

            (0x91, 0x3C),

            (0x00, 0x01),
            (0xFF, 0x00),
            (0x80, 0x00),

            (0x60, 0x01),
            (0x60, 0x00),

            (0x01, 0xFF),
        ]

        for register, value in init_data:
            self._write8(register, value)

        # Read SPAD information
        self._write8(0x80, 0x01)
        self._write8(0xFF, 0x01)
        self._write8(0x00, 0x00)
        self._write8(0xFF, 0x06)

        tmp = self._read8(0x83)

        self._write8(0x83, tmp | 0x04)

        # Wait for SPAD information
        start = time.monotonic()

        while self._read8(0x83) == 0x00:

            if time.monotonic() - start > 1.0:
                raise RuntimeError(
                    "Timeout waiting for VL53L0X SPAD information"
                )

            time.sleep(0.001)

        tmp = self._read8(0x92)

        count = tmp & 0x7F
        is_aperture = bool(tmp & 0x80)

        # Turn off SPAD access
        self._write8(0x81, 0x00)
        self._write8(0xFF, 0x06)

        tmp = self._read8(0x83)

        self._write8(0x83, tmp & ~0x04)

        self._write8(0xFF, 0x01)
        self._write8(0x00, 0x01)
        self._write8(0xFF, 0x00)
        self._write8(0x80, 0x00)

        # Standard tuning settings
        tuning = [
            (0x09, 0x00),
            (0x10, 0x00),
            (0x11, 0x00),
            (0x24, 0x01),
            (0x25, 0xFF),
            (0x75, 0x00),
            (0xFF, 0x01),
            (0x4E, 0x2C),
            (0x48, 0x00),
            (0x30, 0x20),
            (0xFF, 0x00),
            (0x30, 0x09),
            (0x54, 0x00),
            (0x31, 0x04),
            (0x32, 0x03),
            (0x40, 0x83),
            (0x46, 0x25),
            (0x60, 0x00),
            (0x27, 0x00),
            (0x50, 0x06),
            (0x51, 0x00),
            (0x52, 0x96),
            (0x56, 0x08),
            (0x57, 0x30),
            (0x61, 0x00),
            (0x62, 0x00),
            (0x64, 0x00),
            (0x65, 0x00),
            (0x66, 0xA0),
            (0xFF, 0x01),
            (0x22, 0x32),
            (0x47, 0x14),
            (0x49, 0xFF),
            (0x4A, 0x00),
            (0xFF, 0x00),
            (0x7A, 0x0A),
            (0x7B, 0x00),
            (0x78, 0x21),
            (0xFF, 0x01),
            (0x23, 0x34),
            (0x42, 0x00),
            (0x44, 0xFF),
            (0x45, 0x26),
            (0x46, 0x05),
            (0x40, 0x40),
            (0x0E, 0x06),
            (0x20, 0x1A),
            (0x43, 0x40),
            (0xFF, 0x00),
            (0x34, 0x03),
            (0x35, 0x44),
            (0xFF, 0x01),
            (0x31, 0x04),
            (0x4B, 0x09),
            (0x4C, 0x05),
            (0x4D, 0x04),
            (0xFF, 0x00),
            (0x44, 0x00),
            (0x45, 0x20),
            (0x47, 0x08),
            (0x48, 0x28),
            (0x67, 0x00),
            (0x70, 0x04),
            (0x71, 0x01),
            (0x72, 0xFE),
            (0x76, 0x00),
            (0x77, 0x00),
            (0xFF, 0x01),
            (0x0D, 0x01),
            (0xFF, 0x00),
            (0x80, 0x01),
            (0x01, 0xF8),
            (0xFF, 0x01),
            (0x8E, 0x01),
            (0x00, 0x01),
            (0xFF, 0x00),
            (0x80, 0x00),
        ]

        for register, value in tuning:
            self._write8(register, value)

        # Interrupt configuration
        self._write8(0x0A, 0x04)

        tmp = self._read8(0x84)

        self._write8(0x84, tmp & ~0x10)

        self._write8(
            self.SYSTEM_INTERRUPT_CLEAR,
            0x01
        )

        # Sequence configuration
        self._write8(
            self.SYSTEM_SEQUENCE_CONFIG,
            0xE8
        )

        # Perform VHV calibration
        self._perform_single_ref_calibration(0x40)

        # Perform phase calibration
        self._write8(
            self.SYSTEM_SEQUENCE_CONFIG,
            0x02
        )

        self._perform_single_ref_calibration(0x00)

        # Normal ranging configuration
        self._write8(
            self.SYSTEM_SEQUENCE_CONFIG,
            0xE8
        )

        self._write8(
            self.SYSTEM_INTERRUPT_CLEAR,
            0x01
        )

    # ---------------------------------------------------------
    # Calibration
    # ---------------------------------------------------------

    def _perform_single_ref_calibration(self, value):

        self._write8(
            self.SYSRANGE_START,
            0x01 | value
        )

        start = time.monotonic()

        while True:

            status = self._read8(
                self.RESULT_INTERRUPT_STATUS
            )

            if status & 0x07:
                break

            if time.monotonic() - start > 2.0:
                raise RuntimeError(
                    "VL53L0X calibration timeout"
                )

            time.sleep(0.001)

        self._write8(
            self.SYSTEM_INTERRUPT_CLEAR,
            0x01
        )

        self._write8(
            self.SYSRANGE_START,
            0x00
        )

    # ---------------------------------------------------------
    # Distance measurement
    # ---------------------------------------------------------

    def read_distance(self):

        # Start single measurement
        self._write8(
            self.SYSRANGE_START,
            0x01
        )

        start = time.monotonic()

        while True:

            status = self._read8(
                self.RESULT_INTERRUPT_STATUS
            )

            if status & 0x07:
                break

            if time.monotonic() - start > 1.0:
                raise RuntimeError(
                    "VL53L0X measurement timeout"
                )

            time.sleep(0.001)

        # Range result is MSB/LSB at 0x1E/0x1F
        high = self._read8(0x1E)
        low = self._read8(0x1F)

        distance = (high << 8) | low

        # Clear interrupt
        self._write8(
            self.SYSTEM_INTERRUPT_CLEAR,
            0x01
        )

        self._write8(
            self.SYSRANGE_START,
            0x00
        )

        return distance

    def close(self):
        self.bus.close()