import time
from drivers.rmcs2303 import RMCS2303

motor = RMCS2303("/dev/ttyAMA0", 7)

try:
    motor.set_speed(1000)

    for i in range(10):
        print(f"\n========== CYCLE {i + 1}/10 ==========")

        print("CW -> RUN")
        motor.digital_cw()
        time.sleep(3)

        fb = motor.get_speed_feedback()
        pos = motor.get_position()

        print(f"Before disable: feedback={fb}, position={pos}")

        print("DISABLE CW")
        motor.disable_cw()
        time.sleep(3)

        fb = motor.get_speed_feedback()
        pos = motor.get_position()

        print(f"After disable:  feedback={fb}, position={pos}")

finally:
    motor.disable_cw()
    motor.close()
