"""Manual board check, not an automated test. Complete ilmatto.py first."""

import time
import serial
from ilmatto import IlMatto

PORT = "COM3"  # Change this to the cable's port in Device Manager.

board = IlMatto()
try:
    print("Available ports:", board.list_ports())
    print("Connected before opening:", board.is_connected)
    board.connect(PORT)
    print("Connected after handshake:", board.is_connected)
    print("Ping:", board.send_command("PING", "OK PONG RHO4/1"))
    board.set_mode("OFF")
    print("Measured voltage:", board.read_voltage(), "V")

    # TODO: Call set_pid_gains() with your own gains tested in Rho4.
    # Then set_voltage(1.0), set_mode('PID'), wait for your circuit to settle,
    # and print read_voltage() plus its type. It should be a float.
    # time.sleep() is fine in this console check; keep it out of a GUI callback.
    # Compare the returned voltage with the actual output on your instruments.

    # TODO: Try set_voltage('abc'), -0.1, 3.4, float('nan') and float('inf').
    # Catch ValueError for EACH case so the next test still runs.
    # Try invalid gains too. Invalid input must send nothing to the board.
    # Send an unknown command and check that RuntimeError contains its ERR reply.
    # In separate runs: try a missing port, then unplug during read_voltage().
    # Check errors are reported and the port is released; reconnect before reuse.
    # Test a missing reply with a suitable test device/fake serial connection.
    # Confirm it raises TimeoutError rather than waiting forever.
except (ConnectionError, TimeoutError, RuntimeError, ValueError,
        serial.SerialException, OSError, NotImplementedError) as error:
    print(f"{type(error).__name__}: {error}")
finally:
    try:
        if board.is_connected:
            board.set_mode("OFF")
    except (ConnectionError, TimeoutError, RuntimeError, serial.SerialException,
            OSError, NotImplementedError) as error:
        print("Could not confirm MODE OFF:", error)
    finally:
        board.close()
    print("Connected after closing:", board.is_connected)
