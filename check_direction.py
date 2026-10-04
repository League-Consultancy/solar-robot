import time

from drivers.rmcs2303 import RMCS2303


SPEED = 320


def test_motor(name, port):

    motor = RMCS2303(
        port,
        slave_id=7,
    )

    try:

        print(f"\n===== {name}: CW =====")

        motor.set_speed(SPEED)
        motor.digital_cw()

        time.sleep(1)

        motor.disable()

        time.sleep(0.5)

        print(f"{name}: CW stopped")

        print(f"\n===== {name}: CCW =====")

        motor.set_speed(SPEED)
        motor.digital_ccw()

        time.sleep(1)

        motor.disable()

        print(f"{name}: CCW stopped")

    finally:
        motor.disable()
        motor.close()


print("Motor direction test")
print()
print("Observe the physical wheel direction.")
print("Do NOT test on the ground yet.")


test_motor(
    "LEFT MOTOR",
    "/dev/ttyAMA0",
)

test_motor(
    "RIGHT MOTOR",
    "/dev/ttyAMA4",
)
