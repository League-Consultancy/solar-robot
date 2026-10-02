# tests/test_mpu6050.py

import time

from sensors.mpu6050 import MPU6050


mpu = MPU6050(
    bus_number=1,
    address=0x68
)


try:

    print("====================================")
    print("       MPU6050 TEST")
    print("====================================")

    # ---------------------------------------------------------
    # WHO AM I
    # ---------------------------------------------------------

    who_am_i = mpu.who_am_i()

    print()
    print(
        f"WHO_AM_I = 0x{who_am_i:02X}"
    )

    if who_am_i == 0x68:

        print("MPU6050 detected successfully.")

    else:

        print(
            "WARNING: Unexpected WHO_AM_I value."
        )

    # ---------------------------------------------------------
    # INITIALIZE
    # ---------------------------------------------------------

    print()
    print("Initializing MPU6050...")

    mpu.initialize()

    print("MPU6050 initialized.")

    # ---------------------------------------------------------
    # CONTINUOUS DATA
    # ---------------------------------------------------------

    print()
    print("Reading sensor data...")
    print("Press Ctrl+C to stop.")
    print()

    while True:

        data = mpu.read_all()

        accel = data["accel"]
        gyro = data["gyro"]

        temperature = data["temperature"]

        print(
            f"ACCEL  "
            f"X={accel['x']:7.3f} g  "
            f"Y={accel['y']:7.3f} g  "
            f"Z={accel['z']:7.3f} g"
        )

        print(
            f"GYRO   "
            f"X={gyro['x']:7.2f} °/s  "
            f"Y={gyro['y']:7.2f} °/s  "
            f"Z={gyro['z']:7.2f} °/s"
        )

        print(
            f"TEMP   "
            f"{temperature:6.2f} °C"
        )

        print("------------------------------------")

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

    mpu.close()