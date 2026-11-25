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
        """Release the port; calling this twice should be harmless.

        Closing the PC connection does not switch off the board's controller.
        Use set_mode('OFF') before disconnecting when an output stop is wanted.
        """
        # TODO 4: If a handle exists, close it.
        # Use finally to set self._serial = None and clear the receive buffer,
        # even if closing fails. Wrap serial/OSError failures in IlMattoError.
        raise NotImplementedError("TODO 4: close the serial connection")

    def send_command(self, command: str) -> str:
        """Send one ASCII command; return one complete reply without CR/LF.

        Example: 'PING' -> 'OK PONG RHO4/1'. Raise IlMattoError on failure.
        """
        # TODO 5a: Require an open connection. Validate the command: nonempty,
        # ASCII, no embedded CR/LF, and at most 63 encoded bytes before newline.
        # Invalid user arguments should raise ValueError before writing anything.
        # Encode command + '\n' and write it; check the write sent all bytes.
        # Never send a second command before receiving the first one's reply.
        #
        # TODO 5b: Read COMPLETE lines within an overall deadline, using
        # time.monotonic() + self.timeout. A read can return b'' or a partial
        # line. Accumulate bytes in self._receive_buffer until '\n' appears,
        # remove that line and retain any remaining bytes for the next line.
        # A short per-read timeout bounded by the remaining deadline prevents
        # repeated reads from extending the overall wait indefinitely.
        # Decode ASCII and remove CR/LF. Bound buffer size to reject bad data.
        # Skip blank lines, startup 'READY ...' and unsolicited 'DATA ...'.
        # Return an 'OK ...' line. Turn an 'ERR ...' line into IlMattoError.
        # Reject unexpected/malformed replies; do not return them as success.
        #
        # TODO 5c: Handle timeout, unplugging, decode errors and write failures.
        # On transport failure/timeout, clear and close the connection so a late
        # reply cannot be mistaken for the next command's reply. Raise a helpful
        # IlMattoError. Do not automatically resend commands after a timeout.
        # Do not clear the input buffer before every command: it can lose data.
        raise NotImplementedError("TODO 5: exchange a command and reply")

    def read_voltage(self) -> float:
        """Return the measured output voltage as a finite float, in volts."""
        # TODO 6: Send READ through self.send_command().
        # Require the reply format 'OK READ v=2.497'. Extract just the number,
        # convert it using float(), and check math.isfinite(). Return the float.
        # A bad format or number is an IlMattoError, not a voltage of zero.
        raise NotImplementedError("TODO 6: read and parse the measured voltage")

    def set_voltage(self, voltage: float) -> None:
        """Set the target voltage; use set_mode('PID') to enable control."""
        # TODO 7: Convert the input to float, with a helpful ValueError on failure.
        # Reject NaN/infinity and values outside 0 <= value <= self.max_voltage.
        # Format 'SET <value>' and send it through self.send_command().
        # Require an 'OK SET sp=<number>' reply; validate the returned number.
        # The uploaded firmware's limit is 3.3 V. Confirm your actual Config.hpp.
        # SET alone does not enable output when the board is in OFF mode.
        raise NotImplementedError("TODO 7: validate and send a setpoint")

    def set_pid_gains(self, kp: float, ki: float, kd: float) -> None:
        """Update the gains on the board; no Python PID loop is needed."""
        # TODO 8: Convert all three inputs to finite numbers.
        # Uploaded firmware limits: kp 0..1000, ki 0..10000, kd 0..100.
        # Reject invalid inputs with ValueError before transmitting anything.
        # Send 'GAINS <kp> <ki> <kd>'; require the exact reply 'OK GAINS'.
        raise NotImplementedError("TODO 8: validate and send the PID gains")

    def set_mode(self, mode: str) -> None:
        """Choose OFF, OPEN or PID explicitly."""
        # TODO 9: Normalize the string, then require OFF, OPEN or PID.
        # Send 'MODE <mode>'; require the exact reply 'OK MODE mode=<mode>'.
        # OPEN uses manual duty, not the voltage setpoint. For this lab use PID.
        raise NotImplementedError("TODO 9: select the operating mode")


# OPTIONAL TODO: Decode the binary phrase printed in section 3.1 of the handout.
# Print the decoded result somewhere suitable after you understand the puzzle.
