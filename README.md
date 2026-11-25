# Rho5 — Section 3.1 skeleton

Build one Python class that controls your Il Matto and can later be imported by
both GUIs. This starter deliberately leaves the implementation for you, with
numbered TODOs and hints. It contains no GUI code or Git-related files.

## Files

| File | Purpose |
| --- | --- |
| `ilmatto.py` | Your reusable class; all serial communication belongs here |
| `test_ilmatto.py` | Console checks that import and exercise the class |
| `requirements.txt` | The dependency for section 3.1 |
| `README.md` | Setup, protocol reference and TODO order |

## Set up on Windows

Use Python 3.9 or newer. Extract this folder and open a terminal inside it.

```bat
python -m pip install -r requirements.txt
```

If Windows uses `py` for Python, replace `python` with `py` in these commands.
Close PuTTY before opening the port in Python. Find your C232HM cable's COM port
in Device Manager. Streamlit and Tkinter are not needed for this section.

## Confirm your firmware first

These details come from the project's uploaded `Rho4-Dac-Windows.zip`, especially
`docs/PROTOCOL.md`, `Headers/Config.hpp` and `Source/main.cpp`. Check that they match
the firmware actually flashed onto your board. If you changed Rho4, update these
hints to match it before completing the methods.

- Serial: 9600 baud, 8N1, no flow control; ASCII commands ending in `\n`.
- Replies end in CR/LF. Allow a 1 second reply timeout for these commands.
- Setpoint range in the uploaded configuration: 0 to 3.3 V.
- Keep the PID calculation on the board. Python sends gains and setpoints.
- `SET` changes the target. `MODE PID` enables control; `MODE OFF` stops output.
- A measured voltage from `READ` is different from the requested setpoint.

| Operation | Command | Expected example reply |
| --- | --- | --- |
| Confirm board | `PING` | `OK PONG RHO4/1` |
| Disable streaming | `STREAM 0` | `OK STREAM ms=0` |
| Read measured voltage | `READ` | `OK READ v=2.497` |
| Change target | `SET 1.0` | `OK SET sp=1.000` |
| Change gains | `GAINS 120 800 0` | `OK GAINS` |
| Enable controller | `MODE PID` | `OK MODE mode=PID` |
| Stop output | `MODE OFF` | `OK MODE mode=OFF` |
| Inspect state/gains | `STATUS` | `OK STATUS t=... sp=... v=...` |

The gain values above illustrate syntax; use gains you verified in Rho4.
Limits in the uploaded firmware: Kp 0..1000, Ki 0..10000, Kd 0..100.

## Complete the TODOs in order

| TODO | Location | What you implement | How to check it |
| --- | --- | --- | --- |
| 1 | `list_ports()` | Return a list of port names | Run the script without arguments |
| 2 | `is_connected()` | Check the stored serial handle | New instance returns False |
| 3 | `connect()` | Open a port; translate open failures | Correct port opens; wrong port reports an error |
| 4 | `disconnect()` | Close and clear state | Close twice; both should be harmless |
| 5a–c | `send_command()` | Encode, write, receive complete replies and handle failures | PING returns its expected reply |
| 6 | `read_voltage()` | Parse a READ reply into a finite float | Compare the result with the meter/scope |
| 7 | `set_voltage()` | Validate range and send SET | STATUS reports your target |
| 8 | `set_pid_gains()` | Validate all gains and send GAINS | STATUS reports your gains |
| 9 | `set_mode()` | Validate mode and send MODE | PID enables output; OFF stops it |
| 10 | `test_ilmatto.py` | Add negative/error checks | Record valid errors and recovery |

For each method, replace its `raise NotImplementedError(...)` with your code.
Keep the function names and return types agreed with your partner.
The imports `math`, `time`, `serial` and `list_ports` are provided for your TODOs.

### Start with TODO 1

1. Call `list_ports.comports()` to get port-information objects.
2. Create an empty list.
3. Loop over those objects and append each object's `.device`.
4. Return the list.

Then run:

```bat
python test_ilmatto.py
```

You should see a list such as `['COM3']`. An empty list is a valid result if no
ports are available. Before TODO 1 is complete, the script prints a skeleton
checkpoint and exits with a nonzero status; this is expected.

After TODOs 1–9, run the hardware checks, replacing COM3 with your actual port:

```bat
python test_ilmatto.py --port COM3 --voltage 1.0
```

The script sends a target, enables PID, waits briefly, reads voltage, then attempts
to stop output and disconnect. Without `--gains` it leaves gains as configured
and reports the gains check as skipped. To exercise `set_pid_gains()`, repeat
with your three known Rho4 gains:

```text
python test_ilmatto.py --port COM3 --voltage 1.0 --gains YOUR_KP YOUR_KI YOUR_KD
```

Replace all three placeholders with numbers. Do not assume the section is done
until you have exercised every method, including gains and the TODO 10 checks.
The provided script is a starting point, not evidence that your board works.

## Error behaviour to aim for

Use `ValueError` for invalid user input and `IlMattoError` for board/communication
problems. The test script and later GUIs catch these and display useful messages.
Do not silently turn a missing reply into a voltage of zero.

Give reads and writes finite timeouts. Assemble partial serial reads until a
whole line arrives. Ignore startup `READY` and streaming `DATA` lines while
waiting for a reply, using one overall deadline. Check the expected acknowledgement
in each high-level method. On a transport failure or timeout, close/clear the
connection and report the error; reconnect and PING before further commands.

An open handle only describes local port state. It does not guarantee the board
is present or replying. Closing the serial port does not switch the board off.
Later GUI callbacks should serialize access to this object and allow for the
bounded waiting involved in a serial transaction.

## Logbook and references

Record the class interface, confirmed command/reply examples, PID-location
decision, test results and who completed each part. The lab handout requires you
to record AI prompts and understand your code line by line. It also includes an
optional decoding puzzle in section 3.1; a prompt is left in the module.

- Rho5 lab handout, section 3.1, page 6; preparation sections 2.3–2.4.
- Uploaded Rho4 firmware: `docs/PROTOCOL.md` and `Headers/Config.hpp`.
- [pySerial API](https://pyserial.readthedocs.io/en/latest/pyserial_api.html)
- [Port discovery](https://pyserial.readthedocs.io/en/latest/tools.html#serial-tools-list-ports)

Package validation only checks syntax and skeleton entry points. Actual serial
communication must be checked on your own Il Matto after implementing the TODOs.
