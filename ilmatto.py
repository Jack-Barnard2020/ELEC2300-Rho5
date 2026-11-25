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
    def list_ports() -> list[str]:
        """Return port names, such as ['COM3', 'COM7']; [] is also valid."""
        # TODO 1: Call list_ports.comports().
        # Each returned object describes one port; its .device is the name.
        # Collect the names into a list and return it. No board connection needed.
        raise NotImplementedError("TODO 1: list the available ports")

    def is_connected(self) -> bool:
        """Return whether we have an open local serial handle.

        This alone cannot prove the cable is still plugged in; PING checks that
        the board responds. A later read/write failure must clear the handle.
        """
        # TODO 2: Return False when self._serial is None.
        # Otherwise return the handle's .is_open property.
        raise NotImplementedError("TODO 2: check the connection state")

    def connect(self, port: str) -> None:
        """Open the selected port using the stored settings."""
        # TODO 3: Reject an empty port name and invalid settings with ValueError.
        # Require a positive baudrate and finite, positive timeout/max_voltage.
        # If already connected, raise IlMattoError with a helpful message.
        # Construct serial.Serial(port=..., baudrate=..., timeout=...,
        #                         write_timeout=...). Store it in self._serial.
        # Use 8 data bits, no parity, 1 stop bit and no flow control (8N1).
        # Start with an empty self._receive_buffer.
        # Catch serial.SerialException/OSError, clear the handle, and raise
        # IlMattoError explaining which port could not be opened.
        # Do not enable PID here. The test script performs PING separately.
        raise NotImplementedError("TODO 3: open the serial connection")

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
