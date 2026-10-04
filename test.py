from gpiozero import DigitalOutputDevice
import time

RELAY_PIN = 17

# Active-low relay:
# HIGH = OFF
# LOW  = ON
relay = DigitalOutputDevice(
    RELAY_PIN,
    active_high=False,
    initial_value=False
)

print("Relay OFF")
time.sleep(1)

print("Relay ON")
relay.on()
time.sleep(1)

print("Relay OFF")
relay.off()
time.sleep(1)

relay.close()

print("Done")
