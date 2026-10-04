from gpiozero import OutputDevice
import time

class PumpRelay:

    def __init__(self, pin=17):
        self.pin = pin
        self.relay = OutputDevice(pin)

    def start(self):
        # Relay is already ON after initialization.
        # Keep this function for the robot API.
        pass

    def stop(self):
        # Releasing the GPIO turns the relay OFF.
        self.relay.close()

if __name__ == "__main__":
    pump = PumpRelay()

    try:
        pump.start()
        time.sleep(5)
        # Pump running...
        # ...

        pump.stop()
    finally:
        pump.stop()
