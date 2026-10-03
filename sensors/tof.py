from smbus2 import SMBus
import time


class ToF:
    ADDRESS = 0x29

    def __init__(self, bus_number=2):
        self.bus = SMBus(bus_number)

        print(f"Opening /dev/i2c-{bus_number}")

        # Read VL53L0X identification registers
        try:
            model_id = self.bus.read_byte_data(
                self.ADDRESS,
                0xC0
            )

            module_type = self.bus.read_byte_data(
                self.ADDRESS,
                0xC1
            )

            revision_id = self.bus.read_byte_data(
                self.ADDRESS,
                0xC2
            )

            print(f"Model ID:    0x{model_id:02X}")
            print(f"Module type: 0x{module_type:02X}")
            print(f"Revision ID: 0x{revision_id:02X}")

        except Exception as e:
            self.bus.close()
            raise RuntimeError(
                f"VL53L0X communication failed: {e}"
            )

    def close(self):
        self.bus.close()