import time
from drivers.rmcs2303 import RMCS2303

motor = RMCS2303("/dev/ttyAMA0", 7)

try:
    motor.set_speed(320)

    for i in range(5):
        print(f"\n=== CW TEST {i + 1} ===")

        print("CW ON")
        motor.digital_cw()
        time.sleep(2)

        print("DISABLE")
        motor.disable()
        time.sleep(3)

finally:
    motor.disable()
    motor.close()
