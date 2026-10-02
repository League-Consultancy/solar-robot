from drivers.modbus_ascii import ModbusASCII
from motors.rhino_motor import RhinoMotor


PORT = "/dev/ttyAMA0"
SLAVE_ID = 1


uart = ModbusASCII(
    port=PORT,
    slave_id=SLAVE_ID
)

motor = RhinoMotor(uart)

# Tell our Python code that this is an RMCS-2303.
#
# We are NOT configuring encoder LPR yet.
motor.model = RhinoMotor.RMCS_2303


try:

    print("===================================")
    print(" RMCS-2303 WHEEL MOTOR TEST")
    print("===================================")

    print()
    print("1. Reading speed feedback...")

    speed = motor.get_speed_feedback()

    print(f"Current speed: {speed} RPM")

    print()
    print("2. Reading position...")

    position = motor.get_position()

    print(f"Position: {position}")

    print()
    print("Communication looks OK.")

    input(
        "\nMake sure the wheel is safely lifted "
        "off the ground.\n"
        "Press ENTER to start motor..."
    )

    # Very low test speed.
    #
    # IMPORTANT:
    # RMCS-2303 register 14 uses BASE MOTOR RPM,
    # not gearbox output RPM.
    #
    # Start extremely low.
    motor.set_speed(300)

    print()
    print("Motor running at 300 RPM command.")

    input(
        "\nPress ENTER to stop..."
    )

    motor.stop()

    print("Motor stopped.")

except KeyboardInterrupt:

    print("\nKeyboard interrupt!")

    motor.stop()

except Exception as e:

    print()
    print("ERROR:")
    print(type(e).__name__)
    print(e)

    # Try to stop the motor if something went wrong.
    try:
        motor.stop()
    except:
        pass

finally:

    uart.close()