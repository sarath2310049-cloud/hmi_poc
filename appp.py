"""
app.py
======
Phase 5 — Intelligent Context-Aware HMI
Streamlit dashboard with:
  - Live digital twin signals
  - Alarm panel with suppression
  - Root cause + causal chain visualization
  - Role-based views (Operator / Engineer / Manager)
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

# ── Import our intelligence engine ────────────────────────────────
from simulator import PackagingSimulator, FaultScenario
from alarm_engine import AlarmEngine
from priority_engine import PriorityEngine, PRIORITY_LABELS
from rootcause_engine import RootCauseEngine

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="IntelliHMI — Cobot Packaging",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# GLOBAL STYLES
# ─────────────────────────────────────────────

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0a0e1a;
    color: #e2e8f0;
  }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: #0d1220 !important;
    border-right: 1px solid #1e2d45;
  }

  /* Metric cards */
  div[data-testid="metric-container"] {
    background: #111827;
    border: 1px solid #1e2d45;
    border-radius: 10px;
    padding: 16px;
  }

  /* Headers */
  h1, h2, h3 { font-family: 'JetBrains Mono', monospace; }

  /* Alarm card */
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

  /* Action step cards */
  .action-card {
    background: #111827;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
  }

  /* Section header bar */
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

  /* Status badge */
  .badge-critical { background:#ef4444; color:white; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
  .badge-high     { background:#f97316; color:white; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
  .badge-medium   { background:#eab308; color:black; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
  .badge-low      { background:#3b82f6; color:white; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
  .badge-ok       { background:#22c55e; color:white; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }

  /* Predictive warning */
  .predictive-box {
    background: linear-gradient(135deg, #1a1200, #2d2000);
    border: 1px dashed #fbbf24;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 10px;
  }

  /* Chain node */
  .chain-node {
    background: #111827;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 10px 16px;
    margin: 4px 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
  }

  /* Hide streamlit branding */
  #MainMenu {visibility: hidden;}
  footer {visibility: hidden;}
  header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────

def init_state():
    if "sim" not in st.session_state:
        st.session_state.sim      = PackagingSimulator()
        st.session_state.a_eng    = AlarmEngine()
        st.session_state.p_eng    = PriorityEngine()
        st.session_state.rc_eng   = RootCauseEngine()
        st.session_state.scenario = FaultScenario.NONE
        st.session_state.history  = {
            "time": deque(maxlen=40),
            "conveyor_speed": deque(maxlen=40),
            "motor_temp": deque(maxlen=40),
            "motor_current": deque(maxlen=40),
            "throughput": deque(maxlen=40),
        }
        st.session_state.alarm_log = []
        st.session_state.tick      = 0
        st.session_state.role      = "Operator"
        st.session_state.prev_temp_trend = deque(maxlen=5)

init_state()

# ─────────────────────────────────────────────
# PREDICTIVE WARNING ENGINE
# ─────────────────────────────────────────────

def check_predictive(state) -> list:
    warnings = []
    trend = st.session_state.prev_temp_trend
    trend.append(state.motor_temp)

    if len(trend) >= 4:
        # Rising temp trend = all values increasing
        if all(trend[i] < trend[i+1] for i in range(len(trend)-1)):
            if state.motor_temp > 60 and state.motor_temp < 90:
                warnings.append({
                    "type": "PREDICTIVE",
                    "message": f"Motor temperature rising trend detected ({state.motor_temp:.1f}°C). "
                               f"Estimated critical in {max(1, int((90 - state.motor_temp) / 2))} ticks.",
                    "component": "Motor"
                })

    if state.conveyor_speed < 60 and state.conveyor_speed > 20:
        warnings.append({
            "type": "PREDICTIVE",
            "message": f"Conveyor speed degrading ({state.conveyor_speed:.1f}%). Possible jam developing.",
            "component": "Conveyor"
        })

    return warnings

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🏭 IntelliHMI")
    st.markdown("**Cobot Packaging Line v1.0**")
    st.divider()

    # Role selector
    st.markdown("#### 👤 Role")
    role = st.selectbox(
        "View as:",
        ["Operator", "Engineer", "Manager"],
        key="role_select",
        label_visibility="collapsed"
    )
    st.session_state.role = role

    role_desc = {
        "Operator":  "🟢 Active alarms + recovery steps",
        "Engineer":  "🔵 All signals + suppressed alarms + config",
        "Manager":   "🟡 Throughput + downtime impact only",
    }
    st.caption(role_desc[role])
    st.divider()

    # Fault injection
    st.markdown("#### ⚡ Fault Injection")
    scenario_map = {
        "✅ Normal Operation":    FaultScenario.NONE,
        "🔴 Conveyor Jam":        FaultScenario.CONVEYOR_JAM,
        "🟠 Motor Overheat":      FaultScenario.MOTOR_OVERHEAT,
        "🟡 Vision Sensor Fault": FaultScenario.VISION_FAILURE,
    }

    selected = st.selectbox(
        "Inject scenario:",
        list(scenario_map.keys()),
        label_visibility="collapsed"
    )

    if st.button("⚡ Inject Fault", use_container_width=True):
        new_scenario = scenario_map[selected]
        if new_scenario != st.session_state.scenario:
            st.session_state.scenario = new_scenario
            st.session_state.sim.set_scenario(new_scenario)

    st.divider()

    # Auto-refresh
    st.markdown("#### 🔄 Live Feed")
    auto_refresh = st.toggle("Auto Refresh (2s)", value=True)
    if st.button("🔃 Manual Tick", use_container_width=True):
        st.session_state.tick += 1

    st.divider()
    st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
    st.caption(f"Scenario: `{st.session_state.scenario.value}`")

# ─────────────────────────────────────────────
# TICK THE SIMULATION
# ─────────────────────────────────────────────

state      = st.session_state.sim.tick()
alarms     = st.session_state.a_eng.evaluate(state)
prioritized = st.session_state.p_eng.process(alarms)
visible    = st.session_state.p_eng.active_only(prioritized)
counts     = st.session_state.p_eng.summary(prioritized)
report     = st.session_state.rc_eng.analyze(alarms)
predictive = check_predictive(state)

# Update history
h = st.session_state.history
h["time"].append(datetime.now().strftime("%H:%M:%S"))
h["conveyor_speed"].append(state.conveyor_speed)
h["motor_temp"].append(state.motor_temp)
h["motor_current"].append(state.motor_current)
h["throughput"].append(state.packages_per_min)

# Log alarms
for a in alarms:
    st.session_state.alarm_log.append({
        "time": state.timestamp,
        "id": a.alarm_id,
        "name": a.name,
        "severity": a.severity,
        "component": a.component,
    })

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

col_title, col_status = st.columns([3, 1])

with col_title:
    st.markdown("# 🏭 IntelliHMI")
    st.markdown(f"**Intelligent Context-Aware Control Interface** · `{state.timestamp}` · Role: **{role}**")

with col_status:
    if report.is_healthy():
        st.markdown('<div style="background:#052e16;border:1px solid #22c55e;border-radius:10px;padding:16px;text-align:center"><span style="font-size:28px">✅</span><br><b style="color:#22c55e">ALL SYSTEMS NOMINAL</b></div>', unsafe_allow_html=True)
    elif counts["P1"] > 0:
        st.markdown('<div style="background:#2d0808;border:1px solid #ef4444;border-radius:10px;padding:16px;text-align:center"><span style="font-size:28px">🚨</span><br><b style="color:#ef4444">CRITICAL FAULT</b></div>', unsafe_allow_html=True)
    elif counts["P2"] > 0:
        st.markdown('<div style="background:#2d1800;border:1px solid #f97316;border-radius:10px;padding:16px;text-align:center"><span style="font-size:28px">⚠️</span><br><b style="color:#f97316">HIGH ALERT</b></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background:#1a1f00;border:1px solid #eab308;border-radius:10px;padding:16px;text-align:center"><span style="font-size:28px">🟡</span><br><b style="color:#eab308">MONITOR</b></div>', unsafe_allow_html=True)

st.divider()

# ─────────────────────────────────────────────
# OPERATOR VIEW
# ─────────────────────────────────────────────

if role == "Operator":

    # ── Live Signal Metrics ────────────────────────────────────────
    st.markdown('<div class="section-header">📡 Live Signals</div>', unsafe_allow_html=True)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Conveyor Speed", f"{state.conveyor_speed:.1f}%",
              delta="JAM ⚠" if state.conveyor_jammed else "OK",
              delta_color="inverse" if state.conveyor_jammed else "normal")
    m2.metric("Motor Temp", f"{state.motor_temp:.1f}°C",
              delta="HOT ⚠" if state.motor_temp > 75 else "Normal",
              delta_color="inverse" if state.motor_temp > 75 else "normal")
    m3.metric("Motor Current", f"{state.motor_current:.1f}A",
              delta="HIGH ⚠" if state.motor_current > 9 else "Normal",
              delta_color="inverse" if state.motor_current > 9 else "normal")
    m4.metric("Vision", "✓ Detected" if state.vision_detected else "✗ No Package",
              delta=None)
    m5.metric("Throughput", f"{state.packages_per_min:.1f} ppm",
              delta=f"{state.packages_per_min - 12:.1f} vs target",
              delta_color="normal")

    st.divider()

    # ── Two columns: Alarms + Root Cause ──────────────────────────
    col_alarms, col_rc = st.columns([1, 1])

    with col_alarms:
        st.markdown('<div class="section-header">🚨 Active Alarms</div>', unsafe_allow_html=True)
        st.caption(f"{len(alarms)} total · {len(visible)} shown · {counts['suppressed']} suppressed by intelligence")

        if not visible:
            st.markdown('<div class="alarm-healthy">✅ <b>No active alarms</b> — System operating normally</div>', unsafe_allow_html=True)
        else:
            for pa in visible:
                sev = pa.alarm.severity.lower()
                icon_map = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}
                ic = icon_map.get(sev, "⚪")
                st.markdown(f"""
                <div class="alarm-{sev}">
                  <b>{ic} [{pa.priority}] {pa.alarm.name}</b>
                  <span class="badge-{sev}">{pa.alarm.severity}</span><br>
                  <small style="color:#94a3b8">{pa.alarm.component} · {pa.alarm.timestamp}</small><br>
                  <span style="font-size:13px">{pa.alarm.message}</span>
                </div>
                """, unsafe_allow_html=True)

        # Predictive warnings
        if predictive:
            st.markdown("---")
            st.caption("🔮 Predictive Intelligence")
            for pw in predictive:
                st.markdown(f"""
                <div class="predictive-box">
                  ⚡ <b>PREDICTIVE WARNING — {pw['component']}</b><br>
                  <span style="font-size:13px;color:#fbbf24">{pw['message']}</span>
                </div>
                """, unsafe_allow_html=True)

    with col_rc:
        st.markdown('<div class="section-header">🧠 Intelligent Diagnosis</div>', unsafe_allow_html=True)

        if report.is_healthy():
            st.markdown('<div class="alarm-healthy">✅ <b>No fault detected</b><br><span style="font-size:13px">All systems operating within normal parameters.</span></div>', unsafe_allow_html=True)
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

            # Causal chain
            if report.causal_chain:
                st.caption("📍 Causal Chain")
                for i, step in enumerate(report.causal_chain):
                    prefix = "🔴" if i == 0 else ("🔵" if i == len(report.causal_chain)-1 else "🟡")
                    st.markdown(f"""
                    <div class="chain-node">
                      {prefix} <b>[{step.component}]</b> → {step.description}
                    </div>
                    """, unsafe_allow_html=True)
                    if i < len(report.causal_chain) - 1:
                        st.markdown('<div style="text-align:center;color:#3b82f6;font-size:18px">↓</div>', unsafe_allow_html=True)

    st.divider()

    # ── Recovery Actions ───────────────────────────────────────────
    if not report.is_healthy() and report.recommended_actions:
        st.markdown('<div class="section-header">🔧 Recommended Recovery Actions</div>', unsafe_allow_html=True)

        action_icons = {
            "STOP": "🛑", "INSPECT": "🔍", "CLEAR": "🧹", "CHECK": "✔️",
            "RESTART": "🔄", "REDUCE": "⬇️", "MONITOR": "👁️", "LOG": "📋",
            "VERIFY": "✅", "COOL": "❄️", "CLEAN": "🧼", "ALIGN": "🎯", "TEST": "🧪"
        }

        cols = st.columns(min(len(report.recommended_actions), 3))
        for i, action in enumerate(report.recommended_actions):
            with cols[i % 3]:
                ic = action_icons.get(action.action_type, "▶")
                st.markdown(f"""
                <div class="action-card">
                  <b style="color:#93c5fd">{action.step}</b><br>
                  {ic} <b style="color:#fbbf24">[{action.action_type}]</b><br>
                  <span style="color:#e2e8f0">{action.description}</span>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # ── Trend Charts ───────────────────────────────────────────────
    st.markdown('<div class="section-header">📈 Live Trends</div>', unsafe_allow_html=True)

    if len(h["time"]) > 1:
        df = pd.DataFrame({
            "Time": list(h["time"]),
            "Conveyor Speed (%)": list(h["conveyor_speed"]),
            "Motor Temp (°C)": list(h["motor_temp"]),
            "Motor Current (A)": list(h["motor_current"]),
            "Throughput (ppm)": list(h["throughput"]),
        })

        tc1, tc2 = st.columns(2)

        with tc1:
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(
                x=df["Time"], y=df["Conveyor Speed (%)"],
                mode="lines+markers", name="Conveyor Speed",
                line=dict(color="#3b82f6", width=2),
                fill="tozeroy", fillcolor="rgba(59,130,246,0.1)"
            ))
            fig1.add_hline(y=20, line_dash="dash", line_color="#ef4444",
                           annotation_text="Jam threshold", annotation_font_color="#ef4444")
            fig1.update_layout(
                title="Conveyor Speed", template="plotly_dark",
                paper_bgcolor="#111827", plot_bgcolor="#111827",
                height=220, margin=dict(l=10,r=10,t=40,b=10),
                showlegend=False
            )
            st.plotly_chart(fig1, use_container_width=True)

        with tc2:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df["Time"], y=df["Motor Temp (°C)"],
                mode="lines+markers", name="Motor Temp",
                line=dict(color="#f97316", width=2),
                fill="tozeroy", fillcolor="rgba(249,115,22,0.1)"
            ))
            fig2.add_hline(y=75, line_dash="dash", line_color="#eab308",
                           annotation_text="Warning", annotation_font_color="#eab308")
            fig2.add_hline(y=90, line_dash="dash", line_color="#ef4444",
                           annotation_text="Critical", annotation_font_color="#ef4444")
            fig2.update_layout(
                title="Motor Temperature", template="plotly_dark",
                paper_bgcolor="#111827", plot_bgcolor="#111827",
                height=220, margin=dict(l=10,r=10,t=40,b=10),
                showlegend=False
            )
            st.plotly_chart(fig2, use_container_width=True)

# ─────────────────────────────────────────────
# ENGINEER VIEW
# ─────────────────────────────────────────────

elif role == "Engineer":

    st.markdown('<div class="section-header">🔵 Engineer View — Full Diagnostics</div>', unsafe_allow_html=True)

    # All raw signals
    st.markdown("**Raw Signal Dump**")
    raw_cols = st.columns(6)
    raw_cols[0].metric("Conveyor Speed", f"{state.conveyor_speed:.2f}%")
    raw_cols[1].metric("Motor Temp", f"{state.motor_temp:.2f}°C")
    raw_cols[2].metric("Motor Current", f"{state.motor_current:.2f}A")
    raw_cols[3].metric("Vision", "YES" if state.vision_detected else "NO")
    raw_cols[4].metric("Robot", state.robot_status)
    raw_cols[5].metric("Throughput", f"{state.packages_per_min:.2f}")

    st.divider()

    # ALL alarms including suppressed
    st.markdown("**All Alarms (including suppressed)**")
    if not prioritized:
        st.success("No alarms active.")
    else:
        for pa in prioritized:
            tag = " 🔕 SUPPRESSED" if pa.suppressed else ""
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

    # Dependency graph text
    st.markdown("**Machine Dependency Model**")
    st.code("""
Conveyor
  └── Vision Sensor
        └── Cobot (Robot)
              └── System (Throughput)
  └── Motor (bidirectional — jam causes overcurrent)
    """, language="text")

    st.divider()

    # Alarm log table
    st.markdown("**Alarm History Log**")
    if st.session_state.alarm_log:
        log_df = pd.DataFrame(st.session_state.alarm_log[-50:])
        st.dataframe(log_df, use_container_width=True, height=300)
    else:
        st.info("No alarms logged yet.")

    st.divider()

    # Full trend charts
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
        fig.add_trace(go.Scatter(x=df["Time"], y=df["Motor Temp"], name="Motor Temp °C", line=dict(color="#f97316")))
        fig.add_trace(go.Scatter(x=df["Time"], y=df["Motor Current"], name="Current A", line=dict(color="#a855f7")))
        fig.add_trace(go.Scatter(x=df["Time"], y=df["Throughput"], name="Throughput ppm", line=dict(color="#22c55e")))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#111827",
                          plot_bgcolor="#111827", height=350,
                          margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# MANAGER VIEW
# ─────────────────────────────────────────────

elif role == "Manager":

    st.markdown('<div class="section-header">🟡 Manager View — Production Impact</div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Throughput", f"{state.packages_per_min:.1f} ppm", f"{state.packages_per_min - 12:.1f} vs target")
    m2.metric("Active P1 Alarms", counts["P1"], delta="Critical" if counts["P1"] > 0 else "None", delta_color="inverse" if counts["P1"] > 0 else "off")
    m3.metric("Est. Downtime", report.estimated_downtime if not report.is_healthy() else "None")
    m4.metric("System Status", "FAULT" if not report.is_healthy() else "NORMAL")

    st.divider()

    if not report.is_healthy():
        st.error(f"**Active Fault:** {report.root_cause}")
        st.warning(f"**Production Impact:** Throughput at {state.packages_per_min:.1f} ppm vs 12.0 target — {max(0, 12 - state.packages_per_min):.1f} ppm shortfall")
        loss_per_min = max(0, 12 - state.packages_per_min)
        st.info(f"**Estimated loss this incident:** {loss_per_min * 5:.0f} packages if downtime is 5 min · {loss_per_min * 15:.0f} packages if 15 min")
    else:
        st.success("✅ All systems nominal. Production running at target.")

    st.divider()

    # Throughput trend only
    if len(h["time"]) > 1:
        df = pd.DataFrame({"Time": list(h["time"]), "Throughput": list(h["throughput"])})
        fig = px.area(df, x="Time", y="Throughput", title="Production Throughput (packages/min)",
                      color_discrete_sequence=["#22c55e"])
        fig.add_hline(y=12, line_dash="dash", line_color="#ef4444", annotation_text="Target: 12 ppm")
        fig.update_layout(template="plotly_dark", paper_bgcolor="#111827",
                          plot_bgcolor="#111827", height=300,
                          margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# AUTO REFRESH
# ─────────────────────────────────────────────

if auto_refresh:
    time.sleep(2)
    st.rerun()
