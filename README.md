# Rho5 section 3.1 starter

This is deliberately unfinished. Complete the TODOs in ilmatto.py and the manual
checks in test_ilmatto.py. There are no GUIs yet. The module targets the main
firmware in the supplied Rho4-Dac-Windows.zip, not its peripheral smoke example.

## Set up Git first

If your course provides a repository, clone that repository and put these files
in a rho5 subfolder. If you already have a shared Rho4 repository, use a rho5
subfolder there instead. Keep the existing history; do not run git init inside it.

Otherwise create a private, empty repository called rho5 on GitHub (or your course
Git server), and give your partner access. For an empty repository, do not select
an initial README, .gitignore or licence. Download/extract this starter, then put
its five files, including .gitignore, in your local project folder.

Run the following in ordinary Windows CMD, replacing the path and identity:

```bat
cd /d "C:\path\to\rho5"
git --version
git init -b main
git config user.name "Your Name"
git config user.email "your-university-email"
git add .
git status
git commit -m "Add section 3.1 module skeleton"
git remote add origin https://github.com/YOUR_USERNAME/rho5.git
git push -u origin main
```

Use the actual remote URL shown by your Git host. Sign in when Git asks. The
identity settings above apply to this repository, useful on a shared lab PC.
Your partner clones the same remote, rather than creating another repository:

```bat
git clone https://github.com/YOUR_USERNAME/rho5.git
cd rho5
```

At the start of each work session, with a clean working tree:

```bat
git pull --ff-only
```

After finishing a small change:

```bat
git diff
git add ilmatto.py test_ilmatto.py
git commit -m "Describe the part you completed"
git push
```

Agree on function names/return values with your partner before splitting tasks.
For now, one person can implement the module while the other builds a GUI layout.
If push is rejected because your partner pushed first, fetch/pull and reconcile
the changes; do not force-push over their work.

## Python setup on Windows

Use ordinary CMD for these commands. Keep firmware build/flash commands in the
university AVR toolchain DOS shell, where the AVR tools are configured.

```bat
cd /d "C:\path\to\rho5"
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m serial.tools.list_ports
python test_ilmatto.py
```

If the Python launcher `py` is missing, use `python -m venv .venv` with your
installed Python 3. Change PORT in test_ilmatto.py before using the board.
The first run reports NotImplementedError until you complete send_command().
Close PuTTY first. Only one program can own the COM port. Every collaborator
creates their own .venv; Git ignores it. Install Streamlit when starting 3.3.

## What section 3.1 requires

One Python class owns port discovery, connect/close/status, command/reply handling,
numeric voltage reads, setpoints and PID gain updates. Both future GUIs import
this class and never use serial directly. Keep the existing 4 ms PID loop on the
Il Matto so GUI timing and Windows scheduling do not control feedback timing.

| Public operation | Result / firmware exchange |
| --- | --- |
| IlMatto.list_ports() | list[str] of available device names |
| board.connect("COM3") | None; open 9600 8N1; PING, STREAM 0, STATUS |
| board.is_connected | bool property; local port state, not a live cable check |
| board.close() | None; release the port, may be called repeatedly |
| board.send_command(command, expected_reply) | Full matching OK line as str |
| board.read_voltage() | READ -> OK READ v=2.497 -> float 2.497 |
| board.set_voltage(2.5) | SET 2.500 -> OK SET sp=2.500; returns None |
| board.set_pid_gains(kp, ki, kd) | GAINS kp ki kd -> OK GAINS; returns None |
| board.set_mode("PID") | MODE PID -> OK MODE mode=PID; returns None |
| board.set_mode("OFF") | MODE OFF -> OK MODE mode=OFF; returns None |

SET changes only the target. MODE PID enables it; subsequent SET commands adjust
the running target. close() only releases the port: it does not stop the output.
The manual script requests MODE OFF before closing when communication still works.
An unplug or communication failure means an OFF command cannot be confirmed.

Limits from the uploaded firmware: target 0..3.3 V, Kp 0..1000, Ki 0..10000,
Kd 0..100. If you change Config.hpp, update the Python voltage limit too. A legal
target can still be unreachable under load. Gains must come from your own tuning.

## Complete the TODOs in this order

1. send_command(): send one ASCII command with LF, wait for a complete matching
   reply, skip READY/DATA and handle errors. Use a total deadline so continuous
   telemetry cannot keep you waiting forever. Store partial lines in self._rx.
   A finite serial read timeout may return only part of a line.
2. Check PING, connect(), is_connected and close() from test_ilmatto.py.
3. read_voltage(): extract the v= field and convert it to a finite float. Check
   against a measurement. Never substitute zero for a timeout or malformed reply.
4. set_voltage(): validate before sending SET; then explicitly enable MODE PID
   in the test script and allow settling before reading back.
5. set_pid_gains(): validate all three gains before sending GAINS.
6. Complete the manual checks for every method and the failure cases in the script.

Use ValueError for invalid user inputs, ConnectionError for unavailable/lost
connections, TimeoutError for a missing reply, and RuntimeError for ERR or invalid
replies. Catch these at the GUI boundary later and display a useful message.
The starter currently lets pySerial report an open failure; translating that to
ConnectionError consistently in connect() is another small improvement to make.

For reply matching, treat expected_reply ending in a space as a field-bearing
prefix (e.g. OK READ ); otherwise require an exact line. Check ERR before matching
OK. Reject embedded CR/LF so one request cannot send multiple commands.
Only one exchange may run at a time. When adding GUIs, keep serial waits off the
Tkinter main thread and use one serial worker, or protect complete exchanges with
a lock if multiple callers can access the same object. Scheduling with after()
alone does not make blocking serial I/O asynchronous.

## Before moving to 3.2

You should be able to set and read a voltage, change gains, close/reopen, and
report bad input, missing ports, unplugging and missing replies using only the
console script. Record actual readings and errors in your logbook. Confirm the
type returned by read_voltage() is float and that errors do not terminate the
whole interactive application unexpectedly. A syntax check is not a board test.

## Sources / assistance

- Supplied Rho5 - Mini GUI Project.pdf, pp. 5-6, especially section 3.1.
- Supplied Rho4-Dac-Windows.zip: docs/PROTOCOL.md and Headers/Config.hpp.
- https://pyserial.readthedocs.io/en/latest/pyserial_api.html
- https://git-scm.com/book/en/v2/Git-Basics-Getting-a-Git-Repository

The lab asks you to record AI prompts in your logbook and understand each line.
Record the prompt used to obtain this starter and your own changes/results.
