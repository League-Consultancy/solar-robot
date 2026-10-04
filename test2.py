import time
from gpiozero import OutputDevice

# Define the GPIO pin (BCM numbering)
RELAY_PIN = 17 

print("Initializing GPIO pin...")
# Initialize the relay object
relay = OutputDevice(RELAY_PIN, active_high=True, initial_value=False)
print("Initialization successful!")

try:
    print("Starting loop. Press Ctrl+C to exit safely.")
    while True:
        print("Relay ON (COM connected to NO)")
        relay.on()
        time.sleep(2)

        print("Relay OFF (COM connected to NC)")
        relay.off()
        time.sleep(2)

except KeyboardInterrupt:
    print("\nStopping script...")

finally:
    # This block guarantees execution even if the script crashes or stops
    print("Turning relay off and releasing GPIO pin hardware...")
    relay.off()
    relay.close()  # Properly frees the pin so it doesn't get stuck state
    print("Cleanup complete.")
