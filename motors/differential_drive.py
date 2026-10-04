from drivers.rmcs2303 import RMCS2303


class DifferentialDrive:
    """
    Two-motor differential drive.

    motor_left  -> RMCS on UART0
    motor_right -> RMCS on UART4

    IMPORTANT:
    CW/CCW are intentionally kept configurable because the
    physical mounting orientation determines which motor direction
    corresponds to robot forward.
    """

    def __init__(
        self,
        left_port="/dev/ttyAMA0",
        right_port="/dev/ttyAMA4",
        slave_id=7,
    ):
        self.left = RMCS2303(
            left_port,
            slave_id=slave_id,
        )

        self.right = RMCS2303(
            right_port,
            slave_id=slave_id,
        )

        # We will determine these from the physical robot.
        self.left_forward = "cw"
        self.right_forward = "cw"

    # ---------------------------------------------------------
    # Individual motor control
    # ---------------------------------------------------------

    def _run_motor(self, motor, direction, speed):

        motor.set_speed(speed)

        if direction == "cw":
            motor.digital_cw()

        elif direction == "ccw":
            motor.digital_ccw()

        else:
            raise ValueError(
                "Direction must be 'cw' or 'ccw'"
            )

    def _stop_motor(self, motor):
        motor.disable()

    # ---------------------------------------------------------
    # Robot motion
    # ---------------------------------------------------------

    def forward(self, speed):
        self._run_motor(
            self.left,
            self.left_forward,
            speed,
        )

        self._run_motor(
            self.right,
            self.right_forward,
            speed,
        )

    def reverse(self, speed):
        self._run_motor(
            self.left,
            self._opposite(self.left_forward),
            speed,
        )

        self._run_motor(
            self.right,
            self._opposite(self.right_forward),
            speed,
        )

    def turn_left(self, speed):
        """
        Rotate the robot left in place.

        Left wheel  -> reverse
        Right wheel -> forward
        """

        self._run_motor(
            self.left,
            self._opposite(self.left_forward),
            speed,
        )

        self._run_motor(
            self.right,
            self.right_forward,
            speed,
        )

    def turn_right(self, speed):
        """
        Rotate the robot right in place.

        Left wheel  -> forward
        Right wheel -> reverse
        """

        self._run_motor(
            self.left,
            self.left_forward,
            speed,
        )

        self._run_motor(
            self.right,
            self._opposite(self.right_forward),
            speed,
        )

    def stop(self):
        self.left.disable()
        self.right.disable()

    def estop(self):
        self.left.estop()
        self.right.estop()

    # ---------------------------------------------------------
    # Feedback
    # ---------------------------------------------------------

    def get_positions(self):
        return {
            "left": self.left.get_position(),
            "right": self.right.get_position(),
        }

    def get_speeds(self):
        return {
            "left": self.left.get_speed_feedback(),
            "right": self.right.get_speed_feedback(),
        }

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @staticmethod
    def _opposite(direction):
        if direction == "cw":
            return "ccw"

        return "cw"

    def close(self):
        self.stop()

        self.left.close()
        self.right.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
