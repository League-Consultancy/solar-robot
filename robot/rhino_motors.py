# motors/rhino_motor.py

class RhinoMotor:

    RMCS_2303 = "RMCS-2303"
    RMCS_2304 = "RMCS-2304"

    def __init__(self, modbus):

        self.modbus = modbus
        self.model = None

    # =========================================================
    # CONFIGURATION
    # =========================================================

    def configure_2303(
        self,
        encoder_lines,
        acceleration=20000
    ):
        """
        Configure RMCS-2303.

        encoder_lines:
            Encoder Lines Per Rotation (LPR)

        IMPORTANT:
            This is NOT automatically the same as quadrature
            counts per revolution.
        """

        self.model = self.RMCS_2303

        # Register 10
        # Lines Per Rotation

        self.modbus.write_register(
            10,
            encoder_lines
        )

        # Register 12
        # Acceleration

        self.modbus.write_register(
            12,
            acceleration
        )

    # =========================================================

    def configure_2304(
        self,
        acceleration=1
    ):
        """
        Configure RMCS-2304.
        """

        self.model = self.RMCS_2304

        # Register 12
        # Acceleration

        self.modbus.write_register(
            12,
            acceleration
        )

    # =========================================================
    # SPEED
    # =========================================================

    def set_speed(self, speed):

        if self.model == self.RMCS_2303:

            self._set_speed_2303(speed)

        elif self.model == self.RMCS_2304:

            self._set_speed_2304(speed)

        else:

            raise RuntimeError(
                "Motor model has not been configured"
            )

    # =========================================================
    # RMCS-2303
    # =========================================================

    def _set_speed_2303(self, rpm):

        if abs(rpm) > 65535:

            raise ValueError(
                "RMCS-2303 RPM out of range"
            )

        rpm = int(rpm)

        # Positive = CW
        if rpm > 0:

            self.modbus.write_register(
                14,
                rpm
            )

            self.modbus.write_register(
                2,
                0x0101
            )

        # Negative = CCW
        elif rpm < 0:

            self.modbus.write_register(
                14,
                abs(rpm)
            )

            self.modbus.write_register(
                2,
                0x0109
            )

        else:

            self.stop()

    # =========================================================
    # RMCS-2304
    # =========================================================

    def _set_speed_2304(self, pwm):

        if abs(pwm) > 2048:

            raise ValueError(
                "RMCS-2304 PWM out of range"
            )

        pwm = int(pwm)

        # Positive = CW
        if pwm > 0:

            self.modbus.write_register(
                14,
                pwm
            )

            self.modbus.write_register(
                2,
                0x0201
            )

        # Negative = CCW
        elif pwm < 0:

            self.modbus.write_register(
                14,
                abs(pwm)
            )

            self.modbus.write_register(
                2,
                0x0203
            )

        else:

            self.stop()

    # =========================================================
    # BRUSH SPEED
    # =========================================================

    def set_brush_speed(self, percentage):

        if self.model != self.RMCS_2304:

            raise RuntimeError(
                "set_brush_speed() is only for RMCS-2304"
            )

        if not -100 <= percentage <= 100:

            raise ValueError(
                "Brush speed must be between -100 and 100"
            )

        pwm = int(
            abs(percentage) * 2048 / 100
        )

        if percentage < 0:

            pwm = -pwm

        self.set_speed(pwm)

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):

        if self.model == self.RMCS_2303:

            # Register 0
            # Decelerated STOP

            self.modbus.write_register(
                0,
                0x0701
            )

        elif self.model == self.RMCS_2304:

            # Disable CCW/CW command

            self.modbus.write_register(
                2,
                0x0208
            )

    # =========================================================
    # EMERGENCY STOP
    # =========================================================

    def emergency_stop(self):

        if self.model == self.RMCS_2303:

            # E-STOP command

            self.modbus.write_register(
                0,
                0x0700
            )

        elif self.model == self.RMCS_2304:

            # Disable motor

            self.modbus.write_register(
                2,
                0x0208
            )

    # =========================================================
    # SPEED FEEDBACK
    # =========================================================

    def get_speed_feedback(self):

        if self.model != self.RMCS_2303:

            raise RuntimeError(
                "Speed feedback is available here "
                "only for RMCS-2303"
            )

        value = self.modbus.read_registers(
            24,
            1
        )[0]

        # Convert unsigned 16-bit to signed

        if value >= 32768:

            value -= 65536

        return value

    # =========================================================
    # POSITION FEEDBACK
    # =========================================================

    def get_position(self):

        if self.model != self.RMCS_2303:

            raise RuntimeError(
                "Position feedback is only available "
                "for RMCS-2303"
            )

        values = self.modbus.read_registers(
            20,
            2
        )

        position = (
            values[1] << 16
        ) | values[0]

        # Convert to signed 32-bit

        if position >= 2**31:

            position -= 2**32

        return position

    # =========================================================
    # SET HOME
    # =========================================================

    def set_home(self):

        if self.model != self.RMCS_2303:

            raise RuntimeError(
                "SET HOME is for RMCS-2303"
            )

        self.modbus.write_register(
            0,
            0x0800
        )

    # =========================================================
    # SAVE EEPROM
    # =========================================================

    def save_parameters(self):

        slave_id = self.modbus.slave_id

        value = (
            (slave_id << 8) |
            0xFF
        )

        self.modbus.write_register(
            0,
            value
        )

    # =========================================================
    # RESTART
    # =========================================================

    def restart(self):

        if self.model == self.RMCS_2303:

            self.modbus.write_register(
                0,
                0x0900
            )