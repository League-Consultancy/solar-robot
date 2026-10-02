from drivers.modbus_ascii import ModbusASCII
from motors.rhino_motor import RhinoMotor


PORT = "/dev/ttyAMA2"
SLAVE_ID = 3


uart = ModbusASCII(
    port=PORT,
    slave_id=SLAVE_ID
)

motor = RhinoMotor(uart)

# Tell Python this is an RMCS-2304.
motor.configure_2304(
    acceleration=1
)


try:

    print("===================================")
    print(" RMCS-2304 BRUSH MOTOR TEST")
    print("===================================")

    input(
        "\nMake sure the brush is safely positioned.\n"
        "Press ENTER to start at 10%..."
    )

    motor.set_brush_speed(10)

    print("Brush running at 10%")

    input(
        "\nPress ENTER to increase to 20%..."
    )

    motor.set_brush_speed(20)

    print("Brush running at 20%")

    input(
        "\nPress ENTER to reverse at 10%..."
    )

    motor.set_brush_speed(-10)

    print("Brush running reverse at 10%")

    input(
        "\nPress ENTER to stop..."
    )

    motor.stop()

    print("Brush stopped.")

except KeyboardInterrupt:

    print("\nKeyboard interrupt!")

    motor.stop()

except Exception as e:

    print()
    print("ERROR:")
    print(type(e).__name__)
    print(e)

    try:
        motor.stop()
    except:
        pass

finally:

    uart.close()