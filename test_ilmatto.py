"""Console checks for the Rho5 section 3.1 IlMatto module."""

import argparse
import time
from unittest.mock import patch

from ilmatto import IlMatto, IlMattoError


def expect_error(label, error_type, operation, *args):
    """Pass only if the operation raises the expected error."""
    try:
        operation(*args)
    except error_type as exc:
        print(f"PASS - {label}: {exc}")
    else:
        raise AssertionError(
            f"{label}: expected {error_type.__name__}"
        )


def check_errors(board):
    """Test invalid inputs and board-command rejection."""
    board.set_mode("OFF")

    # Check that invalid operations leave these settings unchanged.
    def read_settings():
        reply = board.send_command("STATUS")
        assert reply.startswith("OK STATUS "), reply

        fields = {}
        for item in reply.split()[2:]:
            key, value = item.split("=", 1)
            fields[key] = value

        return {
            key: fields[key]
            for key in ("sp", "kp", "ki", "kd", "mode")
        }

    before = read_settings()

    for value in (
        "abc",
        -0.1,
        board.max_voltage + 0.1,
        float("nan"),
        float("inf"),
    ):
        expect_error(
            f"Invalid voltage {value!r}",
            ValueError,
            board.set_voltage,
            value,
        )

    for gains in (
        ("abc", 0, 0),
        (-1, 0, 0),
        (0, -1, 0),
        (0, 0, -1),
        (1001, 0, 0),
        (0, 10001, 0),
        (0, 0, 101),
        (float("nan"), 0, 0),
        (0, float("inf"), 0),
        (0, 0, float("nan")),
    ):
        expect_error(
            f"Invalid gains {gains!r}",
            ValueError,
            board.set_pid_gains,
            *gains,
        )

    for mode in ("INVALID", None):
        expect_error(
            f"Invalid mode {mode!r}",
            ValueError,
            board.set_mode,
            mode,
        )

    for command in ("", "PING\nREAD", "é", "X" * 64):
        expect_error(
            f"Invalid command {command!r}",
            ValueError,
            board.send_command,
            command,
        )

    expect_error(
        "Unknown command rejected by board",
        IlMattoError,
        board.send_command,
        "NOT_A_COMMAND",
    )

    assert board.send_command("PING") == "OK PONG RHO4/1"
    print("PASS - board still responds after command rejection")

    assert read_settings() == before, (
        "An invalid operation changed the board settings"
    )
    print("PASS - invalid operations left settings unchanged")

    expect_error(
        "Opening an already connected object",
        IlMattoError,
        board.connect,
        "UNUSED_PORT",
    )

    disconnected_board = IlMatto()
    expect_error(
        "Reading while disconnected",
        IlMattoError,
        disconnected_board.read_voltage,
    )

    missing_board = IlMatto()
    try:
        expect_error(
            "Opening a nonexistent port",
            IlMattoError,
            missing_board.connect,
            "/dev/rho5_nonexistent_test_port",
        )
    finally:
        missing_board.disconnect()


class FakeSerial:
    """A small serial substitute for checks without hardware."""

    def __init__(self, response=b"", unplugged=False):
        self.buffer = response
        self.unplugged = unplugged
        self.is_open = True
        self.timeout = 0.01

    def write(self, message):
        if self.unplugged:
            raise OSError("Simulated cable disconnection")
        return len(message)

    def read(self, size=1):
        if not self.buffer:
            time.sleep(min(self.timeout, 0.01))
            return b""

        data = self.buffer[:size]
        self.buffer = self.buffer[size:]
        return data

    def close(self):
        self.is_open = False


def check_simulated_replies():
    """Exercise reply handling, timeout and unplug errors."""
    scenarios = (
        (
            "Startup and telemetry lines",
            b"READY RHO4/1\nDATA v=0.000\nOK PONG RHO4/1\r\n",
            False,
            "ping",
        ),
        ("Board rejection", b"ERR COMMAND\r\n", False, "rejection"),
        ("Malformed reply", b"UNEXPECTED\r\n", False, "failure"),
        ("Reply timeout", b"", False, "failure"),
        ("Cable disconnection", b"", True, "failure"),
        ("Invalid voltage reply", b"OK READ v=abc\r\n", False, "voltage"),
    )

    for label, response, unplugged, operation in scenarios:
        fake = FakeSerial(response, unplugged)
        board = IlMatto(timeout=0.1)

        # Replace the serial constructor only during this simulated check.
        with patch("ilmatto.serial.Serial", return_value=fake):
            try:
                board.connect("SIMULATED_PORT")

                if operation == "ping":
                    assert board.send_command("PING") == "OK PONG RHO4/1"
                    print(f"PASS - {label}")

                elif operation == "voltage":
                    expect_error(
                        label,
                        IlMattoError,
                        board.read_voltage,
                    )

                else:
                    expect_error(
                        label,
                        IlMattoError,
                        board.send_command,
                        "PING",
                    )

                    if operation == "failure":
                        assert not board.is_connected(), (
                            "Communication failure should clear the connection"
                        )
                    else:
                        assert board.is_connected(), (
                            "Board rejection should keep the connection open"
                        )
            finally:
                board.disconnect()

        assert fake.is_open is False

    print("Simulated checks passed.")


def check_unplugging(board, port):
    """Optional manual check using the real cable."""
    board.set_mode("OFF")
    input("Unplug the USB cable, then press Enter: ")

    expect_error(
        "Real cable disconnection",
        IlMattoError,
        board.send_command,
        "PING",
    )
    assert not board.is_connected()

    input("Reconnect the USB cable, wait for it, then press Enter: ")

    board.connect(port)
    assert board.send_command("PING") == "OK PONG RHO4/1"
    board.set_mode("OFF")
    print("PASS - communication restored after reconnecting")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Your cable's serial port")
    parser.add_argument("--voltage", type=float, default=1.0)
    parser.add_argument(
        "--gains",
        nargs=3,
        type=float,
        metavar=("KP", "KI", "KD"),
        help="Three gains you have verified in Rho4",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run simulated reply/failure checks without hardware",
    )
    parser.add_argument(
        "--unplug-test",
        action="store_true",
        help="Include an interactive cable-disconnection check",
    )
    args = parser.parse_args()

    if args.simulate:
        check_simulated_replies()
        return 0

    if args.unplug_test and not args.port:
        parser.error("--unplug-test requires --port")

    print("Available ports:", IlMatto.list_ports())

    if not args.port:
        print("Use --port followed by your cable's port for board checks.")
        return 0

    board = IlMatto()
    verified_board = False
    failed = False

    try:
        assert board.is_connected() is False

        board.connect(args.port)
        assert board.is_connected() is True

        reply = board.send_command("PING")
        assert reply == "OK PONG RHO4/1", reply
        verified_board = True
        print("PASS - connected and PING received")

        assert board.send_command("STREAM 0") == "OK STREAM ms=0"
        board.set_mode("OFF")

        print("Initial status:", board.send_command("STATUS"))

        if args.gains is not None:
            board.set_pid_gains(*args.gains)
            print("PASS - PID gains command accepted:", args.gains)
            print("Check reported gains:", board.send_command("STATUS"))
        else:
            print("SKIPPED - valid gain update; use --gains KP KI KD")

        board.set_voltage(args.voltage)
        board.set_mode("PID")
        print(f"Requested target: {args.voltage:.3f} V")

        time.sleep(1.0)

        for _ in range(5):
            voltage = board.read_voltage()
            assert isinstance(voltage, float)
            print(f"Measured: {voltage:.3f} V")
            time.sleep(0.5)

        print("Compare the measurements with your meter or oscilloscope.")

        check_errors(board)

        if args.unplug_test:
            check_unplugging(board, args.port)

    except (IlMattoError, ValueError, AssertionError, NotImplementedError) as exc:
        failed = True
        print(f"FAILED - {type(exc).__name__}: {exc}")

    finally:
        # Attempt OFF separately so a failed stop cannot prevent closing.
        if verified_board and board.is_connected():
            try:
                board.set_mode("OFF")
                print("Output switched OFF")
            except IlMattoError as exc:
                failed = True
                print("Could not confirm output OFF:", exc)

        try:
            board.disconnect()
            assert board.is_connected() is False
            board.disconnect()
            print("PASS - disconnected; closing twice is harmless")
        except (IlMattoError, AssertionError, NotImplementedError) as exc:
            failed = True
            print("FAILED - connection cleanup:", exc)

    if not failed:
        print("Selected board checks passed.")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())