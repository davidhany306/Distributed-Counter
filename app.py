"""
Attendance App (Streamlit)
==========================
Student view  — mark attendance for your group.
Admin view    — see who attended, export CSV, view all groups summary.
"""

import streamlit as st
import socket
import csv
import io
import os
from datetime import datetime

# ── Settings ──────────────────────────────────────────────────────────────────
HOST       = os.environ.get("ATTEND_HOST", "127.0.0.1")
PORT       = int(os.environ.get("ATTEND_PORT", "5000"))
ADMIN_USER = os.environ.get("ATTEND_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ATTEND_ADMIN_PASS", "1234")
CAPACITY   = int(os.environ.get("ATTEND_CAPACITY", "40"))

LECTURE_GROUPS  = ["L1", "L2"]
TUTORIAL_GROUPS = ["T1-1", "T1-2", "T2-1", "T2-2"]


# ── Helpers ───────────────────────────────────────────────────────────────────
def sanitize(text):
    """Remove characters that would break our colon-separated protocol."""
    return text.replace(":", "").replace("\n", "").replace("\r", "").strip()


def send(cmd):
    """
    Open a TCP connection, send one command, wait for one response.
    Always returns a plain string (never raises).
    """
    try:
        s = socket.socket()
        s.settimeout(5)
        s.connect((HOST, PORT))
        s.sendall((cmd + "\n").encode())

        # Read bytes until we see a newline (= end of response)
        data = b""
        while b"\n" not in data:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk

        s.close()
        return data.decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"ERROR:{e}"


def make_csv(names, ids, group, section, date):
    """Build a CSV file in memory and return it as bytes."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["#", "Student ID", "Name", "Group", "Section", "Date", "Status"])
    for i, (name, sid) in enumerate(zip(names, ids), 1):
        w.writerow([i, sid, name, group, section, date, "Present"])
    return buf.getvalue().encode()


def parse_list_response(res):
    """
    Turn a server LIST response into two lists: names and ids.
    Server format:  LIST:Ahmed|2023001,Sara|2023002,...
    """
    names, ids = [], []
    data = res[len("LIST:"):]       # strip the "LIST:" prefix
    if not data.strip():
        return names, ids           # empty — nobody attended yet

    for entry in data.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if "|" in entry:
            name, sid = entry.split("|", 1)
            names.append(name.strip())
            ids.append(sid.strip())
        else:
            names.append(entry)
            ids.append("")
    return names, ids


def parse_summary_response(res):
    """
    Turn a SUMMARY response into a dict {group: count}.
    Server format:  SUMMARY:L1=5,L2=3,T1-1=12,...
    """
    result = {}
    data = res[len("SUMMARY:"):]
    for item in data.split(","):
        if "=" in item:
            grp, cnt = item.split("=", 1)
            result[grp.strip()] = int(cnt.strip())
    return result


# ── Page config & CSS ─────────────────────────────────────────────────────────
st.set_page_config(page_title="Attendance System", layout="centered", page_icon="📋")

# Read active button states before building CSS
mode_val = st.session_state.get("mode")
page_val = st.session_state.get("page")

student_css = "background:rgba(8,145,178,0.2)!important;border-color:rgba(8,145,178,0.75)!important;color:#67e8f9!important;box-shadow:0 0 30px rgba(8,145,178,0.3)!important;" if mode_val == "Student" else ""
admin_css   = "background:rgba(129,140,248,0.2)!important;border-color:rgba(129,140,248,0.75)!important;color:#a5b4fc!important;box-shadow:0 0 30px rgba(129,140,248,0.3)!important;" if mode_val == "Admin" else ""
lec_css     = "background:rgba(45,212,191,0.2)!important;border-color:rgba(45,212,191,0.75)!important;color:#2dd4bf!important;box-shadow:0 0 30px rgba(45,212,191,0.25)!important;" if page_val == "Lectures" else ""
tut_css     = "background:rgba(129,140,248,0.2)!important;border-color:rgba(129,140,248,0.75)!important;color:#818cf8!important;box-shadow:0 0 30px rgba(129,140,248,0.25)!important;" if page_val == "Tutorials" else ""

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {{ font-family:'Manrope',sans-serif!important; -webkit-font-smoothing:antialiased; }}
.stApp {{
    background:
        radial-gradient(ellipse 80% 50% at 20% 0%,  rgba(6,148,162,0.18)  0%,transparent 60%),
        radial-gradient(ellipse 60% 40% at 85% 10%, rgba(99,102,241,0.14) 0%,transparent 55%),
        radial-gradient(ellipse 50% 60% at 10% 80%, rgba(20,184,166,0.10) 0%,transparent 55%),
        radial-gradient(ellipse 70% 50% at 90% 90%, rgba(139,92,246,0.10) 0%,transparent 55%),
        #080e1a;
    color:#d4dff0; min-height:100vh;
}}
#MainMenu,footer,header {{ visibility:hidden; }}
[data-testid="stSidebar"] {{ display:none; }}
.block-container {{ padding-top:2rem; padding-bottom:5rem; max-width:680px; }}

/* ── Top bar ── */
.top-bar {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:1.8rem; }}
.logo-text {{ font-size:1.15rem; font-weight:800; background:linear-gradient(90deg,#2dd4bf,#818cf8); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; letter-spacing:-0.03em; }}
.live-pill {{ display:flex; align-items:center; gap:0.4rem; background:rgba(52,211,153,0.1); border:1px solid rgba(52,211,153,0.25); border-radius:20px; padding:0.22rem 0.7rem; font-size:0.68rem; color:#34d399; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; }}
.live-dot  {{ width:6px; height:6px; background:#34d399; border-radius:50%; box-shadow:0 0 6px #34d399; animation:blink 1.8s ease-in-out infinite; }}
@keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.3}} }}

/* ── Hero card ── */
.hero {{ background:linear-gradient(135deg,#0d2137 0%,#0c1a30 45%,#110c2a 100%); border:1px solid rgba(45,212,191,0.15); border-radius:18px; padding:1.8rem 2.2rem; margin-bottom:1.6rem; position:relative; overflow:hidden; }}
.hero::before {{ content:''; position:absolute; top:-70px; right:-50px; width:220px; height:220px; background:radial-gradient(circle,rgba(45,212,191,0.13) 0%,transparent 65%); border-radius:50%; pointer-events:none; }}
.hero-top {{ display:flex; justify-content:space-between; align-items:flex-start; }}
.hero-eyebrow {{ font-size:0.68rem; font-weight:700; letter-spacing:0.15em; text-transform:uppercase; color:#2dd4bf; margin-bottom:0.5rem; }}
.hero-title {{ font-size:1.85rem; font-weight:800; color:#f0f6ff; margin:0 0 0.3rem; letter-spacing:-0.04em; line-height:1.2; position:relative; z-index:1; }}
.hero-sub {{ color:#4a6a85; font-size:0.83rem; font-weight:500; position:relative; z-index:1; line-height:1.5; }}
.hero-date {{ background:rgba(45,212,191,0.08); border:1px solid rgba(45,212,191,0.2); border-radius:8px; padding:0.35rem 0.75rem; font-size:0.72rem; color:#2dd4bf; font-weight:600; white-space:nowrap; position:relative; z-index:1; }}

/* ── Step badges ── */
.step-row {{ display:flex; align-items:center; gap:0.5rem; margin-bottom:1.4rem; }}
.step-badge {{ background:rgba(45,212,191,0.1); border:1px solid rgba(45,212,191,0.25); border-radius:6px; padding:0.18rem 0.55rem; font-size:0.65rem; font-weight:800; color:#2dd4bf; letter-spacing:0.1em; text-transform:uppercase; }}
.step-badge.done    {{ background:rgba(52,211,153,0.08); border-color:rgba(52,211,153,0.2); color:#34d399; }}
.step-badge.pending {{ background:rgba(30,53,80,0.5); border-color:#1a2d45; color:#2a4060; }}
.step-arrow {{ color:#1e3550; font-size:0.7rem; }}
.field-label {{ font-size:0.68rem; font-weight:700; color:#2a4060; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.55rem; }}

/* ── Card buttons (default) ── */
div[data-testid="stButton"] > button {{ background:rgba(10,20,38,0.7)!important; color:#90aac8!important; border:1px solid #1a2d45!important; border-radius:14px!important; font-family:'Manrope',sans-serif!important; font-size:0.92rem!important; font-weight:700!important; width:100%!important; padding:1.3rem 1rem!important; transition:all 0.2s ease!important; display:flex!important; align-items:center!important; justify-content:center!important; min-height:88px!important; white-space:pre-wrap!important; line-height:1.5!important; }}
div[data-testid="stButton"] > button:hover {{ background:rgba(45,212,191,0.06)!important; border-color:rgba(45,212,191,0.3)!important; color:#c0cfe8!important; transform:translateY(-2px)!important; box-shadow:0 6px 20px rgba(0,0,0,0.35)!important; }}

/* ── Active card button states ── */
div[data-testid="stButton"]:has(button[key="btn_student"]) > button {{ {student_css} }}
div[data-testid="stButton"]:has(button[key="btn_admin"])   > button {{ {admin_css}   }}
div[data-testid="stButton"]:has(button[key="btn_lec"])     > button {{ {lec_css}     }}
div[data-testid="stButton"]:has(button[key="btn_tut"])     > button {{ {tut_css}     }}

/* ── CTA (Mark Attendance) button ── */
.cta-btn > div[data-testid="stButton"] > button {{ background:linear-gradient(135deg,#0891b2,#6366f1)!important; color:#fff!important; border:none!important; font-size:0.9rem!important; font-weight:700!important; min-height:52px!important; box-shadow:0 4px 20px rgba(8,145,178,0.35)!important; }}
.cta-btn > div[data-testid="stButton"] > button:hover {{ opacity:0.92!important; color:#fff!important; box-shadow:0 6px 28px rgba(8,145,178,0.5)!important; transform:translateY(-2px)!important; }}

/* ── Download button ── */
div[data-testid="stDownloadButton"] > button {{ background:rgba(45,212,191,0.08)!important; color:#2dd4bf!important; border:1px solid rgba(45,212,191,0.3)!important; border-radius:9px!important; font-family:'Manrope',sans-serif!important; font-size:0.82rem!important; font-weight:600!important; padding:0.55rem 1.1rem!important; transition:all 0.2s!important; min-height:unset!important; }}
div[data-testid="stDownloadButton"] > button:hover {{ background:rgba(45,212,191,0.14)!important; border-color:#2dd4bf!important; box-shadow:0 0 16px rgba(45,212,191,0.2)!important; transform:translateY(-1px)!important; }}

/* ── Text inputs & selects ── */
div[data-testid="stTextInput"] > label, div[data-testid="stSelectbox"] > label {{ color:#2a4060!important; font-size:0.68rem!important; font-weight:700!important; letter-spacing:0.12em!important; text-transform:uppercase!important; }}
div[data-testid="stTextInput"] input {{ background:rgba(6,12,24,0.8)!important; border:1px solid #1a2d45!important; border-radius:9px!important; color:#d4dff0!important; font-family:'Manrope',sans-serif!important; font-size:0.9rem!important; font-weight:500!important; padding:0.65rem 1rem!important; }}
div[data-testid="stTextInput"] input:focus {{ border-color:#2dd4bf!important; box-shadow:0 0 0 3px rgba(45,212,191,0.1)!important; }}
div[data-testid="stTextInput"] input::placeholder {{ color:#1e3550!important; }}
div[data-testid="stSelectbox"] > div > div {{ background:rgba(10,20,38,0.7)!important; border:1px solid #1a2d45!important; border-radius:9px!important; color:#c0cfe8!important; font-size:0.88rem!important; }}
div[data-testid="stSelectbox"] > div > div:focus-within {{ border-color:#2dd4bf!important; box-shadow:0 0 0 2px rgba(45,212,191,0.12)!important; }}

/* ── Alert boxes ── */
div[data-testid="stAlert"] {{ border-radius:9px!important; border-left-width:3px!important; font-size:0.84rem!important; font-weight:500!important; background:rgba(10,20,38,0.6)!important; }}

/* ── Stat card ── */
.stat-card {{ background:linear-gradient(135deg,rgba(10,25,48,0.9),rgba(12,20,42,0.9)); border:1px solid rgba(45,212,191,0.18); border-radius:14px; padding:1.2rem 1.5rem; display:flex; align-items:center; gap:1.1rem; margin-top:1rem; position:relative; overflow:hidden; }}
.stat-card::before {{ content:''; position:absolute; top:-25px; right:-25px; width:90px; height:90px; background:radial-gradient(circle,rgba(45,212,191,0.18) 0%,transparent 65%); border-radius:50%; pointer-events:none; }}
.stat-icon {{ font-size:1.6rem; line-height:1; }}
.stat-number {{ font-size:2.2rem; font-weight:800; letter-spacing:-0.04em; line-height:1; background:linear-gradient(90deg,#2dd4bf,#818cf8); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }}
.stat-label {{ color:#2a4a60; font-size:0.7rem; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; margin-top:0.18rem; }}
.stat-sub   {{ color:#1a3045; font-size:0.72rem; margin-top:0.12rem; font-weight:500; }}

/* ── Capacity bar ── */
.cap-bar-wrap {{ margin-top:0.9rem; background:rgba(10,20,38,0.8); border:1px solid #162030; border-radius:12px; padding:0.9rem 1.2rem; }}
.cap-bar-label {{ display:flex; justify-content:space-between; align-items:center; font-size:0.7rem; font-weight:700; color:#2a4060; letter-spacing:0.08em; text-transform:uppercase; margin-bottom:0.5rem; }}
.cap-bar-track {{ height:6px; background:#0d1c30; border-radius:3px; overflow:hidden; }}
.cap-bar-fill  {{ height:100%; border-radius:3px; }}

/* ── Summary grid ── */
.summary-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:0.6rem; margin-top:1rem; }}
.summary-card {{ background:rgba(10,20,38,0.7); border:1px solid #1a2d45; border-radius:10px; padding:0.8rem; text-align:center; }}
.summary-grp  {{ font-size:0.72rem; font-weight:700; color:#4a6a85; text-transform:uppercase; letter-spacing:0.08em; }}
.summary-num  {{ font-size:1.5rem; font-weight:800; color:#2dd4bf; letter-spacing:-0.04em; }}
.summary-cap  {{ font-size:0.65rem; color:#1e3550; margin-top:0.1rem; }}

/* ── Attendee list ── */
.search-wrap div[data-testid="stTextInput"] > label {{ display:none!important; }}
.list-header {{ font-size:0.88rem; font-weight:700; color:#c0cfe8; letter-spacing:-0.02em; margin:1.5rem 0 0.7rem; display:flex; align-items:center; justify-content:space-between; }}
.attendee-item {{ background:rgba(10,20,38,0.55); border:1px solid #162030; border-left:3px solid #0891b2; border-radius:9px; padding:0.62rem 1rem; margin-bottom:0.38rem; display:flex; align-items:center; gap:0.7rem; font-size:0.86rem; color:#90aac8; font-weight:500; }}
.attendee-item:nth-child(3n+1) {{ border-left-color:#0891b2; }}
.attendee-item:nth-child(3n+2) {{ border-left-color:#818cf8; }}
.attendee-item:nth-child(3n)   {{ border-left-color:#2dd4bf; }}
.attendee-num {{ font-size:0.68rem; font-weight:700; color:#1e3550; min-width:16px; text-align:right; }}
.attendee-id  {{ font-size:0.68rem; font-weight:600; color:#4a6a85; background:rgba(10,20,38,0.8); border:1px solid #1a2d45; border-radius:4px; padding:0.1rem 0.4rem; }}

/* ── Misc ── */
.empty-state {{ color:#2a4060; font-size:0.83rem; text-align:center; padding:2.5rem; border:1px dashed #142030; border-radius:12px; margin-top:0.5rem; font-weight:500; }}
.empty-icon  {{ font-size:2rem; margin-bottom:0.6rem; opacity:0.4; }}
.divider     {{ border:none; border-top:1px solid #0d1c30; margin:1.3rem 0; }}
.field-label {{ font-size:0.68rem; font-weight:700; color:#2a4060; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.55rem; }}
.section-tag {{ display:inline-flex; align-items:center; gap:0.4rem; font-size:0.68rem; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; padding:0.2rem 0.6rem; border-radius:6px; margin-bottom:0.6rem; }}
.section-tag.lec {{ background:rgba(45,212,191,0.1); border:1px solid rgba(45,212,191,0.25); color:#2dd4bf; }}
.section-tag.tut {{ background:rgba(129,140,248,0.1); border:1px solid rgba(129,140,248,0.25); color:#818cf8; }}
.btn-underline {{ display:flex; gap:0.75rem; margin-top:-0.4rem; margin-bottom:1rem; }}
.btn-underline-bar {{ flex:1; height:3px; border-radius:2px; }}
.date-filter-label {{ font-size:0.68rem; font-weight:700; color:#2a4060; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.4rem; }}
</style>
""", unsafe_allow_html=True)


# ── Session state defaults ────────────────────────────────────────────────────
if "mode" not in st.session_state:
    st.session_state.mode = None
if "page" not in st.session_state:
    st.session_state.page = None


# ── Top bar ───────────────────────────────────────────────────────────────────
now = datetime.now()
st.markdown(f"""
<div class="top-bar">
    <div class="logo-text">Attendance Tracker</div>
    <div class="live-pill"><div class="live-dot"></div>Live</div>
</div>
<div class="hero">
    <div class="hero-top">
        <div>
            <div class="hero-eyebrow">📋 University Attendance</div>
            <div class="hero-title">Mark Your Attendance</div>
            <div class="hero-sub">Select your role, pick a section, then sign in below.</div>
        </div>
        <div class="hero-date">📅 {now.strftime("%a, %d %b %Y")}<br>
            <span style="color:#4a6a85">🕐 {now.strftime("%H:%M")}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Step progress indicator ───────────────────────────────────────────────────
s1 = "done"    if mode_val else "active"
s2 = "done"    if page_val else ("active" if mode_val else "pending")
s3 = "active"  if page_val else "pending"
st.markdown(f"""
<div class="step-row">
    <span class="step-badge {s1}">{'✓ ' if mode_val else ''}Step 1 · Role</span>
    <span class="step-arrow">›</span>
    <span class="step-badge {s2}">{'✓ ' if page_val else ''}Step 2 · Section</span>
    <span class="step-arrow">›</span>
    <span class="step-badge {s3}">Step 3 · Attend</span>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# STEP 1 — Choose role
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="field-label">Role</div>', unsafe_allow_html=True)
col_s, col_a = st.columns(2)
with col_s:
    if st.button("🎓  Student\n\nMark my attendance", use_container_width=True, key="btn_student"):
        st.session_state.mode = "Student"
        st.session_state.page = None   # reset section when role changes
        st.rerun()
with col_a:
    if st.button("🛡️  Admin\n\nView & export records", use_container_width=True, key="btn_admin"):
        st.session_state.mode = "Admin"
        st.session_state.page = None
        st.rerun()

st.markdown(f"""
<div class="btn-underline">
    <div class="btn-underline-bar" style="background:{'#67e8f9' if mode_val=='Student' else 'transparent'};"></div>
    <div class="btn-underline-bar" style="background:{'#a5b4fc' if mode_val=='Admin'   else 'transparent'};"></div>
</div>
""", unsafe_allow_html=True)

if not st.session_state.mode:
    st.stop()   # don't show anything else until role is chosen

st.markdown("<hr class='divider'>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# STEP 2 — Choose section
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="field-label">Section</div>', unsafe_allow_html=True)
col_l, col_t = st.columns(2)
with col_l:
    if st.button("📖  Lectures\n\nGroups L1 · L2", use_container_width=True, key="btn_lec"):
        st.session_state.page = "Lectures"
        st.rerun()
with col_t:
    if st.button("🧑‍💻  Tutorials\n\nGroups T1-1 · T1-2 · T2-1 · T2-2", use_container_width=True, key="btn_tut"):
        st.session_state.page = "Tutorials"
        st.rerun()

st.markdown(f"""
<div class="btn-underline">
    <div class="btn-underline-bar" style="background:{'#2dd4bf' if page_val=='Lectures'  else 'transparent'};"></div>
    <div class="btn-underline-bar" style="background:{'#818cf8' if page_val=='Tutorials' else 'transparent'};"></div>
</div>
""", unsafe_allow_html=True)

if not st.session_state.page:
    st.stop()   # don't continue until section is chosen

# From here on we have both mode and page confirmed
mode = st.session_state.mode
page = st.session_state.page

st.markdown("<hr class='divider'>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# STEP 3 — Group picker (always visible once section is chosen)
# ════════════════════════════════════════════════════════════════════════════
tag_cls = "lec" if page == "Lectures" else "tut"
st.markdown(f'<span class="section-tag {tag_cls}">{"📖" if page=="Lectures" else "🧑‍💻"} {page}</span>', unsafe_allow_html=True)

groups = LECTURE_GROUPS if page == "Lectures" else TUTORIAL_GROUPS
group  = st.selectbox("Group", groups)

st.markdown("<hr class='divider'>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# STUDENT MODE
# ════════════════════════════════════════════════════════════════════════════
if mode == "Student":
    col_id, col_name = st.columns([1, 2])
    with col_id:
        student_id = st.text_input("Student ID", placeholder="e.g. 20230001")
    with col_name:
        name_raw = st.text_input("Full Name", placeholder="e.g. Ahmed Samy")

    sid  = sanitize(student_id)
    name = sanitize(name_raw)
    st.write("")

    st.markdown('<div class="cta-btn">', unsafe_allow_html=True)
    clicked = st.button("✅  Mark My Attendance", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if clicked:
        if not sid:
            st.warning("⚠️  Please enter your Student ID.")
        elif not sid.isdigit():
            st.warning("⚠️  Student ID must contain numbers only.")
        elif not name:
            st.warning("⚠️  Please enter your full name.")
        else:
            res = send(f"MARK:{group}:{sid}:{name}")
            if "SUCCESS" in res:
                st.success("🎉  Attendance recorded successfully!")
            elif "DUPLICATE" in res:
                st.warning("⚠️  You already marked attendance today.")
            elif "FULL" in res:
                st.error(f"🔴  This group is full ({CAPACITY}/{CAPACITY}). Contact your TA.")
            else:
                st.error("❌  Could not reach the server. Is it running?")

    # Show live count for this group
    res = send(f"GET:{group}")
    if "SUCCESS" in res:
        count     = int(res.split(":")[1])
        pct       = min(count / CAPACITY * 100, 100)
        remaining = max(CAPACITY - count, 0)

        bar_color = "#ef4444" if pct >= 95 else ("#f59e0b" if pct >= 75 else "#2dd4bf")
        cap_msg   = "🔴 Full" if pct >= 100 else ("🔴 Almost full" if pct >= 95 else (f"🟡 Filling up" if pct >= 75 else f"🟢 {remaining} seats left"))

        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">👥</div>
            <div style="flex:1">
                <div class="stat-number">{count}</div>
                <div class="stat-label">Attendees Today</div>
                <div class="stat-sub">{group}</div>
            </div>
        </div>
        <div class="cap-bar-wrap">
            <div class="cap-bar-label">
                <span>Capacity</span>
                <span>{cap_msg} · {count}/{CAPACITY}</span>
            </div>
            <div class="cap-bar-track">
                <div class="cap-bar-fill" style="width:{pct:.1f}%;background:{bar_color};"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# ADMIN MODE
# ════════════════════════════════════════════════════════════════════════════
if mode == "Admin":
    col_u, col_p = st.columns(2)
    with col_u:
        username = st.text_input("Username", placeholder="admin")
    with col_p:
        password = st.text_input("Password", type="password", placeholder="••••••")

    if not (username == ADMIN_USER and password == ADMIN_PASS):
        if username or password:
            st.error("❌  Invalid credentials.")
        st.stop()

    # ── Logged in ────────────────────────────────────────────────────────────
    st.success("✅  Admin access granted.")
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # Date picker
    if "admin_date" not in st.session_state:
        st.session_state.admin_date = datetime.now().date()

    st.markdown('<div class="date-filter-label">📅 Filter by Date</div>', unsafe_allow_html=True)
    col_date, col_today = st.columns([3, 1])
    with col_date:
        selected_date = st.date_input("date", value=st.session_state.admin_date,
                                      key="admin_date_picker", label_visibility="collapsed")
    with col_today:
        if st.button("🔄 Today", use_container_width=True, key="reset_date_btn"):
            st.session_state.admin_date = datetime.now().date()
            st.rerun()

    st.session_state.admin_date = selected_date
    date_str = selected_date.strftime("%Y-%m-%d")

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── All-groups summary ───────────────────────────────────────────────────
    st.markdown('<div class="field-label">All Groups — ' + date_str + '</div>', unsafe_allow_html=True)
    summary_res = send(f"SUMMARY:{date_str}")
    if "SUMMARY:" in summary_res:
        summary = parse_summary_response(summary_res)
        cards_html = '<div class="summary-grid">'
        for grp in sorted(summary):
            cnt = summary[grp]
            pct = min(cnt / CAPACITY * 100, 100)
            color = "#ef4444" if pct >= 95 else ("#f59e0b" if pct >= 75 else "#2dd4bf")
            cards_html += (
                f'<div class="summary-card">'
                f'<div class="summary-grp">{grp}</div>'
                f'<div class="summary-num" style="color:{color}">{cnt}</div>'
                f'<div class="summary-cap">{cnt}/{CAPACITY}</div>'
                f'</div>'
            )
        cards_html += '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)

        # Export ALL groups as one CSV
        st.markdown("<div style='margin-top:0.8rem'>", unsafe_allow_html=True)
        all_names, all_ids, all_groups, all_sections = [], [], [], []
        for grp in sorted(summary):
            section = "Lectures" if grp.startswith("L") else "Tutorials"
            r = send(f"ADMIN:{grp}:{date_str}")
            if "LIST:" in r:
                ns, ids = parse_list_response(r)
                all_names += ns
                all_ids   += ids
                all_groups   += [grp] * len(ns)
                all_sections += [section] * len(ns)

        if all_names:
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["#", "Student ID", "Name", "Group", "Section", "Date", "Status"])
            for i, (name, sid, grp, sec) in enumerate(zip(all_names, all_ids, all_groups, all_sections), 1):
                w.writerow([i, sid, name, grp, sec, date_str, "Present"])
            st.download_button(
                label=f"⬇️  Export All Groups — {date_str}",
                data=buf.getvalue().encode(),
                file_name=f"attendance_all_{date_str}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── Single-group detail ──────────────────────────────────────────────────
    st.markdown('<div class="field-label">Group Detail</div>', unsafe_allow_html=True)
    res = send(f"ADMIN:{group}:{date_str}")

    if "LIST:" not in res:
        st.error("❌  Could not reach the server.")
        st.stop()

    names, ids = parse_list_response(res)
    pct        = min(len(names) / CAPACITY * 100, 100) if names else 0
    bar_color  = "#ef4444" if pct >= 95 else ("#f59e0b" if pct >= 75 else "#2dd4bf")

    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-icon">📊</div>
        <div style="flex:1">
            <div class="stat-number">{len(names)}</div>
            <div class="stat-label">Attendees · {group} · {date_str}</div>
            <div class="stat-sub">{page}</div>
        </div>
    </div>
    <div class="cap-bar-wrap">
        <div class="cap-bar-label"><span>Capacity</span><span>{len(names)}/{CAPACITY}</span></div>
        <div class="cap-bar-track">
            <div class="cap-bar-fill" style="width:{pct:.1f}%;background:{bar_color};"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Per-group CSV export
    if names:
        st.markdown("<div style='margin-top:0.8rem'>", unsafe_allow_html=True)
        st.download_button(
            label=f"⬇️  Export {group} — {date_str}",
            data=make_csv(names, ids, group, page, date_str),
            file_name=f"attendance_{group}_{date_str}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Search box
    st.markdown("<div class='search-wrap' style='margin-top:1rem'>", unsafe_allow_html=True)
    search = st.text_input("search", placeholder="🔍  Search by name or ID…", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

    # Filter list by search query
    if search:
        filtered = [i for i, (n, s) in enumerate(zip(names, ids))
                    if search.lower() in n.lower() or search.lower() in s.lower()]
    else:
        filtered = list(range(len(names)))

    count_label = f"{len(filtered)} of {len(names)}" if search else str(len(names))
    st.markdown(
        f"<div class='list-header'>Attendance List"
        f"<span style='color:#1e3550;font-size:0.75rem;font-weight:600'>{count_label} students</span></div>",
        unsafe_allow_html=True
    )

    if filtered:
        html = ""
        for idx in filtered:
            n      = names[idx]
            s      = ids[idx] if idx < len(ids) else ""
            id_tag = f'<span class="attendee-id">{s}</span>' if s else ""
            html  += f'<div class="attendee-item"><span class="attendee-num">{idx+1}</span>{id_tag}<span>{n}</span></div>'
        st.markdown(html, unsafe_allow_html=True)
    elif search:
        st.markdown(f"<div class='empty-state'><div class='empty-icon'>🔍</div>No results for <strong>{search}</strong></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='empty-state'><div class='empty-icon'>📭</div>No attendance recorded for {group} on {date_str}.</div>", unsafe_allow_html=True)