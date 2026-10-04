import serial
import time


# ============================================================
# CONFIGURATION
# ============================================================

PORT = "/dev/ttyAMA0"
BAUD = 9600
SLAVE = 7

SPEED = 320

RUN_TIME = 1.5
STOP_TIME = 1.0

TEST_CYCLES = 3


# ============================================================
# MODBUS ASCII
# ============================================================

def lrc(data):
    return (-sum(data)) & 0xFF


def make_frame(slave, function, address, value=0):
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


def send_frame(ser, frame):
    ser.reset_input_buffer()

    ser.write(frame)
    ser.flush()

    response = ser.read_until(b"\n")

    return response


# ============================================================
# WRITE SINGLE REGISTER
# ============================================================

def write_register(ser, address, value, label=""):
    frame = make_frame(SLAVE, 6, address, value)

    print(f"\nWRITE {label}")
    print(f"  Address : {address}")
    print(f"  Value   : 0x{value:04X} ({value})")
    print(f"  TX      : {frame.decode().strip()}")

    response = send_frame(ser, frame)

    print(f"  RX      : {response.decode(errors='replace').strip()}")

    return response


# ============================================================
# READ SINGLE REGISTER
# ============================================================

def read_register(ser, address, label=""):
    frame = make_frame(SLAVE, 3, address, 1)

    response = send_frame(ser, frame)

    text = response.decode(errors="replace").strip()

    if not text.startswith(":"):
        print(f"READ {label}: INVALID RESPONSE")
        print("  RX:", repr(response))
        return None

    try:
        raw = bytes.fromhex(text[1:-2])

        # Expected:
        # slave
        # function
        # byte count
        # data high
        # data low

        if len(raw) < 5:
            print(f"READ {label}: SHORT RESPONSE")
            return None

        value = (raw[3] << 8) | raw[4]

        return value

    except Exception as e:
        print(f"READ {label}: PARSE ERROR:", e)
        print("  RX:", repr(response))
        return None


# ============================================================
# READ CONTROL
# ============================================================

def read_control(ser):
    return read_register(
        ser,
        2,
        "CONTROL"
    )


# ============================================================
# READ POSITION
#
# Register 20 = LSB
# Register 22 = MSB
#
# Together = signed 32-bit position
# ============================================================

def read_position(ser):

    lsb = read_register(
        ser,
        20,
        "POSITION LSB"
    )

    msb = read_register(
        ser,
        22,
        "POSITION MSB"
    )

    if lsb is None or msb is None:
        return None

    value = (msb << 16) | lsb

    # Convert unsigned 32-bit to signed 32-bit
    if value >= 0x80000000:
        value -= 0x100000000

    return value


# ============================================================
# READ SPEED FEEDBACK
#
# Register 24
# ============================================================

def read_speed_feedback(ser):

    value = read_register(
        ser,
        24,
        "SPEED FEEDBACK"
    )

    if value is None:
        return None

    # Convert uint16 -> int16
    if value >= 32768:
        value -= 65536

    return value


# ============================================================
# PRINT IMPORTANT REGISTERS
# ============================================================

def print_registers(ser):

    print("\n")
    print("=" * 60)
    print("CURRENT DRIVER STATE")
    print("=" * 60)

    control = read_register(ser, 2, "CONTROL")
    mode = read_register(ser, 3, "MODE")
    pgain = read_register(ser, 4, "P GAIN")
    igain = read_register(ser, 6, "I GAIN")
    vf = read_register(ser, 8, "VF GAIN")
    lpr = read_register(ser, 10, "LPR")
    accel = read_register(ser, 12, "ACCELERATION")
    speed = read_register(ser, 14, "SPEED")

    position = read_position(ser)
    feedback = read_speed_feedback(ser)

    print()
    print(f"CONTROL       : 0x{control:04X}" if control is not None else "CONTROL       : ERROR")
    print(f"MODE          : 0x{mode:04X}" if mode is not None else "MODE          : ERROR")
    print(f"P GAIN        : {pgain}" if pgain is not None else "P GAIN        : ERROR")
    print(f"I GAIN        : {igain}" if igain is not None else "I GAIN        : ERROR")
    print(f"VF GAIN       : {vf}" if vf is not None else "VF GAIN       : ERROR")
    print(f"LPR           : {lpr}" if lpr is not None else "LPR           : ERROR")
    print(f"ACCELERATION  : {accel}" if accel is not None else "ACCELERATION  : ERROR")
    print(f"SPEED COMMAND : {speed}" if speed is not None else "SPEED COMMAND : ERROR")
    print(f"POSITION      : {position}" if position is not None else "POSITION      : ERROR")
    print(f"SPEED FEEDBACK: {feedback}" if feedback is not None else "SPEED FEEDBACK: ERROR")

    print("=" * 60)


# ============================================================
# VERIFY CONTROL REGISTER
# ============================================================

def verify_control(ser, expected):

    actual = read_control(ser)

    if actual is None:
        print("  CONTROL READ FAILED")
        return False

    print(
        f"  Control register: "
        f"0x{actual:04X} "
        f"(expected 0x{expected:04X})"
    )

    if actual == expected:
        print("  CONTROL STATE: OK")
        return True

    print("  CONTROL STATE: *** UNEXPECTED ***")
    return False


# ============================================================
# ONE DIRECTION TEST
# ============================================================

def test_direction(
    ser,
    name,
    start_command,
    expected_running,
    stop_command,
    expected_stopped
):

    print("\n")
    print("#" * 60)
    print(f"# {name}")
    print("#" * 60)

    # --------------------------------------------------------
    # Position before
    # --------------------------------------------------------

    position_before = read_position(ser)

    print(f"\nPosition BEFORE: {position_before}")

    # --------------------------------------------------------
    # Start
    # --------------------------------------------------------

    write_register(
        ser,
        2,
        start_command,
        f"{name} START"
    )

    time.sleep(0.2)

    print("\nChecking control state...")
    verify_control(ser, expected_running)

    print("\n*** MOTOR SHOULD BE RUNNING NOW ***")
    print("*** LOOK AT THE RED LED ***")

    time.sleep(RUN_TIME)

    # --------------------------------------------------------
    # Feedback while running
    # --------------------------------------------------------

    position_running = read_position(ser)
    speed_feedback = read_speed_feedback(ser)

    print("\nFeedback WHILE RUNNING:")
    print(f"  Position      : {position_running}")
    print(f"  Speed feedback: {speed_feedback}")

    # --------------------------------------------------------
    # Stop
    # --------------------------------------------------------

    write_register(
        ser,
        2,
        stop_command,
        f"{name} STOP"
    )

    time.sleep(0.2)

    print("\nChecking control state after STOP...")
    verify_control(ser, expected_stopped)

    print("\n*** MOTOR SHOULD NOW BE STOPPED ***")
    print("*** LOOK AT THE RED LED ***")

    time.sleep(STOP_TIME)

    # --------------------------------------------------------
    # Position after
    # --------------------------------------------------------

    position_after = read_position(ser)

    print(f"\nPosition AFTER: {position_after}")

    # --------------------------------------------------------
    # Calculate movement
    # --------------------------------------------------------

    if (
        position_before is not None
        and position_after is not None
    ):

        delta = position_after - position_before

        print("\n----------------------------------------")
        print(f"{name} RESULT")
        print("----------------------------------------")
        print(f"Position before : {position_before}")
        print(f"Position after  : {position_after}")
        print(f"Position change : {delta}")

        if delta > 0:
            print("Encoder direction: POSITIVE (+)")

        elif delta < 0:
            print("Encoder direction: NEGATIVE (-)")

        else:
            print("Encoder direction: NO MOVEMENT")

    print("----------------------------------------")


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 60)
    print("RMCS-2303 DIRECTION DIAGNOSTIC TEST")
    print("=" * 60)

    ser = serial.Serial(
        PORT,
        BAUD,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=1
    )

    try:

        # ----------------------------------------------------
        # Initial state
        # ----------------------------------------------------

        print("\nINITIAL DRIVER STATE")
        print_registers(ser)

        # ----------------------------------------------------
        # Set speed
        # ----------------------------------------------------

        write_register(
            ser,
            14,
            SPEED,
            f"SET SPEED = {SPEED}"
        )

        time.sleep(0.5)

        # ----------------------------------------------------
        # Verify speed
        # ----------------------------------------------------

        actual_speed = read_register(
            ser,
            14,
            "SPEED"
        )

        print(f"\nSpeed readback: {actual_speed}")

        # ----------------------------------------------------
        # Make sure we start disabled
        # ----------------------------------------------------

        print("\nForcing initial DISABLED state...")

        write_register(
            ser,
            2,
            0x0100,
            "INITIAL DISABLE"
        )

        time.sleep(1)

        verify_control(
            ser,
            0x0100
        )

        # ----------------------------------------------------
        # Repeat tests
        # ----------------------------------------------------

        for cycle in range(1, TEST_CYCLES + 1):

            print("\n\n")
            print("=" * 60)
            print(f"TEST CYCLE {cycle} / {TEST_CYCLES}")
            print("=" * 60)

            # ------------------------------------------------
            # FORWARD
            #
            # DIR = 0
            # ENABLE = 1
            #
            # 0x0101
            # ------------------------------------------------

            test_direction(
                ser,
                "FORWARD",
                start_command=0x0101,
                expected_running=0x0101,
                stop_command=0x0100,
                expected_stopped=0x0100
            )

            # ------------------------------------------------
            # Wait
            # ------------------------------------------------

            print("\nWaiting before reverse...")
            time.sleep(1)

            # ------------------------------------------------
            # REVERSE
            #
            # DIR = 1
            # ENABLE = 1
            #
            # 0x0109
            # ------------------------------------------------

            test_direction(
                ser,
                "REVERSE",
                start_command=0x0109,
                expected_running=0x0109,
                stop_command=0x0108,
                expected_stopped=0x0108
            )

            print("\nCycle complete.")

        # ----------------------------------------------------
        # Final state
        # ----------------------------------------------------

        print("\n")
        print("=" * 60)
        print("FINAL DRIVER STATE")
        print("=" * 60)

        print_registers(ser)

        # ----------------------------------------------------
        # Final disable
        # ----------------------------------------------------

        print("\nFinal disable...")

        write_register(
            ser,
            2,
            0x0108,
            "FINAL REVERSE DISABLE"
        )

        time.sleep(1)

        print("\nFINAL CONTROL:")
        verify_control(ser, 0x0108)

        print("\n")
        print("=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)

    finally:

        ser.close()


if __name__ == "__main__":
    main()
