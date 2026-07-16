"""
dashboard/app.py

Premium AI SaaS Redesign of the Rover Dashboard.
Clean, modern, light-theme interface with custom side navigation,
metric cards, timeline checkpoints, and bug exploration.
"""

import glob
import json
import sys
import os
import time
import urllib.parse
from pathlib import Path
import pandas as pd
import streamlit as st

# Setup Root Directory
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import logging
from src.scanner import scan_repository, validate_repository_url
from src.storage import ScanStore
from src.github_client import create_issue_from_scan
from src.agent import run_agent_for_issue
from src.github_auth import (
    load_installation_id,
    get_app_info,
    get_installation_info,
    list_installation_repositories,
    check_repository_access
)

logger = logging.getLogger("rover.dashboard")
scan_store = ScanStore(base_dir=str(ROOT_DIR / 'scans'))

# Plotly imports check
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# Pages declaration
PAGES = [
    ("Dashboard", "layout-dashboard"),
    ("Repositories & Scanner", "folder-git-2"),
    ("Bug Explorer", "shield-alert"),
    ("Pull Requests", "git-pull-request"),
    ("History", "history"),
    ("Analytics", "bar-chart-3"),
    ("Settings", "settings")
]

# SVG Icon Helper
def get_icon_svg(name, size=18, color="currentColor"):
    icons = {
        "layout-dashboard": '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="10" rx="1"/><rect width="7" height="5" x="3" y="14" rx="1"/>',
        "folder-git-2": '<path d="M9 20H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2v2"/><circle cx="13" cy="12" r="2"/><path d="M18 19c-2.8 0-5-2.2-5-5v3"/><circle cx="18" cy="19" r="2"/><path d="M14 14h3"/>',
        "shield-alert": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
        "git-pull-request": '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 15V9a4 4 0 0 0-4-4H9"/><path d="M6 9v6"/>',
        "history": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>',
        "bar-chart-3": '<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
        "settings": '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.1a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
        "check-circle": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
        "alert-triangle": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/>',
        "info": '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="16" y2="12"/><line x1="12" x2="12" y1="8" y2="8"/>',
        "play": '<polygon points="5 3 19 12 5 21 5 3"/>',
        "refresh-cw": '<path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/>',
        "search": '<circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/>',
        "filter": '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
        "arrow-up-right": '<line x1="7" x2="17" y1="17" y2="7"/><polyline points="7 7 17 7 17 17"/>',
        "arrow-down-right": '<line x1="7" x2="17" y1="7" y2="17"/><polyline points="17 7 17 17 7 17"/>',
        "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
        "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
        "bell": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
        "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="M4.93 4.93l1.41 1.41"/><path d="M15.64 15.64l1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="M6.34 17.66l-1.41 1.41"/><path d="M19.07 4.93l-1.41 1.41"/>'
    }
    inner = icons.get(name, "")
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block; vertical-align:middle;">{inner}</svg>'

# Helper to construct query strings
def make_page_url(page_name):
    current = st.query_params.to_dict()
    current["page"] = page_name
    return "?" + urllib.parse.urlencode(current)

# Global stylesheet injection
def inject_dashboard_theme() -> None:
    st.set_page_config(page_title='Rover - Premium AI Explorer', page_icon='🐕', layout='wide')

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Reset and main layout wrapper */
        html, body, .stApp, p, span, div, label, input, button {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }

        :root {
            color-scheme: light;
        }

        /* Hide streamlit defaults completely */
        [data-testid="stHeader"], footer, #MainMenu {
            display: none !important;
            visibility: hidden !important;
        }
        [data-testid="stToolbar"], [data-testid="stDecoration"] {
            display: none !important;
        }

        /* Base container and body colors */
        .stApp {
            background: #FAFBFF !important;
            color: #0F172A !important;
        }
        
        .block-container {
            max-width: 1320px !important;
            padding: 2.5rem 3.5rem !important;
            background: #FAFBFF !important;
        }

        /* Float sidebar */
        [data-testid="stSidebar"] {
            background: #FAFBFF !important;
            border-right: 1px solid #E2E8F0 !important;
            padding-top: 1rem;
        }
        [data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* Sidebar content styling */
        .sidebar-logo {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 32px;
            padding: 0 12px;
        }
        .logo-box {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, #4F46E5 0%, #06B6D4 100%);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 700;
            font-size: 16px;
        }
        .brand-name {
            font-size: 18px;
            font-weight: 700;
            color: #0F172A;
            letter-spacing: -0.03em;
        }
        .sidebar-menu {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .menu-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 14px;
            border-radius: 8px;
            color: #475569;
            font-weight: 500;
            font-size: 13.5px;
            text-decoration: none;
            transition: all 0.2s ease;
        }
        .menu-item:hover {
            background: #F1F5F9;
            color: #0F172A;
        }
        .menu-item.active {
            background: #EEF2FF;
            color: #4F46E5;
            font-weight: 600;
        }
        .sidebar-footer {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px 12px;
            border-top: 1px solid #E2E8F0;
            margin-top: 40px;
        }
        .user-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: #E2E8F0;
            color: #475569;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 12px;
        }
        .user-info {
            display: flex;
            flex-direction: column;
        }
        .user-name {
            font-size: 13px;
            font-weight: 600;
            color: #0F172A;
        }
        .user-role {
            font-size: 11px;
            color: #64748B;
        }

        /* Top bar elements */
        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
            padding-bottom: 16px;
            border-bottom: 1px solid #E2E8F0;
        }
        .topbar-left {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .topbar-right {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-connected {
            background: #DCFCE7;
            color: #15803D;
            border: 1px solid #BBF7D033;
        }
        .status-disconnected {
            background: #FEE2E2;
            color: #B91C1C;
            border: 1px solid #FCA5A533;
        }
        .topbar-icon {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: 1px solid #E2E8F0;
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .topbar-icon:hover {
            background: #F1F5F9;
            border-color: #CBD5E1;
        }

        /* Hero details */
        .saas-hero {
            background: linear-gradient(135deg, rgba(238, 242, 255, 0.4) 0%, rgba(224, 242, 254, 0.4) 100%);
            border: 1px solid #E2E8F0;
            border-radius: 20px;
            padding: 32px;
            margin-bottom: 24px;
            position: relative;
            overflow: hidden;
        }
        .pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: white;
            border: 1px solid #E2E8F0;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            color: #4F46E5;
        }

        /* Premium SaaS card system */
        .saas-card {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px 0 rgba(0, 0, 0, 0.03);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        .saas-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
            border-color: #CBD5E1;
        }
        
        .metric-card-new {
            flex: 1;
            min-width: 220px;
        }
        .metric-value-animated {
            font-size: 28px;
            font-weight: 700;
            color: #0F172A;
            letter-spacing: -0.03em;
            line-height: 1.1;
        }
        .metric-icon-wrapper {
            width: 40px;
            height: 40px;
            background: #EEF2FF;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* Spacing system */
        .block-container .element-container {
            margin: 8px 0 !important;
        }

        /* Custom buttons styling */
        button[kind="primary"], div.stButton > button {
            background: linear-gradient(135deg, #4F46E5 0%, #06B6D4 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 20px !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2) !important;
            transition: all 0.2s ease !important;
        }
        button[kind="primary"]:hover, div.stButton > button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.3) !important;
        }
        
        /* Custom loader details */
        .pulse-skeleton {
            background: linear-gradient(90deg, #F1F5F9 25%, #E2E8F0 50%, #F1F5F9 75%);
            background-size: 200% 100%;
            animation: loading-pulse 1.5s infinite;
            border-radius: 8px;
        }
        @keyframes loading-pulse {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }

        /* Timeline styles */
        .scanner-timeline-wrapper {
            display: flex;
            flex-direction: column;
            gap: 16px;
            margin: 24px 0;
            position: relative;
            padding-left: 12px;
        }
        .scanner-timeline-wrapper::before {
            content: '';
            position: absolute;
            left: 20px;
            top: 10px;
            bottom: 10px;
            width: 2px;
            background: #E2E8F0;
            z-index: 1;
        }
        .timeline-item {
            display: flex;
            align-items: center;
            gap: 16px;
            position: relative;
            z-index: 2;
        }
        .timeline-item-icon {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px solid #E2E8F0;
        }
        .timeline-item-completed .timeline-item-icon {
            border-color: #16A34A;
        }
        .timeline-item-active .timeline-item-icon {
            border-color: #4F46E5;
            animation: spin 2s linear infinite;
        }
        .timeline-item-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
            background: white;
            border: 1px solid #E2E8F0;
            padding: 12px 16px;
            border-radius: 12px;
        }
        .timeline-item-title {
            font-size: 14px;
            font-weight: 600;
            color: #0F172A;
        }
        .timeline-item-badge {
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 6px;
        }
        .timeline-item-completed .timeline-item-badge {
            background: #DCFCE7;
            color: #15803D;
        }
        .timeline-item-active .timeline-item-badge {
            background: #EEF2FF;
            color: #4F46E5;
        }
        .timeline-item-pending .timeline-item-badge {
            background: #F1F5F9;
            color: #64748B;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# Reusable UI Components
def clean_html(html_str: str) -> str:
    return " ".join(line.strip() for line in html_str.splitlines())

def render_metric_card(title, value, trend_value, trend_direction, icon_name):
    trend_color = "#16A34A" if trend_direction == "up" else "#DC2626" if trend_direction == "down" else "#64748B"
    trend_bg = "#DCFCE7" if trend_direction == "up" else "#FEE2E2" if trend_direction == "down" else "#F1F5F9"
    trend_icon = "arrow-up-right" if trend_direction == "up" else "arrow-down-right" if trend_direction == "down" else "info"
    
    trend_html = ""
    if trend_value:
        trend_html = clean_html(f"""
        <div style="background: {trend_bg}; color: {trend_color}; padding: 2px 6px; border-radius: 6px; font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 2px;">
            {get_icon_svg(trend_icon, 12, trend_color)}
            {trend_value}
        </div>
        """)
        
    st.markdown(
        clean_html(f"""
        <div class="saas-card metric-card-new">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; width: 100%;">
                <div style="display: flex; flex-direction: column; gap: 4px;">
                    <span style="font-size: 11px; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em;">{title}</span>
                    <span class="metric-value-animated">{value}</span>
                </div>
                <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 8px;">
                    <div class="metric-icon-wrapper">{get_icon_svg(icon_name, 20, "#4F46E5")}</div>
                    {trend_html}
                </div>
            </div>
        </div>
        """),
        unsafe_allow_html=True
    )

def render_bug_card(idx, bug, scan_id, repository):
    title = bug.get('title', 'Potential Bug')
    description = bug.get('description', 'No description provided.')
    severity = str(bug.get('severity', 'low')).upper()
    confidence = float(bug.get('confidence', 0.8))
    category = bug.get('category') or bug.get('bug_type') or 'Logic'
    file = bug.get('file', 'unknown')
    line = bug.get('line_number', 1)
    
    sev_colors = {
        "CRITICAL": {"bg": "#FEE2E2", "text": "#991B1B", "border": "#EF4444"},
        "HIGH": {"bg": "#FFEDD5", "text": "#9A3412", "border": "#F97316"},
        "MEDIUM": {"bg": "#FEF9C3", "text": "#854D0E", "border": "#EAB308"},
        "LOW": {"bg": "#ECFDF5", "text": "#065F46", "border": "#10B981"}
    }
    sev_style = sev_colors.get(severity, {"bg": "#F1F5F9", "text": "#475569", "border": "#94A3B8"})
    
    card_html = clean_html(f"""
    <div style="border-left: 4px solid {sev_style['border']}; margin-bottom: 8px;" class="saas-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; gap: 16px;">
            <div style="display: flex; flex-direction: column; gap: 4px;">
                <span style="font-weight: 700; font-size: 15px; color: #0F172A; letter-spacing: -0.01em;">{title}</span>
                <span style="font-size: 12px; color: #64748B; font-family: monospace;">{file}:{line}</span>
            </div>
            <div style="display: flex; gap: 8px;">
                <span style="background: {sev_style['bg']}; color: {sev_style['text']}; border: 1px solid {sev_style['border']}33; padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; text-transform: uppercase;">{severity}</span>
                <span style="background: #F1F5F9; color: #475569; padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 600;">Confidence: {confidence:.2f}</span>
            </div>
        </div>
        <p style="font-size: 13.5px; color: #334155; line-height: 1.5; margin-bottom: 8px;">{description}</p>
        <div style="font-size: 12px; color: #64748B;">
            <span>🏷️ <b>Category:</b> {category}</span>
        </div>
    </div>
    """)
    st.markdown(card_html, unsafe_allow_html=True)

def render_empty_state(title, description, icon_name="info"):
    st.markdown(
        clean_html(f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 24px; text-align: center; background: white; border: 1px dashed #E2E8F0; border-radius: 16px; margin: 16px 0;">
            <div style="width: 48px; height: 48px; background: #F1F5F9; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-bottom: 16px; color: #64748B;">
                {get_icon_svg(icon_name, 24, "#64748B")}
            </div>
            <h3 style="font-size: 15px; font-weight: 600; color: #0F172A; margin: 0 0 6px 0;">{title}</h3>
            <p style="font-size: 13px; color: #64748B; margin: 0; max-width: 320px; line-height: 1.4;">{description}</p>
        </div>
        """),
        unsafe_allow_html=True
    )

def render_scanner_timeline(current_phase, status, progress_val):
    phases = [
        ("cloning", "Cloning Repository"),
        ("traversal", "Discovering Codebase Files"),
        ("static_analysis", "Static Analysis (AST Rules)"),
        ("llm_analysis", "AI Vulnerability Analysis"),
        ("ranking", "Ranking & Deduplicating Findings"),
        ("completed", "Saving Scan & Complete")
    ]
    
    phase_order = ["cloning", "traversal", "static_analysis", "llm_analysis", "ranking", "completed"]
    current_index = -1
    if current_phase in phase_order:
        current_index = phase_order.index(current_phase)
    elif status == "completed":
        current_index = len(phase_order) - 1
        
    timeline_html = '<div class="scanner-timeline-wrapper">'
    for idx, (p_id, p_name) in enumerate(phases):
        if idx < current_index:
            p_status = "completed"
        elif idx == current_index:
            p_status = "active" if status != "completed" else "completed"
        else:
            p_status = "pending"
            
        icon = get_icon_svg("check-circle", 16, "#16A34A") if p_status == "completed" else get_icon_svg("refresh-cw", 16, "#4F46E5") if p_status == "active" else get_icon_svg("clock", 16, "#94A3B8")
        status_class = f"timeline-item-{p_status}"
        
        timeline_html += clean_html(f"""
        <div class="timeline-item {status_class}">
            <div class="timeline-item-icon">{icon}</div>
            <div class="timeline-item-content">
                <span class="timeline-item-title">{p_name}</span>
                <span class="timeline-item-badge">{p_status.upper()}</span>
            </div>
        </div>
        """)
    timeline_html += '</div>'
    return clean_html(timeline_html)

def render_sidebar(active_page):
    st.sidebar.markdown(
        clean_html(f"""
        <div class="sidebar-logo">
            <div class="logo-box">R</div>
            <span class="brand-name">Rover</span>
        </div>
        """),
        unsafe_allow_html=True
    )
    
    menu_html = '<div class="sidebar-menu">'
    for page_name, icon_name in PAGES:
        is_active = active_page == page_name
        active_class = "active" if is_active else ""
        icon_color = "#4F46E5" if is_active else "#64748B"
        url = make_page_url(page_name)
        
        menu_html += f"""
        <a href="{url}" target="_self" class="menu-item {active_class}">
            {get_icon_svg(icon_name, 18, icon_color)}
            <span>{page_name}</span>
        </a>
        """
    menu_html += '</div>'
    
    st.sidebar.markdown(clean_html(menu_html), unsafe_allow_html=True)
    
    st.sidebar.markdown(
        clean_html(f"""
        <div class="sidebar-footer">
            <div class="user-avatar">RS</div>
            <div class="user-info">
                <span class="user-name">Developer</span>
                <span class="user-role">Rover Alpha</span>
            </div>
        </div>
        """),
        unsafe_allow_html=True
    )

def render_topbar(connection_status, target_account, repo_url=None):
    status_html = ""
    if connection_status == "Connected":
        status_html = clean_html(f"""
        <div class="status-badge status-connected">
            <span style="width: 8px; height: 8px; border-radius: 50%; background: #16A34A; display: inline-block;"></span>
            Connected: {target_account}
        </div>
        """)
    else:
        status_html = clean_html("""
        <div class="status-badge status-disconnected">
            <span style="width: 8px; height: 8px; border-radius: 50%; background: #DC2626; display: inline-block;"></span>
            Disconnected
        </div>
        """)
        
    repo_text = repo_url if repo_url else "No Active Repository"
    
    st.markdown(
        clean_html(f"""
        <div class="topbar">
            <div class="topbar-left">
                <span style="font-weight: 500; font-size: 13.5px; color: #64748B;">Active:</span>
                <code style="background: #F1F5F9; padding: 4px 8px; border-radius: 6px; font-weight: 600; color: #0F172A; font-size: 12px;">{repo_text}</code>
            </div>
            <div class="topbar-right">
                {status_html}
                <div style="display: flex; gap: 8px;">
                    <div class="topbar-icon" title="Notifications">{get_icon_svg("bell", 16, "#64748B")}</div>
                    <div class="topbar-icon" title="Profile">{get_icon_svg("user", 16, "#64748B")}</div>
                </div>
            </div>
        </div>
        """),
        unsafe_allow_html=True
    )

# Base logic variables
inject_dashboard_theme()
query_params = st.query_params
active_page = query_params.get("page", "Dashboard")

# Load configuration status
USE_GITHUB_APP = os.getenv("USE_GITHUB_APP", "false").lower() == "true"
installation_id = load_installation_id()
connection_status = "Disconnected"
target_account = "N/A"
app_info = None

if USE_GITHUB_APP and installation_id:
    try:
        inst_info = get_installation_info(installation_id)
        connection_status = "Connected"
        target_account = inst_info.get("account", {}).get("login", "Unknown")
        app_info = get_app_info()
    except Exception:
        connection_status = "Disconnected"

# Render Layout Frames
render_sidebar(active_page)

# Load History Data for calculations
log_files = sorted(glob.glob('logs/*.json'), reverse=True)
runs = []
for f in log_files:
    try:
        with open(f) as fp:
            runs.append(json.load(fp))
    except Exception:
        pass

# Determine active repo
active_repo_url = st.session_state.get('active_repo_url', '')
if not active_repo_url and runs:
    active_repo_url = runs[0].get('repo', '')

render_topbar(connection_status, target_account, active_repo_url)

# ─── ROUTING TO PAGES ───

if active_page == "Dashboard":
    st.markdown(
        clean_html("""
        <div class="saas-hero">
            <div class="pill">Rover Alpha v1.0.0</div>
            <h1 style="font-size: 26px; font-weight: 700; color: #0F172A; margin: 12px 0 8px 0; letter-spacing: -0.02em;">Welcome, Developer</h1>
            <p style="font-size: 14px; color: #475569; margin: 0; line-height: 1.5; max-width: 580px;">Rover continuously explores your repos to automate vulnerability diagnostics and issue fixes.</p>
        </div>
        """),
        unsafe_allow_html=True
    )
    
    # Calculate stats
    total_runs = len(runs)
    issues_processed = len(set(r.get('issue_number') for r in runs if r.get('issue_number'))) if runs else 0
    avg_dur = round(pd.DataFrame(runs)['duration_seconds'].mean(), 1) if (runs and 'duration_seconds' in pd.DataFrame(runs).columns) else "N/A"
    repos_covered = len(set(r.get('repo') for r in runs if r.get('repo'))) if runs else 0
    
    # Metrics Row
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        render_metric_card("Total Runs", total_runs, "+4.2%", "up", "layout-dashboard")
    with m_col2:
        render_metric_card("Issues Fixed", issues_processed, "Active", "neutral", "shield-alert")
    with m_col3:
        render_metric_card("Avg Duration", f"{avg_dur}s" if avg_dur != "N/A" else "N/A", "-2.8%", "up", "clock")
    with m_col4:
        render_metric_card("Repos Tracked", repos_covered, "Stable", "neutral", "folder-git-2")
        
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    
    # Columns for Activity & Recent scans
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        st.markdown("<h3 style='font-size:16px; font-weight:700; color:#0F172A; margin-bottom:12px;'>Recent Fix Runs</h3>", unsafe_allow_html=True)
        if runs:
            for r in runs[:5]:
                repo = r.get('repo', 'unknown')
                ts = r.get('timestamp', '')
                dur = r.get('duration_seconds', '')
                issue = r.get('issue_number', '')
                status = r.get('status', 'completed')
                st.markdown(
                    clean_html(f"""
                    <div style="background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; margin-bottom: 8px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:600; font-size:13.5px; color:#0F172A;">{repo}</span>
                            <span style="font-size:11px; padding: 2px 6px; border-radius:6px; background:#DCFCE7; color:#15803D; font-weight:700;">{status.upper()}</span>
                        </div>
                        <div style="font-size:12px; color:#64748B; margin-top:6px; display:flex; gap:16px;">
                            <span>Issue #{issue}</span>
                            <span>Duration: {dur}s</span>
                            <span>At: {ts}</span>
                        </div>
                    </div>
                    """),
                    unsafe_allow_html=True
                )
        else:
            render_empty_state("No recent runs", "File a GitHub issue with the rover label to launch the fixing agent.", "layout-dashboard")
            
    with col_right:
        st.markdown("<h3 style='font-size:16px; font-weight:700; color:#0F172A; margin-bottom:12px;'>Core Workflows</h3>", unsafe_allow_html=True)
        st.markdown(
            clean_html(f"""
            <div class="saas-card" style="padding: 20px; display:flex; flex-direction:column; gap:12px;">
                <div style="display:flex; gap:12px; align-items:center;">
                    <div style="width:28px; height:28px; background:#EEF2FF; border-radius:6px; display:flex; align-items:center; justify-content:center;">{get_icon_svg("folder-git-2", 14, "#4F46E5")}</div>
                    <span style="font-size:13px; font-weight:600; color:#334155;">Proactive AST Codebase Scanner</span>
                </div>
                <div style="display:flex; gap:12px; align-items:center;">
                    <div style="width:28px; height:28px; background:#EEF2FF; border-radius:6px; display:flex; align-items:center; justify-content:center;">{get_icon_svg("shield-alert", 14, "#4F46E5")}</div>
                    <span style="font-size:13px; font-weight:600; color:#334155;">AI Vulnerability Discovery & Filter</span>
                </div>
                <div style="display:flex; gap:12px; align-items:center;">
                    <div style="width:28px; height:28px; background:#EEF2FF; border-radius:6px; display:flex; align-items:center; justify-content:center;">{get_icon_svg("git-pull-request", 14, "#4F46E5")}</div>
                    <span style="font-size:13px; font-weight:600; color:#334155;">Auto Pytest Validation & PR Open</span>
                </div>
            </div>
            """),
            unsafe_allow_html=True
        )

elif active_page == "Repositories & Scanner":
    st.markdown("<h2 style='font-size:22px; font-weight:700; color:#0F172A; margin-bottom:4px;'>Repository Scanner</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:13.5px; color:#64748B; margin-bottom:24px;'>Launch scan routines to discover bugs and diagnostic alerts inside codebases.</p>", unsafe_allow_html=True)
    
    # Parameter inputs parsing
    url_param = st.query_params.get("repo_url", "")
    auto_scan = st.query_params.get("auto_scan", "").lower() == "true"
    
    # Active Scan Rendering
    active_scan_id = st.session_state.get('active_scan_id')
    if active_scan_id:
        start_time = st.session_state.get('scan_start_time', time.time())
        st.markdown(
            clean_html(f"""
            <div class="saas-card" style="margin-bottom: 24px;">
                <h3 style="font-size: 15px; font-weight: 700; color: #0F172A; margin-bottom: 12px; display:flex; align-items:center; gap:8px;">
                    {get_icon_svg("refresh-cw", 16, "#4F46E5")} Scan active: <code>{active_scan_id}</code>
                </h3>
            </div>
            """),
            unsafe_allow_html=True
        )
        
        progress_bar = st.progress(0)
        phase_text = st.empty()
        metrics_placeholder = st.empty()
        file_text = st.empty()
        timeline_placeholder = st.empty()
        
        while True:
            try:
                scan_data = scan_store.load_scan(active_scan_id)
            except Exception:
                time.sleep(0.5)
                continue
                
            status = scan_data.get("status", "scanning")
            phase = scan_data.get("phase", "cloning")
            progress_val = scan_data.get("progress", 0)
            current_file = scan_data.get("current_file", "")
            files_scanned = scan_data.get("files_scanned", 0)
            elapsed = round(time.time() - start_time, 1)
            
            progress_bar.progress(progress_val)
            phase_text.markdown(f"**Current Stage**: `{phase.upper()}` ({progress_val}%)")
            
            with metrics_placeholder.container():
                col1, col2 = st.columns(2)
                col1.metric("Files Indexed", files_scanned)
                col2.metric("Execution Time", f"{elapsed}s")
                
            timeline_placeholder.markdown(render_scanner_timeline(phase, status, progress_val), unsafe_allow_html=True)
            
            if current_file:
                file_text.text(f"Processing: {current_file}")
            else:
                file_text.empty()
                
            if status in ("completed", "failed"):
                st.session_state.pop('active_scan_id', None)
                st.session_state['latest_scan'] = scan_data
                if status == "completed":
                    st.success(f"Scan finished successfully! Found {len(scan_data.get('bugs', []))} findings.")
                    st.query_params["page"] = "Bug Explorer"
                else:
                    err_msg = scan_data.get("error", "Please verify repository contents or connection status.")
                    st.error(f"Scan run failed: {err_msg}")
                time.sleep(1.5)
                st.rerun()
                break
                
            time.sleep(0.5)
            
    else:
        # Scan Input Panel
        st.markdown("<div class='saas-card'>", unsafe_allow_html=True)
        
        # Auto-start scan trigger
        if auto_scan and url_param:
            st.query_params.clear()
            can_scan = True
            if not validate_repository_url(url_param):
                can_scan = False
                st.error('Please enter a valid GitHub repository URL.')
            elif USE_GITHUB_APP:
                repo_name = url_param.replace('https://github.com/', '').rstrip('/')
                installation_id = load_installation_id()
                if not installation_id or not check_repository_access(installation_id, repo_name):
                    can_scan = False
                    st.error("Access Denied: The GitHub App is not installed or has no access.")
            
            if can_scan:
                import threading
                import uuid
                scan_id = f"scan-{uuid.uuid4().hex[:8]}"
                initial_scan = {
                    "scan_id": scan_id,
                    "repository": url_param,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "status": "scanning",
                    "bugs": [],
                    "phase": "cloning",
                    "progress": 15,
                    "current_file": "Initializing scan..."
                }
                scan_store.save_scan(initial_scan)
                st.session_state['active_repo_url'] = url_param
                
                thread = threading.Thread(target=scan_repository, args=(url_param, None, scan_id))
                thread.start()
                
                st.session_state['active_scan_id'] = scan_id
                st.session_state['scan_start_time'] = time.time()
                st.rerun()

        # Normal Input Trigger form
        if not USE_GITHUB_APP:
            repo_url = st.text_input('Repository Target URL', value=url_param, placeholder='https://github.com/user/project', key='scan-url-pat')
        else:
            if connection_status == "Connected":
                default_index = 1 if url_param else 0
                input_method = st.radio("Select Repository Input Method:", ["Select from GitHub App List", "Paste Repository URL"], index=default_index, horizontal=True, key="input-method")
                
                if input_method == "Select from GitHub App List":
                    if "repos_list" not in st.session_state or st.session_state.get("repos_list_inst_id") != installation_id:
                        with st.spinner("Fetching accessible repositories..."):
                            try:
                                repos = list_installation_repositories(installation_id)
                                st.session_state["repos_list"] = [r["full_name"] for r in repos]
                                st.session_state["repos_list_inst_id"] = installation_id
                            except Exception:
                                st.session_state["repos_list"] = []
                                st.session_state["repos_list_inst_id"] = None
                                
                    repo_list = st.session_state.get("repos_list", [])
                    if repo_list:
                        selected_repo = st.selectbox("Choose Repository", repo_list, key="selected-repo")
                        repo_url = f"https://github.com/{selected_repo}"
                    else:
                        st.info("No repositories found for this installation ID.")
                        repo_url = ""
                else:
                    repo_url = st.text_input('Repository Target URL', value=url_param, placeholder='https://github.com/user/project', key='scan-url-app')
            else:
                st.info("GitHub App is not connected. Install the app under Settings or toggle fallback settings.")
                repo_url = ""
                
        # Trigger button
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        scan_button = st.button('Scan Repository', key='scan-trigger-btn')
        
        if scan_button:
            if not repo_url:
                st.error('Please specify a repository URL.')
            elif not validate_repository_url(repo_url):
                st.error('Invalid repository URL.')
            else:
                if USE_GITHUB_APP:
                    repo_name = repo_url.replace('https://github.com/', '').rstrip('/')
                    installation_id = load_installation_id()
                    if not installation_id or not check_repository_access(installation_id, repo_name):
                        st.error("Access Denied: The GitHub App does not have repository access.")
                        st.stop()
                        
                import threading
                import uuid
                scan_id = f"scan-{uuid.uuid4().hex[:8]}"
                initial_scan = {
                    "scan_id": scan_id,
                    "repository": repo_url,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "status": "scanning",
                    "bugs": [],
                    "phase": "cloning",
                    "progress": 15,
                    "current_file": "Initializing scan..."
                }
                scan_store.save_scan(initial_scan)
                st.session_state['active_repo_url'] = repo_url
                
                thread = threading.Thread(target=scan_repository, args=(repo_url, None, scan_id))
                thread.start()
                
                st.session_state['active_scan_id'] = scan_id
                st.session_state['scan_start_time'] = time.time()
                st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)

elif active_page == "Bug Explorer":
    st.markdown("<h2 style='font-size:22px; font-weight:700; color:#0F172A; margin-bottom:4px;'>Bug Explorer</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:13.5px; color:#64748B; margin-bottom:24px;'>Inspect scan reports, filter alerts, and trigger fix commits.</p>", unsafe_allow_html=True)
    
    latest_scan = st.session_state.get('latest_scan')
    if not latest_scan:
        render_empty_state("No scan findings loaded", "Perform a scan or select a previous scan from the History tab to explore details.", "shield-alert")
    else:
        repo = latest_scan.get('repository', 'Unknown')
        scan_id = latest_scan.get('scan_id', 'unknown')
        findings = latest_scan.get('bugs', [])
        
        st.markdown(
            clean_html(f"""
            <div style="background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; margin-bottom: 24px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-size:11px; text-transform:uppercase; color:#64748B; font-weight:700; letter-spacing:0.05em;">Loaded Scan Repository</span>
                    <h4 style="margin: 2px 0 0 0; font-size:16px; font-weight:700; color:#0F172A;">{repo}</h4>
                </div>
                <div>
                    <span style="font-size:11px; text-transform:uppercase; color:#64748B; font-weight:700; letter-spacing:0.05em; display:block; text-align:right;">Scan ID</span>
                    <code style="font-weight:600; color:#4F46E5;">{scan_id}</code>
                </div>
            </div>
            """),
            unsafe_allow_html=True
        )
        
        if not findings:
            render_empty_state("No bugs discovered", "Good news! No obvious vulnerabilities or security flaws were found in this snapshot.", "check-circle")
        else:
            # Filter options UI
            st.markdown("<div class='saas-card' style='padding: 16px; margin-bottom: 20px;'>", unsafe_allow_html=True)
            col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
            with col_f1:
                search_query = st.text_input("Search Findings", value="", placeholder="Search by title, description or file name...", key="search-findings-query")
            with col_f2:
                sev_filter = st.selectbox("Severity Limit", ["All", "Critical", "High", "Medium", "Low"], key="severity-filter-limit")
            with col_f3:
                sort_by = st.selectbox("Sort Order", ["Confidence: High to Low", "Severity: High to Low", "File Name"], key="sorting-order-findings")
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Apply filtering
            filtered = findings
            if search_query:
                filtered = [f for f in filtered if (search_query.lower() in f.get('title', '').lower() or search_query.lower() in f.get('description', '').lower() or search_query.lower() in f.get('file', '').lower())]
            
            if sev_filter != "All":
                filtered = [f for f in filtered if f.get('severity', '').upper() == sev_filter.upper()]
                
            # Apply sorting
            if sort_by == "Confidence: High to Low":
                filtered = sorted(filtered, key=lambda x: float(x.get('confidence', 0.8)), reverse=True)
            elif sort_by == "Severity: High to Low":
                sev_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
                filtered = sorted(filtered, key=lambda x: sev_rank.get(str(x.get('severity', 'low')).upper(), 0), reverse=True)
            elif sort_by == "File Name":
                filtered = sorted(filtered, key=lambda x: x.get('file', ''))
                
            # Render Bug Cards
            if not filtered:
                render_empty_state("No matching findings", "Try adjusting your search query or severity limit options.", "info")
            else:
                for idx, bug in enumerate(filtered):
                    render_bug_card(idx, bug, scan_id, repo)
                    with st.expander("Expand Details & Fix", expanded=False):
                        if bug.get('reasoning'):
                            st.markdown(f"**Diagnostic Reasoning**:\n{bug.get('reasoning')}")
                        if bug.get('code_snippet'):
                            st.markdown("**Code Preview**:")
                            st.code(bug.get('code_snippet'), language='python')
                        if bug.get('suggested_fix'):
                            st.markdown("**Suggested Patch**:")
                            st.code(bug.get('suggested_fix'), language='python')
                            
                        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                        if st.button("Fix Bug", key=f"fix-btn-{idx}-{scan_id}"):
                            with st.spinner("Initializing fix workflow pipeline..."):
                                try:
                                    issue_number = create_issue_from_scan(
                                        repo,
                                        f"bug-{idx}",
                                        bug.get('title', 'Rover bug report'),
                                        bug.get('description', ''),
                                        severity=bug.get('severity', 'medium'),
                                        confidence=float(bug.get('confidence', 0.8)),
                                        file=bug.get('file'),
                                        line=bug.get('line_number'),
                                        suggested_fix=bug.get('suggested_fix'),
                                    )
                                    target_repo_name = repo.replace('https://github.com/', '').rstrip('/')
                                    run_agent_for_issue(target_repo_name, int(issue_number))
                                    st.success(f"Successfully started fix workflow pipeline! GitHub Issue #{issue_number} has been created.")
                                except Exception as exc:
                                    st.error(f"Failed to start fix pipeline: {exc}")

elif active_page == "Pull Requests":
    st.markdown("<h2 style='font-size:22px; font-weight:700; color:#0F172A; margin-bottom:4px;'>Pull Requests</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:13.5px; color:#64748B; margin-bottom:24px;'>Track pull requests and validation checks opened by the agent.</p>", unsafe_allow_html=True)
    
    pr_runs = [r for r in runs if r.get('status') == 'completed']
    if not pr_runs:
        render_empty_state("No Pull Requests opened yet", "Once Rover successfully resolves issues and runs validations, Pull Requests will appear here.", "git-pull-request")
    else:
        for idx, r in enumerate(pr_runs):
            repo = r.get('repo', 'unknown')
            ts = r.get('timestamp', '')
            issue = r.get('issue_number', '')
            summary = r.get('summary', 'No summary provided.')
            
            st.markdown(
                clean_html(f"""
                <div class="saas-card" style="margin-bottom:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h4 style="margin:0; font-size:14px; font-weight:700; color:#0F172A;">{repo} (PR target: Issue #{issue})</h4>
                        <span style="background:#EEF2FF; color:#4F46E5; padding:2px 8px; border-radius:6px; font-size:11px; font-weight:700;">OPENED</span>
                    </div>
                    <p style="font-size:13px; color:#475569; margin:8px 0 12px 0; line-height:1.4;">{summary}</p>
                    <div style="font-size:11.5px; color:#64748B;">
                        <span>At: {ts}</span>
                    </div>
                </div>
                """),
                unsafe_allow_html=True
            )

elif active_page == "History":
    st.markdown("<h2 style='font-size:22px; font-weight:700; color:#0F172A; margin-bottom:4px;'>Scan History</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:13.5px; color:#64748B; margin-bottom:24px;'>Browse and load codebase vulnerability scans and historical logs.</p>", unsafe_allow_html=True)
    
    scan_files = sorted(glob.glob(str(ROOT_DIR / 'scans/*.json')), reverse=True)
    scan_files = [f for f in scan_files if not f.endswith('_findings.json')]
    
    scans = []
    for sf in scan_files:
        try:
            with open(sf) as f:
                scans.append(json.load(f))
        except Exception:
            pass
            
    if not scans:
        render_empty_state("No scan history found", "Scan a repository under 'Repositories & Scanner' to write history indexes.", "history")
    else:
        for s in scans:
            scan_id = s.get('scan_id')
            repo = s.get('repository', 'unknown')
            ts = s.get('timestamp', '')
            status = s.get('status', 'completed')
            
            bugs_count = s.get('bugs_count', 0)
            if not bugs_count and 'bugs' in s:
                bugs_count = len(s['bugs'])
            if not bugs_count:
                try:
                    findings_data = scan_store.load_scan_findings(scan_id)
                    bugs_count = len(findings_data)
                except Exception:
                    bugs_count = 0
                    
            st.markdown(
                clean_html(f"""
                <div class="saas-card" style="margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h4 style="margin:0; font-size:14.5px; font-weight:700; color:#0F172A;">{repo}</h4>
                        <div style="font-size:12px; color:#64748B; margin-top:4px; display:flex; gap:16px;">
                            <span>Scan ID: <code>{scan_id}</code></span>
                            <span>Bugs: <b>{bugs_count}</b></span>
                            <span>At: {ts}</span>
                        </div>
                    </div>
                </div>
                """),
                unsafe_allow_html=True
            )
            if st.button(f"Load findings: {scan_id}", key=f"load-hist-scan-{scan_id}"):
                full_scan = scan_store.load_scan(scan_id)
                st.session_state['latest_scan'] = full_scan
                st.query_params["page"] = "Bug Explorer"
                st.rerun()

elif active_page == "Analytics":
    st.markdown("<h2 style='font-size:22px; font-weight:700; color:#0F172A; margin-bottom:4px;'>Analytics Dashboard</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:13.5px; color:#64748B; margin-bottom:24px;'>Metrics and diagnostic runtimes visualization.</p>", unsafe_allow_html=True)
    
    if not runs:
        render_empty_state("No data available", "Run fixes to populate data charts.", "bar-chart-3")
    elif HAS_PLOTLY:
        df_chart = pd.DataFrame(runs)
        
        st.markdown("<div class='saas-card' style='margin-bottom:24px;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin:0 0 16px 0; font-size:14px; font-weight:700; color:#0F172A;'>Execution Duration Trend (Seconds)</h4>", unsafe_allow_html=True)
        if 'duration_seconds' in df_chart.columns:
            fig_line = px.line(
                df_chart, 
                y='duration_seconds', 
                title=None,
                markers=True,
                labels={'duration_seconds': 'Seconds', 'index': 'Runs Order'}
            )
            fig_line.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=20, t=10, b=20),
                height=260
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.text("No duration values logged.")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='saas-card'>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin:0 0 16px 0; font-size:14px; font-weight:700; color:#0F172A;'>Runs per Repository</h4>", unsafe_allow_html=True)
        if 'repo' in df_chart.columns:
            repo_counts = df_chart['repo'].value_counts().reset_index()
            repo_counts.columns = ['Repository', 'Count']
            fig_bar = px.bar(
                repo_counts,
                x='Repository',
                y='Count',
                title=None,
                color='Count',
                color_continuous_scale=px.colors.sequential.Indigo
            )
            fig_bar.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=20, t=10, b=20),
                height=260
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Install Plotly to see visual metric trend graphs.")

elif active_page == "Settings":
    st.markdown("<h2 style='font-size:22px; font-weight:700; color:#0F172A; margin-bottom:4px;'>Settings & Connections</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:13.5px; color:#64748B; margin-bottom:24px;'>Manage credentials settings, webhook connections, and configuration variables.</p>", unsafe_allow_html=True)
    
    st.markdown("<div class='saas-card' style='margin-bottom:16px;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='margin:0 0 12px 0; font-size:14.5px; font-weight:700; color:#0F172A;'>App Authentication Details</h4>", unsafe_allow_html=True)
    
    st.markdown(f"**Integration Mode**: `{'GitHub App' if USE_GITHUB_APP else 'Personal Access Token'}`")
    
    if USE_GITHUB_APP:
        st.markdown(f"**Active Installation ID**: `{installation_id}`")
        st.markdown(f"**Connected Target Account**: `{target_account}`")
        if app_info:
            st.markdown(f"**App Settings**: [Manage Installation Settings]({app_info.get('html_url')}/installations/new)")
            
        if st.button("Clear App Installation Status", key="clear-settings-inst"):
            import src.github_auth as auth_mod
            try:
                if auth_mod.INSTALLATION_FILE.exists():
                    auth_mod.INSTALLATION_FILE.unlink()
                st.success("Successfully cleared installation logs.")
                st.rerun()
            except Exception as e:
                st.error(f"Error resetting credentials: {e}")
    else:
        st.info("Using Fallback classic personal access tokens (PAT). Set `USE_GITHUB_APP=true` in environment configuration to migrate to GitHub App auth.")
    st.markdown("</div>", unsafe_allow_html=True)