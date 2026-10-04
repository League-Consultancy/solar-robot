import time
from drivers.rmcs2303 import RMCS2303

motor = RMCS2303("/dev/ttyAMA0", 7)

try:
    motor.set_speed(320)

    for i in range(5):
        print(f"\n========== TEST {i + 1} ==========")

        print("Sending CW...")
        motor.digital_cw()

        time.sleep(0.2)

        control = motor.get_control()
        speed_cmd = motor.get_speed_command()
        speed_fb = motor.get_speed_feedback()

        print(f"Control register : 0x{control:04X}")
        print(f"Speed command    : {speed_cmd}")
        print(f"Speed feedback   : {speed_fb}")

        time.sleep(2)

        print("Disabling...")
        motor.disable()

        time.sleep(3)

finally:
    motor.disable()
    motor.close()
