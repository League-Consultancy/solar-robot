from drivers.rmcs2303 import RMCS2303


motor1 = RMCS2303(
    "/dev/ttyAMA0",
    slave_id=7,
)

motor2 = RMCS2303(
    "/dev/ttyAMA4",
    slave_id=7,
)

try:

    print("========== MOTOR 1 ==========")

    print("ID:          ", motor1.get_id())
    print("Control:     ", hex(motor1.get_control()))
    print("Mode:        ", hex(motor1.get_mode()))
    print("LPR:         ", motor1.get_lpr())
    print("Acceleration:", motor1.get_acceleration())
    print("Speed:       ", motor1.get_speed_command())
    print("Position:    ", motor1.get_position())


    print("\n========== MOTOR 2 ==========")

    print("ID:          ", motor2.get_id())
    print("Control:     ", hex(motor2.get_control()))
    print("Mode:        ", hex(motor2.get_mode()))
    print("LPR:         ", motor2.get_lpr())
    print("Acceleration:", motor2.get_acceleration())
    print("Speed:       ", motor2.get_speed_command())
    print("Position:    ", motor2.get_position())


finally:

    motor1.disable()
    motor2.disable()

    motor1.close()
    motor2.close()
