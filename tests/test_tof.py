from sensors.tof import ToF
import time


tof = ToF()

try:

    while True:

        distance = tof.read_distance()

        print(
            f"Distance: {distance:4d} mm"
        )

        time.sleep(0.2)

except KeyboardInterrupt:

    print("\nStopping...")

finally:

    tof.close()