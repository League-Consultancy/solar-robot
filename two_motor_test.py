import serial
import time
import threading


# ============================================================
# CONFIGURATION
# ============================================================

MOTOR1_PORT = "/dev/ttyAMA0"
MOTOR2_PORT = "/dev/ttyAMA4"

BAUD = 9600

MOTOR1_SLAVE = 7
MOTOR2_SLAVE = 7

SPEED = 320

RUN_TIME = 2.0
SETTLE_TIME = 1.0

CYCLES = 3


# ============================================================
# MODBUS ASCII
# ============================================================

def lrc(data):
    return (-sum(data)) & 0xFF


def make_frame(slave, function, address, value):
    payload = bytes([
        slave,
        function,
        (address >> 8) & 0xFF,
        address & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF,
    ])

    checksum = lrc(payload)

    return (
        ":"
        + payload.hex().upper()
        + f"{checksum:02X}"
        + "\r\n"
    ).encode("ascii")


# ============================================================
# MOTOR CLASS
# ============================================================

class Motor:

    def __init__(self, name, port, slave):
        self.name = name
        self.port = port
        self.slave = slave

        self.ser = serial.Serial(
            port,
            BAUD,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=1
        )

    # --------------------------------------------------------
    # Send command
    # --------------------------------------------------------

    def send(self, function, address, value):

        frame = make_frame(
            self.slave,
            function,
            address,
            value
        )

        self.ser.reset_input_buffer()

        self.ser.write(frame)
        self.ser.flush()

        response = self.ser.read_until(b"\n")

        return response

    # --------------------------------------------------------
    # Write register
    # --------------------------------------------------------

    def write(self, address, value):

        response = self.send(
            6,
            address,
            value
        )

        expected = make_frame(
            self.slave,
            6,
            address,
            value
        )

        return response == expected

    # --------------------------------------------------------
    # Read register
    # --------------------------------------------------------

    def read(self, address):

        response = self.send(
            3,
            address,
            1
        )

        text = response.decode(
            errors="replace"
        ).strip()

        if not text.startswith(":"):
            return None

        try:

            raw = bytes.fromhex(
                text[1:-2]
            )

            if len(raw) < 5:
                return None

            value = (
                (raw[3] << 8)
                |
                raw[4]
            )

            return value

        except Exception:
            return None

    # --------------------------------------------------------
    # Read signed 16 bit
    # --------------------------------------------------------

    def read_signed16(self, address):

        value = self.read(address)

        if value is None:
            return None

        if value >= 32768:
            value -= 65536

        return value

    # --------------------------------------------------------
    # Read 32-bit signed position
    # --------------------------------------------------------

    def position(self):

        lsb = self.read(20)
        msb = self.read(22)

        if lsb is None or msb is None:
            return None

        value = (
            (msb << 16)
            |
            lsb
        )

        # unsigned -> signed 32-bit

        if value >= 0x80000000:
            value -= 0x100000000

        return value

    # --------------------------------------------------------
    # Speed feedback
    # --------------------------------------------------------

    def speed_feedback(self):

        return self.read_signed16(24)

    # --------------------------------------------------------
    # Control register
    # --------------------------------------------------------

    def control(self):

        return self.read(2)

    # --------------------------------------------------------
    # Close
    # --------------------------------------------------------

    def close(self):

        self.ser.close()


# ============================================================
# DISPLAY MOTOR STATE
# ============================================================

def print_state(m1, m2, title):

    p1 = m1.position()
    s1 = m1.speed_feedback()
    c1 = m1.control()

    p2 = m2.position()
    s2 = m2.speed_feedback()
    c2 = m2.control()

    print()
    print(title)
    print("-" * 70)

    print(
        f"{'':12}"
        f"{'MOTOR 1':20}"
        f"{'MOTOR 2':20}"
    )

    print(
        f"{'Control':12}"
        f"{str(hex(c1)):20}"
        f"{str(hex(c2)):20}"
    )

    print(
        f"{'Position':12}"
        f"{str(p1):20}"
        f"{str(p2):20}"
    )

    print(
        f"{'Speed FB':12}"
        f"{str(s1):20}"
        f"{str(s2):20}"
    )

    print("-" * 70)

    return p1, s1, p2, s2


# ============================================================
# SET BOTH SPEEDS
# ============================================================

def set_both_speed(m1, m2, speed):

    print()
    print(f"Setting both motors to speed = {speed}")

    ok1 = m1.write(14, speed)
    ok2 = m2.write(14, speed)

    print(
        f"Motor 1 speed command: "
        f"{'OK' if ok1 else 'FAILED'}"
    )

    print(
        f"Motor 2 speed command: "
        f"{'OK' if ok2 else 'FAILED'}"
    )


# ============================================================
# START BOTH MOTORS
# ============================================================

def start_both(m1, m2, command):

    print()
    print(
        f"Starting BOTH motors "
        f"with 0x{command:04X}"
    )

    # Send as close together as possible
    results = {}

    def start_motor(motor, key):

        results[key] = motor.write(
            2,
            command
        )

    t1 = threading.Thread(
        target=start_motor,
        args=(m1, "m1")
    )

    t2 = threading.Thread(
        target=start_motor,
        args=(m2, "m2")
    )

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print(
        f"Motor 1 start: "
        f"{'OK' if results['m1'] else 'FAILED'}"
    )

    print(
        f"Motor 2 start: "
        f"{'OK' if results['m2'] else 'FAILED'}"
    )


# ============================================================
# STOP BOTH MOTORS
# ============================================================

def stop_both(m1, m2, command):

    print()
    print(
        f"Stopping BOTH motors "
        f"with 0x{command:04X}"
    )

    results = {}

    def stop_motor(motor, key):

        results[key] = motor.write(
            2,
            command
        )

    t1 = threading.Thread(
        target=stop_motor,
        args=(m1, "m1")
    )

    t2 = threading.Thread(
        target=stop_motor,
        args=(m2, "m2")
    )

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print(
        f"Motor 1 stop: "
        f"{'OK' if results['m1'] else 'FAILED'}"
    )

    print(
        f"Motor 2 stop: "
        f"{'OK' if results['m2'] else 'FAILED'}"
    )


# ============================================================
# TEST ONE DIRECTION
# ============================================================

def test_direction(
    m1,
    m2,
    name,
    start_command,
    stop_command
):

    print()
    print("=" * 70)
    print(f"{name} TEST")
    print("=" * 70)

    # --------------------------------------------------------
    # Position before
    # --------------------------------------------------------

    p1_before = m1.position()
    p2_before = m2.position()

    print()
    print("POSITION BEFORE")

    print(
        f"Motor 1: {p1_before}"
    )

    print(
        f"Motor 2: {p2_before}"
    )

    # --------------------------------------------------------
    # Start both
    # --------------------------------------------------------

    start_both(
        m1,
        m2,
        start_command
    )

    time.sleep(0.3)

    # --------------------------------------------------------
    # Verify control
    # --------------------------------------------------------

    c1 = m1.control()
    c2 = m2.control()

    print()
    print("CONTROL AFTER START")

    print(
        f"Motor 1: 0x{c1:04X}"
        if c1 is not None
        else "Motor 1: ERROR"
    )

    print(
        f"Motor 2: 0x{c2:04X}"
        if c2 is not None
        else "Motor 2: ERROR"
    )

    print()
    print("*** BOTH MOTORS SHOULD BE RUNNING ***")
    print("*** OBSERVE BOTH PHYSICAL SHAFTS ***")

    time.sleep(RUN_TIME)

    # --------------------------------------------------------
    # Feedback while running
    # --------------------------------------------------------

    p1_running = m1.position()
    s1_running = m1.speed_feedback()

    p2_running = m2.position()
    s2_running = m2.speed_feedback()

    print()
    print("FEEDBACK WHILE RUNNING")
    print("-" * 70)

    print(
        f"Motor 1:"
        f" position={p1_running},"
        f" speed={s1_running}"
    )

    print(
        f"Motor 2:"
        f" position={p2_running},"
        f" speed={s2_running}"
    )

    # --------------------------------------------------------
    # Stop
    # --------------------------------------------------------

    stop_both(
        m1,
        m2,
        stop_command
    )

    time.sleep(0.5)

    # --------------------------------------------------------
    # Position after
    # --------------------------------------------------------

    p1_after = m1.position()
    p2_after = m2.position()

    print()
    print("POSITION AFTER")

    print(
        f"Motor 1: {p1_after}"
    )

    print(
        f"Motor 2: {p2_after}"
    )

    # --------------------------------------------------------
    # Calculate movement
    # --------------------------------------------------------

    if (
        p1_before is not None
        and p1_after is not None
    ):

        d1 = p1_after - p1_before

    else:

        d1 = None

    if (
        p2_before is not None
        and p2_after is not None
    ):

        d2 = p2_after - p2_before

    else:

        d2 = None

    print()
    print("=" * 70)
    print(f"{name} RESULT")
    print("=" * 70)

    print(
        f"Motor 1 position change: "
        f"{d1}"
    )

    print(
        f"Motor 2 position change: "
        f"{d2}"
    )

    if d1 is not None:

        print(
            "Motor 1 encoder direction: "
            + (
                "POSITIVE"
                if d1 > 0
                else "NEGATIVE"
                if d1 < 0
                else "NONE"
            )
        )

    if d2 is not None:

        print(
            "Motor 2 encoder direction: "
            + (
                "POSITIVE"
                if d2 > 0
                else "NEGATIVE"
                if d2 < 0
                else "NONE"
            )
        )

    # --------------------------------------------------------
    # Compare motors
    # --------------------------------------------------------

    if d1 is not None and d2 is not None:

        print()

        if d1 * d2 > 0:

            print(
                "RESULT: BOTH ENCODERS MOVED "
                "IN THE SAME DIRECTION"
            )

        elif d1 * d2 < 0:

            print(
                "RESULT: ENCODERS MOVED "
                "IN OPPOSITE DIRECTIONS"
            )

        else:

            print(
                "RESULT: ONE OR BOTH MOTORS "
                "DID NOT MOVE"
            )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("RMCS-2303 TWO MOTOR TEST")
    print("=" * 70)

    print()
    print(f"Motor 1 UART: {MOTOR1_PORT}")
    print(f"Motor 2 UART: {MOTOR2_PORT}")
    print(f"Motor 1 ID  : {MOTOR1_SLAVE}")
    print(f"Motor 2 ID  : {MOTOR2_SLAVE}")
    print(f"Speed       : {SPEED}")
    print(f"LPR         : 2262")

    m1 = Motor(
        "Motor 1",
        MOTOR1_PORT,
        MOTOR1_SLAVE
    )

    m2 = Motor(
        "Motor 2",
        MOTOR2_PORT,
        MOTOR2_SLAVE
    )

    try:

        # ====================================================
        # INITIAL STATE
        # ====================================================

        print_state(
            m1,
            m2,
            "INITIAL STATE"
        )

        # ====================================================
        # SET SPEED
        # ====================================================

        set_both_speed(
            m1,
            m2,
            SPEED
        )

        time.sleep(0.5)

        # ====================================================
        # VERIFY SPEED
        # ====================================================

        speed1 = m1.read(14)
        speed2 = m2.read(14)

        print()
        print("SPEED COMMAND READBACK")

        print(
            f"Motor 1: {speed1}"
        )

        print(
            f"Motor 2: {speed2}"
        )

        # ====================================================
        # INITIAL DISABLE
        # ====================================================

        print()
        print("Forcing both motors to disabled state...")

        m1.write(
            2,
            0x0100
        )

        m2.write(
            2,
            0x0100
        )

        time.sleep(1)

        # ====================================================
        # TEST CYCLES
        # ====================================================

        for cycle in range(1, CYCLES + 1):

            print()
            print()
            print("#" * 70)
            print(
                f"# TEST CYCLE {cycle} / {CYCLES}"
            )
            print("#" * 70)

            # ------------------------------------------------
            # FORWARD / CW COMMAND
            # ------------------------------------------------

            test_direction(
                m1,
                m2,
                "FORWARD / CW COMMAND",
                start_command=0x0101,
                stop_command=0x0100
            )

            time.sleep(SETTLE_TIME)

            # ------------------------------------------------
            # REVERSE / CCW COMMAND
            # ------------------------------------------------

            test_direction(
                m1,
                m2,
                "REVERSE / CCW COMMAND",
                start_command=0x0109,
                stop_command=0x0108
            )

            time.sleep(SETTLE_TIME)

        # ====================================================
        # FINAL STATE
        # ====================================================

        print()
        print("=" * 70)
        print("FINAL STATE")
        print("=" * 70)

        print_state(
            m1,
            m2,
            "FINAL"
        )

        # ====================================================
        # FINAL STOP
        # ====================================================

        stop_both(
            m1,
            m2,
            0x0108
        )

        time.sleep(1)

        print()
        print("=" * 70)
        print("TWO MOTOR TEST COMPLETE")
        print("=" * 70)

    except KeyboardInterrupt:

        print()
        print("CTRL+C RECEIVED")
        print("STOPPING BOTH MOTORS")

        try:
            m1.write(2, 0x0108)
            m2.write(2, 0x0108)
        except Exception:
            pass

    finally:

        m1.close()
        m2.close()


if __name__ == "__main__":
    main()
