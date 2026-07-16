"""
dashboard/app.py

Streamlit run-history dashboard for Rover.
Shows every agent run logged in logs/, with metrics and a manual trigger.
"""
import glob
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import urllib.parse

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.scanner import scan_repository, validate_repository_url
from src.storage import ScanStore
from src.github_client import create_issue_from_scan
from src.agent import run_agent_for_issue


def inject_dashboard_theme() -> None:
    st.set_page_config(page_title='Rover', page_icon=':bug:', layout='wide')

    st.markdown(
        """
        <style>
        :root { color-scheme: light; }
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top left, rgba(184, 168, 255, 0.16), transparent 28%),
                radial-gradient(circle at 85% 8%, rgba(168, 216, 255, 0.14), transparent 24%),
                linear-gradient(135deg, #fff8fc 0%, #f8faff 30%, #f4f7fe 70%, #fdfdff 100%);
            min-height: 100vh;
        }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stToolbar"], [data-testid="stDecoration"], footer { display: none !important; }
        .block-container {
            max-width: 1420px;
            padding: 1.2rem 1.2rem 3rem;
            position: relative;
            z-index: 2;
        }
        .shell {
            position: relative;
            padding: 1.2rem;
            border-radius: 32px;
            background: rgba(255, 255, 255, 0.46);
            border: 1px solid rgba(255, 255, 255, 0.72);
            box-shadow: 0 30px 80px rgba(119, 135, 176, 0.18);
            backdrop-filter: blur(35px) saturate(140%);
            -webkit-backdrop-filter: blur(35px) saturate(140%);
            overflow: hidden;
        }
        .shell::before {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(115deg, rgba(255,255,255,0.36), rgba(255,255,255,0.12));
            pointer-events: none;
            mix-blend-mode: screen;
        }
        .hero-card {
            position: relative;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1.2rem;
            padding: 1.4rem 1.5rem;
            border-radius: 28px;
            background: linear-gradient(135deg, rgba(255,255,255,0.72), rgba(255,255,255,0.42));
            border: 1px solid rgba(255,255,255,0.8);
            box-shadow: 0 20px 45px rgba(130, 145, 180, 0.18);
            margin-bottom: 1rem;
            overflow: hidden;
        }
        .hero-card::before {
            content: "";
            position: absolute;
            inset: -40% auto auto -10%;
            width: 280px;
            height: 280px;
            background: radial-gradient(circle, rgba(184, 168, 255, 0.28), transparent 70%);
            animation: drift 18s ease-in-out infinite alternate;
            filter: blur(10px);
        }
        .hero-card::after {
            content: "";
            position: absolute;
            inset: auto -10% -35% auto;
            width: 240px;
            height: 240px;
            background: radial-gradient(circle, rgba(168, 216, 255, 0.22), transparent 72%);
            animation: drift 22s ease-in-out infinite alternate-reverse;
            filter: blur(8px);
        }
        .hero-copy {
            position: relative;
            z-index: 1;
            max-width: 700px;
        }
        .hero-copy h1 {
            font-size: clamp(1.85rem, 2.4vw, 2.6rem);
            font-weight: 700;
            letter-spacing: -0.03em;
            margin: 0.3rem 0 0.4rem;
            color: #22304a;
        }
        .hero-copy p {
            margin: 0;
            color: #50607a;
            font-size: 1rem;
            line-height: 1.6;
        }
        .pill {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.44rem 0.8rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.7);
            border: 1px solid rgba(255,255,255,0.78);
            color: #5d6b84;
            font-size: 0.8rem;
            font-weight: 600;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
        }
        .pill::before {
            content: "";
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: linear-gradient(135deg, #9bd7ff, #b8a8ff);
            box-shadow: 0 0 10px rgba(184,168,255,0.8);
        }
        .panel-card {
            position: relative;
            padding: 1.2rem;
            border-radius: 24px;
            background: rgba(255,255,255,0.56);
            border: 1px solid rgba(255,255,255,0.72);
            box-shadow: 0 20px 42px rgba(123, 138, 176, 0.14);
            backdrop-filter: blur(30px) saturate(150%);
            -webkit-backdrop-filter: blur(30px) saturate(150%);
            margin-bottom: 1rem;
            overflow: hidden;
        }
        .panel-card::before {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(120deg, rgba(255,255,255,0.30), transparent 70%);
            pointer-events: none;
        }
        .section-title {
            margin: 0.4rem 0 0.65rem;
            font-size: 1rem;
            font-weight: 700;
            letter-spacing: 0.01em;
            color: #31415b;
        }
        .subtle-copy {
            margin: 0 0 0.9rem;
            color: #67748b;
            font-size: 0.94rem;
        }
        [data-testid="stMetric"] {
            background: rgba(255,255,255,0.6);
            border: 1px solid rgba(255,255,255,0.76);
            border-radius: 22px;
            padding: 1rem 1rem 0.95rem;
            box-shadow: 0 14px 34px rgba(125, 139, 177, 0.14);
            backdrop-filter: blur(28px) saturate(150%);
            -webkit-backdrop-filter: blur(28px) saturate(150%);
        }
        [data-testid="stMetric"] label {
            color: #6d7994;
            font-size: 0.86rem;
            font-weight: 600;
        }
        [data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #21324b;
            font-weight: 700;
            font-size: 1.55rem;
        }
        [data-testid="stDataFrame"] {
            border-radius: 24px;
            overflow: hidden;
            box-shadow: 0 18px 38px rgba(123, 138, 176, 0.14);
            border: 1px solid rgba(255,255,255,0.78);
            background: rgba(255,255,255,0.56);
        }
        div[data-testid="stExpander"] details {
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.75);
            background: rgba(255,255,255,0.55);
            box-shadow: 0 15px 30px rgba(122, 137, 176, 0.12);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
        }
        div.stButton > button {
            background: linear-gradient(135deg, #bfaeff 0%, #8edcff 55%, #9cead3 100%);
            border: none;
            color: #17324b;
            border-radius: 999px;
            padding: 0.72rem 1.2rem;
            font-weight: 700;
            box-shadow: 0 12px 24px rgba(147, 162, 206, 0.28);
            transition: transform 180ms ease, box-shadow 180ms ease;
        }
        div.stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 16px 28px rgba(147, 162, 206, 0.32);
        }
        div.stButton > button:focus:not(:active) {
            outline: none;
            box-shadow: 0 0 0 4px rgba(168, 216, 255, 0.28);
        }
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input {
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.7);
            background: rgba(255,255,255,0.6);
            color: #23344d;
            box-shadow: inset 0 1px 2px rgba(160,176,203,0.18);
            padding: 0.7rem 0.85rem;
        }
        .empty-state {
            padding: 1.2rem;
            border-radius: 24px;
            background: rgba(255,255,255,0.58);
            border: 1px dashed rgba(171, 188, 221, 0.7);
            color: #5c6b83;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
        }
        .status-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.45rem 0.7rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.72);
            color: #516277;
            font-size: 0.82rem;
            font-weight: 600;
            border: 1px solid rgba(255,255,255,0.8);
        }
        @keyframes drift {
            0% { transform: translate3d(0, 0, 0) scale(1); }
            100% { transform: translate3d(18px, -12px, 0) scale(1.08); }
        }
        /* Layout and spacing tuned to 8px grid */
        :root { --space-1: 8px; --space-2: 16px; --space-3: 24px; --radius: 28px; }
        .block-container { padding: 0.8rem 0.8rem 1.6rem; }
        .hero-card { padding: 0.9rem 1rem; border-radius: var(--radius); gap: 0.8rem; }
        .hero-title { font-size: 2.4rem; margin: 0.25rem 0 0.4rem; }
        .hero-sub { margin-bottom: 0.6rem; }
        .app-sidebar { position: fixed; left: 20px; top: 28px; bottom: 28px; width: 92px; border-radius: 28px; background: rgba(255,255,255,0.44); border: 1px solid rgba(255,255,255,0.64); box-shadow: 0 20px 40px rgba(90,100,120,0.08); padding: 14px; z-index: 5; backdrop-filter: blur(22px); }
        .app-sidebar .logo-circle { width: 44px; height: 44px; border-radius: 12px; display:inline-flex; align-items:center; justify-content:center; background: linear-gradient(135deg,#b8a8ff,#a8d8ff); color:#142033; font-weight:800; box-shadow: 0 6px 18px rgba(136,150,180,0.12); }
        .app-sidebar .logo-text { font-weight:700; margin-top:6px; color:#22304a; font-size:0.98rem; }
        .nav-icons { display:flex; flex-direction:column; gap:12px; margin-top:18px; }
        .nav-item { width:48px; height:48px; border-radius:12px; display:flex; align-items:center; justify-content:center; cursor:pointer; transition:transform 160ms ease, box-shadow 160ms ease; }
        .nav-item.active { background: linear-gradient(135deg,#d8d0ff,#d3f0ff); box-shadow: 0 8px 20px rgba(140,150,190,0.08); }
        .metrics-row { display:flex; gap:12px; margin: 12px 0 14px; }
        .metric-card { flex:1; display:flex; gap:12px; align-items:center; padding:12px; border-radius:20px; background: rgba(255,255,255,0.6); border:1px solid rgba(255,255,255,0.72); box-shadow: 0 18px 36px rgba(120,130,160,0.08); }
        .m-icon { font-size:1.4rem; width:52px; height:52px; border-radius:14px; display:flex; align-items:center; justify-content:center; background: linear-gradient(135deg,#fff,#eef6ff); box-shadow: inset 0 1px 0 rgba(255,255,255,0.6); }
        .m-value { font-weight:800; font-size:1.35rem; color:#142033; }
        .m-label { color:#55677f; font-weight:700; font-size:0.9rem; }
        .panel-row { display:block; gap:12px; }
        .run-card { display:flex; gap:12px; align-items:flex-start; padding:12px; margin:10px 0; border-radius:20px; background: rgba(255,255,255,0.6); border: 1px solid rgba(255,255,255,0.7); box-shadow: 0 18px 36px rgba(120,130,160,0.06); }
        .repo-avatar { width:56px; height:56px; border-radius:12px; display:flex; align-items:center; justify-content:center; font-weight:800; background: linear-gradient(135deg,#ffd7e5,#b8a8ff); color:#142033; }
        .run-top { display:flex; justify-content:space-between; align-items:center; gap:8px; }
        .repo-name { font-weight:700; color:#15304a; }
        .run-meta { display:flex; gap:12px; color:#596a82; font-size:0.9rem; margin-top:6px; }
        .fake-input { min-width:220px; min-height:44px; border-radius:20px; padding:10px 12px; background: rgba(255,255,255,0.6); border:1px solid rgba(255,255,255,0.72); color:#23344d; }
        .trigger-row { display:flex; gap:12px; align-items:center; margin-top:8px; }
        .cta-primary { background: linear-gradient(135deg,#cdb8ff,#9beaff); border:none; padding:10px 18px; border-radius:999px; font-weight:800; color:#052033; box-shadow: 0 12px 28px rgba(120,140,180,0.12); }
        details.run-summary summary { cursor:pointer; font-weight:700; }
        .summary-body { margin-top:8px; color:#4f6178; }
        /* Reduce excessive vertical spacing everywhere */
        .block-container .element-container { margin: 6px 0 !important; padding: 0 !important; }

        </style>
        """,
        unsafe_allow_html=True,
    )
        
        


inject_dashboard_theme()

# background iframe HTML (top-level) - small data URI iframe for animated background
_bg_html = """
<div style="position:fixed; inset:0; z-index:0; pointer-events:none; overflow:hidden; background:transparent;">
    <div style="position:absolute; inset:-10% -10% auto auto; width:46vw; height:46vw; border-radius:50%; background:radial-gradient(circle, rgba(184,168,255,0.14), transparent 70%); filter:blur(32px); animation:floatA 22s ease-in-out infinite alternate;"></div>
    <div style="position:absolute; inset:auto auto -12% -8%; width:40vw; height:40vw; border-radius:50%; background:radial-gradient(circle, rgba(168,216,255,0.16), transparent 68%); filter:blur(34px); animation:floatB 24s ease-in-out infinite alternate-reverse;"></div>
    <div style="position:absolute; inset:8% 18% auto auto; width:240px; height:240px; border-radius:50%; background:radial-gradient(circle, rgba(255,215,230,0.22), transparent 70%); filter:blur(30px); animation:floatC 18s ease-in-out infinite alternate;"></div>
    <canvas id="dust-canvas" style="position:absolute; inset:0; width:100%; height:100%; opacity:0.55;"></canvas>
</div>
<style>
    @keyframes floatA { 0% { transform: translate3d(0,0,0) scale(1); } 100% { transform: translate3d(24px,-22px,0) scale(1.05); } }
    @keyframes floatB { 0% { transform: translate3d(0,0,0) scale(1); } 100% { transform: translate3d(-18px,24px,0) scale(1.03); } }
    @keyframes floatC { 0% { transform: translate3d(0,0,0) scale(1); } 100% { transform: translate3d(14px,16px,0) scale(1.06); } }
</style>
<script>
    const canvas = document.getElementById('dust-canvas');
    const ctx = canvas.getContext('2d');
    let width = 0; let height = 0; let particles = [];
    function resize() {
        width = canvas.clientWidth; height = canvas.clientHeight;
        canvas.width = width * window.devicePixelRatio;
        canvas.height = height * window.devicePixelRatio;
        ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
        particles = Array.from({ length: Math.min(110, Math.max(70, Math.round(width / 16))) }, () => ({
            x: Math.random() * width,
            y: Math.random() * height,
            r: Math.random() * 1.3 + 0.4,
            dx: (Math.random() - 0.5) * 0.25,
            dy: (Math.random() - 0.5) * 0.2,
            a: Math.random() * 0.5 + 0.22,
        }));
    }
    function render() {
        ctx.clearRect(0, 0, width, height);
        particles.forEach((p, i) => {
            p.x += p.dx; p.y += p.dy;
            if (p.x < -10 || p.x > width + 10) p.x = width * Math.random();
            if (p.y < -10 || p.y > height + 10) p.y = height * Math.random();
            ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255,255,255,${p.a})`; ctx.fill();
            if (i % 7 === 0) {
                const q = particles[(i + 1) % particles.length];
                ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y);
                ctx.strokeStyle = `rgba(184,168,255,${0.08 + p.a * 0.06})`; ctx.stroke();
            }
        });
        requestAnimationFrame(render);
    }
    window.addEventListener('resize', resize); resize(); render();
</script>
"""

st.iframe("data:text/html;charset=utf-8," + urllib.parse.quote(_bg_html), height=1)

st.markdown('<div class="shell">', unsafe_allow_html=True)

# Custom sidebar (glass)
st.markdown(
        """
        <aside class="app-sidebar">
            <div class="side-inner">
                <div class="brand">
                    <div class="logo-circle">R</div>
                    <div class="logo-text">Rover</div>
                </div>
                <nav class="nav-icons">
                    <div class="nav-item active" title="Dashboard">🏠</div>
                    <div class="nav-item" title="Runs">🕘</div>
                    <div class="nav-item" title="Settings">⚙️</div>
                </nav>
                <div class="profile">
                    <div class="avatar">RS</div>
                    <div class="ver">v0.9</div>
                </div>
            </div>
        </aside>
        """,
        unsafe_allow_html=True,
)

# HERO
st.markdown(
        """
        <header class="hero-card">
            <div class="hero-copy">
                <div class="pill">Autonomous code explorer • live</div>
                <h1 class="hero-title">Rover</h1>
                <p class="hero-sub">A calm, intelligent assistant that continuously inspects repositories and proposes fix suggestions.</p>
                <div class="hero-stats">
                    <div class="stat">
                        <div class="stat-value" data-value="" id="stat-runs">—</div>
                        <div class="stat-label">Total runs</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" data-value="" id="stat-issues">—</div>
                        <div class="stat-label">Issues processed</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" data-value="" id="stat-duration">—</div>
                        <div class="stat-label">Avg duration (s)</div>
                    </div>
                </div>
            </div>
            <div class="hero-cta">
                <button class="cta-primary" id="open-trigger">Run Rover</button>
                <div class="hero-illus"></div>
            </div>
        </header>
        """,
        unsafe_allow_html=True,
)

# ── Load run history ─────────────────────────────────────────────────
log_files = sorted(glob.glob('logs/*.json'), reverse=True)
runs = []
for f in log_files:
    try:
        with open(f) as fp:
            runs.append(json.load(fp))
    except Exception:
        pass

# ── Metrics & Run History ─────────────────────────────────────────────
if runs:
        df = pd.DataFrame(runs)
        # Inject numbers into hero stats via inline script
        st.markdown(
                f"""
                <script>
                    const runsCount = {len(df)};
                    const issuesCount = {int(df['issue_number'].nunique()) if 'issue_number' in df.columns else 0};
                    const avgDur = {round(df['duration_seconds'].mean(), 1) if 'duration_seconds' in df.columns else '"N/A"'};
                    const elRuns = document.getElementById('stat-runs');
                    const elIssues = document.getElementById('stat-issues');
                    const elDur = document.getElementById('stat-duration');
                    if (elRuns) elRuns.innerText = runsCount;
                    if (elIssues) elIssues.innerText = issuesCount;
                    if (elDur) elDur.innerText = avgDur;
                </script>
                """,
                unsafe_allow_html=True,
        )

        # Render metric cards row (custom look)
        st.markdown("<div class='metrics-row'>", unsafe_allow_html=True)
        st.markdown(
                f"""
                <div class='metric-card'>
                    <div class='m-icon'>✨</div>
                    <div class='m-body'>
                        <div class='m-value'>{len(df)}</div>
                        <div class='m-label'>Total runs</div>
                    </div>
                    <div class='m-trend'>+{round(len(df)/max(1,len(df))*0,1)}%</div>
                </div>
                <div class='metric-card'>
                    <div class='m-icon'>🧭</div>
                    <div class='m-body'>
                        <div class='m-value'>{int(df['issue_number'].nunique()) if 'issue_number' in df.columns else 0}</div>
                        <div class='m-label'>Issues processed</div>
                    </div>
                    <div class='m-trend'>—</div>
                </div>
                <div class='metric-card'>
                    <div class='m-icon'>⏱️</div>
                    <div class='m-body'>
                        <div class='m-value'>{round(df['duration_seconds'].mean(),1) if 'duration_seconds' in df.columns else 'N/A'}</div>
                        <div class='m-label'>Avg duration (s)</div>
                    </div>
                    <div class='m-trend'>—</div>
                </div>
                <div class='metric-card'>
                    <div class='m-icon'>📦</div>
                    <div class='m-body'>
                        <div class='m-value'>{df['repo'].nunique()}</div>
                        <div class='m-label'>Repos covered</div>
                    </div>
                    <div class='m-trend'>—</div>
                </div>
                """,
                unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Run history as cards
        st.markdown("<section class='panel-row'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Run History</div>", unsafe_allow_html=True)
        st.markdown("<div class='subtle-copy'>A premium activity timeline — each run becomes a concise card you can expand.</div>", unsafe_allow_html=True)

        for r in runs:
                repo = r.get('repo', 'unknown')
                ts = r.get('timestamp', '')
                dur = r.get('duration_seconds', '')
                issue = r.get('issue_number', '')
                status = r.get('status', 'completed') if isinstance(r, dict) else 'completed'
                summary = r.get('summary', '') if isinstance(r, dict) else ''
                avatar = repo.split('/')[0][0:2].upper() if isinstance(repo, str) else 'RV'
                st.markdown(
                        f"""
                        <article class='run-card'>
                            <div class='run-left'>
                                <div class='repo-avatar'>{avatar}</div>
                            </div>
                            <div class='run-main'>
                                <div class='run-top'>
                                    <div class='repo-name'>{repo}</div>
                                    <div class='status-chip'>{status}</div>
                                </div>
                                <div class='run-meta'>
                                    <div class='meta-item'>Issue #{issue}</div>
                                    <div class='meta-item'>Duration: {dur}s</div>
                                    <div class='meta-item'>At: {ts}</div>
                                </div>
                                <details class='run-summary'>
                                    <summary>Summary</summary>
                                    <div class='summary-body'>{summary or 'No summary available.'}</div>
                                </details>
                            </div>
                        </article>
                        """,
                        unsafe_allow_html=True,
                )

        st.markdown('</section>', unsafe_allow_html=True)
        if runs and 'summary' in runs[0]:
                # keep the summary accessible as a panel
                st.markdown("<div class='panel-card'>", unsafe_allow_html=True)
                with st.expander('Latest agent summary'):
                        st.text(runs[0]['summary'])
                st.markdown('</div>', unsafe_allow_html=True)
else:
        st.markdown(
                """
                <div class='empty-state'>
                    <strong>No runs yet.</strong><br />
                    File a GitHub issue on rover-target with the rover label, or use the manual trigger below to begin a fresh pass.
                </div>
                """,
                unsafe_allow_html=True,
        )

# Repository scanner panel
scan_store = ScanStore(base_dir=str(ROOT_DIR / 'scans'))

st.markdown("<div class='panel-card trigger-card'>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>Repository Scanner</div>", unsafe_allow_html=True)
st.markdown("<div class='subtle-copy'>Paste a GitHub repository URL and Rover will clone it, scan it, rank the findings, and prepare the fix workflow.</div>", unsafe_allow_html=True)

repo_url = st.text_input('Repository URL', value='', placeholder='https://github.com/user/project', key='repo-url')
scan_button = st.button('Scan Repository', key='scan-repo')

if scan_button:
    if not validate_repository_url(repo_url):
        st.error('Please enter a valid GitHub repository URL such as https://github.com/user/project')
    else:
        progress = st.progress(0)
        status = st.empty()
        status.info('Cloning repository...')
        progress.progress(15)
        result = scan_repository(repo_url)
        progress.progress(70)
        status.info('Ranking findings...')
        result['bugs'] = sorted(result.get('bugs', []), key=lambda item: (-float(item.get('confidence', 0.0)), item.get('severity', ''))) if result.get('bugs') else []
        progress.progress(100)
        status.success(f'Found {len(result.get("bugs", []))} issues for {repo_url}')
        scan_store.save_scan(result)
        st.session_state['latest_scan'] = result
        st.markdown("<div class='section-title'>Findings</div>", unsafe_allow_html=True)
        st.markdown("<div class='subtle-copy'>Each finding can launch the existing Rover fixing pipeline automatically.</div>", unsafe_allow_html=True)
        if result.get('bugs'):
            for idx, bug in enumerate(result['bugs']):
                severity = str(bug.get('severity', 'low')).capitalize()
                st.markdown(
                    f"""
                    <div class='run-card'>
                        <div class='run-main'>
                            <div class='run-top'>
                                <div class='repo-name'>{bug.get('title', 'Bug')}</div>
                                <div class='status-chip'>{severity}</div>
                            </div>
                            <div class='run-meta'>
                                <div class='meta-item'>File: {bug.get('file', 'unknown')}</div>
                                <div class='meta-item'>Line: {bug.get('line_number', 'n/a')}</div>
                                <div class='meta-item'>Confidence: {bug.get('confidence', 0)}</div>
                            </div>
                            <div class='summary-body'>{bug.get('description', '')}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(f"Fix this bug #{idx + 1}", key=f"fix-{idx}"):
                    try:
                        issue_number = create_issue_from_scan(repo_url, f"bug-{idx}", bug.get('title', 'Rover bug report'), bug.get('description', ''))
                        repo_name = repo_url.replace('https://github.com/', '').rstrip('/')
                        run_agent_for_issue(repo_name, int(issue_number))
                        st.success(f'Issue #{issue_number} created and the fix pipeline has started.')
                    except Exception as exc:
                        st.warning(f'Issue creation could not be completed: {exc}')
        else:
            st.info('No obvious issues were detected in the repository snapshot.')

        st.markdown("<div class='section-title'>Execution Timeline</div>", unsafe_allow_html=True)
        timeline = [
            'Clone repository',
            'Static analysis',
            'Gemini scan',
            'Issue creation',
            'Fix',
            'Tests',
            'Pull request',
        ]
        for item in timeline:
            st.markdown(f"- {item}")

st.markdown('</div>', unsafe_allow_html=True)