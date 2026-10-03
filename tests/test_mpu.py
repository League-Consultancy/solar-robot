from sensors.mpu6050 import MPU6050
import time


mpu = MPU6050(bus_number=1)

try:
    while True:

        data = mpu.read_all()

        ax, ay, az = data["acceleration"]
        gx, gy, gz = data["gyroscope"]
        temp = data["temperature"]

        print(
            f"ACC: "
            f"X={ax:+.2f}g "
            f"Y={ay:+.2f}g "
            f"Z={az:+.2f}g | "

            f"GYRO: "
            f"X={gx:+.2f} "
            f"Y={gy:+.2f} "
            f"Z={gz:+.2f} °/s | "

            f"TEMP={temp:.2f}°C"
        )

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    mpu.close()