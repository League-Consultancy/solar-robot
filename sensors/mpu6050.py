# sensors/mpu6050.py

import smbus
import time


class MPU6050:

    # =========================================================
    # MPU6050 REGISTERS
    # =========================================================

    PWR_MGMT_1 = 0x6B

    SMPLRT_DIV = 0x19
    CONFIG = 0x1A

    GYRO_CONFIG = 0x1B
    ACCEL_CONFIG = 0x1C

    ACCEL_XOUT_H = 0x3B

    TEMP_OUT_H = 0x41

    GYRO_XOUT_H = 0x43

    WHO_AM_I = 0x75

    # =========================================================

    def __init__(
        self,
        bus_number=1,
        address=0x68
    ):

        self.address = address

        self.bus = smbus.SMBus(
            bus_number
        )

    # =========================================================
    # INITIALIZE
    # =========================================================

    def initialize(self):

        # Wake MPU6050
        self.bus.write_byte_data(
            self.address,
            self.PWR_MGMT_1,
            0x00
        )

        time.sleep(0.1)

        # Sample rate divider
        #
        # Gyroscope output rate:
        #
        # 8 kHz / (1 + SMPLRT_DIV)
        #
        # With 7:
        #
        # 1000 Hz
        #

        self.bus.write_byte_data(
            self.address,
            self.SMPLRT_DIV,
            7
        )

        # DLPF configuration
        #
        # 0x03 gives approximately
        # 44 Hz gyro / 42 Hz accelerometer bandwidth
        #

        self.bus.write_byte_data(
            self.address,
            self.CONFIG,
            0x03
        )

        # -----------------------------------------------------
        # Gyroscope
        #
        # ±250 °/s
        #
        # FS_SEL = 0
        # -----------------------------------------------------

        self.bus.write_byte_data(
            self.address,
            self.GYRO_CONFIG,
            0x00
        )

        # -----------------------------------------------------
        # Accelerometer
        #
        # ±2g
        #
        # AFS_SEL = 0
        # -----------------------------------------------------

        self.bus.write_byte_data(
            self.address,
            self.ACCEL_CONFIG,
            0x00
        )

    # =========================================================
    # WHO AM I
    # =========================================================

    def who_am_i(self):

        return self.bus.read_byte_data(
            self.address,
            self.WHO_AM_I
        )

    # =========================================================
    # READ 16-BIT SIGNED VALUE
    # =========================================================

    def _read_word_signed(
        self,
        high_register
    ):

        high = self.bus.read_byte_data(
            self.address,
            high_register
        )

        low = self.bus.read_byte_data(
            self.address,
            high_register + 1
        )

        value = (
            (high << 8) |
            low
        )

        # Convert unsigned 16-bit
        # to signed 16-bit

        if value >= 32768:

            value -= 65536

        return value

    # =========================================================
    # ACCELEROMETER
    # =========================================================

    def read_acceleration(self):

        raw_x = self._read_word_signed(
            self.ACCEL_XOUT_H
        )

        raw_y = self._read_word_signed(
            self.ACCEL_XOUT_H + 2
        )

        raw_z = self._read_word_signed(
            self.ACCEL_XOUT_H + 4
        )

        # ±2g → 16384 LSB/g

        ax = raw_x / 16384.0
        ay = raw_y / 16384.0
        az = raw_z / 16384.0

        return ax, ay, az

    # =========================================================
    # GYROSCOPE
    # =========================================================

    def read_gyroscope(self):

        raw_x = self._read_word_signed(
            self.GYRO_XOUT_H
        )

        raw_y = self._read_word_signed(
            self.GYRO_XOUT_H + 2
        )

        raw_z = self._read_word_signed(
            self.GYRO_XOUT_H + 4
        )

        # ±250 °/s → 131 LSB/(°/s)

        gx = raw_x / 131.0
        gy = raw_y / 131.0
        gz = raw_z / 131.0

        return gx, gy, gz

    # =========================================================
    # TEMPERATURE
    # =========================================================

    def read_temperature(self):

        raw_temp = self._read_word_signed(
            self.TEMP_OUT_H
        )

        # MPU6050 temperature formula

        temperature = (
            raw_temp / 340.0
        ) + 36.53

        return temperature

    # =========================================================
    # READ EVERYTHING
    # =========================================================

    def read_all(self):

        ax, ay, az = self.read_acceleration()

        gx, gy, gz = self.read_gyroscope()

        temperature = self.read_temperature()

        return {
            "accel": {
                "x": ax,
                "y": ay,
                "z": az
            },

            "gyro": {
                "x": gx,
                "y": gy,
                "z": gz
            },

            "temperature": temperature
        }

    # =========================================================
    # CLOSE
    # =========================================================

    def close(self):

        self.bus.close()