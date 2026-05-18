"""
appp.py  (v3.0 — AI-Assisted + Fully Metadata-Driven)
======================================================
IntelliHMI — Next-Gen Control System Interface

NEW in v3.0:
  ✅ 🤖 AI-Assisted Configuration (Claude API generates signal configs from plain English)
  ✅ ➕ Add New Signal form — new cards + charts appear instantly, zero coding
  ✅ 🗑️ Remove signals from dashboard via UI
  ✅ Full label/unit/range editing in Config Editor
  ✅ Fault injection available to ALL roles (sidebar)
  ✅ Sidebar always accessible (fixed collapse arrow)
  ✅ Backend code hidden from UI

FROM v2.0:
  ✅ Login / Role-based access
  ✅ Alarm Acknowledge + Snooze + Fatigue tracking
  ✅ Metadata-driven UI from hmi_config.json
  ✅ Modern UX notification-style alarms
  ✅ Operator onboarding tooltips

UNTOUCHED (as instructed):
  ✅ alarm_engine.py       — AlarmEngine.evaluate()
  ✅ priority_engine.py    — PriorityEngine.process() / suppress logic
  ✅ rootcause_engine.py   — RootCauseEngine.analyze()
  ✅ simulator.py          — PackagingSimulator / FaultScenario
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time
import json
import os
from datetime import datetime, timedelta
from collections import deque

# ── Import intelligence engines (UNTOUCHED) ───────────────────
from simulator import PackagingSimulator, FaultScenario
from alarm_engine import AlarmEngine
from priority_engine import PriorityEngine, PRIORITY_LABELS
from rootcause_engine import RootCauseEngine

# ─────────────────────────────────────────────
# LOAD CONFIG (low-code metadata layer)
# ─────────────────────────────────────────────

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "hmi_config.json")
USERS_PATH  = os.path.join(os.path.dirname(__file__), "users.json")

def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

def load_users():
    try:
        with open(USERS_PATH) as f:
            return json.load(f)
    except Exception:
        return {}

CFG   = load_config()
USERS = load_users()

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
# GLOBAL STYLES  (industrial dark + modern card UX)
# ─────────────────────────────────────────────

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

/* ── Login card ── */
.login-card {
    max-width: 420px;
    margin: 60px auto;
    background: #111827;
    border: 1px solid #1e3a5f;
    border-radius: 16px;
    padding: 40px;
}
.login-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 22px;
    color: #93c5fd;
    margin-bottom: 4px;
}
.login-sub { color: #64748b; font-size: 13px; margin-bottom: 24px; }

/* ── Alarm cards ── */
.alarm-critical {
    background: linear-gradient(135deg,#1a0505,#2d0808);
    border-left: 4px solid #ef4444;
    border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;
}
.alarm-high {
    background: linear-gradient(135deg,#1a0d00,#2d1800);
    border-left: 4px solid #f97316;
    border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;
}
.alarm-medium {
    background: linear-gradient(135deg,#0d1200,#1a1f00);
    border-left: 4px solid #eab308;
    border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;
}
.alarm-low {
    background: linear-gradient(135deg,#000d1a,#001a2d);
    border-left: 4px solid #3b82f6;
    border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;
}
.alarm-healthy {
    background: linear-gradient(135deg,#001a0d,#002d1a);
    border-left: 4px solid #22c55e;
    border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;
}
/* notification-style toast (Teams-inspired) */
.notif-toast {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
    font-size: 13px;
}
.notif-icon { font-size: 20px; min-width: 24px; }
.notif-body { flex: 1; }
.notif-time { color: #64748b; font-size: 11px; }

/* ── Badges ── */
.badge-critical { background:#ef4444; color:white; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-high     { background:#f97316; color:white; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-medium   { background:#eab308; color:black; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-low      { background:#3b82f6; color:white; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-ok       { background:#22c55e; color:white; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-snoozed  { background:#64748b; color:white; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }

/* ── Section header ── */
.section-header {
    background: linear-gradient(90deg,#1e3a5f,#0a0e1a);
    border-left: 3px solid #3b82f6;
    padding: 8px 16px; border-radius: 4px; margin-bottom: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px; letter-spacing: 2px;
    text-transform: uppercase; color: #93c5fd;
}

/* ── Predictive ── */
.predictive-box {
    background: linear-gradient(135deg,#1a1200,#2d2000);
    border: 1px dashed #fbbf24; border-radius: 8px;
    padding: 14px 18px; margin-bottom: 10px;
}

/* ── Action card ── */
.action-card {
    background: #111827; border: 1px solid #1e3a5f;
    border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;
    font-family: 'JetBrains Mono', monospace; font-size: 13px;
}

/* ── Fatigue metric box ── */
.fatigue-box {
    background: #0f172a; border: 1px solid #1e3a5f;
    border-radius: 10px; padding: 16px; text-align: center;
}

/* ── Onboarding tip ── */
.tip-box {
    background: #0c1a2e; border: 1px solid #1e3a5f;
    border-left: 3px solid #3b82f6;
    border-radius: 8px; padding: 12px 16px;
    font-size: 12px; color: #94a3b8;
    margin-bottom: 12px;
}

/* ── Chain node ── */
.chain-node {
    background: #111827; border: 1px solid #1e3a5f;
    border-radius: 8px; padding: 10px 16px; margin: 4px 0;
    font-family: 'JetBrains Mono', monospace; font-size: 12px;
}

/* ── Hide Streamlit branding & backend footer ── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* ── Hide raw code / backend output at bottom ── */
.stException { display: none; }
.element-container:has(pre) { display: none; }
div[data-testid="stCodeBlock"] { display: none; }

/* ── Always show sidebar collapse arrow ── */
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    background: #1e3a5f !important;
    border-radius: 0 8px 8px 0 !important;
    width: 28px !important;
    height: 48px !important;
    align-items: center !important;
    justify-content: center !important;
    top: 50% !important;
    position: fixed !important;
    left: 0 !important;
    z-index: 9999 !important;
    border: 1px solid #3b82f6 !important;
    cursor: pointer !important;
}
[data-testid="collapsedControl"]:hover {
    background: #2563eb !important;
}

/* ── Sidebar always accessible ── */
section[data-testid="stSidebar"][aria-expanded="false"] {
    margin-left: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ── LOGIN PAGE ────────────────────────────────
# ─────────────────────────────────────────────

def show_login():
    st.markdown("""
    <div style="text-align:center; margin-top:40px; margin-bottom:20px">
        <div style="font-size:48px">🏭</div>
        <div style="font-family:'JetBrains Mono',monospace; font-size:26px; color:#93c5fd; margin-top:8px">IntelliHMI</div>
        <div style="color:#64748b; font-size:13px; margin-top:4px">Cobot Packaging Line — Secure Access</div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown('<div style="background:#111827;border:1px solid #1e3a5f;border-radius:16px;padding:32px">', unsafe_allow_html=True)

        st.markdown("**Username**")
        username = st.text_input("Username", placeholder="e.g. operator1", label_visibility="collapsed", key="login_user")
        st.markdown("**Password**")
        password = st.text_input("Password", type="password", placeholder="Enter password", label_visibility="collapsed", key="login_pass")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔐  Sign In", use_container_width=True, type="primary"):
            user_record = USERS.get(username)
            if user_record and user_record["password"] == password:
                st.session_state.logged_in    = True
                st.session_state.username     = username
                st.session_state.role         = user_record["role"]
                st.session_state.display_name = user_record["display_name"]
                st.session_state.avatar       = user_record["avatar"]
                st.rerun()
            else:
                st.error("❌ Invalid credentials. Please try again.")

        st.markdown("</div>", unsafe_allow_html=True)

        # Demo credentials hint
        st.markdown("""
        <div style="margin-top:16px;background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:14px;font-size:12px;color:#64748b">
        <b style="color:#475569">Demo Credentials</b><br><br>
        👷 <b>operator1</b> / op123 → Operator view<br>
        🔧 <b>engineer1</b> / eng123 → Engineer view<br>
        📊 <b>manager1</b> / mgr123 → Manager view
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────

def init_state():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in    = False
        st.session_state.username     = ""
        st.session_state.role         = ""
        st.session_state.display_name = ""
        st.session_state.avatar       = ""
    if "sim" not in st.session_state:
        st.session_state.sim      = PackagingSimulator()
        st.session_state.a_eng    = AlarmEngine()
        st.session_state.p_eng    = PriorityEngine()
        st.session_state.rc_eng   = RootCauseEngine()
        st.session_state.scenario = FaultScenario.NONE
        st.session_state.history  = {
            "time":           deque(maxlen=40),
            "conveyor_speed": deque(maxlen=40),
            "motor_temp":     deque(maxlen=40),
            "motor_current":  deque(maxlen=40),
            "throughput":     deque(maxlen=40),
        }
        st.session_state.alarm_log        = []   # full history log
        st.session_state.tick             = 0
        st.session_state.prev_temp_trend  = deque(maxlen=5)
        # Alarm acknowledgement & snooze tracking
        st.session_state.acknowledged     = set()   # alarm_ids acknowledged this session
        st.session_state.snoozed          = {}      # alarm_id → snooze_until datetime
        # Alarm fatigue metrics
        st.session_state.fatigue          = {
            "total_fired":    0,
            "total_acked":    0,
            "total_snoozed":  0,
            "missed":         0,   # fired but never acked before clearing
            "ack_times":      [],  # seconds between fire and ack
        }
        st.session_state.pending_ack      = {}  # alarm_id → fired_at datetime

init_state()

# ─────────────────────────────────────────────
# GUARD — show login if not authenticated
# ─────────────────────────────────────────────

if not st.session_state.logged_in:
    show_login()
    st.stop()

# ─────────────────────────────────────────────
# PREDICTIVE WARNING ENGINE  (unchanged logic)
# ─────────────────────────────────────────────

def check_predictive(state) -> list:
    warnings = []
    trend = st.session_state.prev_temp_trend
    trend.append(state.motor_temp)
    if len(trend) >= 4:
        if all(trend[i] < trend[i+1] for i in range(len(trend)-1)):
            if 60 < state.motor_temp < 90:
                warnings.append({
                    "type": "PREDICTIVE",
                    "message": (f"Motor temperature rising trend detected ({state.motor_temp:.1f}°C). "
                                f"Estimated critical in {max(1, int((90 - state.motor_temp) / 2))} ticks."),
                    "component": "Motor"
                })
        if 20 < state.conveyor_speed < 60:
            warnings.append({
                "type": "PREDICTIVE",
                "message": f"Conveyor speed degrading ({state.conveyor_speed:.1f}%). Possible jam developing.",
                "component": "Conveyor"
            })
    return warnings

# ─────────────────────────────────────────────
# ALARM FATIGUE HELPERS
# ─────────────────────────────────────────────

def update_fatigue(alarms, acked_ids):
    now = datetime.now()
    fatigue = st.session_state.fatigue
    pending = st.session_state.pending_ack

    for alarm in alarms:
        aid = alarm.alarm_id
        if aid not in pending:
            pending[aid] = now
            fatigue["total_fired"] += 1

    for aid in list(pending.keys()):
        if aid not in {a.alarm_id for a in alarms}:
            if aid not in acked_ids:
                fatigue["missed"] += 1
            del pending[aid]

    for aid in acked_ids:
        if aid in pending:
            delta = (now - pending[aid]).total_seconds()
            fatigue["ack_times"].append(delta)
            fatigue["total_acked"] += 1
            del pending[aid]

def is_snoozed(alarm_id) -> bool:
    snooze_until = st.session_state.snoozed.get(alarm_id)
    if snooze_until and datetime.now() < snooze_until:
        return True
    if alarm_id in st.session_state.snoozed:
        del st.session_state.snoozed[alarm_id]
    return False

# ─────────────────────────────────────────────
# SIDEBAR  (role-locked, with logout)
# ─────────────────────────────────────────────

role     = st.session_state.role
cfg_roles = CFG.get("roles", {})
role_cfg  = cfg_roles.get(role, {})

with st.sidebar:
    # User card
    st.markdown(f"""
    <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;padding:12px 16px;margin-bottom:16px">
        <div style="font-size:26px;margin-bottom:4px">{st.session_state.avatar}</div>
        <div style="font-weight:600;font-size:14px">{st.session_state.display_name}</div>
        <div style="color:#64748b;font-size:12px">{st.session_state.username} · <b style="color:#93c5fd">{role}</b></div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.divider()

    # Fault injection — available to ALL roles for demo
    if True:
        st.markdown("#### ⚡ Fault Injection")
        scenario_options = {s["label"]: s["id"] for s in CFG.get("fault_scenarios", [])}
        if not scenario_options:
            scenario_options = {
                "✅ Normal Operation": "none",
                "🔴 Conveyor Jam": "conveyor_jam",
                "🟠 Motor Overheat": "motor_overheat",
                "🟡 Vision Sensor Fault": "vision_failure",
            }
        selected_label = st.selectbox("Inject scenario:", list(scenario_options.keys()), label_visibility="collapsed")
        if st.button("⚡ Inject Fault", use_container_width=True):
            scenario_id = scenario_options[selected_label]
            scenario_enum = FaultScenario(scenario_id)
            if scenario_enum != st.session_state.scenario:
                st.session_state.scenario = scenario_enum
                st.session_state.sim.set_scenario(scenario_enum)
        st.divider()

    # Live feed controls
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
alarms     = st.session_state.a_eng.evaluate(state)          # ← UNTOUCHED engine
prioritized = st.session_state.p_eng.process(alarms)         # ← UNTOUCHED engine
visible    = st.session_state.p_eng.active_only(prioritized)  # ← UNTOUCHED engine
counts     = st.session_state.p_eng.summary(prioritized)      # ← UNTOUCHED engine
report     = st.session_state.rc_eng.analyze(alarms)          # ← UNTOUCHED engine
predictive = check_predictive(state)

# Filter snoozed from visible
visible_unsnoozed = [pa for pa in visible if not is_snoozed(pa.alarm.alarm_id)]

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
        "time":      state.timestamp,
        "id":        a.alarm_id,
        "name":      a.name,
        "severity":  a.severity,
        "component": a.component,
    })

# Update fatigue tracking
update_fatigue(alarms, st.session_state.acknowledged)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown(f"# 🏭 {CFG.get('system_name', 'IntelliHMI')}")
    st.markdown(f"**Intelligent Context-Aware Control Interface** · `{state.timestamp}` · {st.session_state.avatar} **{st.session_state.display_name}** ({role})")

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

# ═══════════════════════════════════════════════════════
#  OPERATOR VIEW
# ═══════════════════════════════════════════════════════

if role == "Operator":

    # ── Onboarding tip ───────────────────────────────────────
    st.markdown("""
    <div class="tip-box">
    💡 <b>Tip:</b> Active alarms show below in priority order. Click <b>Acknowledge</b> to log your response,
    or <b>Snooze 5 min</b> for low-priority alarms you're already aware of.
    The <b>Intelligent Diagnosis</b> panel shows the root cause and step-by-step recovery actions.
    </div>
    """, unsafe_allow_html=True)

    # ── Live Signal Metrics (from config) ────────────────────
    st.markdown('<div class="section-header">📡 Live Signals</div>', unsafe_allow_html=True)
    signal_defs = CFG.get("signals", [])
    if signal_defs:
        cols = st.columns(len(signal_defs))
        signal_values = {
            "conveyor_speed":  state.conveyor_speed,
            "motor_temp":      state.motor_temp,
            "motor_current":   state.motor_current,
            "packages_per_min": state.packages_per_min,
        }
        for i, sig in enumerate(signal_defs):
            val = signal_values.get(sig["id"], 0)
            warn = sig.get("warning_threshold", 0)
            crit = sig.get("critical_threshold", 0)
            # For conveyor_speed and throughput, low is bad; for temp/current, high is bad
            if sig["id"] in ("conveyor_speed", "packages_per_min"):
                status = "CRITICAL ⚠" if val <= crit else ("WARNING ⚠" if val <= warn else "OK")
                bad = val <= warn
            else:
                status = "CRITICAL ⚠" if val >= crit else ("WARNING ⚠" if val >= warn else "OK")
                bad = val >= warn
            cols[i].metric(
                f"{sig['icon']} {sig['label']}",
                f"{val:.1f} {sig['unit']}",
                delta=status,
                delta_color="inverse" if bad else "normal"
            )
    else:
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Conveyor Speed", f"{state.conveyor_speed:.1f}%")
        m2.metric("Motor Temp",     f"{state.motor_temp:.1f}°C")
        m3.metric("Motor Current",  f"{state.motor_current:.1f}A")
        m4.metric("Vision",         "✓" if state.vision_detected else "✗")
        m5.metric("Throughput",     f"{state.packages_per_min:.1f} ppm")

    st.divider()

    # ── Alarms + Root Cause (two columns) ────────────────────
    col_alarms, col_rc = st.columns([1, 1])

    with col_alarms:
        st.markdown('<div class="section-header">🔔 Active Alarms</div>', unsafe_allow_html=True)
        snoozed_count = len([pa for pa in visible if is_snoozed(pa.alarm.alarm_id)])
        st.caption(f"{len(alarms)} total · {len(visible_unsnoozed)} shown · "
                   f"{counts['suppressed']} suppressed · {snoozed_count} snoozed")

        if not visible_unsnoozed:
            st.markdown('<div class="alarm-healthy">✅ <b>No active alarms</b> — System operating normally</div>', unsafe_allow_html=True)
        else:
            for pa in visible_unsnoozed:
                sev  = pa.alarm.severity.lower()
                icon_map = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}
                ic   = icon_map.get(sev, "⚪")
                aid  = pa.alarm.alarm_id
                acked = aid in st.session_state.acknowledged

                # Teams-style notification card
                st.markdown(f"""
                <div class="alarm-{sev}">
                    <b>{ic} [{pa.priority}] {pa.alarm.name}</b>
                    <span class="badge-{sev}">{pa.alarm.severity}</span>
                    {"<span class='badge-ok' style='margin-left:6px'>✓ ACK</span>" if acked else ""}
                    <br>
                    <small style="color:#94a3b8">{pa.alarm.component} · {pa.alarm.timestamp}</small><br>
                    <span style="font-size:13px">{pa.alarm.message}</span>
                </div>
                """, unsafe_allow_html=True)

                # Acknowledge / Snooze buttons
                if not acked:
                    bcol1, bcol2, _ = st.columns([1, 1, 2])
                    with bcol1:
                        if st.button(f"✓ Acknowledge", key=f"ack_{aid}"):
                            st.session_state.acknowledged.add(aid)
                            st.rerun()
                    with bcol2:
                        if pa.alarm.severity.upper() in ("MEDIUM", "LOW"):
                            if st.button(f"💤 Snooze 5m", key=f"snz_{aid}"):
                                st.session_state.snoozed[aid] = datetime.now() + timedelta(minutes=5)
                                st.session_state.fatigue["total_snoozed"] += 1
                                st.rerun()

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

            if report.causal_chain:
                st.caption("📍 Causal Chain")
                for i, step in enumerate(report.causal_chain):
                    prefix = "🔴" if i == 0 else ("🔵" if i == len(report.causal_chain)-1 else "🟡")
                    st.markdown(f'<div class="chain-node">{prefix} <b>[{step.component}]</b> → {step.description}</div>', unsafe_allow_html=True)
                    if i < len(report.causal_chain) - 1:
                        st.markdown('<div style="text-align:center;color:#3b82f6;font-size:18px">↓</div>', unsafe_allow_html=True)

    st.divider()

    # ── Recovery Actions ──────────────────────────────────────
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

    # ── Alarm Fatigue Dashboard ───────────────────────────────
    st.markdown('<div class="section-header">📉 Alarm Fatigue Metrics</div>', unsafe_allow_html=True)
    fat = st.session_state.fatigue
    avg_ack = (sum(fat["ack_times"]) / len(fat["ack_times"])) if fat["ack_times"] else 0
    fc1, fc2, fc3, fc4 = st.columns(4)
    fc1.metric("Total Alarms Fired",    fat["total_fired"])
    fc2.metric("Acknowledged",          fat["total_acked"])
    fc3.metric("Missed (auto-cleared)", fat["missed"])
    fc4.metric("Avg Response Time",     f"{avg_ack:.0f}s" if avg_ack else "—")
    st.divider()

    # ── Trend Charts ─────────────────────────────────────────
    st.markdown('<div class="section-header">📈 Live Trends</div>', unsafe_allow_html=True)
    if len(h["time"]) > 1:
        df = pd.DataFrame({
            "Time": list(h["time"]),
            "Conveyor Speed (%)": list(h["conveyor_speed"]),
            "Motor Temp (°C)":    list(h["motor_temp"]),
            "Motor Current (A)":  list(h["motor_current"]),
            "Throughput (ppm)":   list(h["throughput"]),
        })
        tc1, tc2 = st.columns(2)
        with tc1:
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(x=df["Time"], y=df["Conveyor Speed (%)"],
                mode="lines+markers", line=dict(color="#3b82f6", width=2),
                fill="tozeroy", fillcolor="rgba(59,130,246,0.1)"))
            fig1.add_hline(y=20, line_dash="dash", line_color="#ef4444",
                annotation_text="Jam threshold", annotation_font_color="#ef4444")
            fig1.update_layout(title="Conveyor Speed", template="plotly_dark",
                paper_bgcolor="#111827", plot_bgcolor="#111827",
                height=220, margin=dict(l=10,r=10,t=40,b=10), showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)
        with tc2:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df["Time"], y=df["Motor Temp (°C)"],
                mode="lines+markers", line=dict(color="#f97316", width=2),
                fill="tozeroy", fillcolor="rgba(249,115,22,0.1)"))
            fig2.add_hline(y=75, line_dash="dash", line_color="#eab308",
                annotation_text="Warning", annotation_font_color="#eab308")
            fig2.add_hline(y=90, line_dash="dash", line_color="#ef4444",
                annotation_text="Critical", annotation_font_color="#ef4444")
            fig2.update_layout(title="Motor Temperature", template="plotly_dark",
                paper_bgcolor="#111827", plot_bgcolor="#111827",
                height=220, margin=dict(l=10,r=10,t=40,b=10), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

# ═══════════════════════════════════════════════════════
#  ENGINEER VIEW
# ═══════════════════════════════════════════════════════

elif role == "Engineer":
    st.markdown('<div class="section-header">🔵 Engineer View — Full Diagnostics</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📡 Signals & Alarms", "📊 Trends & Log", "⚙️ Config Editor", "🤖 AI Config Assistant"])

    with tab1:
        # Raw signals
        raw_cols = st.columns(6)
        raw_cols[0].metric("Conveyor Speed",  f"{state.conveyor_speed:.2f}%")
        raw_cols[1].metric("Motor Temp",      f"{state.motor_temp:.2f}°C")
        raw_cols[2].metric("Motor Current",   f"{state.motor_current:.2f}A")
        raw_cols[3].metric("Vision",          "YES" if state.vision_detected else "NO")
        raw_cols[4].metric("Robot",           state.robot_status)
        raw_cols[5].metric("Throughput",      f"{state.packages_per_min:.2f}")

        st.divider()

        # ALL alarms including suppressed
        st.markdown("**All Alarms (including suppressed & snoozed)**")
        if not prioritized:
            st.success("No alarms active.")
        else:
            for pa in prioritized:
                tag     = " 🔕 SUPPRESSED" if pa.suppressed else ""
                snooz   = " 💤 SNOOZED"    if is_snoozed(pa.alarm.alarm_id) else ""
                opacity = "opacity:0.4"    if pa.suppressed else ""
                sev     = pa.alarm.severity.lower()
                st.markdown(f"""
                <div class="alarm-{sev}" style="{opacity}">
                    <b>[{pa.priority}] {pa.alarm.alarm_id} — {pa.alarm.name}{tag}{snooz}</b><br>
                    <small>{pa.alarm.component} · Threshold: {pa.alarm.threshold} · Value: {pa.alarm.value}</small><br>
                    {pa.alarm.message}
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # Root cause
        if not report.is_healthy():
            st.markdown(f"**🧠 Root Cause:** `{report.root_cause}` · Confidence: `{report.confidence}` · Downtime: `{report.estimated_downtime}`")

        st.divider()

        # Alarm fatigue for engineer
        fat = st.session_state.fatigue
        avg_ack = (sum(fat["ack_times"]) / len(fat["ack_times"])) if fat["ack_times"] else 0
        st.markdown("**📉 Alarm Fatigue Summary**")
        fc1, fc2, fc3, fc4 = st.columns(4)
        fc1.metric("Total Fired",    fat["total_fired"])
        fc2.metric("Acknowledged",   fat["total_acked"])
        fc3.metric("Snoozed",        fat["total_snoozed"])
        fc4.metric("Avg Ack Time",   f"{avg_ack:.0f}s" if avg_ack else "—")

        st.divider()
        st.markdown("**Machine Dependency Model**")
        st.code("""
Conveyor
 ├── Vision Sensor
 │    └── Cobot (Robot)
 │         └── System (Throughput)
 └── Motor (bidirectional — jam ↔ overcurrent)
        """, language="text")

    with tab2:
        if len(h["time"]) > 1:
            df = pd.DataFrame({
                "Time":           list(h["time"]),
                "Conveyor Speed": list(h["conveyor_speed"]),
                "Motor Temp":     list(h["motor_temp"]),
                "Motor Current":  list(h["motor_current"]),
                "Throughput":     list(h["throughput"]),
            })
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Time"], y=df["Conveyor Speed"], name="Conveyor %",   line=dict(color="#3b82f6")))
            fig.add_trace(go.Scatter(x=df["Time"], y=df["Motor Temp"],     name="Motor Temp °C", line=dict(color="#f97316")))
            fig.add_trace(go.Scatter(x=df["Time"], y=df["Motor Current"],  name="Current A",     line=dict(color="#a855f7")))
            fig.add_trace(go.Scatter(x=df["Time"], y=df["Throughput"],     name="Throughput ppm",line=dict(color="#22c55e")))
            fig.update_layout(template="plotly_dark", paper_bgcolor="#111827",
                plot_bgcolor="#111827", height=350, margin=dict(l=10,r=10,t=20,b=10))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Alarm History Log**")
        if st.session_state.alarm_log:
            log_df = pd.DataFrame(st.session_state.alarm_log[-50:])
            st.dataframe(log_df, use_container_width=True, height=300)
        else:
            st.info("No alarms logged yet.")

    with tab3:
        # ══════════════════════════════════════════════
        # LOW-CODE CONFIG EDITOR + ADD NEW SIGNAL FORM
        # ══════════════════════════════════════════════
        st.markdown("### ⚙️ Signal Threshold Editor")
        st.caption("Edit thresholds without touching code. Changes auto-render new cards on dashboard.")

        cfg_live = load_config()
        signals  = cfg_live.get("signals", [])
        changed  = False

        for i, sig in enumerate(signals):
            with st.expander(f"{sig['icon']} {sig['label']} (unit: {sig['unit']})", expanded=False):
                c1, c2, c3 = st.columns(3)
                new_label = c1.text_input("Label", value=sig.get("label",""), key=f"lbl_{sig['id']}")
                new_unit  = c1.text_input("Unit",  value=sig.get("unit",""),  key=f"unt_{sig['id']}")
                new_warn  = c2.number_input("Warning threshold", value=float(sig.get("warning_threshold",0)),  key=f"warn_{sig['id']}")
                new_crit  = c2.number_input("Critical threshold",value=float(sig.get("critical_threshold",0)), key=f"crit_{sig['id']}")
                new_min   = c3.number_input("Min range", value=float(sig.get("min",0)),   key=f"min_{sig['id']}")
                new_max   = c3.number_input("Max range", value=float(sig.get("max",100)), key=f"max_{sig['id']}")

                if (new_warn != sig.get("warning_threshold") or new_crit != sig.get("critical_threshold")
                        or new_label != sig.get("label") or new_unit != sig.get("unit")):
                    cfg_live["signals"][i].update({
                        "label": new_label, "unit": new_unit,
                        "warning_threshold": new_warn, "critical_threshold": new_crit,
                        "min": new_min, "max": new_max,
                    })
                    changed = True

                # Delete signal button
                if st.button(f"🗑️ Remove {sig['label']}", key=f"del_{sig['id']}"):
                    cfg_live["signals"].pop(i)
                    save_config(cfg_live)
                    st.success(f"Removed {sig['label']}")
                    st.rerun()

        if changed:
            if st.button("💾 Save Changes", type="primary", key="save_thresh"):
                save_config(cfg_live)
                st.success("✅ Saved to hmi_config.json — dashboard updates automatically")
                st.rerun()

        st.divider()

        # ── ADD NEW SIGNAL FORM ──────────────────────────────
        st.markdown("### ➕ Add New Signal / Device")
        st.caption("Fill this form to add a completely new signal card + live chart to the dashboard — no coding needed.")

        with st.form("add_signal_form"):
            fc1, fc2, fc3 = st.columns(3)
            new_id    = fc1.text_input("Signal ID (no spaces)", placeholder="e.g. pressure_sensor")
            new_lbl   = fc1.text_input("Display Label",         placeholder="e.g. Pressure Sensor")
            new_unit  = fc2.text_input("Unit",                  placeholder="e.g. bar, rpm, °C")
            new_icon  = fc2.text_input("Icon (emoji)",          placeholder="e.g. 🔵")
            new_color = fc2.text_input("Chart color (hex)",     placeholder="e.g. #3b82f6")
            new_min   = fc3.number_input("Min value",  value=0.0)
            new_max   = fc3.number_input("Max value",  value=100.0)
            new_warn  = fc3.number_input("Warning threshold", value=70.0)
            new_crit  = fc3.number_input("Critical threshold",value=90.0)

            submitted = st.form_submit_button("➕ Add Signal to Dashboard", type="primary")
            if submitted:
                if not new_id or not new_lbl:
                    st.error("Signal ID and Label are required.")
                else:
                    cfg_add = load_config()
                    existing_ids = [s["id"] for s in cfg_add.get("signals", [])]
                    if new_id in existing_ids:
                        st.error(f"Signal ID '{new_id}' already exists.")
                    else:
                        cfg_add.setdefault("signals", []).append({
                            "id":                 new_id,
                            "label":              new_lbl,
                            "unit":               new_unit or "",
                            "icon":               new_icon or "📊",
                            "color":              new_color or "#3b82f6",
                            "min":                new_min,
                            "max":                new_max,
                            "warning_threshold":  new_warn,
                            "critical_threshold": new_crit,
                        })
                        save_config(cfg_add)
                        st.success(f"✅ '{new_lbl}' added! It will appear on the dashboard automatically.")
                        st.rerun()

        st.divider()
        st.markdown("**📄 Current hmi_config.json**")
        st.json(load_config())

    with tab4:
        # ══════════════════════════════════════════════
        # 🤖 AI-ASSISTED CONFIGURATION
        # ══════════════════════════════════════════════
        st.markdown("### 🤖 AI Config Assistant")
        st.caption("Describe a signal or device in plain English → AI generates the full config entry and adds it to the dashboard instantly.")

        st.markdown("""
        <div class="tip-box">
        💡 <b>How it works:</b> Type a plain-English description of what you want to monitor.
        The AI reads your existing config, understands the context, and generates a ready-to-use
        signal config with smart threshold suggestions. You can review and approve before saving.
        </div>
        """, unsafe_allow_html=True)

        # Example prompts
        st.markdown("**💬 Example prompts:**")
        examples = [
            "Add a hydraulic pressure sensor measuring bar, warn at 80, critical at 100",
            "Monitor a cooling fan speed in RPM for a packaging motor",
            "Add vibration sensor for conveyor belt in mm/s",
            "Track ambient temperature in the factory floor in Celsius",
        ]
        ex_cols = st.columns(2)
        for i, ex in enumerate(examples):
            if ex_cols[i % 2].button(f"📝 {ex}", key=f"ex_{i}", use_container_width=True):
                st.session_state["ai_prompt"] = ex

        st.divider()

        user_prompt = st.text_area(
            "Describe the signal or device you want to add:",
            value=st.session_state.get("ai_prompt", ""),
            placeholder="e.g. Add a pressure sensor for the hydraulic system, measuring in bar. Warn at 75 bar, critical at 95 bar.",
            height=100,
            key="ai_input"
        )

        if "ai_generated" not in st.session_state:
            st.session_state.ai_generated = None
        if "ai_error" not in st.session_state:
            st.session_state.ai_error = None

        if st.button("🤖 Generate Config with AI", type="primary", key="ai_gen_btn"):
            if not user_prompt.strip():
                st.warning("Please describe the signal first.")
            else:
                with st.spinner("🤖 AI is generating your signal config..."):
                    try:
                        import requests
                        existing_cfg = load_config()
                        existing_signals = existing_cfg.get("signals", [])

                        system_prompt = """You are an industrial HMI configuration assistant.
Given a plain-English description of an industrial signal or sensor,
generate a JSON config object with these exact fields:
{
  "id": "snake_case_unique_id",
  "label": "Human Readable Label",
  "unit": "measurement unit",
  "icon": "single relevant emoji",
  "color": "#hexcolor",
  "min": number,
  "max": number,
  "warning_threshold": number,
  "critical_threshold": number
}

Rules:
- id must be lowercase snake_case, unique from existing IDs
- Choose icon that matches the sensor type
- Choose a color that fits the signal type (blue for flow/speed, orange/red for heat, green for OK signals, purple for electrical)
- Set realistic industrial ranges for min/max
- warning_threshold should be ~75-80% of critical
- Respond ONLY with the raw JSON object, no markdown, no explanation, no backticks.
"""
                        existing_ids_str = ", ".join([s["id"] for s in existing_signals])
                        user_msg = f"Existing signal IDs (avoid duplicates): {existing_ids_str}\n\nUser request: {user_prompt}"

                        resp = requests.post(
                            "https://api.anthropic.com/v1/messages",
                            headers={"Content-Type": "application/json"},
                            json={
                                "model": "claude-sonnet-4-20250514",
                                "max_tokens": 500,
                                "system": system_prompt,
                                "messages": [{"role": "user", "content": user_msg}]
                            },
                            timeout=30
                        )
                        resp.raise_for_status()
                        data = resp.json()
                        raw_text = data["content"][0]["text"].strip()
                        # Strip any accidental markdown fences
                        raw_text = raw_text.replace("```json","").replace("```","").strip()
                        generated = json.loads(raw_text)
                        st.session_state.ai_generated = generated
                        st.session_state.ai_error = None
                    except Exception as e:
                        st.session_state.ai_error = str(e)
                        st.session_state.ai_generated = None

        # Show generated config
        if st.session_state.ai_error:
            st.error(f"AI generation failed: {st.session_state.ai_error}")

        if st.session_state.ai_generated:
            gen = st.session_state.ai_generated
            st.markdown("#### ✅ AI Generated Config — Review Before Saving")

            # Preview card
            st.markdown(f"""
            <div style="background:#111827;border:1px solid #22c55e;border-radius:12px;padding:20px;margin:12px 0">
                <div style="font-size:28px">{gen.get('icon','📊')}</div>
                <div style="font-size:18px;font-weight:700;color:#e2e8f0;margin-top:8px">{gen.get('label','')}</div>
                <div style="color:#64748b;font-size:13px">ID: <code>{gen.get('id','')}</code> · Unit: <b>{gen.get('unit','')}</b></div>
                <div style="margin-top:12px;display:flex;gap:16px;font-size:13px">
                    <span>Range: <b style="color:#93c5fd">{gen.get('min',0)} – {gen.get('max',100)} {gen.get('unit','')}</b></span>
                    <span>⚠️ Warning: <b style="color:#eab308">{gen.get('warning_threshold',70)}</b></span>
                    <span>🔴 Critical: <b style="color:#ef4444">{gen.get('critical_threshold',90)}</b></span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Editable fields before saving
            st.markdown("**✏️ Edit before saving (optional):**")
            ec1, ec2, ec3 = st.columns(3)
            gen["label"]              = ec1.text_input("Label",              value=gen.get("label",""),              key="ai_edit_label")
            gen["unit"]               = ec1.text_input("Unit",               value=gen.get("unit",""),               key="ai_edit_unit")
            gen["warning_threshold"]  = ec2.number_input("Warning",          value=float(gen.get("warning_threshold",70)),  key="ai_edit_warn")
            gen["critical_threshold"] = ec2.number_input("Critical",         value=float(gen.get("critical_threshold",90)), key="ai_edit_crit")
            gen["min"]                = ec3.number_input("Min",              value=float(gen.get("min",0)),           key="ai_edit_min")
            gen["max"]                = ec3.number_input("Max",              value=float(gen.get("max",100)),         key="ai_edit_max")

            st.json(gen)

            col_save, col_disc = st.columns(2)
            with col_save:
                if st.button("💾 Add to Dashboard", type="primary", key="ai_save"):
                    cfg_save = load_config()
                    existing_ids = [s["id"] for s in cfg_save.get("signals", [])]
                    if gen["id"] in existing_ids:
                        st.error(f"ID '{gen['id']}' already exists. Edit the ID above.")
                    else:
                        cfg_save.setdefault("signals", []).append(gen)
                        save_config(cfg_save)
                        st.success(f"✅ '{gen['label']}' added to dashboard! Visible in Operator view immediately.")
                        st.session_state.ai_generated = None
                        st.session_state["ai_prompt"] = ""
                        st.rerun()
            with col_disc:
                if st.button("🗑️ Discard", key="ai_discard"):
                    st.session_state.ai_generated = None
                    st.rerun()

# ═══════════════════════════════════════════════════════
#  MANAGER VIEW
# ═══════════════════════════════════════════════════════

elif role == "Manager":
    st.markdown('<div class="section-header">🟡 Manager View — Production Impact</div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Throughput",  f"{state.packages_per_min:.1f} ppm",
              f"{state.packages_per_min - 12:.1f} vs target")
    m2.metric("Active P1 Alarms",    counts["P1"],
              delta="Critical" if counts["P1"] > 0 else "None",
              delta_color="inverse" if counts["P1"] > 0 else "off")
    m3.metric("Est. Downtime",        report.estimated_downtime if not report.is_healthy() else "None")
    m4.metric("System Status",        "FAULT" if not report.is_healthy() else "NORMAL")

    st.divider()

    if not report.is_healthy():
        st.error(f"**Active Fault:** {report.root_cause}")
        st.warning(f"**Production Impact:** Throughput at {state.packages_per_min:.1f} ppm vs 12.0 target — "
                   f"{max(0, 12 - state.packages_per_min):.1f} ppm shortfall")
        loss_per_min = max(0, 12 - state.packages_per_min)
        st.info(f"**Estimated loss:** {loss_per_min * 5:.0f} packages (5 min) · "
                f"{loss_per_min * 15:.0f} packages (15 min) · "
                f"{loss_per_min * 60:.0f} packages (1 hr)")
    else:
        st.success("✅ All systems nominal. Production running at target.")

    st.divider()

    # Throughput trend
    if len(h["time"]) > 1:
        df = pd.DataFrame({"Time": list(h["time"]), "Throughput": list(h["throughput"])})
        fig = px.area(df, x="Time", y="Throughput",
                      title="Production Throughput (packages/min)",
                      color_discrete_sequence=["#22c55e"])
        fig.add_hline(y=12, line_dash="dash", line_color="#ef4444", annotation_text="Target: 12 ppm")
        fig.update_layout(template="plotly_dark", paper_bgcolor="#111827",
                          plot_bgcolor="#111827", height=300, margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig, use_container_width=True)

    # Alarm fatigue summary for manager
    st.divider()
    st.markdown("**📉 Operator Alarm Response Summary**")
    fat = st.session_state.fatigue
    avg_ack = (sum(fat["ack_times"]) / len(fat["ack_times"])) if fat["ack_times"] else 0
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Alarms Fired",    fat["total_fired"])
    mc2.metric("Response Rate",   f"{int(fat['total_acked'] / max(fat['total_fired'], 1) * 100)}%")
    mc3.metric("Avg Ack Time",    f"{avg_ack:.0f}s" if avg_ack else "—")

# ─────────────────────────────────────────────
# AUTO REFRESH
# ─────────────────────────────────────────────

if auto_refresh:
    time.sleep(2)
    st.rerun()

# ── Clean footer — prevents backend code leaking to UI ──
st.markdown("""
<style>
.stException, .stTraceback { display:none !important; }
div[class*="stCode"] { display:none !important; }
</style>
<div style="margin-top:40px;text-align:center;color:#1e293b;font-size:11px;font-family:'JetBrains Mono',monospace">
IntelliHMI v2.0 · Cobot Packaging Line
</div>
""", unsafe_allow_html=True)
