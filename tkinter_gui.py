"""Rho5 light-mode control panel. Run with: python3 tkinter_gui.py

Keep ilmatto.py in the same directory. All board communication goes through it.
Send voltage enables PID output. Start/Stop only controls voltage monitoring.
"""

import math
import queue
import threading
import time
import tkinter as tk
from collections import deque
from tkinter import messagebox, ttk

from ilmatto import IlMatto


class BoardWorker(threading.Thread):
    """Own the IlMatto object and execute one serial operation at a time.

    Queues carry ordinary Python data. Only the main thread touches Tk widgets.
    """

    def __init__(self, board=None):
        super().__init__(daemon=True)
        self.board = board if board is not None else IlMatto()
        self.requests = queue.Queue()
        self.results = queue.Queue()

    def run(self):
        while True:
            action, args = self.requests.get()
            value, error = None, None
            try:
                if action == "ports":
                    value = self.board.list_ports()
                elif action == "connect":
                    try:
                        self.board.connect(args[0])
                        if self.board.send_command("PING") != "OK PONG RHO4/1":
                            raise ValueError("The selected port did not identify as the Rho4 board.")
                    except Exception:
                        self.board.disconnect()
                        raise
                    value = args[0]
                elif action in ("disconnect", "close"):
                    self.board.disconnect()
                elif action == "read":
                    voltage = self.board.read_voltage()
                    if not math.isfinite(voltage):
                        raise ValueError("The board returned an invalid voltage.")
                    value = (time.monotonic(), voltage)
                elif action == "voltage":
                    self.board.set_voltage(args[0])
                    self.board.set_mode("PID")
                    value = args[0]
                elif action == "gains":
                    self.board.set_pid_gains(*args)
                    value = args
                else:
                    raise ValueError(f"Unknown operation: {action}")
            except Exception as exc:
                # Return failures to the GUI; do not let the worker silently die.
                error = str(exc) or type(exc).__name__
            self.results.put((action, value, error, self.board.is_connected()))
            if action == "close":
                return


class ControlPanel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rho5 | Il Matto Control")
        self.geometry("1100x780")
        self.minsize(900, 760)
        self.configure(bg="#f3f6fa")
        self.samples = deque(maxlen=10000)
        self.time_window = tk.DoubleVar(value=10)
        self.voltage_range = tk.DoubleVar(value=5)
        self.port = tk.StringVar()
        self.connection = tk.StringVar(value="Disconnected")
        self.reading = tk.StringVar(value="— V")
        self.voltage = tk.StringVar()
        self.gains = [tk.StringVar() for _ in range(3)]
        self.message = tk.StringVar(value="Select your board's port and click Connect.")
        self.worker = BoardWorker()
        self.connected = False
        self.connected_port = ""
        self.running = False
        self.busy = False
        self.pending_actions = []
        self.closing = False
        self.next_read = 0.0
        self._style()
        self._layout()
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.worker.start()
        self.refresh_ports()
        self.after(50, self._poll_worker)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f6fa")
        style.configure("TLabel", background="#f3f6fa", foreground="#25344a",
                        font=("Helvetica", 11))
        style.configure("Title.TLabel", font=("Helvetica", 19, "bold"))
        style.configure("Reading.TLabel", foreground="#1764cf", font=("Helvetica", 23, "bold"))
        style.configure("TLabelframe", background="#f3f6fa", bordercolor="#d4dce8")
        style.configure("TLabelframe.Label", background="#f3f6fa", foreground="#25344a",
                        font=("Helvetica", 12, "bold"))
        style.configure("TButton", padding=(12, 8), font=("Helvetica", 11))
        style.configure("TEntry", fieldbackground="white", foreground="#25344a", padding=6)
        style.configure("TCombobox", fieldbackground="white", foreground="#25344a", padding=5)
        style.map("TCombobox", fieldbackground=[("readonly", "white")],
                  foreground=[("readonly", "#25344a")])

    def _layout(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        ttk.Label(self, text="Il Matto Control Panel", style="Title.TLabel").grid(
            row=0, column=0, sticky="w", padx=24, pady=(20, 15))
        body = ttk.Frame(self, padding=(24, 0, 24, 12))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, minsize=300)
        body.rowconfigure(0, weight=1)

        scope = ttk.LabelFrame(body, text="Voltage monitor", padding=12)
        scope.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        scope.columnconfigure(1, weight=1)
        scope.rowconfigure(1, weight=1)
        ttk.Label(scope, text="Measured voltage").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(scope, textvariable=self.reading, style="Reading.TLabel").grid(
            row=0, column=1, sticky="e", pady=(0, 14))

        vertical = ttk.Frame(scope)
        vertical.grid(row=1, column=0, sticky="ns", padx=(0, 8))
        vertical.rowconfigure(1, weight=1)
        self.range_label = ttk.Label(vertical, text="0–4.0 V")
        self.range_label.grid(row=0, column=0)
        ttk.Scale(vertical, orient="vertical", from_=4.0, to=0,
                  variable=self.voltage_range, command=self._scale_changed).grid(
                      row=1, column=0, sticky="ns", pady=8)
        ttk.Label(vertical, text="Range").grid(row=2, column=0)
        self.canvas = tk.Canvas(scope, bg="white", highlightthickness=1,
                                highlightbackground="#d4dce8")
        self.canvas.grid(row=1, column=1, sticky="nsew")
        self.canvas.bind("<Configure>", lambda event: self.draw_plot())

        horizontal = ttk.Frame(scope)
        horizontal.grid(row=2, column=1, sticky="ew", pady=(12, 0))
        horizontal.columnconfigure(0, weight=1)
        self.time_label = ttk.Label(horizontal, text="Time window: 10 s")
        self.time_label.grid(row=0, column=0, sticky="w")
        ttk.Scale(horizontal, from_=1, to=60, orient="horizontal",
                  variable=self.time_window, command=self._scale_changed).grid(
                      row=1, column=0, sticky="ew", pady=(5, 0))

        controls = ttk.Frame(body)
        controls.grid(row=0, column=1, sticky="nsew")
        controls.columnconfigure(0, weight=1)
        connection = self._section(controls, "Connection", 0)
        ttk.Label(connection, textvariable=self.connection, wraplength=260).grid(
            row=0, column=0, sticky="w", pady=(0, 10))
        self.port_dropdown = ttk.Combobox(connection, textvariable=self.port, state="readonly")
        self.port_dropdown.grid(row=1, column=0, sticky="ew")
        self.refresh_button = ttk.Button(connection, text="Refresh ports", command=self.refresh_ports)
        self.refresh_button.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.connect_button = ttk.Button(connection, text="Connect", command=self.toggle_connection)
        self.connect_button.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        voltage = self._section(controls, "Set voltage", 1)
        ttk.Label(voltage, text="Target voltage (0–3.3 V)").grid(row=0, column=0, sticky="w")
        ttk.Entry(voltage, textvariable=self.voltage).grid(row=1, column=0, sticky="ew", pady=7)
        self.voltage_button = ttk.Button(voltage, text="Send voltage", command=self.send_voltage)
        self.voltage_button.grid(row=2, column=0, sticky="ew")
        ttk.Label(voltage, text="Sending enables PID output.").grid(
            row=3, column=0, sticky="w", pady=(7, 0))

        pid = self._section(controls, "PID gains", 2)
        inputs = ttk.Frame(pid)
        inputs.grid(row=0, column=0, sticky="ew")
        for column, (name, variable) in enumerate(zip(("Kp", "Ki", "Kd"), self.gains)):
            inputs.columnconfigure(column, weight=1)
            ttk.Label(inputs, text=name).grid(row=0, column=column, sticky="w", padx=3)
            ttk.Entry(inputs, textvariable=variable, width=7).grid(
                row=1, column=column, sticky="ew", padx=3, pady=(4, 8))
        ttk.Label(pid, text="Blank gain = 0").grid(row=1, column=0, sticky="w", pady=(0, 8))
        self.gains_button = ttk.Button(pid, text="Send gains", command=self.send_gains)
        self.gains_button.grid(row=2, column=0, sticky="ew")

        acquisition = self._section(controls, "Acquisition", 3)
        self.start_button = ttk.Button(acquisition, text="Start", command=self.toggle_acquisition)
        self.start_button.grid(row=0, column=0, sticky="ew")
        ttk.Label(acquisition, text="Pauses readings; output stays active.", wraplength=260).grid(
            row=1, column=0, sticky="w", pady=(7, 0))
        ttk.Label(self, textvariable=self.message, wraplength=1000).grid(
            row=2, column=0, sticky="w", padx=24, pady=(0, 12))

    @staticmethod
    def _section(parent, title, row):
        frame = ttk.LabelFrame(parent, text=title, padding=12)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        frame.columnconfigure(0, weight=1)
        return frame

    def _scale_changed(self, _value):
        self.range_label.configure(text=f"0–{self.voltage_range.get():.1f} V")
        self.time_label.configure(text=f"Time window: {self.time_window.get():.1f} s")
        self.draw_plot()

    def draw_plot(self):
        """Redraw axes and any real samples supplied by append_sample()."""
        c = self.canvas
        c.delete("all")
        left, top = 47, 18
        right, bottom = c.winfo_width() - 16, c.winfo_height() - 37
        if right <= left or bottom <= top:
            return
        window, upper = self.time_window.get(), self.voltage_range.get()
        for step in range(6):
            fraction = step / 5
            y = bottom - fraction * (bottom - top)
            x = left + fraction * (right - left)
            c.create_line(left, y, right, y, fill="#e7edf5")
            c.create_line(x, top, x, bottom, fill="#e7edf5")
            c.create_text(left - 8, y, text=f"{fraction * upper:.1f}", anchor="e", fill="#62748b")
            c.create_text(x, bottom + 15, text=f"{(fraction - 1) * window:.1f}", fill="#62748b")
        c.create_text((left + right) / 2, bottom + 31, text="Time relative to latest sample (s)",
                      fill="#62748b")
        if not self.samples:
            c.create_text((left + right) / 2, (top + bottom) / 2,
                          text="Waiting for voltage readings", fill="#62748b")
            return
        latest = self.samples[-1][0]
        points = []
        for timestamp, voltage in self.samples:
            age = timestamp - latest
            if -window <= age <= 0:
                x = left + (1 + age / window) * (right - left)
                if 0 <= voltage <= upper:
                    y = bottom - voltage / upper * (bottom - top)
                    points.extend((x, y))
                else:
                    # Avoid displaying out-of-range values as a flat trace at the limit.
                    if len(points) >= 4:
                        c.create_line(*points, fill="#2473df", width=2)
                    points = []
        if len(points) >= 4:
            c.create_line(*points, fill="#2473df", width=2)

    def append_sample(self, timestamp, voltage):
        """Call on Tk's main thread with a monotonic timestamp and measured volts."""
        if not math.isfinite(timestamp) or not math.isfinite(voltage):
            raise ValueError("Samples must contain finite numbers")
        self.samples.append((timestamp, voltage))
        self.reading.set(f"{voltage:.3f} V")
        self.draw_plot()

    def refresh_ports(self):
        self._submit("ports")

    def toggle_connection(self):
        if (self.busy and self.pending_actions != ["read"]) or self.closing:
            return
        if self.connected:
            self.running = False
            self._submit("disconnect")
        elif self.port.get():
            self._submit("connect", self.port.get())
        else:
            self.message.set("Select a port first. Use Refresh ports after plugging in the cable.")

    def _submit(self, action, *args):
        if self.closing or (self.busy and (action == "read" or self.pending_actions != ["read"])):
            return
        self.pending_actions.append(action)
        self.busy = True
        self.worker.requests.put((action, args))
        if action != "read":
            self.message.set({"ports": "Checking available ports…",
                              "connect": "Connecting and checking board response…",
                              "disconnect": "Disconnecting…",
                              "voltage": "Sending voltage and enabling PID output…",
                              "gains": "Sending PID gains…"}[action])
        self._update_controls()

    def _update_controls(self):
        idle = (not self.busy or self.pending_actions == ["read"]) and not self.closing
        self.refresh_button.configure(state="normal" if idle else "disabled")
        self.port_dropdown.configure(state="readonly" if idle and not self.connected else "disabled")
        self.connect_button.configure(text="Disconnect" if self.connected else "Connect",
                                      state="normal" if idle else "disabled")
        for button in (self.voltage_button, self.gains_button):
            button.configure(state="normal" if idle and self.connected else "disabled")
        # Stop can be clicked even while a voltage read is waiting for its reply.
        self.start_button.configure(text="Stop" if self.running else "Start",
                                    state="normal" if self.connected and not self.closing else "disabled")

    def _poll_worker(self):
        try:
            while True:
                action, value, error, connected = self.worker.results.get_nowait()
                if action == "close":
                    self.destroy()
                    return
                self.pending_actions.pop(0)
                self.busy = bool(self.pending_actions)
                self.connected = connected
                if self.closing:
                    continue
                if not connected:
                    self.running = False
                    self.connected_port = ""
                    self.connection.set("Disconnected")
                if error:
                    if action == "read":
                        self.running = False
                    self.message.set(f"{action.capitalize()} failed: {error}")
                elif action == "ports":
                    self.port_dropdown.configure(values=value)
                    if self.port.get() not in value and not self.connected:
                        self.port.set(value[0] if value else "")
                    self.message.set("Ports refreshed." if self.connected else
                                     "Select a port and connect." if value else
                                     "No serial ports found. Plug in the cable and refresh.")
                elif action == "connect":
                    self.connected_port = value
                    self.connection.set(f"Connected: {value}")
                    self.samples.clear()
                    self.reading.set("— V")
                    self.draw_plot()
                    self.message.set("Connected. Click Start to monitor voltage.")
                elif action == "disconnect":
                    self.message.set("Disconnected. Last trace retained.")
                elif action == "read":
                    if self.running:
                        self.append_sample(*value)
                elif action == "voltage":
                    self.message.set(f"Setpoint confirmed: {value:.3f} V. PID output enabled.")
                elif action == "gains":
                    kp, ki, kd = value
                    self.message.set(f"Gains confirmed: Kp={kp:g}, Ki={ki:g}, Kd={kd:g}.")
                self._update_controls()
        except queue.Empty:
            pass
        if self.running and not self.busy and time.monotonic() >= self.next_read:
            self.next_read = time.monotonic() + 0.001
            self._submit("read")
        self.after(50, self._poll_worker)

    @staticmethod
    def _number(text, blank_is_zero=False):
        value = float((text.strip() or "0") if blank_is_zero else text.strip())
        if not math.isfinite(value):
            raise ValueError("Enter a finite number")
        return value

    def send_voltage(self):
        if (self.busy and self.pending_actions != ["read"]) or not self.connected or self.closing:
            return
        try:
            target = self._number(self.voltage.get())
            if not 0 <= target <= 3.3:
                raise ValueError("Voltage outside the board's range")
        except ValueError:
            messagebox.showerror("Invalid voltage", "Enter a voltage between 0 and 3.3 V.")
            return
        self._submit("voltage", target)

    def send_gains(self):
        if (self.busy and self.pending_actions != ["read"]) or not self.connected or self.closing:
            return
        try:
            kp, ki, kd = [self._number(v.get(), blank_is_zero=True) for v in self.gains]
        except ValueError:
            messagebox.showerror("Invalid gain", "Enter numbers for gains, or leave them blank for 0.")
            return
        self._submit("gains", kp, ki, kd)

    def toggle_acquisition(self):
        if not self.connected or self.closing:
            return
        self.running = not self.running
        self.next_read = 0.0
        if self.running:
            # Leave a gap across a pause instead of drawing a fabricated line.
            if self.samples:
                self.samples.append((time.monotonic(), float("nan")))
            self.message.set("Monitoring voltage (requests up to 10 times per second).")
        else:
            self.message.set("Readings paused. Board output unchanged.")
        self._update_controls()

    def close_window(self):
        if self.closing:
            return
        self.closing = True
        self.running = False
        self.message.set("Closing connection…")
        self._update_controls()
        # This runs after any in-flight command; Tk stays responsive while waiting.
        self.worker.requests.put(("close", ()))


if __name__ == "__main__":
    ControlPanel().mainloop()