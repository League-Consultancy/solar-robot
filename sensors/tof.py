import time

import board
import busio
import adafruit_vl53l0x


class ToF:
    def __init__(self):
        # I2C0 on Raspberry Pi 5
        #
        # GPIO8  = SDA
        # GPIO9  = SCL
        #
        # board.D8 -> GPIO8
        # board.D9 -> GPIO9

        self.i2c = busio.I2C(
            board.D5,   # SCL
            board.D4    # SDA
        )

        # Wait for I2C bus to become available
        while not self.i2c.try_lock():
            time.sleep(0.01)

        try:
            devices = self.i2c.scan()
            print(
                "I2C devices:",
                [hex(device) for device in devices]
            )
        finally:
            self.i2c.unlock()

        self.sensor = adafruit_vl53l0x.VL53L0X(
            self.i2c,
            address=0x29
        )

        print("VL53L0X initialized")

    def read_distance(self):
        """
        Returns distance in millimeters.
        """
        return self.sensor.range

    def close(self):
        self.i2c.deinit()