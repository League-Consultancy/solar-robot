import time

from smbus2 import SMBus, i2c_msg
import adafruit_vl53l0x


class LinuxI2C:
    def __init__(self, bus_number):
        self.bus = SMBus(bus_number)
        self.locked = False

    def try_lock(self):
        if not self.locked:
            self.locked = True
            return True
        return False

    def unlock(self):
        self.locked = False

    def scan(self):
        devices = []

        for address in range(0x03, 0x78):
            try:
                msg = i2c_msg.write(address, [0])
                self.bus.i2c_rdwr(msg)
                devices.append(address)
            except OSError:
                pass

        return devices

    def writeto(
        self,
        address,
        buffer,
        *,
        start=0,
        end=None,
        stop=True
    ):
        if end is None:
            end = len(buffer)

        data = bytes(buffer[start:end])

        msg = i2c_msg.write(address, data)
        self.bus.i2c_rdwr(msg)

    def readfrom_into(
        self,
        address,
        buffer,
        *,
        start=0,
        end=None,
        stop=True
    ):
        if end is None:
            end = len(buffer)

        length = end - start

        msg = i2c_msg.read(address, length)
        self.bus.i2c_rdwr(msg)

        data = bytes(msg)

        for i, value in enumerate(data):
            buffer[start + i] = value

    def writeto_then_readfrom(
        self,
        address,
        out_buffer,
        in_buffer,
        *,
        out_start=0,
        out_end=None,
        in_start=0,
        in_end=None
    ):
        if out_end is None:
            out_end = len(out_buffer)

        if in_end is None:
            in_end = len(in_buffer)

        write_data = bytes(out_buffer[out_start:out_end])
        read_length = in_end - in_start

        write_msg = i2c_msg.write(
            address,
            write_data
        )

        read_msg = i2c_msg.read(
            address,
            read_length
        )

        self.bus.i2c_rdwr(
            write_msg,
            read_msg
        )

        data = bytes(read_msg)

        for i, value in enumerate(data):
            in_buffer[in_start + i] = value

    def deinit(self):
        self.bus.close()


class ToF:

    ADDRESS = 0x29
    BUS_NUMBER = 2

    def __init__(self):

        print(
            f"Opening VL53L0X on /dev/i2c-{self.BUS_NUMBER}"
        )

        self.i2c = LinuxI2C(
            self.BUS_NUMBER
        )

        devices = self.i2c.scan()

        print(
            "I2C devices:",
            [f"0x{x:02X}" for x in devices]
        )

        if self.ADDRESS not in devices:
            self.close()

            raise RuntimeError(
                "VL53L0X not found at 0x29"
            )

        print("Initializing VL53L0X...")

        self.sensor = adafruit_vl53l0x.VL53L0X(
            self.i2c,
            address=self.ADDRESS
        )

        print("VL53L0X initialized successfully")

    def read_distance(self):
        return self.sensor.range

    def close(self):
        if hasattr(self, "i2c"):
            self.i2c.deinit()