from sensors.tof import ToF
import time


tof = ToF(bus_number=2)

try:
    while True:
        distance = tof.read_distance()

        print(f"Distance: {distance} mm")

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    tof.close()