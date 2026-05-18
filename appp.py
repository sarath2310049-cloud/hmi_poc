"""
app.py
======
Phase 5 — Intelligent Context-Aware HMI
Streamlit dashboard with:
  - Secure role-based login screen
  - Mid-session role switching with password re-verification
  - Alarm panel with suppression
  - Root cause + causal chain visualization
  - Role-based views (Operator / Engineer / Manager / Robot Programmer)
  - Robot Programmer coding IDE page
  - Predictive warning engine
  - Low-code config.json support
  - Fault injection controls for demo
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time
import json
import os
from datetime import datetime
from collections import deque

from simulator import PackagingSimulator, FaultScenario
from alarm_engine import AlarmEngine
from priority_engine import PriorityEngine, PRIORITY_LABELS
from rootcause_engine import RootCauseEngine

st.set_page_config(
    page_title="IntelliHMI — Cobot Packaging",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROLE_CREDENTIALS = {
    "Operator":         {"password": "op1234",   "icon": "🟢"},
    "Engineer":         {"password": "eng5678",  "icon": "🔵"},
    "Manager":          {"password": "mgr9012",  "icon": "🟡"},
    "Robot Programmer": {"password": "robo3456", "icon": "🤖"},
}

ROLE_DESC = {
    "Operator":         "🟢 Active alarms + recovery steps",
    "Engineer":         "🔵 All signals + suppressed alarms + config",
    "Manager":          "🟡 Throughput + downtime impact only",
    "Robot Programmer": "🤖 Robot code editor + motion programming",
}

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0a0e1a;
    color: #e2e8f0;
  }

  section[data-testid="stSidebar"] {
    background: #0d1220 !important;
    border-right: 1px solid #1e2d45;
  }

  div[data-testid="metric-container"] {
    background: #111827;
    border: 1px solid #1e2d45;
    border-radius: 10px;
    padding: 16px;
  }

  h1, h2, h3 { font-family: 'JetBrains Mono', monospace; }

  .alarm-critical {
    background: linear-gradient(135deg, #1a0505, #2d0808);
    border-left: 4px solid #ef4444;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 10px;
  }
  .alarm-high {
    background: linear-gradient(135deg, #1a0d00, #2d1800);
    border-left: 4px solid #f97316;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 10px;
  }
  .alarm-medium {
    background: linear-gradient(135deg, #0d1200, #1a1f00);
    border-left: 4px solid #eab308;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 10px;
  }
  .alarm-low {
    background: linear-gradient(135deg, #000d1a, #001a2d);
    border-left: 4px solid #3b82f6;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 10px;
  }
  .alarm-healthy {
    background: linear-gradient(135deg, #001a0d, #002d1a);
    border-left: 4px solid #22c55e;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 10px;
  }

  .action-card {
    background: #111827;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
  }

  .section-header {
    background: linear-gradient(90deg, #1e3a5f, #0a0e1a);
    border-left: 3px solid #3b82f6;
    padding: 8px 16px;
    border-radius: 4px;
    margin-bottom: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #93c5fd;
  }

  .section-header-robot {
    background: linear-gradient(90deg, #1a1f3a, #0a0e1a);
    border-left: 3px solid #a855f7;
    padding: 8px 16px;
    border-radius: 4px;
    margin-bottom: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #d8b4fe;
  }

  .badge-critical { background:#ef4444; color:white; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
  .badge-high     { background:#f97316; color:white; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
  .badge-medium   { background:#eab308; color:black; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
  .badge-low      { background:#3b82f6; color:white; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
  .badge-ok       { background:#22c55e; color:white; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }

  .predictive-box {
    background: linear-gradient(135deg, #1a1200, #2d2000);
    border: 1px dashed #fbbf24;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 10px;
  }

  .chain-node {
    background: #111827;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 10px 16px;
    margin: 4px 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
  }

  .code-toolbar {
    background: #161b2e;
    border: 1px solid #2d3a5f;
    border-radius: 8px 8px 0 0;
    padding: 8px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #64748b;
  }

  .program-card {
    background: #111827;
    border: 1px solid #2d3a5f;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
  }

  .role-switch-banner {
    background: linear-gradient(135deg, #1a1a0d, #2d2d00);
    border: 1px dashed #fbbf24;
    border-radius: 8px;
    padding: 10px 16px;
    margin-bottom: 12px;
    font-size: 13px;
    color: #fbbf24;
  }

  /* ── Sidebar toggle fix ─────────────────────────────────────── */
  /* Hide header chrome but keep the sidebar collapse/expand toggle */
  #MainMenu { visibility: hidden; }
  footer { visibility: hidden; }
  header[data-testid="stHeader"] {
    background: transparent !important;
    height: 2.5rem !important;
  }

  /* The collapsed-sidebar open button — always keep visible */
  button[data-testid="collapsedControl"] {
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
    background: #1e3a5f !important;
    border-radius: 0 8px 8px 0 !important;
    border: 1px solid #3b82f6 !important;
    color: #93c5fd !important;
    z-index: 99999 !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
  }

  /* The expand/collapse arrow inside the sidebar */
  section[data-testid="stSidebar"] button[data-testid="baseButton-headerNoPadding"],
  section[data-testid="stSidebar"] > div > button {
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
  }
</style>
""", unsafe_allow_html=True)


def init_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.role = None
        st.session_state.login_error = ""

    if "switch_role_mode" not in st.session_state:
        st.session_state.switch_role_mode = False
        st.session_state.switch_role_target = None
        st.session_state.switch_role_error = ""

    if "active_page" not in st.session_state:
        st.session_state.active_page = "Dashboard"

    if "sim" not in st.session_state:
        st.session_state.sim = PackagingSimulator()
        st.session_state.a_eng = AlarmEngine()
        st.session_state.p_eng = PriorityEngine()
        st.session_state.rc_eng = RootCauseEngine()
        st.session_state.scenario = FaultScenario.NONE
        st.session_state.history = {
            "time": deque(maxlen=40),
            "conveyor_speed": deque(maxlen=40),
            "motor_temp": deque(maxlen=40),
            "motor_current": deque(maxlen=40),
            "throughput": deque(maxlen=40),
        }
        st.session_state.alarm_log = []
        st.session_state.tick = 0
        st.session_state.prev_temp_trend = deque(maxlen=5)

    if "robot_programs" not in st.session_state:
        st.session_state.robot_programs = {
            "pick_place_v1": {
                "name": "Pick & Place v1",
                "description": "Standard pick-and-place routine",
                "code": (
                    "# Pick & Place Routine — Standard\n"
                    "# Target: Box A → Conveyor B\n\n"
                    "SPEED 50%\n"
                    "ACCEL 30%\n\n"
                    "HOME\n"
                    "MOVEJ J1=0 J2=-45 J3=90 J4=0 J5=45 J6=0\n"
                    "MOVEL X=320 Y=120 Z=80\n"
                    "MOVEL X=320 Y=120 Z=40\n"
                    "GRIP CLOSE FORCE=40N\n"
                    "MOVEL X=320 Y=120 Z=80\n"
                    "MOVEJ J1=90 J2=-45 J3=90 J4=0 J5=45 J6=0\n"
                    "MOVEL X=150 Y=350 Z=80\n"
                    "MOVEL X=150 Y=350 Z=40\n"
                    "GRIP OPEN\n"
                    "HOME\n"
                ),
                "modified": "2026-05-10 09:22:00",
                "status": "Deployed",
            },
            "scan_inspect": {
                "name": "Vision Inspect Routine",
                "description": "Camera-triggered inspection loop",
                "code": (
                    "# Vision Inspection Routine\n"
                    "# Triggers on vision sensor detect event\n\n"
                    "SPEED 30%\n\n"
                    "WAIT SIGNAL=VISION_DETECT TIMEOUT=5s\n"
                    "MOVEL X=200 Y=200 Z=120\n"
                    "WAIT 0.5s\n"
                    "CAPTURE IMAGE\n"
                    "IF QUALITY < 0.8 THEN\n"
                    "  MOVEJ REJECT_BIN\n"
                    "  GRIP OPEN\n"
                    "ELSE\n"
                    "  MOVEJ PASS_CONVEYOR\n"
                    "  GRIP OPEN\n"
                    "END IF\n"
                    "HOME\n"
                ),
                "modified": "2026-05-14 14:05:00",
                "status": "Staging",
            },
        }

    if "selected_program" not in st.session_state:
        st.session_state.selected_program = None
    if "editor_code" not in st.session_state:
        st.session_state.editor_code = ""
    if "code_output" not in st.session_state:
        st.session_state.code_output = []
    if "sim_running" not in st.session_state:
        st.session_state.sim_running = False


init_state()


def show_login():
    st.markdown("""
    <div style="text-align:center;margin-top:40px">
      <span style="font-size:48px">🏭</span>
      <h1 style="font-family:'JetBrains Mono',monospace;color:#93c5fd;margin:8px 0">IntelliHMI</h1>
      <p style="color:#64748b;font-size:14px">Cobot Packaging Line · Secure Access Portal</p>
    </div>
    """, unsafe_allow_html=True)

    col_center = st.columns([1, 1.5, 1])[1]
    with col_center:
        st.markdown("---")
        st.markdown("#### Select Your Role")
        selected_role = st.selectbox(
            "Role",
            list(ROLE_CREDENTIALS.keys()),
            label_visibility="collapsed",
            format_func=lambda r: f"{ROLE_CREDENTIALS[r]['icon']} {r}"
        )
        st.markdown(f"<small style='color:#64748b'>{ROLE_DESC[selected_role]}</small>", unsafe_allow_html=True)
        st.markdown("")
        password = st.text_input("Password", type="password", placeholder="Enter password...")

        if st.button("🔐 Login", use_container_width=True):
            if password == ROLE_CREDENTIALS[selected_role]["password"]:
                st.session_state.authenticated = True
                st.session_state.role = selected_role
                st.session_state.login_error = ""
                st.rerun()
            else:
                st.session_state.login_error = "Incorrect password. Please try again."

        if st.session_state.login_error:
            st.error(st.session_state.login_error)

        st.markdown("---")
        st.markdown("""
        <div style='text-align:center;font-size:11px;color:#334155'>
          Default credentials for demo:<br>
          Operator: <code>op1234</code> · Engineer: <code>eng5678</code><br>
          Manager: <code>mgr9012</code> · Robot Programmer: <code>robo3456</code>
        </div>
        """, unsafe_allow_html=True)


def show_role_switch_panel():
    st.markdown("#### Switch Role")
    target = st.selectbox(
        "Switch to:",
        [r for r in ROLE_CREDENTIALS if r != st.session_state.role],
        key="switch_target_select",
        label_visibility="collapsed",
        format_func=lambda r: f"{ROLE_CREDENTIALS[r]['icon']} {r}"
    )
    pw = st.text_input(
        "Password for new role",
        type="password",
        key="switch_pw_input",
        placeholder="Enter password..."
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Confirm", use_container_width=True):
            if pw == ROLE_CREDENTIALS[target]["password"]:
                st.session_state.role = target
                st.session_state.switch_role_mode = False
                st.session_state.switch_role_error = ""
                st.session_state.active_page = "Dashboard"
                st.rerun()
            else:
                st.session_state.switch_role_error = "Wrong password"
    with c2:
        if st.button("Cancel", use_container_width=True):
            st.session_state.switch_role_mode = False
            st.session_state.switch_role_error = ""
            st.rerun()

    if st.session_state.switch_role_error:
        st.error(st.session_state.switch_role_error)


def check_predictive(state) -> list:
    warnings = []
    trend = st.session_state.prev_temp_trend
    trend.append(state.motor_temp)

    if len(trend) >= 4:
        if all(trend[i] < trend[i + 1] for i in range(len(trend) - 1)):
            if 60 < state.motor_temp < 90:
                warnings.append({
                    "type": "PREDICTIVE",
                    "message": (
                        f"Motor temperature rising trend detected ({state.motor_temp:.1f}C). "
                        f"Estimated critical in {max(1, int((90 - state.motor_temp) / 2))} ticks."
                    ),
                    "component": "Motor"
                })

    if 20 < state.conveyor_speed < 60:
        warnings.append({
            "type": "PREDICTIVE",
            "message": f"Conveyor speed degrading ({state.conveyor_speed:.1f}%). Possible jam developing.",
            "component": "Conveyor"
        })

    return warnings


def show_coding_page():
    st.markdown('<div class="section-header-robot">Robot Programmer — Code IDE</div>', unsafe_allow_html=True)

    tab_programs, tab_editor, tab_simulator, tab_docs = st.tabs(
        ["Programs", "Editor", "Simulator", "Reference"]
    )

    with tab_programs:
        st.markdown("**Program Library**")
        _, col_new = st.columns([3, 1])
        with col_new:
            if st.button("New Program", use_container_width=True):
                new_key = f"program_{len(st.session_state.robot_programs) + 1}"
                st.session_state.robot_programs[new_key] = {
                    "name": f"New Program {len(st.session_state.robot_programs) + 1}",
                    "description": "New routine",
                    "code": "# New Robot Program\nSPEED 50%\nHOME\n",
                    "modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "Draft",
                }
                st.session_state.selected_program = new_key
                st.session_state.editor_code = st.session_state.robot_programs[new_key]["code"]
                st.rerun()

        for key, prog in list(st.session_state.robot_programs.items()):
            status_color = {
                "Deployed": "#22c55e",
                "Staging": "#eab308",
                "Draft": "#64748b"
            }.get(prog["status"], "#64748b")

            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(f"""
                <div class="program-card">
                  <b style="color:#d8b4fe">{prog['name']}</b>
                  <span style="background:{status_color};color:white;padding:1px 8px;
                    border-radius:10px;font-size:11px;margin-left:8px">{prog['status']}</span><br>
                  <small style="color:#64748b">{prog['description']} · Modified: {prog['modified']}</small>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                if st.button("Edit", key=f"edit_{key}", use_container_width=True):
                    st.session_state.selected_program = key
                    st.session_state.editor_code = prog["code"]
                    st.rerun()
            with c3:
                if st.button("Delete", key=f"del_{key}", use_container_width=True):
                    del st.session_state.robot_programs[key]
                    if st.session_state.selected_program == key:
                        st.session_state.selected_program = None
                    st.rerun()

    with tab_editor:
        if st.session_state.selected_program is None:
            st.info("Select a program from the Programs tab to edit it.")
        else:
            prog = st.session_state.robot_programs[st.session_state.selected_program]

            col_name, col_status = st.columns([3, 1])
            with col_name:
                new_name = st.text_input("Program Name", value=prog["name"], key="prog_name_input")
            with col_status:
                new_status = st.selectbox(
                    "Status",
                    ["Draft", "Staging", "Deployed"],
                    index=["Draft", "Staging", "Deployed"].index(prog["status"]),
                    key="prog_status_input"
                )

            new_desc = st.text_input("Description", value=prog["description"], key="prog_desc_input")

            st.markdown("""
            <div class="code-toolbar">
              Robot Motion Language (RML) · MOVEJ, MOVEL, GRIP, WAIT, IF/THEN/ELSE, SPEED, ACCEL
            </div>
            """, unsafe_allow_html=True)

            edited_code = st.text_area(
                "Code",
                value=prog["code"],
                height=380,
                key="code_editor_area",
                label_visibility="collapsed"
            )
            st.session_state.editor_code = edited_code

            col_save, col_deploy, col_validate = st.columns(3)
            with col_save:
                if st.button("Save", use_container_width=True):
                    prog["code"] = edited_code
                    prog["name"] = new_name
                    prog["status"] = new_status
                    prog["description"] = new_desc
                    prog["modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.success("Program saved.")
            with col_deploy:
                if st.button("Save and Deploy", use_container_width=True):
                    prog["code"] = edited_code
                    prog["name"] = new_name
                    prog["status"] = "Deployed"
                    prog["description"] = new_desc
                    prog["modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.success("Program deployed to robot controller.")
            with col_validate:
                if st.button("Validate Syntax", use_container_width=True):
                    errors = []
                    valid_cmds = {
                        "HOME", "MOVEJ", "MOVEL", "GRIP", "WAIT", "SPEED",
                        "ACCEL", "CAPTURE", "IF", "ELSE", "END", "SIGNAL", "#", ""
                    }
                    for i, line in enumerate(edited_code.split("\n"), 1):
                        stripped = line.strip()
                        if stripped and not stripped.startswith("#"):
                            cmd = stripped.split()[0] if stripped.split() else ""
                            if cmd not in valid_cmds:
                                errors.append(f"Line {i}: Unknown command '{cmd}'")
                    if errors:
                        for e in errors:
                            st.warning(e)
                    else:
                        st.success("Syntax valid — no errors found.")

            if edited_code != prog["code"]:
                st.markdown(
                    '<div class="role-switch-banner">Unsaved changes — click Save or Save and Deploy</div>',
                    unsafe_allow_html=True
                )

    with tab_simulator:
        st.markdown("**Motion Simulator**")
        st.caption("Dry-run your program step-by-step without moving the physical robot.")

        if st.session_state.selected_program is None:
            st.info("Select a program from the Programs tab first.")
        else:
            code = st.session_state.robot_programs[st.session_state.selected_program]["code"]
            lines = [l.strip() for l in code.split("\n") if l.strip() and not l.strip().startswith("#")]

            col_run, col_clear = st.columns(2)
            with col_run:
                if st.button("Run Simulation", use_container_width=True):
                    st.session_state.code_output = []
                    joint_pos = [0, 0, 0, 0, 0, 0]
                    tcp_pos = {"X": 0, "Y": 0, "Z": 0}

                    for line in lines:
                        parts = line.split()
                        cmd = parts[0] if parts else ""
                        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]

                        if cmd == "HOME":
                            joint_pos = [0, 0, 0, 0, 0, 0]
                            tcp_pos = {"X": 0, "Y": 0, "Z": 300}
                            st.session_state.code_output.append(
                                f"[{ts}] HOME  ->  J=[0,0,0,0,0,0]  TCP=(0,0,300)"
                            )
                        elif cmd == "MOVEJ":
                            for p in parts[1:]:
                                if p.startswith("J") and "=" in p:
                                    try:
                                        idx = int(p[1]) - 1
                                        joint_pos[idx] = float(p.split("=")[1])
                                    except Exception:
                                        pass
                            st.session_state.code_output.append(
                                f"[{ts}] MOVEJ -> J={joint_pos}"
                            )
                        elif cmd == "MOVEL":
                            for p in parts[1:]:
                                if "=" in p and p[0] in "XYZ":
                                    try:
                                        tcp_pos[p[0]] = float(p.split("=")[1].split(";")[0])
                                    except Exception:
                                        pass
                            st.session_state.code_output.append(
                                f"[{ts}] MOVEL -> TCP=({tcp_pos['X']},{tcp_pos['Y']},{tcp_pos['Z']})"
                            )
                        elif cmd == "GRIP":
                            gripper = parts[1] if len(parts) > 1 else "?"
                            force = next((p.split("=")[1] for p in parts if "FORCE" in p), "--")
                            st.session_state.code_output.append(
                                f"[{ts}] GRIP {gripper}  Force={force}"
                            )
                        elif cmd == "WAIT":
                            duration = parts[1] if len(parts) > 1 else "?"
                            st.session_state.code_output.append(f"[{ts}] WAIT {duration}")
                        elif cmd == "SPEED":
                            st.session_state.code_output.append(
                                f"[{ts}] SPEED set to {parts[1] if len(parts) > 1 else '?'}"
                            )
                        elif cmd == "ACCEL":
                            st.session_state.code_output.append(
                                f"[{ts}] ACCEL set to {parts[1] if len(parts) > 1 else '?'}"
                            )
                        elif cmd == "CAPTURE":
                            st.session_state.code_output.append(f"[{ts}] CAPTURE IMAGE -> OK")
                        elif cmd in ("IF", "ELSE", "END"):
                            st.session_state.code_output.append(f"[{ts}] {line}")
                        else:
                            st.session_state.code_output.append(f"[{ts}] {line}")

                    st.session_state.code_output.append(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Simulation complete — {len(lines)} instructions executed."
                    )
                    st.rerun()

            with col_clear:
                if st.button("Clear Output", use_container_width=True):
                    st.session_state.code_output = []
                    st.rerun()

            if st.session_state.code_output:
                st.code("\n".join(st.session_state.code_output), language="text")

                joint_values = [0] * 6
                for line in reversed(st.session_state.code_output):
                    if "MOVEJ" in line and "J=[" in line:
                        try:
                            j_str = line.split("J=[")[1].split("]")[0]
                            joint_values = [float(v) for v in j_str.split(",")]
                        except Exception:
                            pass
                        break

                fig = go.Figure(go.Bar(
                    x=[f"J{i+1}" for i in range(6)],
                    y=joint_values,
                    marker_color=["#a855f7"] * 6,
                    text=[f"{v:.0f}deg" for v in joint_values],
                    textposition="auto"
                ))
                fig.update_layout(
                    title="Joint Angles (degrees)",
                    template="plotly_dark",
                    paper_bgcolor="#111827",
                    plot_bgcolor="#111827",
                    height=250,
                    margin=dict(l=10, r=10, t=40, b=10),
                    yaxis_title="Degrees"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Run the simulation to see output here.")

    with tab_docs:
        st.markdown("**Robot Motion Language (RML) Quick Reference**")
        ref_data = {
            "Command": ["HOME", "MOVEJ", "MOVEL", "GRIP OPEN/CLOSE", "WAIT", "SPEED %", "ACCEL %", "CAPTURE IMAGE", "IF / ELSE / END IF"],
            "Description": [
                "Return robot to home position",
                "Joint-space move — specify J1 to J6 angles",
                "Cartesian linear move — specify X Y Z coordinates",
                "Open or close gripper; optional FORCE=Nm",
                "Wait for time (e.g. 0.5s) or signal",
                "Set velocity as percent of max speed",
                "Set acceleration as percent of max",
                "Trigger vision system capture",
                "Conditional logic branch",
            ],
            "Example": [
                "HOME",
                "MOVEJ J1=0 J2=-45 J3=90 J4=0 J5=45 J6=0",
                "MOVEL X=320 Y=120 Z=40",
                "GRIP CLOSE FORCE=40N",
                "WAIT 0.5s",
                "SPEED 50%",
                "ACCEL 30%",
                "CAPTURE IMAGE",
                "IF QUALITY < 0.8 THEN ... ELSE ... END IF",
            ]
        }
        st.dataframe(pd.DataFrame(ref_data), use_container_width=True, height=320)

        st.markdown("---")
        st.markdown("**Joint Limits**")
        limits_data = {
            "Joint": ["J1", "J2", "J3", "J4", "J5", "J6"],
            "Min deg": [-180, -90, -180, -180, -90, -360],
            "Max deg": [180, 90, 180, 180, 90, 360],
            "Max Speed deg/s": [120, 90, 120, 180, 180, 360],
        }
        st.dataframe(pd.DataFrame(limits_data), use_container_width=True)

        st.markdown("**Workspace Envelope**")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Max Reach", "850 mm")
        col_b.metric("Payload", "10 kg")
        col_c.metric("Repeatability", "+/- 0.05 mm")


def show_sidebar(state, counts, report):
    with st.sidebar:
        st.markdown("### IntelliHMI")
        st.markdown("**Cobot Packaging Line v1.0**")
        st.divider()

        role = st.session_state.role
        icon = ROLE_CREDENTIALS[role]["icon"]
        st.markdown(
            f"<div style='background:#111827;border:1px solid #1e3a5f;border-radius:8px;"
            f"padding:10px 14px;margin-bottom:8px'>"
            f"<b style='color:#93c5fd'>{icon} {role}</b><br>"
            f"<small style='color:#64748b'>{ROLE_DESC[role]}</small></div>",
            unsafe_allow_html=True
        )

        col_sw, col_lo = st.columns(2)
        with col_sw:
            sw_label = "Close" if st.session_state.switch_role_mode else "Switch Role"
            if st.button(sw_label, use_container_width=True):
                st.session_state.switch_role_mode = not st.session_state.switch_role_mode
                st.session_state.switch_role_error = ""
        with col_lo:
            if st.button("Logout", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.role = None
                st.session_state.switch_role_mode = False
                st.session_state.active_page = "Dashboard"
                st.rerun()

        if st.session_state.switch_role_mode:
            st.divider()
            show_role_switch_panel()

        st.divider()

        st.markdown("#### Navigation")
        pages = ["Dashboard", "Coding"] if role == "Robot Programmer" else ["Dashboard"]

        for page in pages:
            is_active = st.session_state.active_page == page
            label = f"{'> ' if is_active else ''}{page}"
            if st.button(label, key=f"nav_{page}", use_container_width=True):
                st.session_state.active_page = page
                st.rerun()

        st.divider()

        if role != "Manager":
            st.markdown("#### Fault Injection")
            scenario_map = {
                "Normal Operation": FaultScenario.NONE,
                "Conveyor Jam": FaultScenario.CONVEYOR_JAM,
                "Motor Overheat": FaultScenario.MOTOR_OVERHEAT,
                "Vision Sensor Fault": FaultScenario.VISION_FAILURE,
            }
            selected = st.selectbox(
                "Inject scenario:",
                list(scenario_map.keys()),
                label_visibility="collapsed"
            )
            if st.button("Inject Fault", use_container_width=True):
                new_scenario = scenario_map[selected]
                if new_scenario != st.session_state.scenario:
                    st.session_state.scenario = new_scenario
                    st.session_state.sim.set_scenario(new_scenario)
            st.divider()

        st.markdown("#### Live Feed")
        auto_refresh = st.toggle("Auto Refresh (2s)", value=True)
        if st.button("Manual Tick", use_container_width=True):
            st.session_state.tick += 1

        st.divider()
        st.caption(f"Time: {datetime.now().strftime('%H:%M:%S')}")
        st.caption(f"Scenario: {st.session_state.scenario.value}")

    return auto_refresh


if not st.session_state.authenticated:
    show_login()
    st.stop()

state = st.session_state.sim.tick()
alarms = st.session_state.a_eng.evaluate(state)
prioritized = st.session_state.p_eng.process(alarms)
visible = st.session_state.p_eng.active_only(prioritized)
counts = st.session_state.p_eng.summary(prioritized)
report = st.session_state.rc_eng.analyze(alarms)
predictive = check_predictive(state)

h = st.session_state.history
h["time"].append(datetime.now().strftime("%H:%M:%S"))
h["conveyor_speed"].append(state.conveyor_speed)
h["motor_temp"].append(state.motor_temp)
h["motor_current"].append(state.motor_current)
h["throughput"].append(state.packages_per_min)

for a in alarms:
    st.session_state.alarm_log.append({
        "time": state.timestamp,
        "id": a.alarm_id,
        "name": a.name,
        "severity": a.severity,
        "component": a.component,
    })

auto_refresh = show_sidebar(state, counts, report)
role = st.session_state.role

col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown("# IntelliHMI")
    st.markdown(
        f"**Intelligent Context-Aware Control Interface** · "
        f"`{state.timestamp}` · {ROLE_CREDENTIALS[role]['icon']} **{role}**"
    )
with col_status:
    if report.is_healthy():
        st.markdown('<div style="background:#052e16;border:1px solid #22c55e;border-radius:10px;padding:16px;text-align:center"><span style="font-size:28px">OK</span><br><b style="color:#22c55e">ALL SYSTEMS NOMINAL</b></div>', unsafe_allow_html=True)
    elif counts["P1"] > 0:
        st.markdown('<div style="background:#2d0808;border:1px solid #ef4444;border-radius:10px;padding:16px;text-align:center"><span style="font-size:28px">!!</span><br><b style="color:#ef4444">CRITICAL FAULT</b></div>', unsafe_allow_html=True)
    elif counts["P2"] > 0:
        st.markdown('<div style="background:#2d1800;border:1px solid #f97316;border-radius:10px;padding:16px;text-align:center"><span style="font-size:28px">!!</span><br><b style="color:#f97316">HIGH ALERT</b></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background:#1a1f00;border:1px solid #eab308;border-radius:10px;padding:16px;text-align:center"><span style="font-size:28px">--</span><br><b style="color:#eab308">MONITOR</b></div>', unsafe_allow_html=True)

st.divider()

active_page = st.session_state.active_page

if active_page == "Coding" and role == "Robot Programmer":
    show_coding_page()

elif role in ("Operator", "Robot Programmer"):

    st.markdown('<div class="section-header">Live Signals</div>', unsafe_allow_html=True)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Conveyor Speed", f"{state.conveyor_speed:.1f}%",
              delta="JAM" if state.conveyor_jammed else "OK",
              delta_color="inverse" if state.conveyor_jammed else "normal")
    m2.metric("Motor Temp", f"{state.motor_temp:.1f}C",
              delta="HOT" if state.motor_temp > 75 else "Normal",
              delta_color="inverse" if state.motor_temp > 75 else "normal")
    m3.metric("Motor Current", f"{state.motor_current:.1f}A",
              delta="HIGH" if state.motor_current > 9 else "Normal",
              delta_color="inverse" if state.motor_current > 9 else "normal")
    m4.metric("Vision", "Detected" if state.vision_detected else "No Package", delta=None)
    m5.metric("Throughput", f"{state.packages_per_min:.1f} ppm",
              delta=f"{state.packages_per_min - 12:.1f} vs target",
              delta_color="normal")

    if role == "Robot Programmer":
        st.markdown(
            '<div class="role-switch-banner">Robot Programmer mode — use the Coding page in the sidebar.</div>',
            unsafe_allow_html=True
        )

    st.divider()

    col_alarms, col_rc = st.columns(2)

    with col_alarms:
        st.markdown('<div class="section-header">Active Alarms</div>', unsafe_allow_html=True)
        st.caption(f"{len(alarms)} total · {len(visible)} shown · {counts['suppressed']} suppressed")

        if not visible:
            st.markdown('<div class="alarm-healthy"><b>No active alarms</b> — System operating normally</div>', unsafe_allow_html=True)
        else:
            for pa in visible:
                sev = pa.alarm.severity.lower()
                st.markdown(f"""
                <div class="alarm-{sev}">
                  <b>[{pa.priority}] {pa.alarm.name}</b>
                  <span class="badge-{sev}">{pa.alarm.severity}</span><br>
                  <small style="color:#94a3b8">{pa.alarm.component} · {pa.alarm.timestamp}</small><br>
                  <span style="font-size:13px">{pa.alarm.message}</span>
                </div>
                """, unsafe_allow_html=True)

        if predictive:
            st.markdown("---")
            st.caption("Predictive Intelligence")
            for pw in predictive:
                st.markdown(f"""
                <div class="predictive-box">
                  <b>PREDICTIVE WARNING — {pw['component']}</b><br>
                  <span style="font-size:13px;color:#fbbf24">{pw['message']}</span>
                </div>
                """, unsafe_allow_html=True)

    with col_rc:
        st.markdown('<div class="section-header">Intelligent Diagnosis</div>', unsafe_allow_html=True)

        if report.is_healthy():
            st.markdown('<div class="alarm-healthy"><b>No fault detected</b><br><span style="font-size:13px">All systems operating within normal parameters.</span></div>', unsafe_allow_html=True)
        else:
            conf_color = {"HIGH": "#22c55e", "MEDIUM": "#eab308", "LOW": "#ef4444"}
            cc = conf_color.get(report.confidence, "#94a3b8")
            st.markdown(f"""
            <div style="background:#1a0d2e;border:1px solid #7c3aed;border-radius:10px;padding:16px;margin-bottom:12px">
              <b style="color:#c4b5fd;font-size:15px">ROOT CAUSE IDENTIFIED</b><br>
              <span style="font-size:18px;font-weight:700;color:white">{report.root_cause}</span><br>
              <small>Confidence: <b style="color:{cc}">{report.confidence}</b> · Est. Downtime: <b style="color:#f97316">{report.estimated_downtime}</b></small>
            </div>
            """, unsafe_allow_html=True)

            if report.causal_chain:
                st.caption("Causal Chain")
                for i, step in enumerate(report.causal_chain):
                    prefix = "ROOT" if i == 0 else ("END" if i == len(report.causal_chain) - 1 else "-->")
                    st.markdown(f"""
                    <div class="chain-node">
                      <b>{prefix} [{step.component}]</b> {step.description}
                    </div>
                    """, unsafe_allow_html=True)
                    if i < len(report.causal_chain) - 1:
                        st.markdown('<div style="text-align:center;color:#3b82f6;font-size:18px">v</div>', unsafe_allow_html=True)

    st.divider()

    if not report.is_healthy() and report.recommended_actions:
        st.markdown('<div class="section-header">Recommended Recovery Actions</div>', unsafe_allow_html=True)
        action_icons = {
            "STOP": "STOP", "INSPECT": "CHECK", "CLEAR": "CLEAR", "CHECK": "CHECK",
            "RESTART": "RESTART", "REDUCE": "REDUCE", "MONITOR": "MONITOR", "LOG": "LOG",
            "VERIFY": "VERIFY", "COOL": "COOL", "CLEAN": "CLEAN", "ALIGN": "ALIGN", "TEST": "TEST"
        }
        cols = st.columns(min(len(report.recommended_actions), 3))
        for i, action in enumerate(report.recommended_actions):
            with cols[i % 3]:
                ic = action_icons.get(action.action_type, ">>")
                st.markdown(f"""
                <div class="action-card">
                  <b style="color:#93c5fd">{action.step}</b><br>
                  <b style="color:#fbbf24">[{action.action_type}]</b><br>
                  <span style="color:#e2e8f0">{action.description}</span>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    st.markdown('<div class="section-header">Live Trends</div>', unsafe_allow_html=True)

    if len(h["time"]) > 1:
        df = pd.DataFrame({
            "Time": list(h["time"]),
            "Conveyor Speed (%)": list(h["conveyor_speed"]),
            "Motor Temp (C)": list(h["motor_temp"]),
            "Motor Current (A)": list(h["motor_current"]),
            "Throughput (ppm)": list(h["throughput"]),
        })

        tc1, tc2 = st.columns(2)
        with tc1:
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(
                x=df["Time"], y=df["Conveyor Speed (%)"],
                mode="lines+markers",
                line=dict(color="#3b82f6", width=2),
                fill="tozeroy", fillcolor="rgba(59,130,246,0.1)"
            ))
            fig1.add_hline(y=20, line_dash="dash", line_color="#ef4444", annotation_text="Jam threshold")
            fig1.update_layout(
                title="Conveyor Speed", template="plotly_dark",
                paper_bgcolor="#111827", plot_bgcolor="#111827",
                height=220, margin=dict(l=10, r=10, t=40, b=10), showlegend=False
            )
            st.plotly_chart(fig1, use_container_width=True)

        with tc2:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df["Time"], y=df["Motor Temp (C)"],
                mode="lines+markers",
                line=dict(color="#f97316", width=2),
                fill="tozeroy", fillcolor="rgba(249,115,22,0.1)"
            ))
            fig2.add_hline(y=75, line_dash="dash", line_color="#eab308", annotation_text="Warning")
            fig2.add_hline(y=90, line_dash="dash", line_color="#ef4444", annotation_text="Critical")
            fig2.update_layout(
                title="Motor Temperature", template="plotly_dark",
                paper_bgcolor="#111827", plot_bgcolor="#111827",
                height=220, margin=dict(l=10, r=10, t=40, b=10), showlegend=False
            )
            st.plotly_chart(fig2, use_container_width=True)

elif role == "Engineer":

    st.markdown('<div class="section-header">Engineer View — Full Diagnostics</div>', unsafe_allow_html=True)

    st.markdown("**Raw Signal Dump**")
    raw_cols = st.columns(6)
    raw_cols[0].metric("Conveyor Speed", f"{state.conveyor_speed:.2f}%")
    raw_cols[1].metric("Motor Temp", f"{state.motor_temp:.2f}C")
    raw_cols[2].metric("Motor Current", f"{state.motor_current:.2f}A")
    raw_cols[3].metric("Vision", "YES" if state.vision_detected else "NO")
    raw_cols[4].metric("Robot", state.robot_status)
    raw_cols[5].metric("Throughput", f"{state.packages_per_min:.2f}")

    st.divider()

    st.markdown("**All Alarms (including suppressed)**")
    if not prioritized:
        st.success("No alarms active.")
    else:
        for pa in prioritized:
            tag = " SUPPRESSED" if pa.suppressed else ""
            opacity = "opacity:0.4" if pa.suppressed else ""
            sev = pa.alarm.severity.lower()
            st.markdown(f"""
            <div class="alarm-{sev}" style="{opacity}">
              <b>[{pa.priority}] {pa.alarm.alarm_id} — {pa.alarm.name}{tag}</b><br>
              <small>{pa.alarm.component} · Threshold: {pa.alarm.threshold} · Value: {pa.alarm.value}</small><br>
              {pa.alarm.message}
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    st.markdown("**Machine Dependency Model**")
    st.code("""
Conveyor
  -- Vision Sensor
        -- Cobot (Robot)
              -- System (Throughput)
  -- Motor (bidirectional -- jam causes overcurrent)
    """, language="text")

    st.divider()

    st.markdown("**Alarm History Log**")
    if st.session_state.alarm_log:
        log_df = pd.DataFrame(st.session_state.alarm_log[-50:])
        st.dataframe(log_df, use_container_width=True, height=300)
    else:
        st.info("No alarms logged yet.")

    st.divider()

    st.markdown("**All Signal Trends**")
    if len(h["time"]) > 1:
        df = pd.DataFrame({
            "Time": list(h["time"]),
            "Conveyor Speed": list(h["conveyor_speed"]),
            "Motor Temp": list(h["motor_temp"]),
            "Motor Current": list(h["motor_current"]),
            "Throughput": list(h["throughput"]),
        })
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["Time"], y=df["Conveyor Speed"], name="Conveyor %", line=dict(color="#3b82f6")))
        fig.add_trace(go.Scatter(x=df["Time"], y=df["Motor Temp"], name="Motor Temp C", line=dict(color="#f97316")))
        fig.add_trace(go.Scatter(x=df["Time"], y=df["Motor Current"], name="Current A", line=dict(color="#a855f7")))
        fig.add_trace(go.Scatter(x=df["Time"], y=df["Throughput"], name="Throughput ppm", line=dict(color="#22c55e")))
        fig.update_layout(
            template="plotly_dark", paper_bgcolor="#111827",
            plot_bgcolor="#111827", height=350,
            margin=dict(l=10, r=10, t=20, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)

elif role == "Manager":

    st.markdown('<div class="section-header">Manager View — Production Impact</div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Throughput", f"{state.packages_per_min:.1f} ppm", f"{state.packages_per_min - 12:.1f} vs target")
    m2.metric("Active P1 Alarms", counts["P1"],
              delta="Critical" if counts["P1"] > 0 else "None",
              delta_color="inverse" if counts["P1"] > 0 else "off")
    m3.metric("Est. Downtime", report.estimated_downtime if not report.is_healthy() else "None")
    m4.metric("System Status", "FAULT" if not report.is_healthy() else "NORMAL")

    st.divider()

    if not report.is_healthy():
        st.error(f"Active Fault: {report.root_cause}")
        st.warning(
            f"Production Impact: Throughput at {state.packages_per_min:.1f} ppm vs 12.0 target — "
            f"{max(0, 12 - state.packages_per_min):.1f} ppm shortfall"
        )
        loss_per_min = max(0, 12 - state.packages_per_min)
        st.info(
            f"Estimated loss: {loss_per_min * 5:.0f} packages if 5 min downtime · "
            f"{loss_per_min * 15:.0f} packages if 15 min"
        )
    else:
        st.success("All systems nominal. Production running at target.")

    st.divider()

    if len(h["time"]) > 1:
        df = pd.DataFrame({"Time": list(h["time"]), "Throughput": list(h["throughput"])})
        fig = px.area(df, x="Time", y="Throughput",
                      title="Production Throughput (packages/min)",
                      color_discrete_sequence=["#22c55e"])
        fig.add_hline(y=12, line_dash="dash", line_color="#ef4444", annotation_text="Target: 12 ppm")
        fig.update_layout(
            template="plotly_dark", paper_bgcolor="#111827",
            plot_bgcolor="#111827", height=300,
            margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)

if auto_refresh:
    time.sleep(2)
    st.rerun()
