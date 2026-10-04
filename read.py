import time
from drivers.rmcs2303 import RMCS2303

motor = RMCS2303("/dev/ttyAMA0", 7)

try:
    print("Current position:")
    current = motor.get_position()
    print(current)

    target = current + 500

    print(f"Target position: {target}")

    print("Enabling position mode...")
    motor.position_enable()

    time.sleep(0.5)

    print("Sending position...")
    motor.set_position(target)

    for i in range(10):
        pos = motor.get_position()
        speed = motor.get_speed_feedback()

        print(
            f"{i}: position={pos}, speed={speed}"
        )

        time.sleep(0.5)

finally:
    motor.position_disable()
    motor.close()
