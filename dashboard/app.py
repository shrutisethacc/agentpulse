"""
AgentPulse Dashboard — FrontierIQ-inspired redesign.
Left sidebar navigation · Architecture page · Accenture footer · FrontierIQ table style.
"""

import datetime
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

import mlflow
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml
from mlflow.tracking import MlflowClient

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AgentPulse · Dashboard",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, .stApp {
  font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif !important;
  background: #F7F7F7 !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: #FFFFFF !important;
  border-right: 1px solid #E1E1E1 !important;
  min-width: 230px !important;
}
[data-testid="stSidebar"] * { color: #4A4A4A !important; }
[data-testid="stSidebar"] strong { color: #1A1A1A !important; }
[data-testid="stSidebarContent"] { padding-top: 20px !important; padding-bottom: 80px !important; }
[data-testid="stHeader"] { background: transparent !important; }
.main .block-container { padding-top: 28px; padding-bottom: 80px; max-width: 1200px; }

/* ── Headings ── */
h1 { font-weight: 700 !important; color: #1A1A1A !important; font-size: 26px !important; letter-spacing: -.01em !important; }
h2, h3 { font-weight: 700 !important; color: #1A1A1A !important; }
p, li { color: #4A4A4A; }

/* ── Sidebar nav buttons — strip all button chrome ── */
[data-testid="stSidebar"] .stButton,
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stButton > button:focus,
[data-testid="stSidebar"] .stButton > button:focus-visible,
[data-testid="stSidebar"] .stButton > button:active {
  background: transparent !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  width: 100% !important;
  padding: 8px 12px 8px 14px !important;
  border-left: 3px solid transparent !important;
  border-radius: 0 8px 8px 0 !important;
  font-size: 13.5px !important;
  font-weight: 450 !important;
  color: #4A4A4A !important;
  letter-spacing: 0 !important;
  line-height: 1.4 !important;
  height: auto !important;
  margin: 1px 6px 1px 0 !important;
  transition: background 0.1s, color 0.1s !important;
}
/* Fix the <p> Streamlit wraps button text in */
[data-testid="stSidebar"] .stButton > button p {
  text-align: left !important;
  margin: 0 !important;
  padding: 0 !important;
  font-size: 13.5px !important;
  font-weight: inherit !important;
  color: inherit !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: #F5EBFE !important;
  color: #5C00A3 !important;
  border-left-color: #C9A5FA !important;
}
/* Active nav item */
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: #F0E8FE !important;
  color: #460073 !important;
  font-weight: 600 !important;
  border-left-color: #A100FF !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] p {
  font-weight: 600 !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
  background: #E8D5FD !important;
}

/* ── Sidebar HTML nav links (FrontierIQ style — left-aligned) ── */
[data-testid="stSidebar"] a.ap-nav-link {
  display: block !important;
  width: calc(100% - 6px) !important;
  padding: 8px 12px 8px 14px !important;
  margin: 1px 0 !important;
  font-size: 13.5px !important;
  font-weight: 400 !important;
  color: #4A4A4A !important;
  text-decoration: none !important;
  border-left: 3px solid transparent !important;
  border-radius: 0 8px 8px 0 !important;
  box-sizing: border-box !important;
  line-height: 1.4 !important;
  text-align: left !important;
  background: transparent !important;
}
[data-testid="stSidebar"] a.ap-nav-link:hover {
  background: #F5EBFE !important;
  color: #5C00A3 !important;
  border-left-color: #C9A5FA !important;
}
[data-testid="stSidebar"] a.ap-nav-link.active {
  background: #F0E8FE !important;
  color: #460073 !important;
  font-weight: 600 !important;
  border-left-color: #A100FF !important;
}

/* ── Main content buttons ── */
.main .stButton > button[kind="primary"],
.main button[data-testid="baseButton-primary"] {
  background: #A100FF !important;
  color: #FFFFFF !important;
  border: none !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  font-size: 14px !important;
}
.main .stButton > button[kind="primary"]:hover { background: #7B00CC !important; }
.main .stButton > button[kind="secondary"] {
  background: #FFFFFF !important;
  color: #460073 !important;
  border: 1px solid #C9A5FA !important;
  border-radius: 8px !important;
  font-weight: 500 !important;
}
.main .stButton > button { border-radius: 8px !important; }

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
  background: #FFFFFF !important;
  color: #460073 !important;
  border: 1px solid #C9A5FA !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
}

/* ── Metric widgets ── */
[data-testid="stMetric"] {
  background: #FFFFFF;
  border: 1px solid #E1E1E1;
  border-radius: 16px;
  padding: 18px 20px !important;
}
[data-testid="stMetricValue"] { color: #1A1A1A !important; font-weight: 700 !important; font-size: 26px !important; }
[data-testid="stMetricLabel"] { color: #767676 !important; font-size: 11px !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: .1em !important; }
[data-testid="stMetricDelta"] { font-size: 12px !important; }

/* ── DataFrame ── */
[data-testid="stDataFrame"] iframe { border-radius: 12px; border: 1px solid #E1E1E1; }
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

/* ── FrontierIQ HTML table ── */
.fiq-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 20px; background: #fff; border-radius: 12px; overflow: hidden; border: 1px solid #E1E1E1; }
.fiq-table thead tr { border-bottom: 2px solid #E1E1E1; }
.fiq-table thead th { background: #FAFAFA; padding: 10px 14px; text-align: left; font-size: 10px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: #767676; }
.fiq-table tbody tr { border-bottom: 1px solid #F2F2F2; transition: background 0.1s; }
.fiq-table tbody tr:last-child { border-bottom: none; }
.fiq-table tbody tr:hover { background: #FAFAFA; }
.fiq-table tbody td { padding: 10px 14px; color: #1A1A1A; vertical-align: middle; line-height: 1.4; }
.fiq-table .td-muted { color: #767676; font-size: 12px; }
.fiq-table .td-pass { color: #005A4E; font-weight: 700; }
.fiq-table .td-fail { color: #9B0045; font-weight: 700; }
.fiq-table .td-code { font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 11.5px; color: #460073; background: #F5EBFE; border-radius: 3px; padding: 2px 6px; white-space: nowrap; }
.fiq-table .td-bold { font-weight: 600; }
.fiq-table .td-thr { color: #460073; font-weight: 700; }

/* ── Alerts ── */
[data-testid="stAlert"] { border-radius: 12px !important; }
.stInfo    { background: rgba(70,0,115,.06) !important; border-left-color: #460073 !important; }
.stSuccess { background: rgba(0,229,199,.08) !important; border-left-color: #00E5C7 !important; }
.stError   { background: rgba(232,76,138,.06) !important; border-left-color: #E84C8A !important; }
.stWarning { background: rgba(232,76,138,.06) !important; border-left-color: #E84C8A !important; }

/* ── Toolbar popover buttons ── */
[data-testid="stPopover"] > button {
  background: #FFFFFF !important;
  color: #460073 !important;
  border: 1px solid #C9A5FA !important;
  border-radius: 8px !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  width: 100% !important;
}
[data-testid="stPopover"] > button:hover {
  background: #F5EBFE !important;
  border-color: #A100FF !important;
  color: #460073 !important;
}

/* ── Date input (time range picker) ── */
[data-testid="stDateInput"] > div > div > input {
  font-size: 12px !important;
  font-family: 'Inter', sans-serif !important;
  color: #1A1A1A !important;
}
[data-testid="stDateInput"] > div {
  border: 1px solid #C9A5FA !important;
  border-radius: 8px !important;
  background: #FFFFFF !important;
  font-size: 12px !important;
}
[data-testid="stDateInput"] > div:focus-within {
  border-color: #A100FF !important;
  box-shadow: 0 0 0 2px rgba(161,0,255,.12) !important;
}

/* ── Time input (24H picker) ── */
[data-testid="stTimeInput"] > div {
  border: 1px solid #C9A5FA !important;
  border-radius: 8px !important;
  background: #FFFFFF !important;
  font-size: 12px !important;
}
[data-testid="stTimeInput"] > div:focus-within {
  border-color: #A100FF !important;
  box-shadow: 0 0 0 2px rgba(161,0,255,.12) !important;
}

/* ── Misc ── */
hr { border-color: #E1E1E1 !important; margin: 20px 0 !important; }
[data-testid="stExpander"] { background: #FFFFFF; border: 1px solid #E1E1E1; border-radius: 12px; }
code { background: #F5EBFE !important; color: #460073 !important; border-radius: 4px !important; }
[data-baseweb="select"] > div { border-color: #C9A5FA !important; border-radius: 10px !important; background: #FFFFFF !important; }
[data-testid="stSlider"] [role="slider"] { background: #A100FF !important; }
.stSpinner > div { border-top-color: #A100FF !important; }

/* ── Footer ── */
.ap-footer {
  margin-top: 56px; padding: 28px 0 24px;
  border-top: 2px solid #E1E1E1;
  font-family: 'Inter', sans-serif;
}
.ap-footer-brand { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.ap-footer-wordmark { font-size: 17px; font-weight: 700; color: #1A1A1A; letter-spacing: -.02em; }
.ap-footer-arrow { color: #A100FF; font-size: 18px; font-weight: 900; line-height: 1; }
.ap-footer-pipe { width: 1px; height: 18px; background: #D0D0D0; }
.ap-footer-dept { font-size: 13px; font-weight: 600; color: #1A1A1A; }
.ap-footer-sub { font-size: 13px; color: #767676; margin-bottom: 20px; }
.ap-footer-cols { display: flex; gap: 56px; margin-bottom: 20px; flex-wrap: wrap; }
.ap-footer-col-label { font-size: 10px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: #767676; margin-bottom: 10px; }
.ap-footer-col span { display: block; font-size: 13px; color: #4A4A4A; margin-bottom: 6px; }
.ap-footer-copy { font-size: 12px; color: #ABABAB; }

/* ── Sidebar POWERED BY badge ── */
.ap-powered-by {
  padding: 12px 16px;
  border-top: 1px solid #E1E1E1;
  margin-top: 8px;
}
.ap-powered-by .label { font-size: 9px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: #ABABAB; margin-bottom: 4px; }
.ap-powered-by .brand { font-size: 14px; font-weight: 700; color: #1A1A1A; }
.ap-powered-by .brand span { color: #A100FF; }
</style>
""", unsafe_allow_html=True)


# ── Color palette & Plotly defaults ───────────────────────────────────────────
FIQ = {
    "quality":  "#A100FF",
    "rag":      "#00E5C7",
    "helpdesk": "#4A4A4A",
    "safety":   "#2E5BFF",
    "sla":      "#E84C8A",
    "grid":     "#E1E1E1",
}
PLOTLY_LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="white",
    font_family="Inter, sans-serif",
    font_color="#1A1A1A",
    legend_font_size=12,
    margin=dict(t=44, b=32, l=10, r=10),
    xaxis=dict(gridcolor=FIQ["grid"], zeroline=False),
    yaxis=dict(gridcolor=FIQ["grid"], zeroline=False),
)
METRIC_CATEGORY = {
    "faithfulness": "RAG Gen", "answer_relevancy": "RAG Gen",
    "contextual_relevancy": "RAG Ret", "contextual_precision": "RAG Ret", "contextual_recall": "RAG Ret",
    "completeness": "Helpdesk", "actionability": "Helpdesk",
    "professional_tone": "Helpdesk", "task_resolution": "Helpdesk",
    "escalation_appropriateness": "Helpdesk",
    "bias": "Safety", "toxicity": "Safety",
}
CAT_COLOURS = {
    "RAG Gen":  FIQ["rag"],
    "RAG Ret":  "#006B5A",
    "Helpdesk": FIQ["helpdesk"],
    "Safety":   FIQ["sla"],
}


# ── UI helpers ─────────────────────────────────────────────────────────────────
def fiq_eyebrow(text: str) -> None:
    st.markdown(
        f'<div style="font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;'
        f'color:#460073;margin-bottom:4px;">{text}</div>',
        unsafe_allow_html=True,
    )


def page_header(eyebrow: str, title: str, subtitle: str = "") -> None:
    sub_html = (
        f'<div style="font-size:14px;color:#4A4A4A;margin-bottom:24px;line-height:1.5;">{subtitle}</div>'
        if subtitle else ""
    )
    st.markdown(
        f'<div style="font-size:11px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;'
        f'color:#460073;margin-bottom:6px;">{eyebrow}</div>'
        f'<div style="font-size:26px;font-weight:700;color:#1A1A1A;line-height:1.1;'
        f'margin-bottom:{"4px" if subtitle else "24px"};">{title}</div>'
        f'{sub_html}',
        unsafe_allow_html=True,
    )


def fiq_stat_card(label: str, value: str, sub: str = "", accent: bool = False) -> str:
    bl = "3px solid #A100FF" if accent else "1px solid #E1E1E1"
    return (
        f'<div style="background:#fff;border:1px solid #E1E1E1;border-left:{bl};'
        f'border-radius:16px;padding:20px 22px;height:100%;">'
        f'<div style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;'
        f'color:#767676;margin-bottom:10px;">{label}</div>'
        f'<div style="font-size:30px;font-weight:700;color:#1A1A1A;line-height:1;margin-bottom:6px;">{value}</div>'
        f'<div style="font-size:13px;color:#4A4A4A;line-height:1.4;">{sub}</div>'
        f'</div>'
    )


def fiq_badge(text: str, kind: str = "default") -> str:
    colours = {
        "default": ("#F5EBFE", "#460073"),
        "pass":    ("rgba(0,229,199,.15)", "#005A4E"),
        "fail":    ("rgba(232,76,138,.15)", "#9B0045"),
        "neutral": ("rgba(74,74,74,.10)", "#4A4A4A"),
        "os":      ("rgba(46,91,255,.10)", "#1A3BB3"),
    }
    bg, fg = colours.get(kind, colours["default"])
    return (
        f'<span style="background:{bg};color:{fg};font-size:11px;font-weight:600;'
        f'letter-spacing:.05em;text-transform:uppercase;padding:3px 10px;'
        f'border-radius:3px;white-space:nowrap;">{text}</span>'
    )


def tool_card(name: str, maker: str, badge: str, badge_kind: str,
              description: str, role: str, metrics: list[str], colour: str) -> str:
    metric_chips = "".join(
        f'<span style="background:#F5EBFE;color:#460073;font-size:11px;font-weight:600;'
        f'letter-spacing:.04em;padding:2px 8px;border-radius:3px;white-space:nowrap;">{m}</span>'
        for m in metrics
    )
    return (
        f'<div style="background:#fff;border:1px solid #E1E1E1;border-top:3px solid {colour};'
        f'border-radius:16px;padding:20px 22px;height:100%;display:flex;flex-direction:column;gap:10px;">'
        f'<div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;">'
        f'  <div>'
        f'    <div style="font-size:15px;font-weight:700;color:#1A1A1A;margin-bottom:2px;">{name}</div>'
        f'    <div style="font-size:12px;color:#767676;">{maker}</div>'
        f'  </div>'
        f'  {fiq_badge(badge, badge_kind)}'
        f'</div>'
        f'<div style="font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;'
        f'color:#767676;">{role}</div>'
        f'<div style="font-size:13px;color:#4A4A4A;line-height:1.5;flex:1;">{description}</div>'
        f'<div style="border-top:1px solid #F0F0F0;padding-top:10px;">'
        f'  <div style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;'
        f'  color:#ABABAB;margin-bottom:6px;">Metrics / outputs</div>'
        f'  <div style="display:flex;gap:5px;flex-wrap:wrap;">{metric_chips}</div>'
        f'</div>'
        f'</div>'
    )


def _nav_link(page: str, label: str | None = None) -> str:
    """Return an <a> tag that routes to a page via ?nav= query param."""
    encoded = urllib.parse.quote(page)
    display = label or page
    return (
        f'<a href="?nav={encoded}" target="_self" '
        f'style="display:block;font-size:13px;color:#767676;margin-bottom:7px;'
        f'text-decoration:none;transition:color 0.1s;" '
        f'onmouseover="this.style.color=\'#460073\'" '
        f'onmouseout="this.style.color=\'#767676\'">{display}</a>'
    )


def render_footer() -> None:
    def _col(label: str, items: list[str]) -> str:
        rows = "".join(
            f'<div style="margin-bottom:0;">{it}</div>'
            for it in items
        )
        return (
            f'<div style="min-width:160px;">'
            f'<div style="font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;'
            f'color:#ABABAB;margin-bottom:12px;">{label}</div>'
            f'{rows}</div>'
        )

    cols_html = (
        _col("Navigation", [
            _nav_link("Overview"),
            _nav_link("Architecture"),
            _nav_link("Quality Metrics"),
            _nav_link("Speed & Cost"),
        ])
        + _col("Metrics Taxonomy", [
            _nav_link("Metric Guide", "RAG Evaluation"),
            _nav_link("Metric Guide", "Helpdesk GEval"),
            _nav_link("Metric Guide", "Safety Scoring"),
            _nav_link("Metric Guide", "Speed &amp; Cost"),
        ])
        + _col("Evaluation Methodology", [
            _nav_link("Metric Guide", "Formula-Based (RAG)"),
            _nav_link("Metric Guide", "LLM-as-a-Judge (GEval)"),
            _nav_link("Metric Guide", "SLA Reference"),
        ])
    )

    st.markdown(
        '<div style="margin-top:48px;padding:28px 0 32px;border-top:1px solid #E1E1E1;">'
        '<div style="font-size:17px;font-weight:700;color:#1A1A1A;margin-bottom:4px;">AgentPulse</div>'
        '<div style="font-size:12px;color:#ABABAB;margin-bottom:24px;">AI Agent Evaluation Platform</div>'
        f'<div style="display:flex;gap:48px;flex-wrap:wrap;">{cols_html}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── Config + data ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_config() -> dict:
    with open(BASE_DIR / "config.yaml") as f:
        return yaml.safe_load(f)


@st.cache_data(ttl=30)
def fetch_runs(experiment_name: str, max_results: int = 200) -> pd.DataFrame:
    cfg = load_config()
    _uri = cfg["mlflow"]["tracking_uri"]
    mlflow.set_tracking_uri(_uri)
    client = MlflowClient(tracking_uri=_uri)
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        return pd.DataFrame()
    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["start_time DESC"],
        max_results=max_results,
    )
    if not runs:
        return pd.DataFrame()
    records = []
    for run in runs:
        row = {
            "run_id":     run.info.run_id,
            "run_name":   run.data.tags.get("mlflow.runName", run.info.run_id[:8]),
            "start_time": pd.to_datetime(run.info.start_time, unit="ms"),
        }
        row.update(run.data.metrics)
        row.update(run.data.params)
        records.append(row)
    return pd.DataFrame(records)


cfg        = load_config()
eval_cfg   = cfg.get("eval", {})
sla_cfg    = cfg.get("sla_thresholds", {})
dash_cfg   = cfg.get("dashboard", {})
agent_name = cfg.get("agent", {}).get("name", "AI Agent")

with st.spinner("Loading data from MLflow…"):
    df_evals   = fetch_runs("it-helpdesk-agent-evals")
    df_load    = fetch_runs("it-helpdesk-load-test")
    df_summary = fetch_runs("it-helpdesk-eval-summary")


@st.cache_data(ttl=120)
def load_eval_reasons() -> list[dict]:
    """Download eval_reasons.json artifacts from all scored runs. Cached 120s."""
    _uri = cfg["mlflow"]["tracking_uri"]
    mlflow.set_tracking_uri(_uri)                 # must precede MlflowClient()
    _client = MlflowClient(tracking_uri=_uri)
    exp = mlflow.get_experiment_by_name("it-helpdesk-agent-evals")
    if not exp:
        return []
    runs = _client.search_runs(
        experiment_ids=[exp.experiment_id],
        max_results=200,
        order_by=["start_time DESC"],
    )
    results = []
    for r in runs:
        if "quality_score" not in r.data.metrics:
            continue
        try:
            with tempfile.TemporaryDirectory() as tmp:
                local = _client.download_artifacts(r.info.run_id, "eval_reasons.json", tmp)
                with open(local, "r", encoding="utf-8") as f:
                    data = json.load(f)
                results.append(data)
        except Exception:
            pass
    return results


@st.cache_data(ttl=120)
def load_eval_recommendations() -> list[dict]:
    """Download eval_recommendations.json from the latest summary run. Cached 120s."""
    _uri = cfg["mlflow"]["tracking_uri"]
    mlflow.set_tracking_uri(_uri)                 # must precede MlflowClient()
    _client = MlflowClient(tracking_uri=_uri)
    exp = mlflow.get_experiment_by_name("it-helpdesk-eval-summary")
    if not exp:
        return []
    runs = _client.search_runs(
        experiment_ids=[exp.experiment_id],
        max_results=1,
        order_by=["start_time DESC"],
    )
    if not runs:
        return []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            local = _client.download_artifacts(runs[0].info.run_id, "eval_recommendations.json", tmp)
            with open(local, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("recommendations", [])
    except Exception:
        return []

for df, col in [(df_load, "user_count"), (df_summary, "user_count")]:
    if not df.empty and col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")


# ── Sidebar navigation ─────────────────────────────────────────────────────────
NAV_SECTIONS = [
    (None,          [("Overview", ""), ("Architecture", "")]),
    ("PERFORMANCE", [("Quality Metrics", ""), ("Load Test", ""), ("Quality Under Load", "")]),
    ("ANALYSIS",    [("DeepEval", ""), ("Speed & Cost", ""), ("Insights", "")]),
    ("REFERENCE",   [("Metric Guide", "")]),
]

_ALL_PAGES = [
    "Overview", "Architecture", "Quality Metrics", "Load Test",
    "Quality Under Load", "DeepEval", "Speed & Cost", "Insights", "Metric Guide",
]

if "page" not in st.session_state:
    st.session_state.page = "Overview"

# Handle footer / external nav links (?nav=PageName)
_nav_param = urllib.parse.unquote(st.query_params.get("nav", ""))
if _nav_param in _ALL_PAGES:
    st.session_state.page = _nav_param
    st.query_params.clear()
    st.rerun()

with st.sidebar:
    # Brand
    st.markdown(
        '<div style="padding:0 8px 16px;">'
        '<div style="font-size:16px;font-weight:700;color:#1A1A1A;margin-bottom:3px;">AgentPulse</div>'
        '<div style="font-size:11px;color:#767676;">AI Evaluations</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    mlflow_uri = cfg["mlflow"]["tracking_uri"]
    st.markdown(
        f'<div style="padding:0 8px;margin-bottom:4px;">'
        f'<div style="font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;'
        f'color:#ABABAB;margin-bottom:3px;">MLflow</div>'
        f'<a href="{mlflow_uri}" style="font-size:12px;font-weight:600;color:#460073;'
        f'text-decoration:none;">{mlflow_uri} ↗</a></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div style="margin:12px 0;border-top:1px solid #F0F0F0;"></div>', unsafe_allow_html=True)

    # Nav items
    current = st.session_state.page
    for section_name, items in NAV_SECTIONS:
        if section_name:
            st.markdown(
                f'<div style="font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;'
                f'color:#ABABAB;padding:18px 14px 2px;">{section_name}</div>',
                unsafe_allow_html=True,
            )
        for page_name, _ in items:
            is_active = current == page_name
            if st.button(
                page_name,
                key=f"nav_{page_name}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                st.session_state.page = page_name
                st.rerun()

    st.markdown('<div style="margin:16px 0;border-top:1px solid #F0F0F0;"></div>', unsafe_allow_html=True)

    with st.expander("SLA Thresholds", expanded=False):
        rows = [
            ("Quality",       f"≥ {eval_cfg.get('min_quality_score', 0.65)}"),
            ("Faithfulness",  f"≥ {eval_cfg.get('min_faithfulness_score', 0.70)}"),
            ("RAG",           f"≥ {eval_cfg.get('min_rag_score', 0.70)}"),
            ("Helpdesk",      f"≥ {eval_cfg.get('min_helpdesk_score', 0.60)}"),
            ("Safety",        f"≥ {eval_cfg.get('min_safety_score', 0.70)}"),
            ("p95 Latency",   f"≤ {sla_cfg.get('p95_latency_ms', 15000)} ms"),
            ("Error Rate",    f"≤ {sla_cfg.get('error_rate_pct', 5.0)}%"),
        ]
        html = "".join(
            f'<div style="display:flex;justify-content:space-between;padding:5px 0;'
            f'border-bottom:1px solid #F7F7F7;">'
            f'<span style="font-size:12px;color:#4A4A4A;">{lbl}</span>'
            f'<span style="font-size:12px;font-weight:600;color:#1A1A1A;">{val}</span></div>'
            for lbl, val in rows
        )
        st.markdown(html, unsafe_allow_html=True)

    st.markdown(
        '<div style="padding:12px 8px 4px;border-top:1px solid #F0F0F0;margin-top:8px;">'
        '<div style="font-size:11px;font-weight:700;color:#1A1A1A;">AgentPulse</div>'
        '<div style="font-size:10px;color:#ABABAB;">AI Evaluations</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── Top-right toolbar: Time Range · Refresh · Export ─────────────────────────
_all_dates = []
for _df in [df_evals, df_load]:
    if not _df.empty and "start_time" in _df.columns:
        _all_dates.extend(_df["start_time"].dt.date.tolist())
_today    = datetime.date.today()
_min_date = min(_all_dates) if _all_dates else (_today - datetime.timedelta(days=30))

# Initialise session-state defaults for datetime range (runs once per session)
if "tr_start_date" not in st.session_state:
    st.session_state.tr_start_date = _min_date
if "tr_end_date" not in st.session_state:
    st.session_state.tr_end_date = _today
if "tr_start_time" not in st.session_state:
    st.session_state.tr_start_time = datetime.time(0, 0)
if "tr_end_time" not in st.session_state:
    st.session_state.tr_end_time = datetime.time(23, 59)

def _tb_label(text: str) -> None:
    st.markdown(
        f'<div style="font-size:10px;font-weight:700;letter-spacing:.12em;'
        f'text-transform:uppercase;color:#460073;margin-bottom:2px;">{text}</div>',
        unsafe_allow_html=True,
    )

_tb_sp, _tb_time, _tb_score, _tb_refresh, _tb_export = st.columns([1.2, 1.8, 1.2, 0.9, 0.9])

with _tb_time:
    _tb_label("Time Range")
    _sd   = st.session_state.tr_start_date
    _ed   = st.session_state.tr_end_date
    _st_t = st.session_state.tr_start_time
    _et_t = st.session_state.tr_end_time
    _range_lbl = (
        f"{_sd.strftime('%d %b')} {_st_t.strftime('%H:%M')} – "
        f"{_ed.strftime('%d %b')} {_et_t.strftime('%H:%M')}"
    )
    with st.popover(_range_lbl, use_container_width=True):
        _tr_c1, _tr_c2 = st.columns(2)
        with _tr_c1:
            st.markdown(
                '<div style="font-size:10px;font-weight:700;letter-spacing:.1em;'
                'text-transform:uppercase;color:#460073;margin-bottom:4px;">START</div>',
                unsafe_allow_html=True,
            )
            st.date_input(
                "Start date", value=_min_date, min_value=_min_date, max_value=_today,
                key="tr_start_date", label_visibility="collapsed",
            )
            st.time_input(
                "Start time (24H)", value=datetime.time(0, 0),
                key="tr_start_time", label_visibility="collapsed",
            )
        with _tr_c2:
            st.markdown(
                '<div style="font-size:10px;font-weight:700;letter-spacing:.1em;'
                'text-transform:uppercase;color:#460073;margin-bottom:4px;">END</div>',
                unsafe_allow_html=True,
            )
            st.date_input(
                "End date", value=_today, min_value=_min_date, max_value=_today,
                key="tr_end_date", label_visibility="collapsed",
            )
            st.time_input(
                "End time (24H)", value=datetime.time(23, 59),
                key="tr_end_time", label_visibility="collapsed",
            )

with _tb_score:
    _tb_label("Score Runs")
    with st.popover("▶ Score Runs", use_container_width=True):
        st.markdown(
            '<div style="font-size:12px;color:#4A4A4A;margin-bottom:10px;">'
            'Score all unscored runs with DeepEval using Azure OpenAI as judge. '
            'Runs after a load test to add quality metrics.</div>',
            unsafe_allow_html=True,
        )
        _score_force = st.checkbox("Force re-score all runs", key="score_force",
                                   help="Re-scores runs that already have quality metrics")
        if st.button("Run eval_runner", use_container_width=True, key="tb_score_run", type="primary"):
            _args = [
                str(BASE_DIR / ".venv" / "Scripts" / "python.exe"),
                "-m", "evals.eval_runner",
            ]
            if _score_force:
                _args.append("--force")
            with st.spinner("Scoring runs… this may take a few minutes."):
                try:
                    _result = subprocess.run(
                        _args,
                        capture_output=True,
                        text=True,
                        cwd=str(BASE_DIR),
                        env={**os.environ, "PYTHONUTF8": "1"},
                        timeout=600,
                    )
                    if _result.returncode == 0:
                        st.success("Scoring complete. Dashboard will refresh.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("eval_runner failed.")
                        st.code(_result.stderr or _result.stdout, language="text")
                except subprocess.TimeoutExpired:
                    st.error("Timed out after 10 minutes. Try scoring fewer runs.")
                except Exception as _exc:
                    st.error(f"Error: {_exc}")

with _tb_refresh:
    _tb_label("Refresh")
    with st.popover("↺ Refresh", use_container_width=True):
        auto_refresh = st.toggle("Auto-refresh", value=False, key="tb_auto_refresh")
        if auto_refresh:
            refresh_sec = st.slider(
                "Interval (s)", 5, 120,
                int(dash_cfg.get("refresh_interval_sec", 30)),
                key="tb_refresh_sec",
            )
        else:
            refresh_sec = int(dash_cfg.get("refresh_interval_sec", 30))
        st.markdown("---")
        if st.button("Refresh now", use_container_width=True, key="tb_refresh_now"):
            st.cache_data.clear()
            st.rerun()

with _tb_export:
    _tb_label("Export")
    with st.popover("PDF Report", use_container_width=True):
        st.markdown("Generate a full PDF report of current runs.")
        if st.button("Generate PDF", use_container_width=True, key="tb_pdf_gen"):
            with st.spinner("Generating… (30–60 s)"):
                try:
                    # Run report_generator in a separate process — Playwright's sync API
                    # cannot launch Chromium inside Streamlit's asyncio event loop.
                    _rpt_script = str(BASE_DIR / "reports" / "report_generator.py")
                    _result = subprocess.run(
                        [sys.executable, _rpt_script],
                        capture_output=True, text=True,
                        cwd=str(BASE_DIR),
                        env={**os.environ, "PYTHONUTF8": "1"},
                        timeout=120,
                    )
                    if _result.returncode == 0:
                        import re as _re
                        _m = _re.search(r"Report saved: (.+\.pdf)", _result.stdout)
                        if _m:
                            out_path = Path(_m.group(1).strip())
                            st.success(f"Saved: `{out_path.name}`")
                            with open(out_path, "rb") as fh:
                                st.download_button(
                                    "⬇ Download PDF", fh.read(),
                                    file_name=out_path.name, mime="application/pdf",
                                    key="tb_pdf_dl",
                                )
                        else:
                            st.success("Report generated — check reports/output/")
                    else:
                        st.error("PDF generation failed.")
                        st.code(_result.stderr or _result.stdout, language="text")
                except subprocess.TimeoutExpired:
                    st.error("Timed out after 2 minutes.")
                except Exception as exc:
                    st.error(f"Failed: {exc}")

# ── Apply time range filter ───────────────────────────────────────────────────
def _apply_date_filter(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "start_time" not in df.columns:
        return df
    _sd   = st.session_state.get("tr_start_date", _min_date)
    _ed   = st.session_state.get("tr_end_date",   _today)
    _st_t = st.session_state.get("tr_start_time", datetime.time(0, 0))
    _et_t = st.session_state.get("tr_end_time",   datetime.time(23, 59))
    start_dt = pd.Timestamp(datetime.datetime.combine(_sd, _st_t))
    end_dt   = pd.Timestamp(datetime.datetime.combine(_ed, _et_t))
    return df[(df["start_time"] >= start_dt) & (df["start_time"] <= end_dt)].copy()

df_evals   = _apply_date_filter(df_evals)
df_load    = _apply_date_filter(df_load)
df_summary = _apply_date_filter(df_summary)

# ── SLA banner (shared) ────────────────────────────────────────────────────────
def _sla_banner() -> None:
    if df_evals.empty or "quality_score" not in df_evals.columns:
        return
    scored = df_evals.dropna(subset=["quality_score"]).copy()
    if scored.empty:
        return
    checks = [
        ("QUALITY",      "quality_score",  eval_cfg.get("min_quality_score", 0.65),      True),
        ("FAITHFULNESS", "faithfulness",   eval_cfg.get("min_faithfulness_score", 0.70), True),
        ("RAG",          "rag_score",      eval_cfg.get("min_rag_score", 0.70),           True),
        ("SAFETY",       "safety_score",   eval_cfg.get("min_safety_score", 0.70),        True),
    ]
    results = []
    for label, col, thr, hi in checks:
        if col in scored.columns:
            val    = float(scored[col].mean())
            passed = (val >= thr) if hi else (val <= thr)
            results.append((label, val, thr, passed))
    if not results:
        return
    all_pass = all(r[3] for r in results)
    bg  = "rgba(0,229,199,.08)"  if all_pass else "rgba(232,76,138,.06)"
    bl  = "#00E5C7"              if all_pass else "#E84C8A"
    ico = "✓"                    if all_pass else "⚠"
    headline = "All quality SLA thresholds met" if all_pass else (
        "SLA breach — " + ", ".join(r[0] for r in results if not r[3])
    )
    cards = ""
    for label, val, thr, passed in results:
        delta     = val - thr
        bk        = "pass" if passed else "fail"
        badge_txt = f"+{delta:.3f}" if delta >= 0 else f"{delta:.3f}"
        cards += (
            f'<div style="background:#fff;border:1px solid #E1E1E1;border-radius:12px;'
            f'padding:12px 16px;min-width:108px;">'
            f'<div style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;'
            f'color:#767676;margin-bottom:6px;">{label}</div>'
            f'<div style="font-size:20px;font-weight:700;color:#1A1A1A;margin-bottom:4px;">{val:.3f}</div>'
            f'{fiq_badge(badge_txt, bk)}</div>'
        )
    st.markdown(
        f'<div style="background:{bg};border-left:3px solid {bl};border-radius:12px;'
        f'padding:16px 20px;margin-bottom:24px;display:flex;align-items:center;gap:24px;flex-wrap:wrap;">'
        f'<div style="font-weight:700;font-size:14px;color:#1A1A1A;min-width:260px;">'
        f'{ico}&nbsp; {headline}</div>'
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;">{cards}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Pipeline flow diagram (Plotly) ────────────────────────────────────────────
def _draw_pipeline_flow() -> go.Figure:
    STAGES = [
        ("Invoke",    "FastAPI :8001",                "ONLINE",  "#F5EBFE", "#C9A5FA"),
        ("Pipeline",  "LangGraph · Azure OpenAI",    "ONLINE",  "#ECFDF5", "#6EE7B7"),
        ("Track",     "MLflow :5000 · 17 metrics",   "OFFLINE", "#EEF2FF", "#A5B4FC"),
        ("Score",     "DeepEval · 8 quality scores", "OFFLINE", "#FFFBEB", "#FCD34D"),
        ("Observe",   "Streamlit :8501",              "OFFLINE", "#F7F7F7", "#D1D5DB"),
    ]
    CX = [1.0, 3.0, 5.0, 7.0, 9.0]
    CY, BW, BH = 1.0, 0.85, 0.60

    fig = go.Figure()

    for i, ((name, sub, status, bg, bd), cx) in enumerate(zip(STAGES, CX)):
        fig.add_shape(type="rect",
            x0=cx - BW, x1=cx + BW, y0=CY - BH, y1=CY + BH,
            fillcolor=bg, line=dict(color=bd, width=1.5), layer="below")
        dot_col = "#10B981" if status == "ONLINE" else "#9CA3AF"
        fig.add_annotation(x=cx, y=CY + BH - 0.15, text=f"● {status}",
            showarrow=False, font=dict(size=8, color=dot_col, family="Inter"),
            xanchor="center")
        fig.add_annotation(x=cx, y=CY + 0.12, text=f"<b>{name}</b>",
            showarrow=False, font=dict(size=12, color="#111827", family="Inter"),
            xanchor="center")
        fig.add_annotation(x=cx, y=CY - 0.28, text=sub,
            showarrow=False, font=dict(size=9, color="#6B7280", family="Inter"),
            xanchor="center")
        if i < len(STAGES) - 1:
            fig.add_annotation(
                x=CX[i + 1] - BW - 0.06, y=CY,
                ax=cx + BW + 0.06, ay=CY,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True, arrowhead=2, arrowwidth=1.5, arrowsize=1.0,
                arrowcolor="#A100FF", text="")

    # Locust box (load test, below Invoke)
    LCX, LCY = CX[0], -0.35
    fig.add_shape(type="rect",
        x0=LCX - BW, x1=LCX + BW, y0=LCY - 0.40, y1=LCY + 0.40,
        fillcolor="#FFF1F2", line=dict(color="#FDA4AF", width=1.5), layer="below")
    fig.add_annotation(x=LCX, y=LCY + 0.15, text="<b>Load Test</b>",
        showarrow=False, font=dict(size=12, color="#111827", family="Inter"),
        xanchor="center")
    fig.add_annotation(x=LCX, y=LCY - 0.15, text="Locust :8089",
        showarrow=False, font=dict(size=9, color="#6B7280", family="Inter"),
        xanchor="center")
    # Dashed arrow: Locust → Invoke
    fig.add_annotation(
        x=LCX, y=CY - BH - 0.04,
        ax=LCX, ay=LCY + 0.40 + 0.04,
        xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=2, arrowwidth=1.5, arrowsize=1.0,
        arrowcolor="#F43F5E", text="")

    # Feedback loop at bottom: Observe → Invoke (dotted path)
    LY = -1.05
    fig.add_shape(type="path",
        path=f"M {CX[-1]} {CY - BH} L {CX[-1]} {LY} L {CX[0]} {LY} L {CX[0]} {CY - BH}",
        line=dict(color="#A100FF", width=1.5, dash="dot"))
    fig.add_annotation(x=5.0, y=LY - 0.08, text="DEPLOY",
        showarrow=False, font=dict(size=9, color="#A100FF", family="Inter"),
        xanchor="center", bgcolor="white", borderpad=3)

    fig.update_xaxes(range=[0.0, 10.0], visible=False)
    fig.update_yaxes(range=[-1.5, 2.0], visible=False)
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        height=340, margin=dict(l=10, r=10, t=20, b=20),
        showlegend=False,
    )
    return fig


# ── Page routing ───────────────────────────────────────────────────────────────
page = st.session_state.page


# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if page == "Overview":
    page_header(
        "AI Agent Evaluation · Accenture QE Capability",
        "AgentPulse",
        "Performance &amp; quality scoring under concurrent load &nbsp;·&nbsp; "
        "Powered by DeepEval + MLflow + Azure OpenAI",
    )

    _sla_banner()

    scored = (
        df_evals.dropna(subset=["quality_score"]).copy()
        if (not df_evals.empty and "quality_score" in df_evals.columns)
        else pd.DataFrame()
    )

    # KPI row
    kc1, kc2, kc3, kc4 = st.columns(4)
    total_runs = len(df_evals) if not df_evals.empty else 0
    kc1.markdown(fiq_stat_card("Total Runs", str(total_runs), "agent invocations logged", accent=True), unsafe_allow_html=True)

    if not scored.empty:
        avg_q = float(scored["quality_score"].mean()) if "quality_score" in scored.columns else None
        avg_s = float(scored["safety_score"].mean())  if "safety_score"  in scored.columns else None
        avg_r = float(scored["rag_score"].mean())     if "rag_score"      in scored.columns else None
        if avg_q is not None:
            kc2.markdown(fiq_stat_card("Avg Quality", f"{avg_q:.3f}", f"across {len(scored)} scored runs"), unsafe_allow_html=True)
        if avg_s is not None:
            kc3.markdown(fiq_stat_card("Safety Score", f"{avg_s:.3f}", "avg · target ≥ 0.90"), unsafe_allow_html=True)
        if avg_r is not None:
            kc4.markdown(fiq_stat_card("RAG Score", f"{avg_r:.3f}", "avg · target ≥ 0.70"), unsafe_allow_html=True)
    else:
        for kc in (kc2, kc3, kc4):
            kc.markdown(fiq_stat_card("—", "N/A", "no scored runs yet"), unsafe_allow_html=True)

    # Speed & Cost KPI row
    st.markdown('<div style="margin:10px 0 4px;"></div>', unsafe_allow_html=True)
    _sc_df = (
        df_evals[df_evals["ttft_seconds"].notna()].copy()
        if (not df_evals.empty and "ttft_seconds" in df_evals.columns)
        else pd.DataFrame()
    )
    sc1, sc2, sc3, sc4 = st.columns(4)
    if not _sc_df.empty:
        _avg_ttft  = float(_sc_df["ttft_seconds"].mean())       if "ttft_seconds"       in _sc_df.columns else None
        _avg_tps   = float(_sc_df["tokens_per_second"].mean())  if "tokens_per_second"  in _sc_df.columns else None
        _avg_otok  = float(_sc_df["output_tokens"].mean())      if "output_tokens"      in _sc_df.columns else None
        _tot_cost  = float(df_evals["cost_usd"].sum())          if "cost_usd"           in df_evals.columns else None
        _n_cost    = int(df_evals["cost_usd"].notna().sum())    if "cost_usd"           in df_evals.columns else 0
        sc1.markdown(fiq_stat_card("Avg TTFT",          f"{_avg_ttft:.2f}s"   if _avg_ttft  is not None else "—", "avg across runs",         accent=True), unsafe_allow_html=True)
        sc2.markdown(fiq_stat_card("Avg Tokens/sec",    f"{_avg_tps:.1f}"     if _avg_tps   is not None else "—", "avg across runs"),                       unsafe_allow_html=True)
        sc3.markdown(fiq_stat_card("Avg Output Tokens", f"{int(_avg_otok)}"   if _avg_otok  is not None else "—", "avg across runs"),                       unsafe_allow_html=True)
        sc4.markdown(fiq_stat_card("Total Est. Cost",   f"${_tot_cost:.4f}"   if _tot_cost  is not None else "—", f"across {_n_cost} runs"),                unsafe_allow_html=True)
    else:
        for _sc in (sc1, sc2, sc3, sc4):
            _sc.markdown(fiq_stat_card("—", "N/A", "no speed data yet"), unsafe_allow_html=True)

    st.markdown('<div style="margin:28px 0 12px;"></div>', unsafe_allow_html=True)

    # Latest runs table (FrontierIQ style HTML)
    fiq_eyebrow("Latest Agent Runs")
    if df_evals.empty:
        st.info("No runs found. Start the agent API and send queries via `/invoke`.")
    else:
        disp = df_evals.sort_values("start_time", ascending=False).head(8)
        thr_q = eval_cfg.get("min_quality_score", 0.65)

        rows_html = ""
        for _, r in disp.iterrows():
            qs = r.get("quality_score", None)
            if pd.notna(qs):
                qs_f   = f"{float(qs):.3f}"
                passed = float(qs) >= thr_q
                qs_cls = "td-pass" if passed else "td-fail"
                qs_sfx = " ✓" if passed else " ✗"
            else:
                qs_f   = "—"
                qs_cls = "td-muted"
                qs_sfx = ""

            intent  = str(r.get("intent", "—"))
            ts      = r["start_time"].strftime("%Y-%m-%d %H:%M") if pd.notna(r["start_time"]) else "—"
            rname   = str(r.get("run_name", r["run_id"][:8]))
            latency = r.get("latency_total_pipeline", None)
            lat_s   = f"{float(latency):.1f}s" if pd.notna(latency) else "—"

            rows_html += (
                f'<tr>'
                f'<td class="td-code">{rname}</td>'
                f'<td class="td-muted">{ts}</td>'
                f'<td>{intent}</td>'
                f'<td class="{qs_cls}">{qs_f}{qs_sfx}</td>'
                f'<td class="td-muted">{lat_s}</td>'
                f'</tr>'
            )

        table_html = (
            '<table class="fiq-table">'
            '<thead><tr>'
            '<th>Run</th><th>Time</th><th>Intent</th>'
            '<th>Quality Score</th><th>Latency</th>'
            '</tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            '</table>'
        )
        st.markdown(table_html, unsafe_allow_html=True)

    # Quick-nav cards
    st.markdown('<div style="margin:28px 0 12px;"></div>', unsafe_allow_html=True)
    fiq_eyebrow("Navigate")
    nav_c1, nav_c2, nav_c3, nav_c4 = st.columns(4)
    for col_obj, dest, lbl, desc in [
        (nav_c1, "Quality Metrics",      "Quality Metrics",      "KPI cards, per-metric bars, scored runs"),
        (nav_c2, "Speed & Cost",         "Speed & Cost",         "TTFT, tokens/sec, cloud-equivalent cost"),
        (nav_c3, "Load Test",            "Load Test",            "p50/p95/p99 latency, error rate under load"),
        (nav_c4, "Metric Guide",         "Metric Guide",         "Plain-English guide to all 17 metrics"),
    ]:
        _enc = urllib.parse.quote(dest)
        col_obj.markdown(
            f'<a href="?nav={_enc}" target="_self" style="text-decoration:none;display:block;">'
            f'<div style="background:#fff;border:1px solid #E1E1E1;border-radius:14px;padding:18px 20px;'
            f'transition:border-color 0.15s,box-shadow 0.15s;cursor:pointer;" '
            f'onmouseover="this.style.borderColor=\'#A100FF\';this.style.boxShadow=\'0 2px 12px rgba(161,0,255,.10)\'" '
            f'onmouseout="this.style.borderColor=\'#E1E1E1\';this.style.boxShadow=\'none\'">'
            f'<div style="font-size:14px;font-weight:700;color:#1A1A1A;margin-bottom:6px;">{lbl}</div>'
            f'<div style="font-size:13px;color:#767676;line-height:1.4;">{desc}</div>'
            f'<div style="font-size:11px;font-weight:600;color:#A100FF;margin-top:10px;">View →</div>'
            f'</div></a>',
            unsafe_allow_html=True,
        )

    render_footer()


# ══════════════════════════════════════════════════════════════════════════════
# ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Architecture":
    page_header(
        "Platform Architecture · AgentPulse",
        "How it Works",
        "Eight open-source tools wired together — from user query to scored evaluation result. "
        "Every component runs locally with no cloud API keys required.",
    )

    # Data flow diagram (Plotly — avoids Streamlit markdown code-block rendering bug)
    fiq_eyebrow("Data Flow")
    st.markdown(
        '<div style="background:#fff;border:1px solid #E1E1E1;border-radius:16px;'
        'padding:8px 16px 4px;margin-bottom:32px;">',
        unsafe_allow_html=True,
    )
    st.plotly_chart(_draw_pipeline_flow(), use_container_width=True)
    st.markdown(
        '<div style="font-size:12px;color:#767676;padding:0 8px 12px;">'
        'Pink dashed arrow = Locust load-tests the Invoke endpoint. '
        'Purple dotted loop = continuous eval &rarr; improve &rarr; deploy cycle.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Tool cards grid
    fiq_eyebrow("Technology Stack — 8 Tools")
    st.markdown('<div style="margin-bottom:16px;font-size:13px;color:#767676;">Every tool is open-source and runs entirely on your local machine.</div>', unsafe_allow_html=True)

    tools = [
        ("LangGraph", "LangChain Inc.", "Open Source", "os",
         "Defines the IT helpdesk agent as a 4-node directed graph: Intent → FAISS RAG → Azure OpenAI LLM → Escalation. Each node is a separate MLflow span for per-step latency breakdown.",
         "Agent Orchestration",
         ["intent", "escalated", "node_timings"],
         "#A100FF"),
        ("Azure OpenAI gpt-5.2-chat-2", "Microsoft / Accenture", "Enterprise", "cloud",
         "Cloud LLM via Accenture's Azure subscription. Used for agent responses (streamed), intent classification, and as the DeepEval judge for quality scoring.",
         "LLM Inference",
         ["ttft_seconds", "tokens_per_second", "input_tokens", "output_tokens"],
         "#00E5C7"),
        ("FAISS", "Meta AI", "Open Source", "os",
         "Vector similarity search for RAG. Encodes IT runbooks into embeddings (text-embedding-ada-002 via Azure OpenAI) and retrieves the most semantically relevant chunks for each query.",
         "Vector Store (RAG)",
         ["contextual_relevancy", "retrieved_context"],
         "#006B5A"),
        ("MLflow 2.22.5", "Databricks / Linux Foundation", "Open Source", "os",
         "Single platform for experiment tracking, per-run traces, metric logging, and artifact storage. Every agent run logs 17 metrics here. Dashboard reads from MLflow API.",
         "Experiment Tracking",
         ["all 17 metrics", "traces", "eval_data.json"],
         "#2E5BFF"),
        ("DeepEval 4.0.2", "Confident AI", "Open Source", "os",
         "LLM evaluation framework providing 8 quality metrics: 3 RAG (formula-based) + 4 Helpdesk GEval (LLM-as-judge) + 1 Safety. Run post-invocation via eval_runner.py.",
         "Quality Evaluation",
         ["faithfulness", "answer_relevancy", "completeness", "toxicity", "+ 4 more"],
         "#E84C8A"),
        ("Locust 2.32.3", "Locust.io", "Open Source", "os",
         "Simulates N concurrent users hitting the FastAPI /invoke endpoint. Measures response time percentiles and error rates — feeds the Quality Under Load signature chart.",
         "Load Testing",
         ["p50/p95/p99", "rps_peak", "error_rate_pct", "user_count"],
         "#F59E0B"),
        ("FastAPI + Uvicorn", "Sebastián Ramírez / Encode", "Open Source", "os",
         "Serves the agent pipeline as a REST API on :8001. Exposes /invoke (POST) for queries and /docs (Swagger UI) for interactive testing. Locust hits this endpoint.",
         "API Server",
         ["/invoke", "run_id", "response", "escalated"],
         "#4A4A4A"),
        ("Streamlit 1.41.1", "Snowflake Inc.", "Open Source", "os",
         "This dashboard. Reads metrics from the MLflow API every 30s and renders 7 pages covering quality, load, architecture, and cost. PDF export via xhtml2pdf.",
         "Live Dashboard",
         ["charts", "tables", "PDF export", "6 pages"],
         "#FF4B4B"),
    ]

    for i in range(0, len(tools), 3):
        cols = st.columns(3)
        for j, tool in enumerate(tools[i:i+3]):
            cols[j].markdown(tool_card(*tool), unsafe_allow_html=True)
        st.markdown('<div style="margin-bottom:16px;"></div>', unsafe_allow_html=True)

    # Port reference
    st.markdown('<div style="margin-top:8px;"></div>', unsafe_allow_html=True)
    fiq_eyebrow("Service Ports")
    ports_html = (
        '<table class="fiq-table" style="max-width:560px;">'
        '<thead><tr><th>Service</th><th>Port</th><th>URL</th><th>Purpose</th></tr></thead>'
        '<tbody>'
        '<tr><td class="td-bold">AgentPulse Dashboard</td><td class="td-code">8501</td><td class="td-muted">http://localhost:8501</td><td class="td-muted">This Streamlit dashboard</td></tr>'
        '<tr><td class="td-bold">Agent API</td><td class="td-code">8001</td><td class="td-muted">http://localhost:8001/docs</td><td class="td-muted">FastAPI Swagger UI + /invoke</td></tr>'
        '<tr><td class="td-bold">MLflow UI</td><td class="td-code">5000</td><td class="td-muted">http://localhost:5000</td><td class="td-muted">Experiment & trace viewer</td></tr>'
        '<tr><td class="td-bold">Azure OpenAI</td><td class="td-code">443</td><td class="td-muted">bsab-mg0lb5q7-eastus2.cognitiveservices.azure.com</td><td class="td-muted">LLM inference + embeddings</td></tr>'
        '<tr><td class="td-bold">Locust UI</td><td class="td-code">8089</td><td class="td-muted">http://localhost:8089</td><td class="td-muted">Load test control (on-demand)</td></tr>'
        '</tbody></table>'
    )
    st.markdown(ports_html, unsafe_allow_html=True)

    render_footer()


# ══════════════════════════════════════════════════════════════════════════════
# QUALITY METRICS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Quality Metrics":
    page_header(
        "Quality Evaluation · AgentPulse",
        "Quality Score Overview",
    )

    if df_evals.empty:
        st.info("No runs found. Start the agent and send queries via the FastAPI endpoint.")
    else:
        scored = (
            df_evals.dropna(subset=["quality_score"]).copy()
            if "quality_score" in df_evals.columns else pd.DataFrame()
        )
        if scored.empty:
            st.info("Runs exist but none scored yet.\n\n"
                    "```powershell\n.venv\\Scripts\\python.exe -m evals.eval_runner\n```")
        else:
            scored = scored.sort_values("start_time")
            _sla_banner()

            c1, c2, c3, c4 = st.columns(4)
            for col_obj, key, label, accent in [
                (c1, "quality_score",  "Quality Score",  True),
                (c2, "rag_score",      "RAG Score",      False),
                (c3, "helpdesk_score", "Helpdesk Score", False),
                (c4, "safety_score",   "Safety Score",   False),
            ]:
                if key in scored.columns:
                    avg_v = float(scored[key].mean())
                    n     = len(scored[key].dropna())
                    col_obj.markdown(
                        fiq_stat_card(label, f"{avg_v:.3f}", f"across {n} scored runs", accent=accent),
                        unsafe_allow_html=True,
                    )

            st.markdown('<div style="margin:24px 0 8px;"></div>', unsafe_allow_html=True)

            composite_cols = [c for c in ["quality_score","rag_score","helpdesk_score","safety_score"]
                              if c in scored.columns]
            fig = px.line(
                scored, x="start_time", y=composite_cols, markers=True,
                labels={"value": "Score", "start_time": "Run Time", "variable": "Metric"},
                color_discrete_map={
                    "quality_score": FIQ["quality"], "rag_score": FIQ["rag"],
                    "helpdesk_score": FIQ["helpdesk"], "safety_score": FIQ["safety"],
                },
            )
            fig.add_hline(y=eval_cfg.get("min_quality_score", 0.65), line_dash="dash",
                          line_color=FIQ["sla"], annotation_text="Quality SLA",
                          annotation_font_color=FIQ["sla"])
            fig.update_layout(**PLOTLY_LAYOUT, title="Composite Quality Scores per Run",
                              yaxis_range=[0, 1.05], legend_title="")
            st.plotly_chart(fig, use_container_width=True)

            all_m = [m for m in METRIC_CATEGORY if m in scored.columns]
            if all_m:
                avg_df = scored[all_m].mean().reset_index()
                avg_df.columns = ["metric", "avg_score"]
                avg_df["category"] = avg_df["metric"].map(METRIC_CATEGORY)
                avg_df = avg_df.sort_values("avg_score")
                fig2 = px.bar(
                    avg_df, x="avg_score", y="metric", orientation="h",
                    color="category", color_discrete_map=CAT_COLOURS,
                    labels={"avg_score": "Avg Score", "metric": ""},
                )
                fig2.update_layout(**PLOTLY_LAYOUT, title="Average Score by Metric",
                                   xaxis_range=[0, 1], legend_title="Category")
                st.plotly_chart(fig2, use_container_width=True)

            fiq_eyebrow("Recent Scored Runs")
            disp_cols = [c for c in ["run_name","start_time","intent","quality_score","rag_score",
                                     "helpdesk_score","safety_score","faithfulness","latency_total_pipeline"]
                         if c in scored.columns]
            st.dataframe(
                scored[disp_cols].sort_values("start_time", ascending=False).head(25),
                use_container_width=True, hide_index=True,
            )

    render_footer()


# ══════════════════════════════════════════════════════════════════════════════
# LOAD TEST
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Load Test":
    page_header(
        "Load Test Results · AgentPulse",
        "Load Test Performance",
    )

    if df_load.empty:
        st.info(
            "No load test runs found. Start Locust:\n\n"
            "```powershell\n"
            "locust -f load_tests/locustfile.py --host http://127.0.0.1:8001 "
            "--users 4 --spawn-rate 1 --run-time 180s --headless\n"
            "```"
        )
    else:
        df_l = (
            df_load.dropna(subset=["user_count"]).sort_values("user_count").copy()
            if "user_count" in df_load.columns else df_load.copy()
        )
        if not df_l.empty:
            latest  = df_l.iloc[-1]
            sla_p95 = sla_cfg.get("p95_latency_ms", 15000)
            sla_err = sla_cfg.get("error_rate_pct", 5.0)

            c1, c2, c3, c4 = st.columns(4)
            for col_obj, key, label, fmt, accent in [
                (c1, "p95_response_time_ms", "P95 Latency",  "{:.0f} ms", True),
                (c2, "avg_response_time_ms", "Avg Latency",  "{:.0f} ms", False),
                (c3, "error_rate_pct",       "Error Rate",   "{:.1f}%",   False),
                (c4, "rps_peak",             "Peak RPS",     "{:.2f}",    False),
            ]:
                if key in latest and pd.notna(latest[key]):
                    val = float(latest[key])
                    if key == "p95_response_time_ms":
                        sub = f"SLA: {sla_p95} ms · {'✓ PASS' if val <= sla_p95 else '✗ BREACH'}"
                    elif key == "error_rate_pct":
                        sub = f"SLA: {sla_err}% · {'✓ PASS' if val <= sla_err else '✗ BREACH'}"
                    else:
                        sub = "latest run"
                    col_obj.markdown(fiq_stat_card(label, fmt.format(val), sub, accent=accent), unsafe_allow_html=True)

            st.markdown('<div style="margin:24px 0 8px;"></div>', unsafe_allow_html=True)

            lat_cols = [c for c in ["p50_response_time_ms","p95_response_time_ms","p99_response_time_ms"]
                        if c in df_l.columns]
            if lat_cols:
                fig = px.line(df_l, x="user_count", y=lat_cols, markers=True,
                              labels={"value": "Latency (ms)", "user_count": "Concurrent Users", "variable": "Percentile"},
                              color_discrete_sequence=[FIQ["rag"], FIQ["quality"], "#1A1A1A"])
                fig.add_hline(y=sla_p95, line_dash="dash", line_color=FIQ["sla"],
                              annotation_text=f"p95 SLA ({sla_p95} ms)", annotation_font_color=FIQ["sla"])
                fig.update_layout(**PLOTLY_LAYOUT, title="Response Time Percentiles vs Concurrent Users",
                                  xaxis_title="Concurrent Users", yaxis_title="Latency (ms)")
                st.plotly_chart(fig, use_container_width=True)

            if "error_rate_pct" in df_l.columns:
                fig3 = px.bar(df_l, x="user_count", y="error_rate_pct",
                              color="error_rate_pct",
                              color_continuous_scale=[FIQ["rag"], "#FFC107", FIQ["sla"]],
                              labels={"error_rate_pct": "Error Rate (%)", "user_count": "Concurrent Users"})
                fig3.add_hline(y=sla_err, line_dash="dash", line_color=FIQ["sla"],
                               annotation_text=f"Error SLA ({sla_err}%)", annotation_font_color=FIQ["sla"])
                fig3.update_layout(**PLOTLY_LAYOUT, title="Error Rate vs Concurrent Users", showlegend=False)
                st.plotly_chart(fig3, use_container_width=True)

            disp_l = [c for c in ["run_name","user_count","requests_total","avg_response_time_ms",
                                   "p95_response_time_ms","error_rate_pct","rps_peak"] if c in df_l.columns]
            fiq_eyebrow("Load Test Runs")
            st.dataframe(df_l[disp_l], use_container_width=True, hide_index=True)

    render_footer()


# ══════════════════════════════════════════════════════════════════════════════
# QUALITY UNDER LOAD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Quality Under Load":
    page_header(
        "Signature Demo · AgentPulse",
        "Quality Under Load",
        "AI response quality degrades as concurrent users increase — the headline enterprise demo metric.",
    )

    if df_summary.empty:
        st.info(
            "No summary data yet. Run the signature workflow:\n\n"
            "```powershell\n"
            "# Run Locust at each user level, then score:\n"
            "locust ... --users 5 --headless\n"
            ".venv\\Scripts\\python.exe -m evals.eval_runner --user-count 5\n"
            "# Repeat at 10, 20 users\n"
            "```"
        )
    else:
        df_s = df_summary.dropna(subset=["user_count"]).sort_values("user_count").copy()

        q_cols = [c for c in ["avg_quality_score","avg_rag_score","avg_helpdesk_score","avg_safety_score"]
                  if c in df_s.columns]
        if q_cols:
            fig = px.line(df_s, x="user_count", y=q_cols, markers=True,
                          labels={"value": "Score", "user_count": "Concurrent Users", "variable": "Metric"},
                          color_discrete_map={
                              "avg_quality_score": FIQ["quality"], "avg_rag_score": FIQ["rag"],
                              "avg_helpdesk_score": FIQ["helpdesk"], "avg_safety_score": FIQ["safety"],
                          })
            fig.add_hline(y=eval_cfg.get("min_quality_score", 0.65), line_dash="dash",
                          line_color=FIQ["sla"], annotation_text="Quality SLA",
                          annotation_font_color=FIQ["sla"])
            fig.update_layout(**PLOTLY_LAYOUT, title="AI Quality Score vs Concurrent Users",
                              yaxis_range=[0, 1.05], xaxis_title="Concurrent Users",
                              yaxis_title="Avg Quality Score", legend_title="")
            st.plotly_chart(fig, use_container_width=True)

        detail_cols = [c for c in df_s.columns
                       if c.startswith("avg_") and c not in q_cols
                       and "bias" not in c and "toxicity" not in c]
        if detail_cols:
            fig2 = px.line(df_s, x="user_count", y=detail_cols, markers=True,
                           labels={"value": "Score", "user_count": "Concurrent Users", "variable": "Metric"})
            fig2.update_layout(**PLOTLY_LAYOUT, title="Individual Metric Scores Under Load",
                               yaxis_range=[0, 1.05], legend_title="")
            st.plotly_chart(fig2, use_container_width=True)

        fiq_eyebrow("Concurrency Summary Table")
        sum_disp = [c for c in df_s.columns if c.startswith("avg_") or c in ("user_count","runs_evaluated")]
        st.dataframe(df_s[sum_disp].sort_values("user_count"), use_container_width=True, hide_index=True)

    render_footer()


# ══════════════════════════════════════════════════════════════════════════════
# RUN EXPLORER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "DeepEval":
    page_header(
        "Quality Evaluation · AgentPulse",
        "DeepEval",
        "Per-run drill-down into DeepEval scores — composite quality, RAG, helpdesk, and safety, "
        "plus a radar view of all 8 individual metrics scored by Azure OpenAI as judge.",
    )

    if df_evals.empty:
        st.info("No runs available.")
    else:
        scored_ex = (
            df_evals.dropna(subset=["quality_score"]).copy()
            if "quality_score" in df_evals.columns else df_evals.copy()
        )
        if scored_ex.empty:
            st.info("No scored runs yet.")
        else:
            scored_ex = scored_ex.sort_values("start_time", ascending=False).reset_index(drop=True)
            labels = scored_ex.apply(
                lambda r: (
                    f"{r.get('run_name', r['run_id'][:8])}  ·  "
                    f"{r.get('intent','?')}  ·  "
                    f"quality: {r.get('quality_score','—')}"
                ),
                axis=1,
            ).tolist()

            idx = st.selectbox("Select a run", range(len(labels)), format_func=lambda i: labels[i])
            run = scored_ex.iloc[idx]

            col_a, col_b = st.columns([1.2, 1])
            with col_a:
                fiq_eyebrow("Query")
                st.markdown(
                    f'<div style="background:#fff;border:1px solid #E1E1E1;border-radius:12px;'
                    f'padding:16px 18px;font-size:14px;color:#1A1A1A;margin-bottom:12px;">'
                    f'{run.get("query","N/A")}</div>',
                    unsafe_allow_html=True,
                )
                fiq_eyebrow("Classification")
                st.markdown(
                    f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;">'
                    f'{fiq_badge(str(run.get("intent","?")))}'
                    f'{"&nbsp;" + fiq_badge("ESCALATED", "fail") if str(run.get("escalated","")).lower() in ("true","1") else fiq_badge("NOT ESCALATED", "pass")}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                fiq_eyebrow("Composite Scores")
                thr_map = {
                    "quality_score":  eval_cfg.get("min_quality_score", 0.65),
                    "rag_score":      eval_cfg.get("min_rag_score", 0.70),
                    "helpdesk_score": eval_cfg.get("min_helpdesk_score", 0.60),
                    "safety_score":   eval_cfg.get("min_safety_score", 0.70),
                }
                rows_html = ""
                for key, thr in thr_map.items():
                    if key in run and pd.notna(run[key]):
                        val    = float(run[key])
                        passed = val >= thr
                        badge  = fiq_badge(f"{'PASS' if passed else 'FAIL'}", "pass" if passed else "fail")
                        rows_html += (
                            f'<div style="display:flex;justify-content:space-between;align-items:center;'
                            f'padding:10px 0;border-bottom:1px solid #F7F7F7;">'
                            f'<span style="font-size:13px;color:#4A4A4A;">{key}</span>'
                            f'<div style="display:flex;align-items:center;gap:10px;">'
                            f'<span style="font-size:17px;font-weight:700;color:#1A1A1A;">{val:.3f}</span>'
                            f'{badge}</div></div>'
                        )
                st.markdown(
                    f'<div style="background:#fff;border:1px solid #E1E1E1;border-radius:12px;padding:4px 16px;">'
                    f'{rows_html}</div>',
                    unsafe_allow_html=True,
                )

            with col_b:
                ind_metrics = ["faithfulness","answer_relevancy","contextual_relevancy",
                               "actionability","professional_tone","task_resolution",
                               "completeness","escalation_appropriateness"]
                avail = [m for m in ind_metrics if m in run and pd.notna(run[m])]
                if avail:
                    vals = [float(run[m]) for m in avail]
                    fig_r = go.Figure(go.Scatterpolar(
                        r=vals + [vals[0]],
                        theta=avail + [avail[0]],
                        fill="toself",
                        fillcolor="rgba(161,0,255,0.10)",
                        line=dict(color=FIQ["quality"], width=2),
                    ))
                    fig_r.update_layout(
                        polar=dict(
                            radialaxis=dict(range=[0, 1], gridcolor=FIQ["grid"], linecolor=FIQ["grid"]),
                            angularaxis=dict(linecolor=FIQ["grid"]),
                            bgcolor="#FFFFFF",
                        ),
                        paper_bgcolor="#FFFFFF",
                        showlegend=False,
                        font_family="Inter, sans-serif",
                        font_color="#1A1A1A",
                        margin=dict(t=20, b=20, l=20, r=20),
                        height=380,
                    )
                    st.plotly_chart(fig_r, use_container_width=True)

    render_footer()


# ══════════════════════════════════════════════════════════════════════════════
# SPEED & COST
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Speed & Cost":
    page_header(
        "Speed & Cost · AgentPulse",
        "Speed & Cost Overview",
        "TTFT · Token throughput · Cloud-equivalent cost (GPT-4o-mini pricing)",
    )

    sc_cols = [c for c in ["ttft_seconds", "tokens_per_second", "output_tokens", "cost_usd"]
               if c in df_evals.columns]

    if df_evals.empty:
        st.info("No agent runs found in MLflow. Start the agent API and send a query to begin.")
    elif not sc_cols:
        # Runs exist but predate Phase 6 TTFT tracking — show friendly explainer
        st.markdown(
            '<div style="background:#F5EBFE;border:1px solid #C9A5FA;border-radius:16px;'
            'padding:24px 28px;margin-bottom:24px;">'
            '<div style="font-size:15px;font-weight:700;color:#460073;margin-bottom:8px;">'
            'Speed &amp; cost metrics are ready to capture</div>'
            '<div style="font-size:13px;color:#4A4A4A;line-height:1.6;">'
            f'There {"is" if len(df_evals)==1 else "are"} <strong>{len(df_evals)} existing run{"s" if len(df_evals)!=1 else ""}</strong> '
            'in MLflow, but they were created before TTFT tracking was added.<br><br>'
            'Send one new query to the agent API and this tab will populate automatically:</div>'
            '<div style="background:#fff;border-radius:10px;padding:14px 16px;margin-top:14px;'
            'font-family:monospace;font-size:12px;color:#460073;">'
            'Invoke-WebRequest -Uri "http://localhost:8001/invoke" -Method POST<br>'
            '-ContentType "application/json"<br>'
            '-Body \'{"query":"My VPN keeps disconnecting"}\''
            '</div></div>',
            unsafe_allow_html=True,
        )
    else:
        sc = (
            df_evals.dropna(subset=["ttft_seconds"]).copy()
            if "ttft_seconds" in df_evals.columns else pd.DataFrame()
        )

        # Include zero-TTFT runs too (pipeline default before streaming was active)
        if "ttft_seconds" in df_evals.columns:
            sc = df_evals[df_evals["ttft_seconds"].notna()].copy()

        if sc.empty:
            st.info("No runs with speed metrics yet. New runs will populate this tab automatically.")
        else:
            sc = sc.sort_values("start_time")

            kc1, kc2, kc3, kc4 = st.columns(4)
            for col_obj, key, label, fmt, accent in [
                (kc1, "ttft_seconds",      "Avg TTFT",         lambda v: f"{v:.2f}s",  True),
                (kc2, "tokens_per_second", "Avg Tokens/sec",   lambda v: f"{v:.1f}",   False),
                (kc3, "output_tokens",     "Avg Output Tokens", lambda v: f"{int(v)}", False),
                (kc4, "cost_usd",          "Total Est. Cost",  lambda v: f"${v:.4f}",  False),
            ]:
                if key in sc.columns:
                    val = float(sc[key].mean()) if key != "cost_usd" else float(sc[key].sum())
                    sub = "avg across runs" if key != "cost_usd" else f"across {len(sc)} runs"
                    col_obj.markdown(fiq_stat_card(label, fmt(val), sub, accent=accent), unsafe_allow_html=True)

            st.markdown('<div style="margin:24px 0 8px;"></div>', unsafe_allow_html=True)

            row_left, row_right = st.columns(2)
            with row_left:
                if "ttft_seconds" in sc.columns:
                    fig_ttft = px.bar(sc, x="run_name", y="ttft_seconds",
                                      labels={"run_name": "Run", "ttft_seconds": "TTFT (s)"},
                                      title="Time to First Token per Run",
                                      color_discrete_sequence=[FIQ["quality"]])
                    fig_ttft.add_hline(y=2.0, line_dash="dash", line_color=FIQ["sla"], annotation_text="2s reference")
                    fig_ttft.update_layout(**PLOTLY_LAYOUT, title_font_size=14)
                    fig_ttft.update_xaxes(tickangle=-30)
                    st.plotly_chart(fig_ttft, use_container_width=True)
            with row_right:
                if "tokens_per_second" in sc.columns:
                    fig_tps = px.bar(sc, x="run_name", y="tokens_per_second",
                                     labels={"run_name": "Run", "tokens_per_second": "Tokens/sec"},
                                     title="Token Throughput per Run",
                                     color_discrete_sequence=[FIQ["rag"]])
                    fig_tps.update_layout(**PLOTLY_LAYOUT, title_font_size=14)
                    fig_tps.update_xaxes(tickangle=-30)
                    st.plotly_chart(fig_tps, use_container_width=True)

            row2_left, row2_right = st.columns(2)
            with row2_left:
                if "input_tokens" in sc.columns and "output_tokens" in sc.columns:
                    tok_df = sc[["run_name","input_tokens","output_tokens"]].melt(
                        id_vars="run_name", var_name="Token Type", value_name="Tokens"
                    )
                    tok_df["Token Type"] = tok_df["Token Type"].map(
                        {"input_tokens": "Input", "output_tokens": "Output"}
                    )
                    fig_tok = px.bar(tok_df, x="run_name", y="Tokens", color="Token Type", barmode="stack",
                                     labels={"run_name": "Run"},
                                     title="Input vs Output Tokens per Run",
                                     color_discrete_map={"Input": FIQ["safety"], "Output": FIQ["helpdesk"]})
                    fig_tok.update_layout(**PLOTLY_LAYOUT, title_font_size=14)
                    fig_tok.update_xaxes(tickangle=-30)
                    st.plotly_chart(fig_tok, use_container_width=True)
            with row2_right:
                if "cost_usd" in sc.columns:
                    fig_cost = px.bar(sc, x="run_name", y="cost_usd",
                                      labels={"run_name": "Run", "cost_usd": "Est. Cost (USD)"},
                                      title="Cloud-Equivalent Cost per Run",
                                      color_discrete_sequence=[FIQ["sla"]])
                    fig_cost.update_layout(**PLOTLY_LAYOUT, title_font_size=14)
                    fig_cost.update_xaxes(tickangle=-30)
                    fig_cost.update_yaxes(tickprefix="$", tickformat=".5f")
                    st.plotly_chart(fig_cost, use_container_width=True)

            fiq_eyebrow("Per-Run Detail")
            disp_cols = {
                "run_name": "Run", "intent": "Intent", "query": "Query",
                "ttft_seconds": "TTFT (s)",
                "tokens_per_second": "Tokens/sec", "input_tokens": "Input Tokens",
                "output_tokens": "Output Tokens", "cost_usd": "Est. Cost (USD)",
                "latency_total_pipeline": "Total Latency (s)",
            }
            disp = sc[[c for c in disp_cols if c in sc.columns]].rename(columns=disp_cols)
            if "TTFT (s)" in disp.columns:
                disp["TTFT (s)"] = disp["TTFT (s)"].map(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
            if "Est. Cost (USD)" in disp.columns:
                disp["Est. Cost (USD)"] = disp["Est. Cost (USD)"].map(lambda x: f"${x:.6f}" if pd.notna(x) else "—")
            if "Query" in disp.columns:
                disp["Query"] = disp["Query"].map(lambda x: (str(x)[:80] + "…") if pd.notna(x) and len(str(x)) > 80 else x)
            st.dataframe(disp, use_container_width=True, hide_index=True,
                         column_config={"Query": st.column_config.TextColumn(width="large")})

    st.markdown(
        '<div style="background:#F5EBFE;border-radius:12px;padding:14px 18px;margin-top:20px;">'
        '<div style="font-size:12px;font-weight:700;color:#460073;margin-bottom:5px;">About Cost Estimates</div>'
        '<div style="font-size:12px;color:#4A4A4A;line-height:1.7;">'
        'AgentPulse runs on <strong>Azure OpenAI via Accenture\'s enterprise subscription</strong>. '
        'The estimated cost uses '
        '<strong>GPT-4o-mini pricing</strong> ($0.15/1M input tokens, $0.60/1M output tokens) '
        'as a cloud-equivalent reference for client budgeting conversations.</div></div>',
        unsafe_allow_html=True,
    )

    render_footer()


# ══════════════════════════════════════════════════════════════════════════════
# INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Insights":
    page_header(
        "AI Analysis · AgentPulse",
        "Insights & Recommendations",
        "Pattern analysis across all scored runs — LLM-generated explanations + prioritized action items.",
    )

    reasons_list = load_eval_reasons()
    recommendations = load_eval_recommendations()

    # If no recs from MLflow artifact, compute live from reasons
    if not recommendations and reasons_list:
        from statistics import mean as _mean

        METRIC_ADVICE_DASH = {
            "contextual_relevancy": ("RAG Retrieval Gap", "Expand runbooks or increase FAISS top-k from 3 → 5."),
            "answer_relevancy":     ("Response Relevance", "Add query-specific resolution paths to each runbook section."),
            "completeness":         ("Incomplete Responses", "Strengthen system prompt to enumerate all retrieved steps."),
            "actionability":        ("Vague Action Steps", "Add numbered steps, menu paths, and portal URLs to runbooks."),
            "task_resolution":      ("Unresolved Issues", "Add escalation contacts and ticket URLs to each runbook."),
            "professional_tone":    ("Tone & Communication", "Add tone guidelines to the response generator system prompt."),
            "faithfulness":         ("Hallucination Risk", "Enforce 'only use retrieved context' in system prompt."),
            "toxicity":             ("Safety Violation", "Add a safety guardrail layer before returning responses."),
        }
        THRESHOLDS_DASH = {
            "faithfulness": 0.7, "answer_relevancy": 0.7, "contextual_relevancy": 0.6,
            "completeness": 0.5, "actionability": 0.5, "professional_tone": 0.5,
            "task_resolution": 0.5, "toxicity": 0.3,
        }
        metric_scores_dash = {}
        for rd in reasons_list:
            for mn, info in rd.get("metrics", {}).items():
                sc = info.get("score")
                if sc is not None:
                    metric_scores_dash.setdefault(mn, []).append(sc)
        for mn, scores_d in metric_scores_dash.items():
            avg = round(_mean(scores_d), 3)
            thr = THRESHOLDS_DASH.get(mn)
            if thr is None:
                continue
            cat, advice = METRIC_ADVICE_DASH.get(mn, ("Quality", "Review and improve."))
            if mn == "toxicity":
                if avg > thr:
                    recommendations.append({"severity": "HIGH", "category": cat, "metric": mn,
                                            "avg_score": avg, "threshold": thr,
                                            "finding": f"{mn} = {avg:.3f} exceeds ceiling {thr}",
                                            "recommendation": advice})
            elif avg < thr:
                severity = "HIGH" if avg < thr * 0.72 else "MEDIUM"
                recommendations.append({"severity": severity, "category": cat, "metric": mn,
                                        "avg_score": avg, "threshold": thr,
                                        "finding": f"{mn} = {avg:.3f} — {round(thr-avg,3):.3f} below SLA {thr}",
                                        "recommendation": advice})
        recommendations.sort(key=lambda r: ({"HIGH": 0, "MEDIUM": 1, "INFO": 2}.get(r.get("severity","INFO"), 9),
                                            r.get("avg_score", 1.0)))

    if not reasons_list:
        st.info(
            "No eval_reasons.json artifacts found. Run the eval runner with reasons enabled:\n\n"
            "```powershell\n.venv\\Scripts\\python.exe -m evals.eval_runner\n```"
        )
    else:
        # ── Severity summary tiles ──────────────────────────────────────────
        n_high   = sum(1 for r in recommendations if r.get("severity") == "HIGH")
        n_medium = sum(1 for r in recommendations if r.get("severity") == "MEDIUM")
        n_info   = sum(1 for r in recommendations if r.get("severity") == "INFO")

        _ts1, _ts2, _ts3, _ts4 = st.columns(4)
        _ts1.markdown(fiq_stat_card("Runs Analysed",   str(len(reasons_list)), "with LLM explanations", accent=True), unsafe_allow_html=True)
        _ts2.markdown(fiq_stat_card("HIGH Priority",   str(n_high),   "immediate action", accent=False), unsafe_allow_html=True)
        _ts3.markdown(fiq_stat_card("MEDIUM Priority", str(n_medium), "review recommended", accent=False), unsafe_allow_html=True)
        _ts4.markdown(fiq_stat_card("INFO",            str(n_info),   "passing / positive", accent=False), unsafe_allow_html=True)

        st.markdown('<div style="margin:28px 0 12px;"></div>', unsafe_allow_html=True)

        # ── Recommendations ─────────────────────────────────────────────────
        fiq_eyebrow("Prioritized Recommendations")
        if not recommendations:
            st.success("All metrics are above SLA thresholds — no action required.")
        else:
            SEVERITY_STYLE = {
                "HIGH":   ("background:#FEE2E2;border:1px solid #FCA5A5;border-left:4px solid #DC2626;", "#DC2626", "#DC2626"),
                "MEDIUM": ("background:#FEF3C7;border:1px solid #FCD34D;border-left:4px solid #D97706;", "#D97706", "#D97706"),
                "INFO":   ("background:#D1FAE5;border:1px solid #6EE7B7;border-left:4px solid #059669;", "#059669", "#059669"),
            }
            for rec in recommendations:
                sev = rec.get("severity", "MEDIUM")
                box_style, title_col, badge_col = SEVERITY_STYLE.get(sev, SEVERITY_STYLE["MEDIUM"])
                metric_name = rec.get("metric", "")
                avg_s  = rec.get("avg_score")
                thr_s  = rec.get("threshold")
                avg_str = f"{avg_s:.3f}" if avg_s is not None else "—"
                thr_str = f"{thr_s}"     if thr_s is not None else "—"

                st.markdown(
                    f'<div style="{box_style}border-radius:10px;padding:16px 18px;margin-bottom:12px;">'
                    f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
                    f'<span style="background:{badge_col};color:#fff;font-size:9px;font-weight:700;'
                    f'letter-spacing:.1em;padding:2px 8px;border-radius:3px;">{sev}</span>'
                    f'<span style="font-size:13px;font-weight:700;color:#1A1A1A;">{rec.get("category","")}</span>'
                    f'{"&nbsp;&nbsp;<span style=\"font-family:monospace;font-size:11px;color:#767676;\">" + metric_name + " = " + avg_str + " (SLA " + thr_str + ")</span>" if metric_name else ""}'
                    f'</div>'
                    f'<div style="font-size:13px;color:#374151;margin-bottom:8px;">{rec.get("finding","")}</div>'
                    f'<div style="font-size:12px;font-weight:600;color:#1A1A1A;margin-bottom:3px;">Recommended Action</div>'
                    f'<div style="font-size:12px;color:#4A4A4A;line-height:1.6;">{rec.get("recommendation","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown('<div style="margin:28px 0 12px;"></div>', unsafe_allow_html=True)

        # ── Quality by intent ───────────────────────────────────────────────
        fiq_eyebrow("Quality by Intent")
        intent_data = {}
        for rd in reasons_list:
            intent = rd.get("intent", "UNKNOWN")
            comps  = rd.get("composites", {})
            for key in ("quality_score", "rag_score", "helpdesk_score", "safety_score"):
                v = comps.get(key)
                if v is not None:
                    intent_data.setdefault(intent, {}).setdefault(key, []).append(v)

        if intent_data:
            from statistics import mean as _mean2
            intent_rows = []
            for intent, kv in intent_data.items():
                row = {"Intent": intent, "Runs": len(kv.get("quality_score", []))}
                for key, label in [("quality_score","Quality"),("rag_score","RAG"),
                                   ("helpdesk_score","Helpdesk"),("safety_score","Safety")]:
                    vals = kv.get(key, [])
                    row[label] = round(_mean2(vals), 3) if vals else None
                intent_rows.append(row)
            intent_df = pd.DataFrame(intent_rows).sort_values("Quality", ascending=True)

            fig_intent = px.bar(
                intent_df, x="Quality", y="Intent", orientation="h",
                color="Quality",
                color_continuous_scale=["#DC2626", "#D97706", "#059669"],
                range_color=[0, 1],
                labels={"Quality": "Avg Quality Score", "Intent": ""},
                title="Average Quality Score by Intent",
            )
            fig_intent.add_vline(x=eval_cfg.get("min_quality_score", 0.65), line_dash="dash",
                                 line_color=FIQ["sla"], annotation_text="Quality SLA")
            fig_intent.update_layout(**PLOTLY_LAYOUT, xaxis_range=[0, 1], showlegend=False,
                                     coloraxis_showscale=False)
            st.plotly_chart(fig_intent, use_container_width=True)

            st.dataframe(
                intent_df.set_index("Intent"),
                use_container_width=True,
            )

        st.markdown('<div style="margin:28px 0 12px;"></div>', unsafe_allow_html=True)

        # ── Per-run metric explanations ──────────────────────────────────────
        fiq_eyebrow("Per-Run Metric Explanations")

        run_labels = [
            f"{rd.get('run_name', rd.get('run_id','?')[:8])}  ·  "
            f"{rd.get('intent','?')}  ·  "
            f"quality: {rd.get('composites',{}).get('quality_score','—')}"
            for rd in reasons_list
        ]
        if run_labels:
            sel_idx = st.selectbox("Select a run to inspect", range(len(run_labels)),
                                   format_func=lambda i: run_labels[i])
            sel_run = reasons_list[sel_idx]

            st.markdown(
                f'<div style="background:#fff;border:1px solid #E1E1E1;border-radius:10px;'
                f'padding:14px 18px;margin-bottom:16px;font-size:13px;color:#1A1A1A;">'
                f'<strong>Query:</strong> {sel_run.get("query","—")}</div>',
                unsafe_allow_html=True,
            )

            METRIC_COLS = {
                "faithfulness": FIQ["quality"], "answer_relevancy": FIQ["rag"],
                "contextual_relevancy": FIQ["safety"], "completeness": FIQ["helpdesk"],
                "actionability": FIQ["quality"], "professional_tone": FIQ["rag"],
                "task_resolution": FIQ["helpdesk"], "toxicity": FIQ["sla"],
            }
            metric_data = sel_run.get("metrics", {})
            for metric_name, colour in METRIC_COLS.items():
                info = metric_data.get(metric_name, {})
                score = info.get("score")
                reason = info.get("reason", "No explanation available.")
                verdicts = info.get("verdicts", [])
                statements = info.get("statements", [])
                score_str = f"{score:.3f}" if score is not None else "N/A"

                with st.expander(f"**{metric_name}** — {score_str}", expanded=False):
                    if score is not None:
                        st.progress(float(score), text=f"Score: {score_str}")
                    st.markdown(
                        f'<div style="background:#F7F7F7;border-left:3px solid {colour};'
                        f'border-radius:6px;padding:10px 14px;margin:8px 0;'
                        f'font-size:13px;color:#374151;line-height:1.6;">'
                        f'<strong>Explanation:</strong> {reason}</div>',
                        unsafe_allow_html=True,
                    )
                    if verdicts:
                        st.markdown("**Verdicts (claim-level):**")
                        for v in verdicts[:5]:
                            icon = "✓" if str(v.get("verdict","")).lower() in ("yes","true","1") else "✗"
                            v_reason = v.get("reason", "")
                            st.markdown(
                                f'<div style="font-size:12px;padding:4px 8px;margin:3px 0;'
                                f'border-left:2px solid {"#059669" if icon=="✓" else "#DC2626"};">'
                                f'{icon} {v_reason}</div>',
                                unsafe_allow_html=True,
                            )
                    if statements:
                        st.markdown("**Statements evaluated:**")
                        for s in statements[:5]:
                            st.markdown(f'<div style="font-size:12px;color:#767676;padding:2px 0;">• {s}</div>',
                                        unsafe_allow_html=True)

    render_footer()


# ══════════════════════════════════════════════════════════════════════════════
# METRIC GUIDE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Metric Guide":
    page_header(
        "Evaluation Framework · Metric Reference",
        "Metric Guide",
        "All scores are 0–1. Higher is better (except Toxicity, which should be near 0). "
        "Powered by DeepEval 4.0.2. AI judge: Azure OpenAI.",
    )

    def _metric_card(name, category, colour, sla, simple_what, simple_how, sla_label="≥"):
        return (
            f'<div style="background:#fff;border:1px solid #E1E1E1;border-left:4px solid {colour};'
            f'border-radius:12px;padding:20px 22px;margin-bottom:14px;">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<div style="font-size:15px;font-weight:700;color:#1A1A1A;">{name}</div>'
            f'<span style="background:#F5EBFE;color:#460073;font-size:10px;font-weight:600;'
            f'letter-spacing:.08em;text-transform:uppercase;padding:2px 8px;border-radius:3px;">{category}</span>'
            f'<span style="background:#F7F7F7;color:#4A4A4A;font-size:10px;font-weight:600;'
            f'padding:2px 8px;border-radius:3px;margin-left:auto;">SLA {sla_label} {sla}</span>'
            f'</div>'
            f'<div style="font-size:13px;color:#1A1A1A;font-weight:600;margin-bottom:4px;">What it measures</div>'
            f'<div style="font-size:13px;color:#4A4A4A;margin-bottom:10px;">{simple_what}</div>'
            f'<div style="font-size:12px;color:#767676;font-weight:600;margin-bottom:2px;">How it\'s calculated</div>'
            f'<div style="font-size:12px;color:#767676;">{simple_how}</div>'
            f'</div>'
        )

    # ── SLA PASS / FAIL table ──────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;'
        'color:#460073;margin:8px 0 12px;">How PASS / FAIL is Determined</div>',
        unsafe_allow_html=True,
    )

    sla_rows = [
        ("quality_score",        "≥ 0.65", "PASS", "Overall headline KPI. If avg quality across runs is ≥ 0.65 the agent is considered production-ready."),
        ("faithfulness",         "≥ 0.70", "PASS", "Hallucination guard. Fails if the agent is making up facts not in the knowledge base."),
        ("answer_relevancy",     "≥ 0.70", "PASS", "Relevance guard. Fails if responses are factually correct but don't address the user's actual question."),
        ("contextual_relevancy", "≥ 0.70", "PASS", "Retrieval quality. Fails if RAG is fetching wrong documents for the query."),
        ("rag_score",            "≥ 0.70", "PASS", "Composite of all 3 RAG metrics. One number for the full retrieval pipeline health."),
        ("completeness",         "≥ 0.60", "PASS", "Helpdesk domain. Fails if the agent is leaving out key resolution steps."),
        ("actionability",        "≥ 0.60", "PASS", "Helpdesk domain. Fails if steps are too vague for a user to act on."),
        ("professional_tone",    "≥ 0.60", "PASS", "Helpdesk domain. Fails if tone is inappropriate for enterprise IT support."),
        ("task_resolution",      "≥ 0.60", "PASS", "Helpdesk domain. Fails if the user still can't resolve their issue from the response."),
        ("helpdesk_score",       "≥ 0.60", "PASS", "Composite of all 4 helpdesk GEval metrics. Overall service quality score."),
        ("safety_score",         "≥ 0.90", "PASS", "= 1 − toxicity. Hard threshold — any toxic content is a serious breach."),
        ("toxicity",             "≤ 0.10", "FAIL if > 0.10", "Lower is better. > 0.10 means harmful content in responses — hard FAIL."),
    ]

    sla_rows_html = "".join(
        f'<tr style="background:{"#FAFAFA" if i % 2 == 0 else "#fff"};">'
        f'<td class="td-code">{metric}</td>'
        f'<td class="td-thr">{threshold}</td>'
        f'<td class="td-pass">✓ {result}</td>'
        f'<td class="td-muted">{meaning}</td>'
        f'</tr>'
        for i, (metric, threshold, result, meaning) in enumerate(sla_rows)
    )
    st.markdown(
        '<table class="fiq-table"><thead><tr>'
        '<th>Metric</th><th>SLA Threshold</th><th>Result if Met</th><th>What a FAIL means</th>'
        f'</tr></thead><tbody>{sla_rows_html}</tbody></table>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="background:#fff;border:1px solid #E1E1E1;border-left:4px solid #A100FF;'
        'border-radius:12px;padding:16px 20px;margin-bottom:16px;">'
        '<div style="font-size:13px;font-weight:700;color:#1A1A1A;margin-bottom:8px;">'
        'Who sets the SLA thresholds?</div>'
        '<div style="font-size:13px;color:#4A4A4A;line-height:1.7;">'
        'SLA thresholds are defined in <code>config.yaml</code> under <code>sla_thresholds:</code> — '
        'you set them, not the tool. The defaults below are AgentPulse\'s recommended starting points, '
        'calibrated against published industry benchmarks for enterprise RAG and helpdesk AI systems. '
        'For a client demo, adjust these to match the client\'s own quality bar or existing SLAs.<br><br>'
        '<strong>Current thresholds:</strong> '
        'quality ≥ 0.65 · faithfulness ≥ 0.70 · answer_relevancy ≥ 0.70 · rag ≥ 0.70 · '
        'helpdesk ≥ 0.60 · safety ≥ 0.90 · toxicity ≤ 0.10'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Industry benchmark references ─────────────────────────────────────
    st.markdown(
        '<div style="background:#F7F7F7;border:1px solid #E1E1E1;border-radius:12px;'
        'padding:14px 18px;margin-bottom:28px;">'
        '<div style="font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;'
        'color:#767676;margin-bottom:10px;">Industry Standard References</div>'
        '<div style="display:flex;gap:24px;flex-wrap:wrap;">'

        '<div style="min-width:200px;">'
        '<div style="font-size:11px;font-weight:700;color:#1A1A1A;margin-bottom:3px;">RAGAS (RAG Metrics)</div>'
        '<div style="font-size:12px;color:#4A4A4A;margin-bottom:4px;">Faithfulness, Answer Relevancy, Contextual Relevancy benchmarks</div>'
        '<a href="https://docs.ragas.io/en/stable/concepts/metrics/index.html" target="_blank" '
        'style="font-size:12px;color:#A100FF;font-weight:600;text-decoration:none;">docs.ragas.io ↗</a>'
        '</div>'

        '<div style="min-width:200px;">'
        '<div style="font-size:11px;font-weight:700;color:#1A1A1A;margin-bottom:3px;">DeepEval Benchmarks</div>'
        '<div style="font-size:12px;color:#4A4A4A;margin-bottom:4px;">LLM evaluation metric standards and scoring guidance</div>'
        '<a href="https://docs.confident-ai.com/docs/metrics-introduction" target="_blank" '
        'style="font-size:12px;color:#A100FF;font-weight:600;text-decoration:none;">docs.confident-ai.com ↗</a>'
        '</div>'

        '<div style="min-width:200px;">'
        '<div style="font-size:11px;font-weight:700;color:#1A1A1A;margin-bottom:3px;">HELM (Stanford)</div>'
        '<div style="font-size:12px;color:#4A4A4A;margin-bottom:4px;">Holistic evaluation of LLMs — accuracy, safety, and robustness</div>'
        '<a href="https://crfm.stanford.edu/helm/latest/" target="_blank" '
        'style="font-size:12px;color:#A100FF;font-weight:600;text-decoration:none;">crfm.stanford.edu ↗</a>'
        '</div>'

        '<div style="min-width:200px;">'
        '<div style="font-size:11px;font-weight:700;color:#1A1A1A;margin-bottom:3px;">ToxiGen / HarmBench</div>'
        '<div style="font-size:12px;color:#4A4A4A;margin-bottom:4px;">Safety and toxicity evaluation standards for enterprise AI</div>'
        '<a href="https://github.com/microsoft/ToxiGen" target="_blank" '
        'style="font-size:12px;color:#A100FF;font-weight:600;text-decoration:none;">github.com/microsoft/ToxiGen ↗</a>'
        '</div>'

        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── How metrics are scored ─────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;'
        'color:#460073;margin:4px 0 12px;">How Metrics Are Scored</div>',
        unsafe_allow_html=True,
    )

    methods_left, methods_right = st.columns(2)
    with methods_left:
        st.markdown(
            '<div style="background:#fff;border:1px solid #E1E1E1;border-left:4px solid #00E5C7;'
            'border-radius:12px;padding:18px 20px;margin-bottom:14px;">'
            '<div style="font-size:14px;font-weight:700;color:#1A1A1A;margin-bottom:6px;">'
            'Formula-Based Scoring</div>'
            '<div style="font-size:11px;color:#767676;font-weight:700;text-transform:uppercase;'
            'letter-spacing:.08em;margin-bottom:10px;">Used for: RAG metrics</div>'
            '<div style="font-size:13px;color:#4A4A4A;line-height:1.7;">'
            'A mathematical algorithm checks the response against the retrieved context. '
            'No LLM judgment involved — the score is computed deterministically.<br><br>'
            '<strong>Example — Faithfulness:</strong> Every factual claim in the response is extracted, '
            'then each is checked against the knowledge base. '
            'Score = supported claims ÷ total claims. '
            '"Restart your router" with no runbook mention? That claim fails.<br><br>'
            '<strong>Metrics:</strong> Contextual Relevancy · Faithfulness · Answer Relevancy'
            '</div></div>',
            unsafe_allow_html=True,
        )
    with methods_right:
        st.markdown(
            '<div style="background:#fff;border:1px solid #E1E1E1;border-left:4px solid #A100FF;'
            'border-radius:12px;padding:18px 20px;margin-bottom:14px;">'
            '<div style="font-size:14px;font-weight:700;color:#1A1A1A;margin-bottom:6px;">'
            'GEval — LLM as the Judge</div>'
            '<div style="font-size:11px;color:#767676;font-weight:700;text-transform:uppercase;'
            'letter-spacing:.08em;margin-bottom:10px;">Used for: Helpdesk &amp; Safety metrics</div>'
            '<div style="font-size:13px;color:#4A4A4A;line-height:1.7;">'
            'Instead of a formula, a second LLM reads the response and scores it — like a human reviewer. '
            'You write the scoring criteria in plain English; the judge reasons and returns 0–1.<br><br>'
            '<strong>Why GEval?</strong> Some qualities are impossible to measure with a formula: '
            '<em>"Is this tone professional?"</em> or <em>"Could the user actually fix their issue?"</em><br><br>'
            '<strong>Our judge:</strong> Azure OpenAI gpt-5.2-chat-2 (Accenture enterprise subscription).<br>'
            '<strong>Metrics:</strong> Completeness · Actionability · Professional Tone · Task Resolution · Toxicity'
            '</div></div>',
            unsafe_allow_html=True,
        )

    # ── Individual metrics ─────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;'
        'color:#460073;margin:20px 0 12px;">Individual Metrics (8)</div>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown(_metric_card(
            "Contextual Relevancy", "RAG · Retrieval", FIQ["rag"], 0.70,
            "When the agent looks up information to answer a question, does it find the right documents? "
            "Even if it finds documents, they might be about a different topic.",
            "Each retrieved document chunk is checked: does it relate to the question? "
            "Score = number of relevant chunks ÷ total chunks checked.",
        ), unsafe_allow_html=True)
        st.markdown(_metric_card(
            "Faithfulness", "RAG · Generation", FIQ["rag"], 0.70,
            "Does the agent only say things that are actually in its knowledge base? "
            "Low score means the agent is making things up.",
            "Every fact in the response is checked against the knowledge base documents. "
            "Score = number of facts backed by real documents ÷ total facts checked.",
        ), unsafe_allow_html=True)
        st.markdown(_metric_card(
            "Answer Relevancy", "RAG · Generation", FIQ["rag"], 0.70,
            "Does the response actually answer what was asked? "
            "A response can be factually correct but still talk about the wrong thing.",
            "Questions are generated from the response and compared to the original query. "
            "Score = how many generated questions match what was originally asked.",
        ), unsafe_allow_html=True)
        st.markdown(_metric_card(
            "Completeness", "Helpdesk · GEval", FIQ["helpdesk"], 0.60,
            "Did the response include all the important steps to fix the issue? "
            "Missing key steps = low score.",
            "An AI judge reads the response and the knowledge base together and checks: "
            "are all the important steps included? Full marks if nothing is missing; lower if key steps are left out.",
        ), unsafe_allow_html=True)
    with col_right:
        st.markdown(_metric_card(
            "Actionability", "Helpdesk · GEval", FIQ["helpdesk"], 0.60,
            "Can the user actually follow the steps given? "
            "'Contact IT support' is vague. 'Click Settings > Network > Reset' is actionable.",
            "An AI judge checks if the steps are clear, numbered, and specific enough to follow. "
            "Specific step-by-step instructions score high; vague advice scores low.",
        ), unsafe_allow_html=True)
        st.markdown(_metric_card(
            "Professional Tone", "Helpdesk · GEval", FIQ["helpdesk"], 0.60,
            "Is the response polite, clear, and appropriate for a work setting? "
            "Not too casual, not rude, easy to read.",
            "An AI judge reads the response and checks: is the language polite and suitable for work? "
            "Rude, confusing, or overly casual language scores low.",
        ), unsafe_allow_html=True)
        st.markdown(_metric_card(
            "Task Resolution", "Helpdesk · GEval", FIQ["helpdesk"], 0.60,
            "After reading the response, could the user fix their problem without needing to ask again? "
            "This is the most important helpdesk metric.",
            "An AI judge acts like the user and asks: 'Can I fix my problem using only this answer?' "
            "Score 1 if yes; lower if the response is incomplete or needs more help.",
        ), unsafe_allow_html=True)
        st.markdown(_metric_card(
            "Toxicity", "Safety", FIQ["sla"], 0.10,
            "Does the response say anything harmful, offensive, or inappropriate? "
            "For enterprise use, this must always be near zero.",
            "Every statement in the response is checked for harmful content. "
            "Score = percentage of harmful statements. Safety score = 1 − toxicity.",
            sla_label="≤",
        ), unsafe_allow_html=True)

    # ── Composite KPIs ─────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;'
        'color:#460073;margin:20px 0 12px;">Composite KPIs (4)</div>',
        unsafe_allow_html=True,
    )
    composites_html = ""
    for name, formula, colour, description in [
        ("RAG Score",      "mean(faithfulness + answer_relevancy + contextual_relevancy) ÷ 3",
         FIQ["rag"],
         "How well the agent retrieves and uses its knowledge base. Low RAG score = retrieval or hallucination problem."),
        ("Helpdesk Score", "mean(completeness + actionability + professional_tone + task_resolution) ÷ 4",
         FIQ["helpdesk"],
         "How useful and complete the response is for an enterprise IT helpdesk user."),
        ("Safety Score",   "1 − toxicity",
         FIQ["safety"],
         "Inverse of toxicity. Should always be > 0.9 for enterprise use."),
        ("Quality Score",  "mean(rag_score + helpdesk_score + safety_score) ÷ 3  ← Headline KPI",
         FIQ["quality"],
         "The single headline metric — overall quality of one agent run. Used in the Quality Under Load chart."),
    ]:
        composites_html += (
            f'<div style="background:#fff;border:1px solid #E1E1E1;border-left:4px solid {colour};'
            f'border-radius:12px;padding:16px 20px;margin-bottom:10px;display:flex;gap:20px;align-items:flex-start;">'
            f'<div style="min-width:140px;flex-shrink:0;">'
            f'<div style="font-size:14px;font-weight:700;color:#1A1A1A;margin-bottom:4px;">{name}</div>'
            f'<code style="font-size:11px;">{formula}</code>'
            f'</div>'
            f'<div style="font-size:13px;color:#4A4A4A;padding-top:2px;line-height:1.5;">{description}</div>'
            f'</div>'
        )
    st.markdown(composites_html, unsafe_allow_html=True)

    # ── Speed & Cost metrics ───────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;'
        'color:#460073;margin:28px 0 8px;">Speed &amp; Cost Metrics (5)</div>'
        '<div style="font-size:13px;color:#767676;margin-bottom:16px;">'
        'Observability metrics captured automatically on every agent run — no scoring step needed.</div>',
        unsafe_allow_html=True,
    )

    def _obs_card(name, unit, colour, simple_what, simple_how):
        return (
            f'<div style="background:#fff;border:1px solid #E1E1E1;border-left:4px solid {colour};'
            f'border-radius:12px;padding:20px 22px;margin-bottom:14px;">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
            f'<div style="font-size:15px;font-weight:700;color:#1A1A1A;">{name}</div>'
            f'<span style="background:#F5EBFE;color:#460073;font-size:10px;font-weight:600;'
            f'letter-spacing:.08em;text-transform:uppercase;padding:2px 8px;border-radius:3px;">Speed &amp; Cost</span>'
            f'<span style="background:#F7F7F7;color:#4A4A4A;font-size:10px;font-weight:600;'
            f'padding:2px 8px;border-radius:3px;margin-left:auto;">Unit: {unit}</span>'
            f'</div>'
            f'<div style="font-size:13px;color:#1A1A1A;font-weight:600;margin-bottom:4px;">What it measures</div>'
            f'<div style="font-size:13px;color:#4A4A4A;margin-bottom:10px;">{simple_what}</div>'
            f'<div style="font-size:12px;color:#767676;font-weight:600;margin-bottom:2px;">How it\'s captured</div>'
            f'<div style="font-size:12px;color:#767676;">{simple_how}</div>'
            f'</div>'
        )

    sc_left, sc_right = st.columns(2)
    with sc_left:
        st.markdown(_obs_card(
            "TTFT — Time to First Token", "seconds", "#2E5BFF",
            "How long does the user wait before the agent starts responding? "
            "A fast TTFT makes the agent feel quick even if the full answer takes longer. "
            "This is the most important speed metric for AI systems.",
            "The agent starts streaming the response as soon as the LLM begins generating. "
            "TTFT = time from sending the request to receiving the first word back. "
            "Logged automatically on every call.",
        ), unsafe_allow_html=True)
        st.markdown(_obs_card(
            "Input Tokens", "count", "#4A4A4A",
            "How many words (tokens) did the agent send to the LLM? Includes the system instructions, "
            "the user's question, and the documents retrieved from the knowledge base. More tokens = higher cost.",
            "Azure OpenAI returns the exact input token count in its API response. "
            "Logged automatically on every call.",
        ), unsafe_allow_html=True)
        st.markdown(_obs_card(
            "Est. Cost (USD)", "USD", FIQ["sla"],
            "How much does each agent call cost on Azure OpenAI? "
            "Useful for client conversations — e.g. 10,000 queries/day at $0.0002 each = $2/day.",
            "Calculated from input and output token counts × the Azure OpenAI pricing rate. "
            "The rate constants can be updated in <code>response_generator.py</code> if the model changes.",
        ), unsafe_allow_html=True)
    with sc_right:
        st.markdown(_obs_card(
            "Tokens per Second", "tokens/s", "#00E5C7",
            "How fast is the LLM generating its response? Higher = faster, more responsive output. "
            "Azure OpenAI typically delivers 30–100 tok/s depending on model and server load.",
            "Calculated from output token count ÷ generation time. "
            "Logged automatically on every call.",
        ), unsafe_allow_html=True)
        st.markdown(_obs_card(
            "Output Tokens", "count", "#4A4A4A",
            "How many words (tokens) did the LLM write in its response? "
            "Longer responses = higher cost and slower streaming.",
            "Azure OpenAI returns the exact output token count in its API response. "
            "Logged automatically on every call.",
        ), unsafe_allow_html=True)

    st.markdown(
        '<div style="background:#F5EBFE;border-radius:12px;padding:16px 20px;margin-top:8px;">'
        '<div style="font-size:12px;font-weight:700;color:#460073;margin-bottom:6px;">'
        'Why cost tracking matters</div>'
        '<div style="font-size:12px;color:#4A4A4A;line-height:1.7;">'
        'When showing a client AgentPulse, the natural question is: <em>"What will this cost us in production?"</em> '
        'The Est. Cost figure lets you answer concretely — e.g. "Each helpdesk query costs ~$0.0002 on Azure OpenAI, '
        'so 10,000 queries/day = ~$2/day." It also lets you compare model quality vs. cost side by side.'
        '</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="background:#F5EBFE;border-radius:12px;padding:16px 20px;margin-top:14px;">'
        '<div style="font-size:12px;font-weight:700;color:#460073;margin-bottom:6px;">How scores are captured</div>'
        '<div style="font-size:12px;color:#4A4A4A;line-height:1.7;">'
        '<strong>Quality metrics (8 + 4 composites):</strong><br>'
        '1. Each agent run logs query, response, and retrieved context to MLflow as <code>eval_data.json</code>.<br>'
        '2. Run <code>.venv\\Scripts\\python.exe -m evals.eval_runner</code> to score with DeepEval.<br>'
        '3. Judge is Azure OpenAI gpt-5.2-chat-2 (Accenture subscription).<br>'
        '4. Scores are written back to the same MLflow run as metrics.<br><br>'
        '<strong>Speed &amp; Cost metrics (5):</strong><br>'
        '1. Captured automatically on every <code>/invoke</code> call — no separate scoring step.<br>'
        '2. TTFT and token counts come from Azure OpenAI streaming metadata (usage_metadata on last chunk).<br>'
        '3. Cost calculated in <code>response_generator.py</code> and logged to MLflow immediately.'
        '</div></div>',
        unsafe_allow_html=True,
    )

    render_footer()



# ── Auto-refresh ───────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(refresh_sec)
    st.cache_data.clear()
    st.rerun()
