"""TicketPilot — support operations dashboard. Run: streamlit run dashboard.py"""
import html
import os
from collections import Counter

import pandas as pd
import altair as alt
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(page_title="TicketPilot | Support workspace", page_icon="🎫", layout="wide", initial_sidebar_state="collapsed")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {color-scheme:light!important}
html,body,[data-testid="stApp"],.stApp,button,input,textarea,select {font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif!important}
[data-testid="stAppViewContainer"], [data-testid="stApp"],.stApp {background:#F7F9FC!important;color:#18243A!important}
[data-testid="stHeader"] {background:#F7F9FC!important;height:2.8rem}
[data-testid="stMainBlockContainer"] {max-width:1240px!important;padding:3.5rem 2rem 3rem!important}
[data-testid="stSidebar"] {display:none}
[data-testid="stVerticalBlock"] {gap:.85rem}
h1,h2,h3,p {font-family:'Inter',sans-serif!important}
h1,h2,h3 {color:#18243A!important;letter-spacing:-.045em!important}
h1 {font-size:1.85rem!important;line-height:1.2!important}
p {line-height:1.55}
.tp-top {display:flex;align-items:center;justify-content:space-between;padding:12px 0 12px;border-bottom:1px solid #E4EAF2;margin-bottom:8px}
.tp-brand {display:flex;gap:10px;align-items:center;font-size:20px;font-weight:800;letter-spacing:-.05em;color:#15233B}
.tp-logo {display:grid;place-items:center;width:36px;height:36px;border-radius:10px;background:#4F46E5;color:#fff;font-size:19px}
.tp-kicker {font-size:10px;font-weight:800;letter-spacing:.13em;text-transform:uppercase;color:#635BCA;margin:0 0 5px}
.tp-intro {margin:7px 0 12px}
.tp-intro h1 {font-size:24px!important;margin:0 0 5px!important}
.tp-muted {color:#64748B;font-size:13px;line-height:1.6}
.tp-panel {background:white;border:1px solid #E4EAF2;border-radius:13px;padding:18px 20px;margin:8px 0 12px}
.tp-panel h3 {font-size:16px!important;margin:0 0 5px}
.tp-small {font-size:11px;color:#7B8799}
.tp-chip {display:inline-flex;align-items:center;gap:5px;border-radius:999px;padding:5px 10px;font-size:11px;font-weight:700;background:#EEF2FF;color:#4F46E5;margin-right:7px}
.tp-chip.green {background:#E9F8F0;color:#18764B}.tp-chip.red {background:#FFF0F0;color:#B73C4C}.tp-chip.amber {background:#FFF4DF;color:#956113}
.tp-answer {background:#F8FAFF;border:1px solid #E5EAF5;border-radius:10px;padding:15px 17px;color:#25344D;line-height:1.65;margin:9px 0}
.tp-label {font-size:10px;text-transform:uppercase;letter-spacing:.1em;font-weight:800;color:#64748B;margin:0 0 6px}
.tp-divider {border-top:1px solid #E8EDF4;margin:12px 0}
[data-testid="stMetric"] {background:#fff!important;border:1px solid #E4EAF2!important;border-radius:12px!important;padding:15px 17px!important;min-height:94px!important}
[data-testid="stMetricLabel"] p {color:#64748B!important;font-size:12px!important;font-weight:500!important}
[data-testid="stMetricValue"] {color:#18243A!important;font-size:25px!important;font-weight:700!important}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea {background:#fff!important;color:#18243A!important;border:1px solid #D7DFEB!important;border-radius:9px!important;box-shadow:none!important}
[data-testid="stTextInput"] input::placeholder,[data-testid="stTextArea"] textarea::placeholder {color:#94A3B8!important;opacity:1!important}
[data-testid="stSelectbox"] [data-baseweb="select"]>div {background:#fff!important;color:#18243A!important;border:1px solid #D7DFEB!important;border-radius:9px!important;box-shadow:none!important}
[data-testid="stSelectbox"] [data-baseweb="select"] * {color:#18243A!important}
[data-testid="stSelectbox"] [data-baseweb="select"] svg {fill:#64748B!important}
[data-testid="stWidgetLabel"] p {color:#475569!important;font-size:12px!important;font-weight:600!important}
.stButton>button[kind="primary"] {background:#4F46E5!important;color:#fff!important;border:1px solid #4F46E5!important;border-radius:9px!important;min-height:41px!important;font-weight:700!important}
.stButton>button[kind="secondary"] {background:#fff!important;color:#334155!important;border:1px solid #D7DFEB!important;border-radius:9px!important;min-height:40px!important}
[data-testid="stButton"] button[kind="primary"], .stButton>button[kind="primary"] {background:#4F46E5!important;color:#fff!important;border-color:#4F46E5!important;box-shadow:none!important}
[data-testid="stButton"] button[kind="primary"] p, [data-testid="stButton"] button[kind="primary"] span {color:#fff!important}
[data-testid="stButton"] button[kind="secondary"] {background:#fff!important;color:#334155!important;border:1px solid #E2E8F0!important;box-shadow:none!important}
[data-testid="stButton"] button[kind="secondary"] p, [data-testid="stButton"] button[kind="secondary"] span {color:#334155!important}
[data-testid="stButton"] button:hover {border-color:#4F46E5!important}
[data-testid="stExpander"] {background:#fff!important;border:1px solid #E4EAF2!important;border-radius:10px!important;margin:5px 0!important}
[data-testid="stAlert"] {border-radius:10px!important}
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {color:#294F78!important}
[data-testid="stCaptionContainer"] p {color:#64748B!important}
[data-testid="stVegaLiteChart"] {background:#fff!important;border:1px solid #E4EAF2!important;border-radius:12px!important;padding:10px!important}
@media(max-width:800px){[data-testid="stMainBlockContainer"]{padding:.7rem 1rem 2rem!important}.tp-intro h1{font-size:21px!important}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def api(method, path, **kwargs):
    try:
        response = requests.request(method, f"{API_URL}{path}", timeout=90, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc


def safe(value):
    return html.escape(str(value if value is not None else ""))


def status_chip(status):
    labels = {"auto_resolved": "Auto-resolved", "needs_review": "Needs review", "escalated": "Escalated", "resolved": "Resolved"}
    tone = {"auto_resolved": "green", "resolved": "green", "needs_review": "amber", "escalated": "red"}.get(status, "")
    return f'<span class="tp-chip {tone}">{safe(labels.get(status, status))}</span>'


def section(title, subtitle=None, kicker=None):
    st.markdown(f'<div class="tp-intro">{f"<div class=tp-kicker>{safe(kicker)}</div>" if kicker else ""}<h1>{safe(title)}</h1>{f"<div class=tp-muted>{safe(subtitle)}</div>" if subtitle else ""}</div>', unsafe_allow_html=True)


def feedback(ticket_id, corrected_intent, rating, approved):
    return api("POST", f"/tickets/{ticket_id}/feedback", json={"approved": approved, "rating": rating, "corrected_intent": corrected_intent})


try:
    health = api("GET", "/health")
    metrics = api("GET", "/metrics")
except RuntimeError as exc:
    st.error(str(exc))
    st.code("uvicorn src.api:app --reload", language="bash")
    st.stop()

st.markdown('<div class="tp-top"><div class="tp-brand"><div class="tp-logo">✦</div>TicketPilot</div><div class="tp-small">SUPPORT OPERATIONS WORKSPACE</div></div>', unsafe_allow_html=True)
header_left, header_right = st.columns([4, 1], vertical_alignment="center")
with header_left:
    st.markdown('<div class="tp-chip green">● API connected</div><span class="tp-chip">' + ('AI agent enabled' if health.get('llm') else 'Fallback mode') + '</span><span class="tp-small">Demo environment · Mock orders</span>', unsafe_allow_html=True)
with header_right:
    if st.button("↻ Refresh", use_container_width=True):
        st.rerun()

section("Your support workspace", "Process customer requests, review decisions, and track performance — all in one place.", "OVERVIEW")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Tickets processed", f"{metrics.get('tickets', 0):,}")
k2.metric("Auto-resolution rate", f"{metrics.get('auto_resolve_rate', 0):.0%}")
k3.metric("P95 latency", f"{(metrics.get('latency_ms_p95') or 0):,.0f} ms")
k4.metric("Average rating", f"{metrics['avg_rating']:.1f} / 5" if metrics.get('avg_rating') is not None else "—")
# Explicit navigation avoids Streamlit's tab underline and theme-specific hover behavior.
if "active_view" not in st.session_state:
    st.session_state.active_view = "Process ticket"

nav1, nav2, nav3, nav_space = st.columns([1.15, 1.1, .9, 2.5], gap="small")
for col, name, icon in (
    (nav1, "Process ticket", "✦"),
    (nav2, "Review queue", "☷"),
    (nav3, "Analytics", "▥"),
):
    with col:
        if st.button(
            f"{icon}  {name}",
            key=f"nav_{name}",
            type="primary" if st.session_state.active_view == name else "secondary",
            use_container_width=True,
        ):
            st.session_state.active_view = name
            st.rerun()

if st.session_state.active_view == "Process ticket":
    section("New customer request", "Paste a customer message and see how TicketPilot handles it.", "01 / TICKET INTAKE")
    left, right = st.columns([1.15, .85], gap="large")
    with left:
        st.markdown("**Customer message**")
        customer_text = st.text_area("Customer message", value="Where is my order 10233?", height=175, label_visibility="collapsed", placeholder="Describe a customer's issue...")
        run = st.button("Process ticket →", type="primary", disabled=not customer_text.strip(), use_container_width=True)
        st.markdown('<div class="tp-panel"><div class="tp-kicker">WHAT HAPPENS NEXT</div><div class="tp-muted">① Understand the request &nbsp; → &nbsp; ② Retrieve policy &nbsp; → &nbsp; ③ Assess risk &nbsp; → &nbsp; ④ Resolve or route to a human</div></div>', unsafe_allow_html=True)
        if run:
            try:
                with st.spinner("Classifying, retrieving evidence, and checking safety..."):
                    st.session_state["latest_ticket"] = api("POST", "/tickets", json={"text": customer_text.strip()})
            except RuntimeError as exc:
                st.error(str(exc))
    with right:
        st.markdown("**Decision & suggested reply**")
        result = st.session_state.get("latest_ticket")
        if not result:
            st.markdown('<div class="tp-panel"><div class="tp-kicker">READY WHEN YOU ARE</div><h3>Your ticket result will appear here</h3><div class="tp-muted">Submit a message to see its intent, risk, proposed response, and evidence.</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="tp-panel"><div class="tp-small">TICKET #{safe(result.get("id", "—"))} · DECISION</div><div style="margin:12px 0">{status_chip(result.get("status", ""))}<span class="tp-chip">{safe(result.get("priority", "—"))}</span></div><div class="tp-divider"></div><div class="tp-label">Detected intent</div><h3>{safe(result.get("intent", "—")).replace("_", " ").title()}</h3><div class="tp-muted">Confidence: {float(result.get("confidence", 0)):.1%} · {safe(result.get("agent", "—"))} agent · {float(result.get("latency_ms", 0)):,.0f} ms</div><div class="tp-divider"></div><div class="tp-label">Suggested customer reply</div><div class="tp-answer">{safe(result.get("reply", ""))}</div></div>', unsafe_allow_html=True)
            if result.get("route_reasons"):
                st.warning("Why this was routed: " + "; ".join(map(str, result["route_reasons"])))
            if result.get("risk_reasons"):
                st.error("Risk signals: " + "; ".join(map(str, result["risk_reasons"])))
            if result.get("citations"):
                st.caption("Policy references: " + ", ".join(map(str, result["citations"])))
            with st.expander("View agent actions"):
                if result.get("actions"):
                    st.json(result["actions"])
                else:
                    st.caption("No tools executed for this ticket.")
            with st.expander("View technical details"):
                st.json({key: result.get(key) for key in ("intent", "category", "confidence", "priority", "status", "agent", "guardrail_issues", "tokens_in", "tokens_out", "latency_ms")})

if st.session_state.active_view == "Review queue":
    section("Review queue", "Prioritize escalations, correct classifications, and approve safe resolutions.", "02 / HUMAN REVIEW")
    filter_col, search_col = st.columns([1, 2])
    with filter_col:
        status_filter = st.selectbox("Filter by status", ["Needs review", "Escalated", "Auto-resolved", "Resolved", "All"], index=0)
    with search_col:
        search = st.text_input("Search tickets", placeholder="Search by message, intent, or ticket number")
    status_map = {"Needs review": "needs_review", "Escalated": "escalated", "Auto-resolved": "auto_resolved", "Resolved": "resolved"}
    try:
        rows = api("GET", "/tickets", params={"status": status_map[status_filter]} if status_filter != "All" else {})
        intents = api("GET", "/intents")
    except RuntimeError as exc:
        st.error(str(exc))
        rows, intents = [], []
    if not isinstance(rows, list):
        rows = []
    if not isinstance(intents, list):
        intents = []
    term = search.strip().lower()
    if term:
        rows = [t for t in rows if term in (str(t.get("text", "")) + " " + str(t.get("intent", "")) + " " + str(t.get("id", ""))).lower()]
    st.caption(f"{len(rows)} ticket(s) found")
    if not rows:
        st.info("No tickets match your filters. Try another status or search term.")
    for t in rows:
        tid = t.get("id")
        status = t.get("status", "")
        preview = str(t.get("text", ""))[:75]
        heading = f"#{tid}  ·  {str(t.get('priority', '—'))}  ·  {str(t.get('intent', '—')).replace('_', ' ')}  ·  {preview}"
        with st.expander(heading):
            st.markdown(status_chip(status), unsafe_allow_html=True)
            st.markdown("**Customer message**")
            st.write(t.get("text", ""))
            st.markdown("**Suggested reply**")
            st.markdown(f'<div class="tp-answer">{safe(t.get("reply", ""))}</div>', unsafe_allow_html=True)
            if t.get("route_reasons"):
                st.warning("Routing: " + "; ".join(map(str, t["route_reasons"])))
            if t.get("citations"):
                st.caption("Policy evidence: " + ", ".join(map(str, t["citations"])))
            edit_col, rating_col = st.columns([2, 1])
            with edit_col:
                corrected = st.selectbox("Correct intent", ["Keep original"] + [i for i in intents if i != "Keep original"], key=f"intent_{tid}")
            with rating_col:
                rating = st.select_slider("Reply quality", options=[1, 2, 3, 4, 5], value=4, key=f"rating_{tid}")
            corrected_value = None if corrected == "Keep original" else corrected
            st.caption("Saving feedback should not automatically resolve escalated tickets.")
            action_col, approve_col = st.columns(2)
            with action_col:
                if st.button("Save classification feedback", key=f"save_{tid}", use_container_width=True):
                    # Existing API has no feedback-only contract; do not pretend this is safe.
                    st.info("Feedback-only saving needs a backend endpoint that preserves ticket status. Do not approve this ticket just to save a correction.")
            with approve_col:
                can_approve = status == "needs_review"
                if st.button("Approve resolution", key=f"approve_{tid}", type="primary", disabled=not can_approve, use_container_width=True):
                    try:
                        feedback(tid, corrected_value, rating, approved=True)
                        st.success("Resolution approved and feedback recorded.")
                        st.rerun()
                    except RuntimeError as exc:
                        st.error(str(exc))
                if status == "escalated":
                    st.caption("Escalated cases require specialist handling; approval is disabled.")

def light_bar_chart(values, label, color="#4F46E5", height=220):
    items = [{"Category": str(k).replace("_", " ").title(), "Tickets": int(v)} for k, v in values.items()]
    if not items:
        st.info("No data available yet.")
        return
    data = pd.DataFrame(items)
    chart = (alt.Chart(data)
        .mark_bar(color=color, cornerRadiusEnd=5, size=24)
        .encode(
            y=alt.Y("Category:N", sort="-x", title=None, axis=alt.Axis(labelColor="#475569", labelFontSize=12, labelLimit=190, domain=False, ticks=False)),
            x=alt.X("Tickets:Q", title=None, axis=alt.Axis(labelColor="#64748B", gridColor="#E9EEF5", domain=False, tickMinStep=1), scale=alt.Scale(zero=True)),
            tooltip=["Category:N", "Tickets:Q"])
        .properties(height=max(125, min(height, 42 * len(items) + 52)), background="#FFFFFF")
        .configure_view(stroke=None)
        .configure_axis(labelFont="Inter", titleFont="Inter"))
    st.altair_chart(chart, use_container_width=True, theme=None)


if st.session_state.active_view == "Analytics":
    section("Performance overview", "A quick view of the tickets processed in this demo workspace.", "03 / OPERATIONS ANALYTICS")
    chart_left, chart_right = st.columns(2, gap="large")
    with chart_left:
        st.markdown("**Tickets by status**")
        light_bar_chart(metrics.get("by_status") or {}, "Status", "#5B55D8")
    with chart_right:
        st.markdown("**Tickets by priority**")
        light_bar_chart(metrics.get("by_priority") or {}, "Priority", "#19A68D")
    st.markdown("**Most common intents**")
    light_bar_chart(metrics.get("top_intents") or {}, "Intent", "#8575DF", height=280)
    st.caption(f"LLM tokens: {metrics.get('tokens_in', 0):,} input / {metrics.get('tokens_out', 0):,} output. These are demo operational metrics, not offline evaluation results.")

st.markdown('<div class="tp-divider"></div><div class="tp-small" style="text-align:center">TicketPilot · Policy-grounded support automation · Human oversight · Demo only</div>', unsafe_allow_html=True)
