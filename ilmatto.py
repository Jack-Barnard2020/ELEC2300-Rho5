"""Rho5 section 3.1: complete the numbered TODOs, one method at a time.

Protocol hints match the uploaded Rho4-Dac-Windows.zip, not necessarily a
modified version on your board. Keep all serial calls inside this module.
"""

import math
import time

import serial
from serial.tools import list_ports


class IlMattoError(Exception):
    """An understandable communication/board error for the GUI to display."""


class IlMatto:
    """Manage one board. The PID calculation stays on the Il Matto.

    This skeleton is deliberately incomplete. Public methods below form the
    interface that both later GUIs can use. Call them sequentially.
    """

    def __init__(self, baudrate=9600, timeout=1.0, max_voltage=3.3):
        # Construction stores settings; it does not open a port.
        self.baudrate = baudrate
        self.timeout = timeout
        self.max_voltage = max_voltage
        self._serial = None
        self._receive_buffer = b""

    @staticmethod
    @staticmethod
    def list_ports() -> list[str]:
        """Return the names of available serial ports."""
        ports = []

        for port in list_ports.comports():
            ports.append(port.device)

        return ports

    def is_connected(self) -> bool:
        """Return whether we have an open local serial handle.

        This alone cannot prove the cable is still plugged in; PING checks that
        the board responds. A later read/write failure must clear the handle.
        """
        if self._serial is None:
            return False
        return self._serial.is_open


    def connect(self, port: str) -> None:
        """Open the selected serial port."""
        if not isinstance(port, str) or not port.strip():
            raise ValueError("Enter a valid serial port name.")

        if self.is_connected():
            raise IlMattoError("Already connected. Disconnect first.")

        if not isinstance(self.baudrate, int) or self.baudrate <= 0:
            raise ValueError("Baud rate must be a positive integer.")

        try:
            timeout = float(self.timeout)
            max_voltage = float(self.max_voltage)
        except (TypeError, ValueError) as exc:
            raise ValueError("Timeout and voltage limit must be numbers.") from exc

        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Timeout must be finite and positive.")

        if not math.isfinite(max_voltage) or max_voltage <= 0:
            raise ValueError("Voltage limit must be finite and positive.")

        try:
            self._serial = serial.Serial(
                port=port.strip(),
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout,
                write_timeout=timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )
        except (serial.SerialException, OSError) as exc:
            self._serial = None
            raise IlMattoError(f"Could not open {port}: {exc}") from exc

        self.timeout = timeout
        self.max_voltage = max_voltage
        self._receive_buffer = b""


    def disconnect(self) -> None:
        """Close the port and clear the connection state."""
        try:
            if self._serial is not None:
                self._serial.close()

        except (serial.SerialException, OSError) as exc:
            raise IlMattoError(
                f"Could not close the connection: {exc}"
            ) from exc

        finally:
            self._fromserial = None
            self._receive_buffer = b""
    
    def send_command(self, command: str) -> str:
        """Send one ASCII command and return its complete reply."""
        if not self.is_connected():
            raise IlMattoError("Connect to the board first.")

        # Validate the command before sending anything.
        if not isinstance(command, str) or not command.strip():
            raise ValueError("Command must be a nonempty string.")

        if "\r" in command or "\n" in command:
            raise ValueError("Send only one command at a time.")

        try:
            encoded = command.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError(
                "Commands must contain ASCII characters."
            ) from exc

        if len(encoded) > 63:
            raise ValueError("Command must be at most 63 bytes long.")

        deadline = time.monotonic() + self.timeout

        try:
            # Finish the command with the newline expected by the firmware.
            message = encoded + b"\n"
            written = self._serial.write(message)

            if written != len(message):
                raise OSError("The complete command could not be sent.")

            while True:
                remaining = deadline - time.monotonic()

                if remaining <= 0:
                    raise TimeoutError("The board did not reply in time.")

                # Process a reply only after receiving its newline.
                if b"\n" in self._receive_buffer:
                    line, self._receive_buffer = (
                        self._receive_buffer.split(b"\n", 1)
                    )
                    reply = line.decode("ascii").rstrip("\r")

                    # Ignore blank lines, startup messages and telemetry.
                    if not reply:
                        continue

                    if reply.startswith(("READY ", "DATA ")):
                        continue

                    if reply.startswith("OK "):
                        return reply

                    if reply.startswith("ERR "):
                        raise IlMattoError(
                            f"Board rejected command: {reply}"
                        )

                    raise ValueError(
                        f"Unexpected board reply: {reply!r}"
                    )

                # Read another byte without exceeding the overall timeout.
                self._serial.timeout = min(0.05, remaining)
                self._receive_buffer += self._serial.read(1)

                if len(self._receive_buffer) > 1024:
                    raise ValueError(
                        "Received an excessively long reply."
                    )

        except (
            serial.SerialException,
            OSError,
            UnicodeError,
            ValueError,
        ) as exc:
            # Clear the connection after a communication failure.
            try:
                self.disconnect()
            except IlMattoError:
                pass

            raise IlMattoError(
                f"Communication failed: {exc}"
            ) from exc

    def read_voltage(self) -> float:
        """Read the measured output voltage and return it as a float."""
        reply = self.send_command("READ")

        # Expected reply example: OK READ v=2.497
        prefix = "OK READ v="

        if not reply.startswith(prefix):
            raise IlMattoError(
                f"Unexpected voltage reply: {reply!r}"
            )

        number = reply[len(prefix):]

        try:
            voltage = float(number)
        except ValueError as exc:
            raise IlMattoError(
                f"Invalid voltage in reply: {reply!r}"
            ) from exc

        if not math.isfinite(voltage):
            raise IlMattoError(
                f"Voltage must be finite: {reply!r}"
            )

        return voltage   

    def set_voltage(self, voltage: float) -> None:
        """Validate and send a voltage setpoint to the board."""
        try:
            value = float(voltage)
        except (TypeError, ValueError) as exc:
            raise ValueError("Voltage must be a number.") from exc

        if not math.isfinite(value):
            raise ValueError("Voltage must be finite.")

        if not 0 <= value <= self.max_voltage:
            raise ValueError(
                f"Voltage must be between 0 and {self.max_voltage} V."
            )

        # Send the target using three decimal places.
        target = f"{value:.3f}"
        reply = self.send_command(f"SET {target}")

        prefix = "OK SET sp="

        if not reply.startswith(prefix):
            raise IlMattoError(
                f"Unexpected setpoint reply: {reply!r}"
            )

        try:
            confirmed = float(reply[len(prefix):])
        except ValueError as exc:
            raise IlMattoError(
                f"Invalid setpoint acknowledgement: {reply!r}"
            ) from exc

        if not math.isfinite(confirmed):
            raise IlMattoError("Board returned a nonfinite setpoint.")

        if not math.isclose(
            confirmed,
            float(target),
            rel_tol=0.0,
            abs_tol=0.0005,
        ):
            raise IlMattoError(
                f"Board confirmed {confirmed} V; requested {target} V."
            )

    def set_pid_gains(self, kp: float, ki: float, kd: float) -> None:
        """Validate and send PID gains to the board."""
        try:
            kp = float(kp)
            ki = float(ki)
            kd = float(kd)
        except (TypeError, ValueError) as exc:
            raise ValueError("PID gains must be numbers.") from exc

        # Limits defined by your uploaded Rho4 firmware.
        for name, value, maximum in (
            ("Kp", kp, 1000),
            ("Ki", ki, 10000),
            ("Kd", kd, 100),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite.")

            if not 0 <= value <= maximum:
                raise ValueError(
                    f"{name} must be between 0 and {maximum}."
                )

        command = f"GAINS {kp:.6g} {ki:.6g} {kd:.6g}"
        reply = self.send_command(command)

        if reply != "OK GAINS":
            raise IlMattoError(
                f"Unexpected PID gains reply: {reply!r}"
            )

    def set_mode(self, mode: str) -> None:
        """Select OFF, OPEN or PID mode."""
        if not isinstance(mode, str):
            raise ValueError("Mode must be a string.")

        mode = mode.strip().upper()

        if mode not in ("OFF", "OPEN", "PID"):
            raise ValueError("Mode must be OFF, OPEN or PID.")

        reply = self.send_command(f"MODE {mode}")
        expected = f"OK MODE mode={mode}"

        if reply != expected:
            raise IlMattoError(
                f"Unexpected mode reply: {reply!r}"
            )



