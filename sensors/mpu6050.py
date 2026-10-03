from smbus2 import SMBus
import time


class MPU6050:
    ADDRESS = 0x68

    PWR_MGMT_1 = 0x6B
    SMPLRT_DIV = 0x19
    CONFIG = 0x1A
    GYRO_CONFIG = 0x1B
    ACCEL_CONFIG = 0x1C
    WHO_AM_I = 0x75

    ACCEL_XOUT_H = 0x3B

    def __init__(self, bus_number=1, address=0x68):
        self.bus = SMBus(bus_number)
        self.address = address

        # Check sensor
        who_am_i = self.bus.read_byte_data(
            self.address,
            self.WHO_AM_I
        )

        print(f"MPU6050 WHO_AM_I: 0x{who_am_i:02X}")

        if who_am_i != 0x68:
            raise RuntimeError(
                f"Unexpected MPU6050 ID: 0x{who_am_i:02X}"
            )

        # Wake up MPU6050
        self.bus.write_byte_data(
            self.address,
            self.PWR_MGMT_1,
            0x00
        )

        time.sleep(0.1)

        # Sample rate
        self.bus.write_byte_data(
            self.address,
            self.SMPLRT_DIV,
            7
        )

        # Digital low-pass filter
        self.bus.write_byte_data(
            self.address,
            self.CONFIG,
            0x03
        )

        # Gyroscope ±250 °/s
        self.bus.write_byte_data(
            self.address,
            self.GYRO_CONFIG,
            0x00
        )

        # Accelerometer ±2g
        self.bus.write_byte_data(
            self.address,
            self.ACCEL_CONFIG,
            0x00
        )

        print("MPU6050 initialized")

    def read_raw_data(self, register):
        high = self.bus.read_byte_data(
            self.address,
            register
        )

        low = self.bus.read_byte_data(
            self.address,
            register + 1
        )

        value = (high << 8) | low

        if value >= 32768:
            value -= 65536

        return value

    def read_acceleration(self):
        ax = self.read_raw_data(0x3B)
        ay = self.read_raw_data(0x3D)
        az = self.read_raw_data(0x3F)

        return (
            ax / 16384.0,
            ay / 16384.0,
            az / 16384.0
        )

    def read_gyroscope(self):
        gx = self.read_raw_data(0x43)
        gy = self.read_raw_data(0x45)
        gz = self.read_raw_data(0x47)

        return (
            gx / 131.0,
            gy / 131.0,
            gz / 131.0
        )

    def read_temperature(self):
        raw = self.read_raw_data(0x41)

        return (raw / 340.0) + 36.53

    def read_all(self):
        accel = self.read_acceleration()
        gyro = self.read_gyroscope()
        temp = self.read_temperature()

        return {
            "acceleration": accel,
            "gyroscope": gyro,
            "temperature": temp
        }

    def close(self):
        self.bus.close()