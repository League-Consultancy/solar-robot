from drivers.modbus_ascii import ModbusASCII
from motors.rhino_motor import RhinoMotor


PORT = "/dev/ttyAMA0"
SLAVE_ID = 1


uart = ModbusASCII(
    port=PORT,
    slave_id=SLAVE_ID
)

motor = RhinoMotor(uart)

motor.model = RhinoMotor.RMCS_2303


try:

    print()
    print("======================================")
    print("     INTERACTIVE WHEEL MOTOR TEST")
    print("======================================")
    print()
    print("Commands:")
    print()
    print("  f <rpm>   Forward")
    print("  r <rpm>   Reverse")
    print("  s         Stop")
    print("  v         Speed feedback")
    print("  p         Position")
    print("  h         Set home")
    print("  q         Quit")
    print()

    while True:

        command = input("> ").strip()

        if not command:
            continue

        # -----------------------------------------
        # FORWARD
        # -----------------------------------------

        if command.startswith("f "):

            rpm = int(
                command.split()[1]
            )

            motor.set_speed(
                abs(rpm)
            )

            print(
                f"Forward command: {abs(rpm)} RPM"
            )

        # -----------------------------------------
        # REVERSE
        # -----------------------------------------

        elif command.startswith("r "):

            rpm = int(
                command.split()[1]
            )

            motor.set_speed(
                -abs(rpm)
            )

            print(
                f"Reverse command: {abs(rpm)} RPM"
            )

        # -----------------------------------------
        # STOP
        # -----------------------------------------

        elif command == "s":

            motor.stop()

            print("Motor stopped.")

        # -----------------------------------------
        # SPEED FEEDBACK
        # -----------------------------------------

        elif command == "v":

            speed = motor.get_speed_feedback()

            print(
                f"Speed feedback: {speed} RPM"
            )

        # -----------------------------------------
        # POSITION
        # -----------------------------------------

        elif command == "p":

            position = motor.get_position()

            print(
                f"Position: {position}"
            )

        # -----------------------------------------
        # HOME
        # -----------------------------------------

        elif command == "h":

            motor.set_home()

            print("Home position set.")

        # -----------------------------------------
        # QUIT
        # -----------------------------------------

        elif command == "q":

            motor.stop()

            print("Motor stopped.")
            print("Exiting.")

            break

        else:

            print("Unknown command.")

except KeyboardInterrupt:

    print("\nStopping motor...")

    try:
        motor.stop()
    except:
        pass

finally:

    uart.close()