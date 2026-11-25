"""Manual section 3.1 check script. No GUI or direct serial calls here.

Run without arguments after TODO 1. Full board checks need TODOs 1-9.
This is an interactive hardware check, not a pytest test suite.
"""

import argparse
import time

from ilmatto import IlMatto, IlMattoError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Your board's port, for example COM3")
    parser.add_argument("--voltage", type=float, default=1.0, help="Test target in V")
    parser.add_argument("--gains", nargs=3, type=float, metavar=("KP", "KI", "KD"),
                        help="Optional: use gains you have already checked in Rho4")
    args = parser.parse_args()

    try:
        print("Available ports:", IlMatto.list_ports())
    except NotImplementedError as exc:
        print("Skeleton checkpoint:", exc)
        return 1

    if not args.port:
        print("Port listing finished. Complete the remaining methods before")
        print("running: python test_ilmatto.py --port COM3")
        return 0

    board = IlMatto()
    verified_board = False
    failed = False
    try:
        assert board.is_connected() is False, "New instance should be disconnected"
        board.connect(args.port)
        assert board.is_connected() is True, "Port did not open"
        reply = board.send_command("PING")
        assert reply == "OK PONG RHO4/1", f"Unexpected handshake: {reply!r}"
        verified_board = True
        assert board.send_command("STREAM 0") == "OK STREAM ms=0"
        print("Status:", board.send_command("STATUS"))
        board.set_mode("OFF")

        if args.gains:
            board.set_pid_gains(*args.gains)
            print("PID gains updated:", args.gains)
        else:
            print("Gains check skipped. Repeat with --gains KP KI KD to test it.")

        print("Initial measurement:", board.read_voltage(), "V")
        board.set_voltage(args.voltage)
        board.set_mode("PID")
        time.sleep(1.0)  # Bench check only: allow the output time to settle.
        measured = board.read_voltage()
        assert isinstance(measured, float), "read_voltage() must return a float"
        print(f"Target: {args.voltage:.3f} V; measured: {measured:.3f} V")
        print("Compare this reading with your meter/scope and record the result.")

        # TODO 10: Add failure checks after the normal exchange works.
        # a) set_voltage('abc'), -0.1, max_voltage + 0.1, NaN and infinity:
        #    catch ValueError and report PASS; no serial write should occur.
        # b) Invalid/nonfinite/out-of-range gains and an invalid mode:
        #    expect ValueError. Confirm an invalid setting leaves STATUS unchanged.
        # c) Send an unknown command: catch IlMattoError from the ERR reply.
        # d) Separately try an unused port, disconnected read, unplugged cable,
        #    and a nonresponding board. Expect a useful error and bounded wait.
        #    Reconnect before continuing after a transport failure.
        # e) Feed partial/malformed/READY/DATA replies using a small fake serial
        #    object if available; confirm only a complete valid reply is accepted.
        # Do not put intentional unplug tests in the middle of normal checks.

    except (IlMattoError, ValueError, NotImplementedError, AssertionError) as exc:
        failed = True
        print(f"Check stopped: {type(exc).__name__}: {exc}")
    finally:
        # Attempt output stop independently from closing so a failed stop does
        # not prevent releasing the port. The board can keep running if unplugged.
        if verified_board:
            try:
                board.set_mode("OFF")
            except (IlMattoError, NotImplementedError) as exc:
                failed = True
                print("Could not confirm output OFF:", exc)
        try:
            board.disconnect()
            assert board.is_connected() is False
            board.disconnect()  # Closing twice should work.
        except (IlMattoError, NotImplementedError, AssertionError) as exc:
            failed = True
            print("Connection cleanup check failed:", exc)

    if not failed:
        print("Implemented normal checks passed; complete TODO 10 separately.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
