import serial
import time
import threading


# ============================================================
# CONFIG
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


def make_frame(register, value):

    data = bytes([
        SLAVE_ID,
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
            timeout=0.1,
            write_timeout=0.1
        )

        self.direction = None

    # --------------------------------------------------------
    # SEND RAW FRAME
    # --------------------------------------------------------

    def send(self, frame):

        self.ser.write(frame)
        self.ser.flush()

    # --------------------------------------------------------
    # SET SPEED
    # --------------------------------------------------------

    def set_speed(self, speed):

        frame = make_frame(14, abs(int(speed)))
        self.send(frame)

    # --------------------------------------------------------
    # COMMAND FRAMES
    # --------------------------------------------------------

    def cw_frame(self):

        return make_frame(2, 0x0101)

    def ccw_frame(self):

        return make_frame(2, 0x0109)

    def stop_frame(self):

        if self.direction == "cw":

            return make_frame(2, 0x0100)

        elif self.direction == "ccw":

            return make_frame(2, 0x0108)

        return None


# ============================================================
# SEND TO TWO MOTORS AT THE SAME TIME
# ============================================================

def send_simultaneous(motor1, frame1, motor2, frame2):

    """
    Send commands to both UARTs concurrently.
    """

    thread1 = threading.Thread(
        target=motor1.send,
        args=(frame1,)
    )

    thread2 = threading.Thread(
        target=motor2.send,
        args=(frame2,)
    )

    # Start both threads as close together as possible
    thread1.start()
    thread2.start()

    # Wait until both transmissions finish
    thread1.join()
    thread2.join()


# ============================================================
# SOLAR ROBOT
# ============================================================

class SolarRobot:

    def __init__(self):

        print("Connecting motors...")

        self.motor1 = Motor(MOTOR1_PORT)
        self.motor2 = Motor(MOTOR2_PORT)

        # Set speed
        self.motor1.set_speed(SPEED)
        self.motor2.set_speed(SPEED)

        print("Robot ready.")

    # ========================================================
    # FORWARD
    # ========================================================

    def forward(self):

        print("FORWARD")

        frame1 = self.motor1.cw_frame()
        frame2 = self.motor2.ccw_frame()

        send_simultaneous(
            self.motor1,
            frame1,
            self.motor2,
            frame2
        )

        self.motor1.direction = "cw"
        self.motor2.direction = "ccw"

    # ========================================================
    # REVERSE
    # ========================================================

    def reverse(self):

        print("REVERSE")

        # First stop both motors simultaneously
        self.stop()

        # Allow drive to settle
        time.sleep(DIRECTION_CHANGE_DELAY)

        frame1 = self.motor1.ccw_frame()
        frame2 = self.motor2.cw_frame()

        send_simultaneous(
            self.motor1,
            frame1,
            self.motor2,
            frame2
        )

        self.motor1.direction = "ccw"
        self.motor2.direction = "cw"

    # ========================================================
    # LEFT
    # ========================================================

    def left(self):

        print("LEFT")

        self.stop()

        time.sleep(DIRECTION_CHANGE_DELAY)

        frame1 = self.motor1.cw_frame()
        frame2 = self.motor2.cw_frame()

        send_simultaneous(
            self.motor1,
            frame1,
            self.motor2,
            frame2
        )

        self.motor1.direction = "cw"
        self.motor2.direction = "cw"

    # ========================================================
    # RIGHT
    # ========================================================

    def right(self):

        print("RIGHT")

        self.stop()

        time.sleep(DIRECTION_CHANGE_DELAY)

        frame1 = self.motor1.ccw_frame()
        frame2 = self.motor2.ccw_frame()

        send_simultaneous(
            self.motor1,
            frame1,
            self.motor2,
            frame2
        )

        self.motor1.direction = "ccw"
        self.motor2.direction = "ccw"

    # ========================================================
    # STOP BOTH SIMULTANEOUSLY
    # ========================================================

    def stop(self):

        frame1 = self.motor1.stop_frame()
        frame2 = self.motor2.stop_frame()

        if frame1 is None and frame2 is None:
            return

        # If one motor has no direction, send only to the other
        if frame1 is None:

            self.motor2.send(frame2)

        elif frame2 is None:

            self.motor1.send(frame1)

        else:

            send_simultaneous(
                self.motor1,
                frame1,
                self.motor2,
                frame2
            )

        self.motor1.direction = None
        self.motor2.direction = None

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        self.stop()

        self.motor1.ser.close()
        self.motor2.ser.close()


# ============================================================
# MAIN
# ============================================================

robot = None

try:

    robot = SolarRobot()

    print()
    print("==============================")
    print(" SOLAR ROBOT")
    print("==============================")
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
