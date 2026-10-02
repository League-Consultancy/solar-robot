# sensors/vl53l0x.py

import board
import busio
import adafruit_vl53l0x


class VL53L0X:

    DEFAULT_ADDRESS = 0x29

    def __init__(
        self,
        address=DEFAULT_ADDRESS
    ):

        # Raspberry Pi hardware I2C
        self.i2c = busio.I2C(
            board.SCL,
            board.SDA
        )

        # Create sensor
        self.sensor = adafruit_vl53l0x.VL53L0X(
            self.i2c,
            address=address
        )

    # =========================================================
    # DISTANCE
    # =========================================================

    def read_distance_mm(self):

        return self.sensor.range

    # =========================================================

    def read_distance_cm(self):

        return self.sensor.range / 10.0

    # =========================================================

    def read_distance_m(self):

        return self.sensor.range / 1000.0

    # =========================================================
    # TIMING
    # =========================================================

    def set_timing_budget(self, microseconds):

        self.sensor.measurement_timing_budget = microseconds

    # =========================================================
    # CLOSE
    # =========================================================

    def close(self):

        # Release I2C bus
        self.i2c.deinit()