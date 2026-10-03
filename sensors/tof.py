import time

import board
import busio
import adafruit_vl53l0x


class ToF:
    def __init__(self):
        # IMPORTANT:
        # VL53L0X is connected to I2C0:
        # GPIO8  -> SDA
        # GPIO9  -> SCL
        #
        # On Raspberry Pi, bus 0 corresponds to /dev/i2c-0.

        self.i2c = busio.I2C(
            board.SCL2,
            board.SDA2
        )

        self.sensor = adafruit_vl53l0x.VL53L0X(
            self.i2c,
            address=0x29
        )

        print("VL53L0X initialized on I2C0")

    def read_distance(self):
        """
        Return distance in millimeters.
        """
        return self.sensor.range

    def close(self):
        self.i2c.deinit()