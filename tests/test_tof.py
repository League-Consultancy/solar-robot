# tests/test_vl53l0x.py

import time

from sensors.tof import VL53L0X


sensor = VL53L0X()


try:

    print("====================================")
    print("          VL53L0X TEST")
    print("====================================")

    # ---------------------------------------------------------
    # Use 33 ms timing budget
    # ---------------------------------------------------------

    sensor.set_timing_budget(33000)

    print()
    print("VL53L0X initialized.")
    print("Timing budget: 33 ms")

    print()
    print("Starting distance measurements...")
    print("Press Ctrl+C to stop.")
    print()

    while True:

        distance_mm = sensor.read_distance_mm()

        distance_cm = distance_mm / 10.0

        print(
            f"Distance: "
            f"{distance_mm:4d} mm   "
            f"{distance_cm:6.1f} cm"
        )

        time.sleep(0.1)


except KeyboardInterrupt:

    print()
    print("Stopping...")


except Exception as e:

    print()
    print("ERROR:")
    print(type(e).__name__)
    print(e)


finally:

    sensor.close()