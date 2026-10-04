import serial
import time


# ============================================================
# CONFIGURATION
# ============================================================

MOTOR1_PORT = "/dev/ttyAMA0"
MOTOR2_PORT = "/dev/ttyAMA4"

BAUDRATE = 9600
SLAVE_ID = 7

SPEED = 320

DIRECTION_CHANGE_DELAY = 0.15


# ============================================================
# MODBUS ASCII
# ============================================================

def lrc(data):
    return (-sum(data)) & 0xFF


def make_frame(slave, register, value):

    data = bytes([
        slave,
        0x06,
        (register >> 8) & 0xFF,
        register & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF
    ])

    checksum = lrc(data)

    return (
        b":"
        + data.hex().upper().encode()
        + f"{checksum:02X}".encode()
        + b"\r\n"
    )


# ============================================================
# MOTOR
# ============================================================

class Motor:

    def __init__(self, port):

        self.port = port

        self.ser = serial.Serial(
            port=port,
            baudrate=BAUDRATE,
            bytesize=8,
            parity=serial.PARITY_NONE,
            stopbits=1,
            timeout=0.5
        )

        self.direction = None

        time.sleep(0.1)

    # --------------------------------------------------------
    # WRITE REGISTER
    # --------------------------------------------------------

    def write(self, register, value):

        frame = make_frame(
            SLAVE_ID,
            register,
            value
        )

        self.ser.write(frame)
        self.ser.flush()

        time.sleep(0.03)

        # Clear/read response
        self.ser.read_all()

    # --------------------------------------------------------
    # SPEED
    # --------------------------------------------------------

    def set_speed(self, speed):

        self.write(14, abs(int(speed)))

    # --------------------------------------------------------
    # RAW CW
    # --------------------------------------------------------

    def _cw(self):

        # 0101 = Digital mode + CW + Enable
        self.write(2, 0x0101)

        self.direction = "cw"

    # --------------------------------------------------------
    # RAW CCW
    # --------------------------------------------------------

    def _ccw(self):

        # 0109 = Digital mode + CCW + Enable
        self.write(2, 0x0109)

        self.direction = "ccw"

    # --------------------------------------------------------
    # STOP CURRENT DIRECTION
    # --------------------------------------------------------

    def stop(self):

        if self.direction == "cw":

            # 0100 = Disable CW
            self.write(2, 0x0100)

        elif self.direction == "ccw":

            # 0108 = Disable CCW
            self.write(2, 0x0108)

        self.direction = None

        time.sleep(DIRECTION_CHANGE_DELAY)

    # --------------------------------------------------------
    # SET CW
    # --------------------------------------------------------

    def cw(self):

        # If already CW, nothing to change
        if self.direction == "cw":
            return

        # If running CCW, disable CCW first
        if self.direction == "ccw":
            self.stop()

        self._cw()

    # --------------------------------------------------------
    # SET CCW
    # --------------------------------------------------------

    def ccw(self):

        # If already CCW, nothing to change
        if self.direction == "ccw":
            return

        # If running CW, disable CW first
        if self.direction == "cw":
            self.stop()

        self._ccw()

    # --------------------------------------------------------
    # CLOSE
    # --------------------------------------------------------

    def close(self):

        try:
            self.stop()
        except:
            pass

        self.ser.close()


# ============================================================
# SOLAR ROBOT
# ============================================================

class SolarRobot:

    def __init__(self):

        print("Connecting motors...")

        self.motor1 = Motor(MOTOR1_PORT)
        self.motor2 = Motor(MOTOR2_PORT)

        # Configure speed
        self.motor1.set_speed(SPEED)
        self.motor2.set_speed(SPEED)

        print("Robot ready.")
        print(f"Speed: {SPEED}")

    # ========================================================
    # FORWARD
    # ========================================================

    def forward(self):

        print("FORWARD")

        # Tested physical mapping:
        #
        # M1 = CW
        # M2 = CCW

        self.motor1.cw()
        self.motor2.ccw()

    # ========================================================
    # REVERSE
    # ========================================================

    def reverse(self):

        print("REVERSE")

        # M1 = CCW
        # M2 = CW

        self.motor1.ccw()
        self.motor2.cw()

    # ========================================================
    # LEFT
    # ========================================================

    def left(self):

        print("LEFT")

        # M1 = CCW
        # M2 = CCW

        self.motor1.ccw()
        self.motor2.ccw()

    # ========================================================
    # RIGHT
    # ========================================================

    def right(self):

        print("RIGHT")

        # M1 = CW
        # M2 = CW

        self.motor1.cw()
        self.motor2.cw()

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        print("STOP")

        self.motor1.stop()
        self.motor2.stop()

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        self.stop()

        self.motor1.close()
        self.motor2.close()


# ============================================================
# MAIN
# ============================================================

robot = None

try:

    robot = SolarRobot()

    print()
    print("================================")
    print(" SOLAR ROBOT CONTROL")
    print("================================")
    print()
    print("1 = Forward")
    print("2 = Reverse")
    print("3 = Left")
    print("4 = Right")
    print("5 = Stop")
    print("q = Quit")
    print()

    while True:

        command = input("Command: ").strip().lower()

        if command == "1":

            robot.forward()

        elif command == "2":

            robot.reverse()

        elif command == "3":

            robot.left()

        elif command == "4":

            robot.right()

        elif command == "5":

            robot.stop()

        elif command == "q":

            break

        else:

            print("Invalid command")


except KeyboardInterrupt:

    print("\nInterrupted")


finally:

    if robot is not None:

        try:
            robot.close()
        except:
            pass

    print("Robot stopped.")
