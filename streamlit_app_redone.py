"""Rho5 Streamlit control panel.

Run with:
    streamlit run streamlit_app.py

Keep ilmatto.py in the same directory. All board communication goes through
the IlMatto module; this GUI does not use pyserial directly.
"""

import math
import threading
import time

import altair as alt
import pandas as pd
import streamlit as st

from ilmatto import IlMatto


# Streamlit reruns the script after interactions. Cache one IlMatto instance
# so that a new serial connection is not opened on every rerun.
@st.cache_resource
def get_board():
    return IlMatto()


# The fragment and the buttons may access the board close together. This lock
# makes sure that only one serial operation uses the connection at a time.
@st.cache_resource
def get_board_lock():
    return threading.RLock()


board = get_board()
board_lock = get_board_lock()


# ------------------------------- Page setup -------------------------------

st.set_page_config(page_title="ST_APP: Il Matto Control", layout="wide")
st.title("ST_APP: Il Matto Control Panel")
st.caption("Rho5 | Streamlit control panel")


# ------------------------------ Session state -----------------------------

def initialise_state():
    """Create the values that must survive Streamlit script reruns."""
    defaults = {
        "ports": [],
        "selected_port": None,
        "connected": False,
        "connected_port": "",
        "running": False,
        "samples": [],
        "reading": None,
        "message": "Select your board's port and click Connect.",
        "time_window": 10,
        "voltage_range": 4.0,
        "target_voltage": "2.5",
        "kp": "",
        "ki": "",
        "kd": "",
    }

    for name, value in defaults.items():
        if name not in st.session_state:
            st.session_state[name] = value


initialise_state()


# ------------------------------ Board actions -----------------------------

def refresh_ports():
    """Ask IlMatto for the available serial ports."""
    try:
        with board_lock:
            ports = board.list_ports()

        st.session_state.ports = ports

        if st.session_state.selected_port not in ports:
            st.session_state.selected_port = ports[0] if ports else None

        if ports:
            st.session_state.message = "Ports refreshed."
        else:
            st.session_state.message = (
                "No serial ports found. Plug in the cable and refresh."
            )
    except Exception as exc:
        st.session_state.message = f"Could not list ports: {exc}"


def connect_board():
    """Connect to the selected port and check that it is the Rho4 board."""
    port = st.session_state.selected_port

    if not port or port not in st.session_state.ports:
        st.session_state.message = "Select a valid port first."
        return

    try:
        with board_lock:
            board.connect(port)
            reply = board.send_command("PING")

            if reply != "OK PONG RHO4/1":
                board.disconnect()
                raise ValueError(
                    "The selected port did not identify as the Rho4 board."
                )

        st.session_state.connected = True
        st.session_state.connected_port = port
        st.session_state.running = False
        st.session_state.samples = []
        st.session_state.reading = None
        st.session_state.message = (
            f"Connected to {port}. Click Start to monitor voltage."
        )

    except Exception as exc:
        # If connection or the PING check fails, leave the port closed.
        try:
            with board_lock:
                board.disconnect()
        except Exception:
            pass

        st.session_state.connected = False
        st.session_state.connected_port = ""
        st.session_state.running = False
        st.session_state.message = f"Connection failed: {exc}"


def disconnect_board():
    """Stop monitoring and close the serial connection."""
    st.session_state.running = False

    try:
        with board_lock:
            board.disconnect()
        st.session_state.message = "Disconnected. Last trace retained."
    except Exception as exc:
        st.session_state.message = f"Disconnect failed: {exc}"

    st.session_state.connected = False
    st.session_state.connected_port = ""


def send_voltage():
    """Validate and send a voltage setpoint."""
    try:
        target = float(st.session_state.target_voltage.strip())

        if not math.isfinite(target) or not 0.0 <= target <= 3.3:
            raise ValueError

    except (AttributeError, TypeError, ValueError):
        st.session_state.message = (
            "Enter a valid voltage between 0 and 3.3 V."
        )
        return

    try:
        with board_lock:
            board.set_voltage(target)
            board.set_mode("PID")

        st.session_state.message = (
            f"Setpoint confirmed: {target:.3f} V. PID output enabled."
        )
    except Exception as exc:
        st.session_state.message = f"Could not set voltage: {exc}"
        try:
            with board_lock:
                st.session_state.connected = board.is_connected()
        except Exception:
            st.session_state.connected = False


def send_gains():
    """Read the three PID gain fields and send them to IlMatto."""
    try:
        gains = []

        for field in ("kp", "ki", "kd"):
            # An empty field means zero, matching the Tkinter GUI.
            value = float(st.session_state[field].strip() or "0")

            if not math.isfinite(value):
                raise ValueError

            gains.append(value)

    except (AttributeError, TypeError, ValueError):
        st.session_state.message = (
            "Enter valid numbers for Kp, Ki and Kd (blank means 0)."
        )
        return

    try:
        with board_lock:
            board.set_pid_gains(*gains)

        st.session_state.message = (
            f"Gains confirmed: Kp={gains[0]:g}, "
            f"Ki={gains[1]:g}, Kd={gains[2]:g}."
        )
    except Exception as exc:
        st.session_state.message = f"Could not send PID gains: {exc}"
        try:
            with board_lock:
                st.session_state.connected = board.is_connected()
        except Exception:
            st.session_state.connected = False


def toggle_acquisition():
    """Start or pause voltage readings without changing the board output."""
    if not st.session_state.connected:
        return

    st.session_state.running = not st.session_state.running

    if st.session_state.running:
        # Add a gap marker so the chart does not draw a line across a pause.
        if st.session_state.samples:
            st.session_state.samples.append((time.monotonic(), None))

        st.session_state.message = (
            "Monitoring voltage (requests up to 10 times per second)."
        )
    else:
        st.session_state.message = (
            "Readings paused. Board output unchanged."
        )


# ---------------------------- Voltage monitoring -------------------------

@st.fragment(run_every=0.1)
def voltage_monitor():
    """Update the measured voltage and chart without rerunning the controls."""
    if st.session_state.connected and st.session_state.running:
        try:
            with board_lock:
                voltage = float(board.read_voltage())

            if not math.isfinite(voltage):
                raise ValueError("The board returned an invalid voltage.")

            now = time.monotonic()
            st.session_state.samples.append((now, voltage))
            st.session_state.reading = voltage

            # Keep enough history for the maximum 60-second display window.
            cutoff = now - 65
            st.session_state.samples = [
                sample
                for sample in st.session_state.samples
                if sample[0] >= cutoff
            ]

        except Exception as exc:
            st.session_state.running = False
            st.session_state.message = f"Voltage read failed: {exc}"

            try:
                with board_lock:
                    st.session_state.connected = board.is_connected()
            except Exception:
                st.session_state.connected = False

            if not st.session_state.connected:
                st.session_state.connected_port = ""

    # Display the latest numerical measurement and acquisition state.
    measured_column, status_column = st.columns([2, 1])

    with measured_column:
        if st.session_state.reading is None:
            st.metric("Measured voltage", "— V")
        else:
            st.metric(
                "Measured voltage",
                f"{st.session_state.reading:.3f} V",
            )

    with status_column:
        st.write("**Acquisition**")
        st.write("Running" if st.session_state.running else "Paused")

    # Convert monotonic timestamps into seconds relative to the latest time.
    window = st.session_state.time_window
    upper = st.session_state.voltage_range
    now = time.monotonic()

    visible_samples = [
        (timestamp, voltage)
        for timestamp, voltage in st.session_state.samples
        if now - timestamp <= window
    ]

    if visible_samples:
        chart_data = pd.DataFrame(
            [
                {
                    "Time (s)": timestamp - now,
                    "Voltage (V)": voltage,
                }
                for timestamp, voltage in visible_samples
            ]
        )

        chart = (
            alt.Chart(chart_data)
            .mark_line(color="#2473df", strokeWidth=1)
            .encode(
                x=alt.X(
                    "Time (s):Q",
                    title="Time (s)",
                    scale=alt.Scale(domain=[-window, 0]),
                ),
                y=alt.Y(
                    "Voltage (V):Q",
                    title="Voltage (V)",
                    scale=alt.Scale(domain=[0, upper]),
                ),
            )
            .properties(height=660)
        )

        st.altair_chart(chart, use_container_width=True)
    else:
        st.info(
            "Waiting for voltage readings. Connect to the board and click Start."
        )


# -------------------------------- Main layout ------------------------------

monitor_column, controls_column = st.columns([2.1, 1], gap="large")


# Left-hand side: live voltage display, graph and graph controls.
with monitor_column:
    st.subheader("Voltage monitor")
    voltage_monitor()

    range_column, time_column = st.columns(2)

    with range_column:
        st.slider(
            "Voltage range (V)",
            min_value=0.0,
            max_value=4.0,
            step=0.01,
            key="voltage_range",
        )

    with time_column:
        st.slider(
            "Time window (seconds)",
            min_value=0.0,
            max_value=60.0,
            step=0.01,
            key="time_window",
        )


# Right-hand side: connection, setpoint, PID and acquisition controls.
with controls_column:
    st.subheader("Connection")

    if st.session_state.connected:
        st.success(f"Connected: {st.session_state.connected_port}")
    else:
        st.warning("Disconnected")

    if st.button("Refresh ports", use_container_width=True):
        refresh_ports()
        st.rerun()

    ports = st.session_state.ports

    if ports:
        if st.session_state.selected_port not in ports:
            st.session_state.selected_port = ports[0]

        selected_index = ports.index(st.session_state.selected_port)

        st.selectbox(
            "COM port",
            options=ports,
            index=selected_index,
            key="selected_port",
            disabled=st.session_state.connected,
        )
    else:
        st.selectbox(
            "COM port",
            options=["No ports found"],
            disabled=True,
        )

    if st.session_state.connected:
        if st.button("Disconnect", use_container_width=True):
            disconnect_board()
            st.rerun()
    else:
        if st.button(
            "Connect",
            use_container_width=True,
            disabled=not bool(ports),
        ):
            connect_board()
            st.rerun()

    st.divider()
    st.subheader("Set voltage")

    st.text_input(
        "Target voltage (0–3.3 V)",
        key="target_voltage",
        disabled=not st.session_state.connected,
    )
    st.caption("Sending enables PID output.")

    if st.button(
        "Send voltage",
        use_container_width=True,
        disabled=not st.session_state.connected,
    ):
        send_voltage()
        st.rerun()

    st.divider()
    st.subheader("PID gains")

    kp_column, ki_column, kd_column = st.columns(3)

    with kp_column:
        st.text_input(
            "Kp",
            key="kp",
            placeholder="0",
            disabled=not st.session_state.connected,
        )

    with ki_column:
        st.text_input(
            "Ki",
            key="ki",
            placeholder="0",
            disabled=not st.session_state.connected,
        )

    with kd_column:
        st.text_input(
            "Kd",
            key="kd",
            placeholder="0",
            disabled=not st.session_state.connected,
        )

    st.caption("Blank gain = 0")

    if st.button(
        "Send gains",
        use_container_width=True,
        disabled=not st.session_state.connected,
    ):
        send_gains()
        st.rerun()

    st.divider()
    st.subheader("Acquisition")

    if st.session_state.connected:
        button_label = "Stop" if st.session_state.running else "Start"

        if st.button(button_label, use_container_width=True):
            toggle_acquisition()
            st.rerun()
    else:
        st.button("Start", use_container_width=True, disabled=True)

    st.caption("Pauses readings; output stays active.")


# Message bar at the bottom of the page.
st.divider()
st.caption(st.session_state.message)
