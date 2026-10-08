from flask import Flask, render_template, jsonify
import threading
import time

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
# HARDWARE
# ============================================================

print("Initializing robot...")

robot = SolarRobot()

brush = RMCS2304Motor(
    port="/dev/ttyAMA1",
    slave_id=7,
    baudrate=9600
)

brush.set_speed(2048)

print("Initializing MPU6050...")

imu = MPU6050(
    bus_number=1,
    address=0x68
)

print("Initializing ToF...")

#tof = ToF()

print("All hardware initialized.")


# ============================================================
# LOCKS
# ============================================================

robot_lock = threading.Lock()
sensor_lock = threading.Lock()


# ============================================================
# ROBOT STATE
# ============================================================

current_command = "stop"
brush_state = False
pump_state = True

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
# SENSOR THREAD
# ============================================================

def sensor_loop():

    global sensor_data

    while True:

        try:

            imu_data = imu.read_all()

 #           distance = tof.read_distance()

            with sensor_lock:

                sensor_data = {

                    "acceleration": {
                        "x": imu_data["acceleration"][0],
                        "y": imu_data["acceleration"][1],
                        "z": imu_data["acceleration"][2]
                    },

                    "gyroscope": {
                        "x": imu_data["gyroscope"][0],
                        "y": imu_data["gyroscope"][1],
                        "z": imu_data["gyroscope"][2]
                    },

                    "temperature":
                        imu_data["temperature"],

  #                  "tof":
  #                      distance
                }

        except Exception as e:

            print("Sensor error:", e)

        time.sleep(0.05)


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# DRIVE
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
            "error": "Invalid command"
        }), 400


    with robot_lock:

        try:

            commands[command]()

            current_command = command

        except Exception as e:

            print(
                "Motor error:",
                e
            )

            try:
                robot.stop()
            except:
                pass

            current_command = "stop"

            return jsonify({
                "success": False,
                "error": str(e)
            }), 500


    return jsonify({

        "success": True,

        "command":
            current_command
    })

@app.route("/brush/on", methods=["POST"])
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
            "error": str(e)
        }), 500


@app.route("/brush/off", methods=["POST"])
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
            "error": str(e)
        }), 500

# ============================================================
# SENSOR DATA
# ============================================================

@app.route("/pump/on", methods=["POST"])
def pump_on():
    global pump_state

    try:
        # Relay is already ON after initialization.
        pump = PumpRelay(pin=17)
        pump_state = True

        return jsonify({
            "success": True,
            "pump": True
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/pump/off", methods=["POST"])
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
            "error": str(e)
        }), 500

@app.route("/sensors")
def sensors():

    with sensor_lock:

        data = {

            "acceleration":
                sensor_data["acceleration"].copy(),

            "gyroscope":
                sensor_data["gyroscope"].copy(),

            "temperature":
                sensor_data["temperature"],

            "tof":
                sensor_data["tof"]
        }

    return jsonify(data)


# ============================================================
# ROBOT STATUS
# ============================================================

@app.route("/status")
def status():

    return jsonify({

        "command":
            current_command
    })


# ============================================================
# SHUTDOWN
# ============================================================

def shutdown():

    print()
    print("Shutting down robot...")

    try:

        with robot_lock:
            robot.stop()

    except Exception as e:

        print(
            "Robot stop error:",
            e
        )

    try:

        robot.close()

    except Exception as e:

        print(
            "Robot close error:",
            e
        )

    try:

        imu.close()

    except Exception as e:

        print(
            "IMU close error:",
            e
        )

    try:

        tof.close()

    except Exception as e:

        print(
            "ToF close error:",
            e
        )

    print("Hardware closed.")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    sensor_thread = threading.Thread(
        target=sensor_loop,
        daemon=True
    )

    sensor_thread.start()

    print()
    print("==============================")
    print("     SOLAR ROBOT SERVER")
    print("==============================")
    print()
    print("Open from mobile:")
    print()
    print("http://<RASPBERRY_PI_IP>:5000")
    print()

    try:

        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,
            threaded=True
        )

    except KeyboardInterrupt:

        print("\nKeyboard interrupt.")

    finally:

        shutdown()