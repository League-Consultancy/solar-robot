from flask import Flask, render_template, jsonify

import threading
import time

from collections import deque

import cv2
import numpy as np
import tensorflow as tf


from motors.drive_final import SolarRobot
from motors.brush_final import RMCS2304Motor

from sensors.mpu6050 import MPU6050
from sensors.tof import ToF
from sensors.relay import PumpRelay


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

# ------------------------------------------------------------
# AI MODEL
# ------------------------------------------------------------

MODEL_PATH = "training/best_model.keras"

MODEL_SIZE = 224

CLASS_NAMES = [
    "forward",
    "left",
    "right",
    "turn"
]


# ------------------------------------------------------------
# CAMERA
# ------------------------------------------------------------

CAMERA_DEVICE = "/dev/video3"

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

CAMERA_FPS = 15


# ------------------------------------------------------------
# AI DECISION
# ------------------------------------------------------------

PREDICTION_WINDOW = 5

REQUIRED_PREDICTIONS = 3


# ------------------------------------------------------------
# TURN PROBING
# ------------------------------------------------------------

# Temporary value.
#
# Later this should be replaced by encoder-based
# positioning using RMCS-2303 feedback.

PROBE_TIME = 0.25

PROBE_SETTLE_TIME = 0.10

PROBE_FRAMES = 5


# ------------------------------------------------------------
# TOF
# ------------------------------------------------------------

# ToF returns millimeters.

# 5 cm = 50 mm

TOF_THRESHOLD_MM = 50

# Distance must remain above threshold
# for this amount of time.

TOF_TRIGGER_TIME = 3.0

# Temporary time-based reverse distance.

# Later replace with encoder-based distance.

TOF_REVERSE_TIME = 0.40

# ToF polling interval.

TOF_POLL_INTERVAL = 0.05


# ============================================================
# HARDWARE INITIALIZATION
# ============================================================

print()
print("========================================")
print("INITIALIZING SOLAR ROBOT")
print("========================================")
print()


# ------------------------------------------------------------
# DRIVE MOTORS
# ------------------------------------------------------------

print("Initializing drive motors...")

robot = SolarRobot()


# ------------------------------------------------------------
# BRUSH
# ------------------------------------------------------------

print("Initializing brush...")

brush = RMCS2304Motor(
    port="/dev/ttyAMA1",
    slave_id=7,
    baudrate=9600
)

brush.set_speed(2048)


# ------------------------------------------------------------
# IMU
# ------------------------------------------------------------

print("Initializing MPU6050...")

imu = MPU6050(
    bus_number=1,
    address=0x68
)


# ------------------------------------------------------------
# TOF
# ------------------------------------------------------------

print("Initializing ToF...")

tof = ToF()


# ------------------------------------------------------------
# PUMP
# ------------------------------------------------------------

print("Initializing pump...")

pump = PumpRelay(
    pin=17
)

# Pump starts ON.

pump_state = True


# ------------------------------------------------------------
# CAMERA
# ------------------------------------------------------------

print("Initializing navigation camera...")

camera = cv2.VideoCapture(
    CAMERA_DEVICE
)

if not camera.isOpened():

    print(
        f"WARNING: Could not open camera "
        f"{CAMERA_DEVICE}"
    )

else:

    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        CAMERA_WIDTH
    )

    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        CAMERA_HEIGHT
    )

    camera.set(
        cv2.CAP_PROP_FPS,
        CAMERA_FPS
    )

    print(
        "Navigation camera initialized."
    )


# ------------------------------------------------------------
# AI MODEL
# ------------------------------------------------------------

print("Loading navigation model...")

navigation_model = tf.keras.models.load_model(
    MODEL_PATH
)

print(
    "Navigation model loaded."
)


print()
print("All hardware initialized.")
print()


# ============================================================
# LOCKS
# ============================================================

# Protect physical motor commands.

robot_lock = threading.Lock()


# Protect sensor_data.

sensor_lock = threading.Lock()


# Protect camera access.

camera_lock = threading.Lock()


# Protect autonomous status.

autonomous_status_lock = threading.Lock()


# ============================================================
# ROBOT STATE
# ============================================================

current_command = "stop"

brush_state = False

autonomous_mode = False


# ============================================================
# SENSOR DATA
# ============================================================

sensor_data = {

    "acceleration": {
        "x": 0,
        "y": 0,
        "z": 0
    },

    "gyroscope": {
        "x": 0,
        "y": 0,
        "z": 0
    },

    "temperature": 0,

    "tof": 0
}


# ============================================================
# AUTONOMOUS STATE
# ============================================================

autonomous_state = "IDLE"


# Possible states:
#
# IDLE
# NORMAL
# TOF_RECOVERY
# TURN_PROBE
# TURN_EXECUTE
# STOPPED


# ============================================================
# AUTONOMOUS THREAD CONTROL
# ============================================================

autonomous_thread = None

autonomous_stop_event = threading.Event()


# ============================================================
# TOF EVENT
# ============================================================

# ToF thread sets this.
#
# Autonomous thread handles it.

tof_event = threading.Event()


# ============================================================
# TOF STATE
# ============================================================

tof_trigger_start = None

tof_event_active = False


# ============================================================
# AUTONOMOUS STATUS
# ============================================================

autonomous_status = {

    "running": False,

    "state": "IDLE",

    "prediction": "none",

    "confidence": 0.0,

    "decision": "none",

    "previous_turn": None,

    "prediction_history": [],

    "tof_distance": 0,

    "tof_timer": 0,

    "tof_event": False,

    "error": None
}


# ============================================================
# SENSOR THREAD
# ============================================================

def sensor_loop():

    global sensor_data

    while True:

        try:

            imu_data = imu.read_all()

            # ------------------------------------------------
            # ToF is handled by dedicated ToF thread.
            # ------------------------------------------------

            with sensor_lock:

                sensor_data = {

                    "acceleration": {

                        "x":
                            imu_data[
                                "acceleration"
                            ][0],

                        "y":
                            imu_data[
                                "acceleration"
                            ][1],

                        "z":
                            imu_data[
                                "acceleration"
                            ][2]
                    },

                    "gyroscope": {

                        "x":
                            imu_data[
                                "gyroscope"
                            ][0],

                        "y":
                            imu_data[
                                "gyroscope"
                            ][1],

                        "z":
                            imu_data[
                                "gyroscope"
                            ][2]
                    },

                    "temperature":
                        imu_data["temperature"],

                    "tof":
                        sensor_data["tof"]
                }


        except Exception as e:

            print(
                "[SENSOR] Error:",
                e
            )


        time.sleep(
            0.05
        )


# ============================================================
# AUTONOMOUS STATUS HELPER
# ============================================================

def update_autonomous_status(**kwargs):

    global autonomous_status

    with autonomous_status_lock:

        autonomous_status.update(
            kwargs
        )


# ============================================================
# MOTOR COMMAND
# ============================================================

def execute_motor_command(command):

    """
    Central motor command function.

    This is the ONLY function used by autonomous
    navigation to command the drive motors.
    """

    global current_command

    commands = {

        "forward":
            robot.forward,

        "backward":
            robot.reverse,

        "reverse":
            robot.reverse,

        "left":
            robot.left,

        "right":
            robot.right,

        "stop":
            robot.stop
    }


    if command not in commands:

        raise ValueError(
            f"Invalid motor command: {command}"
        )


    with robot_lock:

        commands[command]()

        current_command = command


# ============================================================
# AI PREDICTION
# ============================================================

def predict_navigation(frame):

    """
    Run one frame through MobileNetV3.

    Returns:

        class_name
        confidence
    """

    image = cv2.resize(
        frame,
        (
            MODEL_SIZE,
            MODEL_SIZE
        )
    )


    image = np.asarray(
        image,
        dtype=np.float32
    )


    image = np.expand_dims(
        image,
        axis=0
    )


    predictions = navigation_model.predict(
        image,
        verbose=0
    )[0]


    class_index = int(
        np.argmax(predictions)
    )


    confidence = float(
        predictions[class_index]
    )


    class_name = CLASS_NAMES[
        class_index
    ]


    return (
        class_name,
        confidence
    )


# ============================================================
# 3-OF-5 DECISION
# ============================================================

def get_confirmed_decision(history):

    """
    Confirm a decision if a class appears
    at least 3 times in the last 5 predictions.
    """

    if len(history) < PREDICTION_WINDOW:

        return None


    counts = {

        "forward": 0,

        "left": 0,

        "right": 0,

        "turn": 0
    }


    for result in history:

        counts[result] += 1


    # --------------------------------------------------------
    # Direction decisions
    # --------------------------------------------------------

    if (
        counts["left"]
        >= REQUIRED_PREDICTIONS
    ):

        return "left"


    if (
        counts["right"]
        >= REQUIRED_PREDICTIONS
    ):

        return "right"


    if (
        counts["turn"]
        >= REQUIRED_PREDICTIONS
    ):

        return "turn"


    if (
        counts["forward"]
        >= REQUIRED_PREDICTIONS
    ):

        return "forward"


    return None


# ============================================================
# PROBE PREDICTIONS
# ============================================================

def capture_probe_predictions():

    results = []


    for _ in range(
        PROBE_FRAMES
    ):

        # ----------------------------------------------------
        # Allow manual shutdown
        # ----------------------------------------------------

        if autonomous_stop_event.is_set():

            break


        # ----------------------------------------------------
        # Camera
        # ----------------------------------------------------

        with camera_lock:

            ret, frame = camera.read()


        if not ret:

            print(
                "[AUTO] Probe camera failure."
            )

            continue


        # ----------------------------------------------------
        # AI
        # ----------------------------------------------------

        result, confidence = (
            predict_navigation(frame)
        )


        results.append(
            (
                result,
                confidence
            )
        )


        print(
            f"[PROBE] "
            f"{result:8s} "
            f"{confidence:.3f}"
        )


    return results


# ============================================================
# EVALUATE PROBE
# ============================================================

def evaluate_probe(results):

    if not results:

        return None


    counts = {

        "forward": 0,

        "left": 0,

        "right": 0,

        "turn": 0
    }


    for result, confidence in results:

        counts[result] += 1


    if (
        counts["left"]
        >= REQUIRED_PREDICTIONS
    ):

        return "left"


    if (
        counts["right"]
        >= REQUIRED_PREDICTIONS
    ):

        return "right"


    if (
        counts["forward"]
        >= REQUIRED_PREDICTIONS
    ):

        return "forward"


    if (
        counts["turn"]
        >= REQUIRED_PREDICTIONS
    ):

        return "turn"


    return None


# ============================================================
# CONTROLLED MOVEMENT
# ============================================================

def move_for(
    direction,
    duration
):

    """
    Move for a fixed amount of time.

    Used for temporary probe/reverse movement.

    IMPORTANT:
    Later replace time-based movement with encoder
    position feedback.
    """

    if autonomous_stop_event.is_set():

        return False


    print(
        f"[AUTO] "
        f"Moving {direction} "
        f"for {duration:.2f}s"
    )


    execute_motor_command(
        direction
    )


    start = time.monotonic()


    while (
        time.monotonic() - start
        < duration
    ):

        if autonomous_stop_event.is_set():

            execute_motor_command(
                "stop"
            )

            return False


        time.sleep(
            0.01
        )


    execute_motor_command(
        "stop"
    )


    time.sleep(
        PROBE_SETTLE_TIME
    )


    return True


# ============================================================
# TURN EVENT
# ============================================================

def handle_turn(previous_turn):

    """
    Resolve TURN using left/right probing.

    Sequence:

        CENTER
           |
        LEFT PROBE
           |
        CENTER
           |
        RIGHT PROBE
           |
        CENTER
           |
        CHOOSE
    """

    global autonomous_state


    update_autonomous_status(
        state="TURN_PROBE"
    )


    autonomous_state = (
        "TURN_PROBE"
    )


    print()
    print(
        "================================"
    )
    print(
        "[AUTO] TURN PROBE START"
    )
    print(
        "================================"
    )


    # ========================================================
    # STOP
    # ========================================================

    execute_motor_command(
        "stop"
    )

    time.sleep(
        0.15
    )


    # ========================================================
    # LEFT PROBE
    # ========================================================

    print(
        "[AUTO] Probing LEFT..."
    )


    if not move_for(
        "left",
        PROBE_TIME
    ):

        return previous_turn


    left_results = (
        capture_probe_predictions()
    )


    left_decision = (
        evaluate_probe(
            left_results
        )
    )


    print(
        "[AUTO] LEFT result:",
        left_decision
    )


    # ========================================================
    # RETURN TO CENTER
    # ========================================================

    print(
        "[AUTO] Returning center..."
    )


    if not move_for(
        "right",
        PROBE_TIME
    ):

        return previous_turn


    # ========================================================
    # RIGHT PROBE
    # ========================================================

    print(
        "[AUTO] Probing RIGHT..."
    )


    if not move_for(
        "right",
        PROBE_TIME
    ):

        return previous_turn


    right_results = (
        capture_probe_predictions()
    )


    right_decision = (
        evaluate_probe(
            right_results
        )
    )


    print(
        "[AUTO] RIGHT result:",
        right_decision
    )


    # ========================================================
    # RETURN TO CENTER
    # ========================================================

    print(
        "[AUTO] Returning center..."
    )


    if not move_for(
        "left",
        PROBE_TIME
    ):

        return previous_turn


    # ========================================================
    # DECISION
    # ========================================================

    print()
    print(
        "[AUTO] "
        f"LEFT={left_decision}, "
        f"RIGHT={right_decision}"
    )


    # --------------------------------------------------------
    # Clear LEFT
    # --------------------------------------------------------

    if left_decision == "left":

        print(
            "[AUTO] Choosing LEFT"
        )

        return "left"


    # --------------------------------------------------------
    # Clear RIGHT
    # --------------------------------------------------------

    if right_decision == "right":

        print(
            "[AUTO] Choosing RIGHT"
        )

        return "right"


    # --------------------------------------------------------
    # LEFT + FORWARD
    # --------------------------------------------------------

    if (
        left_decision == "left"
        and right_decision == "forward"
    ):

        return "left"


    # --------------------------------------------------------
    # RIGHT + FORWARD
    # --------------------------------------------------------

    if (
        right_decision == "right"
        and left_decision == "forward"
    ):

        return "right"


    # --------------------------------------------------------
    # Both forward / ambiguous
    #
    # Use previous turn.
    # --------------------------------------------------------

    if previous_turn in (
        "left",
        "right"
    ):

        print(
            "[AUTO] "
            "Using previous turn:",
            previous_turn
        )

        return previous_turn


    # --------------------------------------------------------
    # Nothing reliable
    # --------------------------------------------------------

    print(
        "[AUTO] "
        "No reliable turn."
    )


    return "stop"


# ============================================================
# TOF EVENT HANDLER
# ============================================================

def handle_tof_event(
    previous_turn
):

    """
    ToF has detected an edge.

    IMPORTANT:

    This function runs INSIDE the autonomous thread.

    Therefore the autonomous AI loop is BLOCKED until
    this entire function finishes.

    Sequence:

        STOP
          ↓
        REVERSE
          ↓
        TURN PROBE
          ↓
        EXECUTE TURN
          ↓
        RETURN
          ↓
        AI resumes
    """

    global autonomous_state
    global tof_event_active


    tof_event_active = True


    autonomous_state = (
        "TOF_RECOVERY"
    )


    update_autonomous_status(

        state="TOF_RECOVERY",

        tof_event=True,

        decision="tof_edge"
    )


    print()
    print(
        "========================================"
    )
    print(
        "[AUTO] TOF EVENT"
    )
    print(
        "========================================"
    )


    try:

        # ====================================================
        # STOP
        # ====================================================

        print(
            "[AUTO] STOP"
        )


        execute_motor_command(
            "stop"
        )


        time.sleep(
            0.15
        )


        # ====================================================
        # REVERSE
        # ====================================================

        print(
            "[AUTO] REVERSE"
        )


        success = move_for(
            "reverse",
            TOF_REVERSE_TIME
        )


        if not success:

            execute_motor_command(
                "stop"
            )

            return previous_turn


        # ====================================================
        # STOP
        # ====================================================

        execute_motor_command(
            "stop"
        )


        time.sleep(
            0.15
        )


        # ====================================================
        # TURN
        # ====================================================

        print(
            "[AUTO] Starting TURN..."
        )


        turn_result = handle_turn(
            previous_turn
        )


        # ====================================================
        # EXECUTE FINAL TURN
        # ====================================================

        autonomous_state = (
            "TURN_EXECUTE"
        )


        update_autonomous_status(
            state="TURN_EXECUTE"
        )


        if turn_result == "left":

            print(
                "[AUTO] Executing LEFT"
            )


            execute_motor_command(
                "left"
            )


            # ------------------------------------------------
            # IMPORTANT
            #
            # We need some time for the actual turn.
            #
            # This is currently time-based.
            # Later use IMU/encoder.
            # ------------------------------------------------

            time.sleep(
                PROBE_TIME
            )


            execute_motor_command(
                "stop"
            )


            return "left"


        elif turn_result == "right":

            print(
                "[AUTO] Executing RIGHT"
            )


            execute_motor_command(
                "right"
            )


            time.sleep(
                PROBE_TIME
            )


            execute_motor_command(
                "stop"
            )


            return "right"


        else:

            print(
                "[AUTO] "
                "TURN FAILED -> STOP"
            )


            execute_motor_command(
                "stop"
            )


            return "stop"


    finally:

        # ====================================================
        # TURN COMPLETE
        # ====================================================

        print()
        print(
            "========================================"
        )
        print(
            "[AUTO] TOF TURN COMPLETE"
        )
        print(
            "========================================"
        )


        tof_event_active = False


        # Clear the event only AFTER the complete
        # recovery + turn operation is finished.

        tof_event.clear()


        update_autonomous_status(

            tof_event=False,

            tof_timer=0
        )


# ============================================================
# TOF MONITOR THREAD
# ============================================================

def tof_monitor_loop():

    """
    Dedicated ToF monitoring thread.

    IMPORTANT:

    This thread NEVER controls the motors.

    It only detects:

        distance > 50 mm
        continuously for 3 seconds

    and then sets:

        tof_event.set()

    The autonomous thread handles the actual recovery.
    """

    global tof_trigger_start


    while True:

        try:

            # ------------------------------------------------
            # Only monitor in autonomous mode
            # ------------------------------------------------

            if not autonomous_mode:

                tof_trigger_start = None

                time.sleep(
                    TOF_POLL_INTERVAL
                )

                continue


            # ------------------------------------------------
            # Read ToF
            # ------------------------------------------------

            distance = (
                tof.read_distance()
            )


            # ------------------------------------------------
            # Store ToF value
            # ------------------------------------------------

            with sensor_lock:

                sensor_data[
                    "tof"
                ] = distance


            update_autonomous_status(

                tof_distance=distance
            )


            # ------------------------------------------------
            # Invalid reading
            # ------------------------------------------------

            if distance is None:

                tof_trigger_start = None

                update_autonomous_status(
                    tof_timer=0
                )

                time.sleep(
                    TOF_POLL_INTERVAL
                )

                continue


            # ------------------------------------------------
            # LARGE DISTANCE
            # ------------------------------------------------

            if (
                distance
                > TOF_THRESHOLD_MM
            ):

                # --------------------------------------------
                # Start timer
                # --------------------------------------------

                if tof_trigger_start is None:

                    tof_trigger_start = (
                        time.monotonic()
                    )


                # --------------------------------------------
                # Calculate duration
                # --------------------------------------------

                elapsed = (
                    time.monotonic()
                    -
                    tof_trigger_start
                )


                update_autonomous_status(

                    tof_timer=elapsed
                )


                # --------------------------------------------
                # Already waiting for current event
                # --------------------------------------------

                if tof_event.is_set():

                    time.sleep(
                        TOF_POLL_INTERVAL
                    )

                    continue


                # --------------------------------------------
                # 3 SECOND CONFIRMATION
                # --------------------------------------------

                if (
                    elapsed
                    >= TOF_TRIGGER_TIME
                ):

                    print()
                    print(
                        "========================================"
                    )
                    print(
                        "[TOF] EDGE CONDITION CONFIRMED"
                    )
                    print(
                        f"[TOF] Distance: "
                        f"{distance} mm"
                    )
                    print(
                        f"[TOF] Duration: "
                        f"{elapsed:.2f}s"
                    )
                    print(
                        "========================================"
                    )


                    # ----------------------------------------
                    # Signal autonomous thread
                    # ----------------------------------------

                    tof_event.set()


                    # Reset timer.
                    #
                    # The event remains set until the
                    # autonomous turn is complete.

                    tof_trigger_start = None


            # ------------------------------------------------
            # NORMAL DISTANCE
            # ------------------------------------------------

            else:

                tof_trigger_start = None


                update_autonomous_status(
                    tof_timer=0
                )


        except Exception as e:

            print(
                "[TOF] Error:",
                e
            )

            tof_trigger_start = None


        time.sleep(
            TOF_POLL_INTERVAL
        )


# ============================================================
# AUTONOMOUS LOOP
# ============================================================

def autonomous_loop():

    global autonomous_mode
    global autonomous_state


    prediction_history = deque(
        maxlen=PREDICTION_WINDOW
    )


    previous_turn = None


    autonomous_state = "NORMAL"


    update_autonomous_status(

        running=True,

        state="NORMAL",

        prediction="none",

        confidence=0.0,

        decision="none",

        previous_turn=None,

        prediction_history=[],

        error=None
    )


    print()
    print(
        "========================================"
    )
    print(
        "AUTONOMOUS NAVIGATION STARTED"
    )
    print(
        "========================================"
    )


    try:

        while not autonomous_stop_event.is_set():

            # =================================================
            # TOF HAS PRIORITY
            # =================================================

            if tof_event.is_set():

                print(
                    "[AUTO] "
                    "Pausing AI for ToF event."
                )


                # ------------------------------------------------
                # IMPORTANT
                #
                # handle_tof_event() BLOCKS this thread.
                #
                # No AI prediction or normal movement can
                # happen until it returns.
                # ------------------------------------------------

                turn_result = (
                    handle_tof_event(
                        previous_turn
                    )
                )


                # ------------------------------------------------
                # Update previous turn
                # ------------------------------------------------

                if turn_result in (
                    "left",
                    "right"
                ):

                    previous_turn = (
                        turn_result
                    )


                update_autonomous_status(

                    previous_turn=
                        previous_turn
                )


                # ------------------------------------------------
                # Clear prediction history.
                #
                # Old predictions are no longer relevant
                # after physically changing direction.
                # ------------------------------------------------

                prediction_history.clear()


                autonomous_state = (
                    "NORMAL"
                )


                update_autonomous_status(

                    state="NORMAL",

                    prediction="none",

                    confidence=0.0,

                    prediction_history=[],

                    previous_turn=
                        previous_turn
                )


                print(
                    "[AUTO] "
                    "Resuming AI navigation."
                )


                continue


            # =================================================
            # CAMERA
            # =================================================

            with camera_lock:

                ret, frame = (
                    camera.read()
                )


            if not ret:

                print(
                    "[AUTO] "
                    "Camera frame failed."
                )


                execute_motor_command(
                    "stop"
                )


                time.sleep(
                    0.1
                )


                continue


            # =================================================
            # AI
            # =================================================

            result, confidence = (
                predict_navigation(
                    frame
                )
            )


            prediction_history.append(
                result
            )


            update_autonomous_status(

                prediction=result,

                confidence=confidence,

                prediction_history=
                    list(
                        prediction_history
                    ),

                previous_turn=
                    previous_turn
            )


            print(
                f"[AUTO] "
                f"{result:8s} "
                f"{confidence:.3f} "
                f"| "
                f"{list(prediction_history)}"
            )


            # =================================================
            # NEED 5 PREDICTIONS
            # =================================================

            if (
                len(prediction_history)
                < PREDICTION_WINDOW
            ):

                execute_motor_command(
                    "forward"
                )

                continue


            # =================================================
            # 3 / 5 DECISION
            # =================================================

            decision = (
                get_confirmed_decision(
                    prediction_history
                )
            )


            # ------------------------------------------------
            # No stable decision
            # ------------------------------------------------

            if decision is None:

                execute_motor_command(
                    "forward"
                )

                continue


            # =================================================
            # CONFIRMED DECISION
            # =================================================

            print()
            print(
                "[AUTO] CONFIRMED:",
                decision.upper()
            )


            update_autonomous_status(

                decision=decision
            )


            # Clear old predictions

            prediction_history.clear()


            # =================================================
            # FORWARD
            # =================================================

            if decision == "forward":

                execute_motor_command(
                    "forward"
                )


            # =================================================
            # LEFT
            # =================================================

            elif decision == "left":

                previous_turn = "left"


                execute_motor_command(
                    "left"
                )


            # =================================================
            # RIGHT
            # =================================================

            elif decision == "right":

                previous_turn = "right"


                execute_motor_command(
                    "right"
                )


            # =================================================
            # TURN
            # =================================================

            elif decision == "turn":

                turn_result = (
                    handle_turn(
                        previous_turn
                    )
                )


                if turn_result == "left":

                    previous_turn = "left"


                    execute_motor_command(
                        "left"
                    )


                    time.sleep(
                        PROBE_TIME
                    )


                    execute_motor_command(
                        "stop"
                    )


                elif turn_result == "right":

                    previous_turn = "right"


                    execute_motor_command(
                        "right"
                    )


                    time.sleep(
                        PROBE_TIME
                    )


                    execute_motor_command(
                        "stop"
                    )


                else:

                    execute_motor_command(
                        "stop"
                    )


                update_autonomous_status(

                    previous_turn=
                        previous_turn,

                    decision=
                        turn_result
                )


    except Exception as e:

        print()
        print(
            "========================================"
        )
        print(
            "[AUTO] FATAL ERROR"
        )
        print(
            e
        )
        print(
            "========================================"
        )


        update_autonomous_status(
            error=str(e)
        )


        try:

            execute_motor_command(
                "stop"
            )

        except Exception:

            pass


    finally:

        # ----------------------------------------------------
        # ALWAYS STOP
        # ----------------------------------------------------

        try:

            execute_motor_command(
                "stop"
            )

        except Exception:

            pass


        autonomous_mode = False

        autonomous_state = (
            "STOPPED"
        )


        update_autonomous_status(

            running=False,

            state="STOPPED",

            tof_event=False
        )


        tof_event.clear()


        print(
            "[AUTO] "
            "Navigation stopped."
        )


# ============================================================
# START AUTONOMOUS
# ============================================================

def start_autonomous():

    global autonomous_thread
    global autonomous_mode
    global autonomous_state


    if autonomous_mode:

        return False


    # --------------------------------------------------------
    # Reset events
    # --------------------------------------------------------

    autonomous_stop_event.clear()

    tof_event.clear()


    # --------------------------------------------------------
    # Reset state
    # --------------------------------------------------------

    autonomous_mode = True

    autonomous_state = (
        "NORMAL"
    )


    update_autonomous_status(

        running=True,

        state="NORMAL",

        decision="none",

        error=None
    )


    # --------------------------------------------------------
    # Start autonomous thread
    # --------------------------------------------------------

    autonomous_thread = (
        threading.Thread(

            target=autonomous_loop,

            daemon=True,

            name="AutonomousNavigation"
        )
    )


    autonomous_thread.start()


    return True


# ============================================================
# STOP AUTONOMOUS
# ============================================================

def stop_autonomous():

    global autonomous_mode
    global autonomous_state


    if not autonomous_mode:

        return


    print(
        "[AUTO] "
        "Stop requested."
    )


    # --------------------------------------------------------
    # Tell autonomous loop to stop.
    # --------------------------------------------------------

    autonomous_stop_event.set()


    # --------------------------------------------------------
    # Clear pending ToF event.
    # --------------------------------------------------------

    tof_event.clear()


    # --------------------------------------------------------
    # IMMEDIATELY stop physical motors.
    # --------------------------------------------------------

    try:

        with robot_lock:

            robot.stop()


        global current_command

        current_command = (
            "stop"
        )


    except Exception as e:

        print(
            "[AUTO] "
            "Stop motor error:",
            e
        )


    # --------------------------------------------------------
    # State
    # --------------------------------------------------------

    autonomous_mode = False

    autonomous_state = (
        "STOPPED"
    )


    update_autonomous_status(

        running=False,

        state="STOPPED",

        tof_event=False
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# MANUAL DRIVE
# ============================================================

@app.route(
    "/drive/<command>",
    methods=["POST"]
)
def drive(command):

    global current_command


    commands = {

        "forward":
            robot.forward,

        "backward":
            robot.reverse,

        "left":
            robot.left,

        "right":
            robot.right,

        "stop":
            robot.stop
    }


    if command not in commands:

        return jsonify({

            "success": False,

            "error":
                "Invalid command"

        }), 400


    # ========================================================
    # MANUAL COMMAND OVERRIDES AUTONOMOUS MODE
    # ========================================================

    if autonomous_mode:

        stop_autonomous()


    # ========================================================
    # EXECUTE COMMAND
    # ========================================================

    with robot_lock:

        try:

            commands[command]()

            current_command = (
                command
            )


        except Exception as e:

            print(
                "Motor error:",
                e
            )


            try:

                robot.stop()

            except Exception:

                pass


            current_command = (
                "stop"
            )


            return jsonify({

                "success": False,

                "error":
                    str(e)

            }), 500


    return jsonify({

        "success": True,

        "command":
            current_command
    })


# ============================================================
# AUTONOMOUS ON
# ============================================================

@app.route(
    "/autonomous/on",
    methods=["POST"]
)
def autonomous_on():

    success = (
        start_autonomous()
    )


    if not success:

        return jsonify({

            "success": False,

            "error":
                "Autonomous mode already running"

        })


    return jsonify({

        "success": True,

        "autonomous": True

    })


# ============================================================
# AUTONOMOUS OFF
# ============================================================

@app.route(
    "/autonomous/off",
    methods=["POST"]
)
def autonomous_off():

    stop_autonomous()


    return jsonify({

        "success": True,

        "autonomous": False

    })


# ============================================================
# AUTONOMOUS STATUS
# ============================================================

@app.route(
    "/autonomous/status"
)
def autonomous_status_route():

    with autonomous_status_lock:

        data = (
            autonomous_status.copy()
        )


        data[
            "prediction_history"
        ] = list(
            autonomous_status[
                "prediction_history"
            ]
        )


    data[
        "autonomous"
    ] = autonomous_mode


    return jsonify(
        data
    )


# ============================================================
# BRUSH ON
# ============================================================

@app.route(
    "/brush/on",
    methods=["POST"]
)
def brush_on():

    global brush_state


    try:

        brush.start()

        brush_state = True


        return jsonify({

            "success": True,

            "brush": True

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "error":
                str(e)

        }), 500


# ============================================================
# BRUSH OFF
# ============================================================

@app.route(
    "/brush/off",
    methods=["POST"]
)
def brush_off():

    global brush_state


    try:

        brush.stop()

        brush_state = False


        return jsonify({

            "success": True,

            "brush": False

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "error":
                str(e)

        }), 500


# ============================================================
# PUMP ON
# ============================================================

@app.route(
    "/pump/on",
    methods=["POST"]
)
def pump_on():

    global pump_state


    try:

        pump.start()

        pump_state = True


        return jsonify({

            "success": True,

            "pump": True

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "error":
                str(e)

        }), 500


# ============================================================
# PUMP OFF
# ============================================================

@app.route(
    "/pump/off",
    methods=["POST"]
)
def pump_off():

    global pump_state


    try:

        pump.stop()

        pump_state = False


        return jsonify({

            "success": True,

            "pump": False

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "error":
                str(e)

        }), 500


# ============================================================
# SENSOR DATA
# ============================================================

@app.route(
    "/sensors"
)
def sensors():

    with sensor_lock:

        data = {

            "acceleration":
                sensor_data[
                    "acceleration"
                ].copy(),

            "gyroscope":
                sensor_data[
                    "gyroscope"
                ].copy(),

            "temperature":
                sensor_data[
                    "temperature"
                ],

            "tof":
                sensor_data[
                    "tof"
                ]
        }


    return jsonify(
        data
    )


# ============================================================
# ROBOT STATUS
# ============================================================

@app.route(
    "/status"
)
def status():

    with autonomous_status_lock:

        auto_data = {

            "running":
                autonomous_status[
                    "running"
                ],

            "state":
                autonomous_status[
                    "state"
                ],

            "prediction":
                autonomous_status[
                    "prediction"
                ],

            "confidence":
                autonomous_status[
                    "confidence"
                ],

            "decision":
                autonomous_status[
                    "decision"
                ],

            "previous_turn":
                autonomous_status[
                    "previous_turn"
                ],

            "tof_distance":
                autonomous_status[
                    "tof_distance"
                ],

            "tof_timer":
                autonomous_status[
                    "tof_timer"
                ],

            "tof_event":
                autonomous_status[
                    "tof_event"
                ]
        }


    return jsonify({

        "command":
            current_command,

        "autonomous":
            autonomous_mode,

        "autonomous_status":
            auto_data,

        "brush":
            brush_state,

        "pump":
            pump_state

    })


# ============================================================
# SHUTDOWN
# ============================================================

def shutdown():

    print()
    print(
        "========================================"
    )
    print(
        "SHUTTING DOWN ROBOT"
    )
    print(
        "========================================"
    )


    # ========================================================
    # STOP AUTONOMOUS
    # ========================================================

    try:

        stop_autonomous()

    except Exception as e:

        print(
            "Autonomous shutdown error:",
            e
        )


    # ========================================================
    # STOP ROBOT
    # ========================================================

    try:

        with robot_lock:

            robot.stop()

    except Exception as e:

        print(
            "Robot stop error:",
            e
        )


    # ========================================================
    # STOP BRUSH
    # ========================================================

    try:

        brush.stop()

    except Exception as e:

        print(
            "Brush stop error:",
            e
        )


    # ========================================================
    # STOP PUMP
    # ========================================================

    try:

        pump.stop()

    except Exception as e:

        print(
            "Pump stop error:",
            e
        )


    # ========================================================
    # CLOSE DRIVE
    # ========================================================

    try:

        robot.close()

    except Exception as e:

        print(
            "Robot close error:",
            e
        )


    # ========================================================
    # CLOSE CAMERA
    # ========================================================

    try:

        with camera_lock:

            camera.release()

    except Exception as e:

        print(
            "Camera close error:",
            e
        )


    # ========================================================
    # CLOSE IMU
    # ========================================================

    try:

        imu.close()

    except Exception as e:

        print(
            "IMU close error:",
            e
        )


    # ========================================================
    # CLOSE TOF
    # ========================================================

    try:

        tof.close()

    except Exception as e:

        print(
            "ToF close error:",
            e
        )


    print(
        "Hardware closed."
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # SENSOR THREAD
    # --------------------------------------------------------

    sensor_thread = (
        threading.Thread(

            target=sensor_loop,

            daemon=True,

            name="SensorThread"
        )
    )


    sensor_thread.start()


    # --------------------------------------------------------
    # TOF THREAD
    # --------------------------------------------------------

    tof_thread = (
        threading.Thread(

            target=tof_monitor_loop,

            daemon=True,

            name="ToFMonitor"
        )
    )


    tof_thread.start()


    # --------------------------------------------------------
    # SERVER
    # --------------------------------------------------------

    print()
    print(
        "========================================"
    )
    print(
        "        SOLAR ROBOT SERVER"
    )
    print(
        "========================================"
    )
    print()


    print(
        "Manual control available."
    )


    print(
        "Autonomous navigation available."
    )


    print()


    print(
        "Open from mobile:"
    )


    print()


    print(
        "http://<RASPBERRY_PI_IP>:5000"
    )


    print()


    try:

        app.run(

            host="0.0.0.0",

            port=5000,

            debug=False,

            threaded=True
        )


    except KeyboardInterrupt:

        print(
            "\nKeyboard interrupt."
        )


    finally:

        shutdown()