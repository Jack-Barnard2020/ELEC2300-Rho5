"""Rho5 section 3.1 starter. Complete the TODOs before using either GUI."""

import math
import time
import serial
from serial.tools import list_ports


class IlMatto:
    def __init__(self):
        self._serial = None
        self._rx = bytearray()  # Keep incomplete lines here between reads.

    @staticmethod
    def list_ports():
        return sorted(port.device for port in list_ports.comports())

    @property
    def is_connected(self):
        # This checks the local port. Only a successful command proves a reply.
        return self._serial is not None and self._serial.is_open

    def connect(self, port):
        self.close()
        try:
            self._serial = serial.Serial(
                port, baudrate=9600, timeout=0.1, write_timeout=1,
                bytesize=8, parity="N", stopbits=1,
                xonxoff=False, rtscts=False, dsrdtr=False,
            )
            self.send_command("PING", "OK PONG RHO4/1")
            self.send_command("STREAM 0", "OK STREAM ms=0")
            self.send_command("STATUS", "OK STATUS ")
        except Exception:
            self.close()  # Release the port if opening or the handshake fails.
            raise

    def close(self):
        try:
            if self._serial is not None:
                self._serial.close()
        finally:
            self._serial = None
            self._rx.clear()

    def send_command(self, command, expected_reply):
        """Return a complete matching OK line, without CR/LF; raise on failure."""
        if not self.is_connected:
            raise ConnectionError("Connect to the Il Matto first.")
        # TODO 1: Reject empty/non-ASCII commands, CR/LF and commands >63 bytes.
        # Encode command + "\n" as ASCII and write it. Check every byte was sent.
        # TODO 2: Use time.monotonic() to set one deadline, at least 1 s away.
        # Read bytes into self._rx. Only parse a line once it ends in b"\n".
        # A read can time out halfway through a line: keep those bytes.
        # TODO 3: Decode a complete line and remove its CR/LF.
        # Skip blank, READY and DATA lines, even after STREAM 0.
        # Raise RuntimeError with the board's message for an ERR line.
        # Return an OK line only if it matches expected_reply at a token boundary.
        # An unexpected OK line should raise RuntimeError, not count as success.
        # TODO 4: On deadline expiry, close() then raise TimeoutError.
        # On serial.SerialException/OSError, close() then raise ConnectionError.
        # Closing after a timeout prevents a late reply matching the next command.
        # Do not retry automatically. Send one command and await its reply.
        raise NotImplementedError("Complete the command/reply exchange first.")

    def read_voltage(self):
        """Return the measured feedback voltage as a float, in volts."""
        reply = self.send_command("READ", "OK READ ")
        # TODO: From 'OK READ v=2.497', extract v and return float('2.497').
        # Check the v field exists and math.isfinite(value) is True.
        # Raise RuntimeError for a malformed reply; do not return a fake zero.
        raise NotImplementedError("Parse the measured voltage from reply.")

    def set_voltage(self, volts):
        """Set the target in volts. Call set_mode('PID') to enable output."""
        # TODO: Convert volts to float; reject 'abc', NaN and infinity.
        # Require 0 <= volts <= 3.3, matching your uploaded Config.hpp.
        # Raise ValueError for bad input BEFORE writing anything.
        # Send f'SET {volts:.3f}' and expect 'OK SET sp=' followed by a number.
        # Use expected_reply='OK SET ' with send_command(). Return None.
        raise NotImplementedError("Validate the target, then send SET.")

    def set_pid_gains(self, kp, ki, kd):
        """Update gains; the PID calculation stays on the Il Matto."""
        # TODO: Convert all three inputs to finite floats; otherwise ValueError.
        # Firmware limits: Kp 0..1000, Ki 0..10000, Kd 0..100.
        # Validate ALL three before sending 'GAINS kp ki kd'. Expect 'OK GAINS'.
        # Keep enough decimal places for small Kd; return None on success.
        raise NotImplementedError("Validate the gains, then send GAINS.")

    def set_mode(self, mode):
        if mode not in ("OFF", "OPEN", "PID"):
            raise ValueError("Mode must be OFF, OPEN or PID.")
        self.send_command(f"MODE {mode}", f"OK MODE mode={mode}")
