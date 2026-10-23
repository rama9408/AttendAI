"""
Global widgets shown at the top of EVERY page of AttendAI:
  1. A role-aware search bar (teacher / student / not logged in)
  2. An "Ask AI" chatbot (Gemini) for app help + general questions +
     questions about the logged-in user's own attendance data

Usage (one line per screen):
    from src.components.global_widgets import render_global_widgets
    render_global_widgets()
"""
import os
import streamlit as st
from google import genai
from google.genai import types

from src.database.db import (
    get_teacher_subjects,
    get_teacher_students_index,
    get_subject_roster_with_logs,
    get_student_subjects,
    get_student_attendance,
)
from src.pipelines.analytics import analyze_student_subject

# Tried in order. Override the first one by adding GEMINI_MODEL to secrets.
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

APP_GUIDE = """
ABOUT ATTENDAI (use this to answer "how do I..." questions):
- AttendAI is an AI-based attendance system using face recognition and voice recognition.
- Students log in with FaceID (camera or uploaded photo). New students register once with
  their name (voice enrollment is optional). Returning students just scan their face.
- Students can enroll in a subject using the subject's join code / QR shared by the teacher,
  and unenroll from the subject card. Students never mark attendance themselves.
- Students see their attended/total classes per subject, plus "My Attendance Analytics":
  classes to recover, classes they can safely miss, semester-end projection, and a risk tier.
  The attendance threshold used is 75%.
- Teachers log in with username + password (or register). Their dashboard has 4 tabs:
  Take Attendance (upload classroom photos -> Run Face Analysis, or Use Voice Attendance),
  Manage Subjects (create subjects, share join code), Attendance Records (session-wise
  records with CSV download), Student Analytics (risk-sorted at-risk student list).
- Face and voice data are stored as encrypted embeddings, not raw images.
""".strip()

# (audience, title, description, keywords, teacher_tab_to_open_or_None)
FEATURES = [
    ("teacher", "Take Attendance", "Upload classroom photos for face attendance, or use voice attendance.",
     "attendance photo face voice mark present absent scan take", "take_attendance"),
    ("teacher", "Manage Subjects", "Create subjects and share the join code / QR with students.",
     "subject create course share code qr join manage", "manage_subjects"),
    ("teacher", "Attendance Records", "Session-wise attendance records, with CSV download.",
     "records history csv download report session export", "attendance_records"),
    ("teacher", "Student Analytics", "Risk-sorted list of students who need attention.",
     "analytics risk critical at-risk shortage low defaulter", "student_analytics"),
    ("student", "Enroll in Subject", "Use the 'Enroll in Subject' button at the top of your dashboard with the code from your teacher.",
     "enroll join subject code qr", None),
    ("student", "My Attendance Analytics", "Scroll down on your dashboard: recovery calculator, bunk calculator, projection, risk tier.",
     "analytics recover bunk projection risk tier percentage 75", None),
    ("student", "Unenroll", "Use 'Unenroll from this course' on the subject card.",
     "unenroll leave remove drop subject", None),
    ("guest", "Student Portal", "Log in with FaceID. New students can register on the same screen.",
     "student login faceid face register camera", None),
    ("guest", "Teacher Portal", "Log in with username and password, or register a teacher profile.",
     "teacher login password register", None),
]


# ---------------------------------------------------------------- helpers

def _secret(name):
    try:
        val = st.secrets.get(name)
    except Exception:
        val = None
    return val or os.environ.get(name)


def _identity():
    """Role is detected from session data (not user_role, which isn't cleared on logout)."""
    if "teacher_data" in st.session_state:
        return "teacher", st.session_state.teacher_data
    if "student_data" in st.session_state:
        return "student", st.session_state.student_data
    return "guest", None


def _match(query, *fields):
    """True if every word of the query appears somewhere in the given fields."""
    hay = " ".join(str(f) for f in fields if f is not None).lower()
    return all(word in hay for word in query.lower().split())


# ------------------------------------------------- cached data (short TTL)

@st.cache_data(ttl=60, show_spinner=False)
def _student_stats(student_id):
    subjects = get_student_subjects(student_id)
    logs = get_student_attendance(student_id)

    by_subject = {}
    for log in logs:
        by_subject.setdefault(log["subject_id"], []).append(log)

    out = []
    for node in subjects:
        sub = node["subjects"]
        sub_logs = by_subject.get(sub["subject_id"], [])
        row = {
            "name": sub["name"], "code": sub["subject_code"], "section": sub["section"],
            "total": len(sub_logs),
            "attended": sum(1 for l in sub_logs if l.get("is_present")),
            "pct": None, "tier": None, "recovery": None, "bunk": None, "projection": None,
        }
        if sub_logs:
            r = analyze_student_subject(sub_logs)
            row.update(pct=r["percentage"], tier=r["tier"].label, recovery=r["recovery_needed"],
                       bunk=r["can_bunk"], projection=r["projection"])
        out.append(row)
    return out


@st.cache_data(ttl=60, show_spinner=False)
def _teacher_index(teacher_id):
    subjects = get_teacher_subjects(teacher_id)
    enrollments = get_teacher_students_index(teacher_id)

    students = {}
    for e in enrollments:
        stu = e.get("students") or {}
        sub = e.get("subjects") or {}
        sid = stu.get("student_id")
        if sid is None:
            continue
        entry = students.setdefault(sid, {"id": sid, "name": stu.get("name") or "Unknown", "subjects": []})
        entry["subjects"].append({"subject_id": sub.get("subject_id"), "name": sub.get("name"),
                                  "code": sub.get("subject_code")})
    return subjects, list(students.values())


@st.cache_data(ttl=60, show_spinner=False)
def _teacher_context(teacher_id, teacher_name):
    subjects, _ = _teacher_index(teacher_id)
    lines = [f"Logged-in user: teacher {teacher_name}", "Their subjects:"]
    if not subjects:
        lines.append("- (no subjects created yet)")
    for s in subjects:
        lines.append(f"- {s['name']} ({s['subject_code']}), section {s['section']}: "
                     f"{s['total_students']} students, {s['total_classes']} classes held")
        flagged = []
        for stu in get_subject_roster_with_logs(s["subject_id"]):
            r = analyze_student_subject(stu["logs"])
            if r["tier"].label in ("Critical", "At-Risk"):
                flagged.append(f"{stu['name']} ({r['percentage']}%, {r['tier'].label})")
        lines.append("  Students needing attention: " + (", ".join(flagged[:15]) or "none"))
    return "\n".join(lines)


def _student_context(student):
    lines = [f"Logged-in user: student {student['name']}", "Their enrolled subjects:"]
    stats = _student_stats(student["student_id"])
    if not stats:
        lines.append("- (not enrolled in any subject yet)")
    for s in stats:
        if s["pct"] is None:
            lines.append(f"- {s['name']} ({s['code']}): no attendance recorded yet")
        else:
            lines.append(
                f"- {s['name']} ({s['code']}): attended {s['attended']}/{s['total']} = {s['pct']}%, "
                f"risk tier {s['tier']}, classes to recover {s['recovery']}, can safely miss {s['bunk']}, "
                f"semester-end projection {s['projection']}%")
    return "\n".join(lines)


# ----------------------------------------------------------------- search

def _go_teacher(tab, subject_label=None):
    """on_click callback: jump to a teacher tab (and preselect the subject)."""
    st.session_state.current_teacher_tab = tab
    key = {"attendance_records": "attendance_records_subject_select",
           "student_analytics": "analytics_subject_select"}.get(tab)
    if key and subject_label:
        st.session_state[key] = subject_label
    st.session_state["gw_search"] = ""


def _render_results(query, role, user):
    with st.container(border=True):
        st.caption(f'Results for "{query}"')
        found = False

        # --- features / help topics (all roles) ---
        for audience, title, desc, kw, tab in FEATURES:
            if audience != role or not _match(query, title, desc, kw):
                continue
            found = True
            c1, c2 = st.columns([4, 1], vertical_alignment="center")
            c1.markdown(f"**{title}** — {desc}")
            if role == "teacher" and tab:
                c2.button("Open", key=f"gw_feat_{tab}", on_click=_go_teacher, args=(tab,), width="stretch")

        # --- teacher: subjects + students ---
        if role == "teacher":
            subjects, students = _teacher_index(user["teacher_id"])

            for s in subjects:
                if not _match(query, s["name"], s["subject_code"], s["section"]):
                    continue
                found = True
                label = f"{s['name']} - {s['subject_code']}"
                c1, c2, c3 = st.columns([3, 1, 1], vertical_alignment="center")
                c1.markdown(f"📘 **{s['name']}** ({s['subject_code']}) · Section {s['section']} · "
                            f"{s['total_students']} students · {s['total_classes']} classes")
                c2.button("Records", key=f"gw_rec_{s['subject_id']}", on_click=_go_teacher,
                          args=("attendance_records", label), width="stretch")
                c3.button("Analytics", key=f"gw_ana_{s['subject_id']}", on_click=_go_teacher,
                          args=("student_analytics", label), width="stretch")

            shown = 0
            for stu in students:
                if shown >= 8:
                    break
                if not _match(query, stu["name"], stu["id"]):
                    continue
                found = True
                shown += 1
                st.markdown(f"🧑‍🎓 **{stu['name']}** (ID {stu['id']}) · "
                            + ", ".join(f"{x['name']} ({x['code']})" for x in stu["subjects"]))
                btn_cols = st.columns(min(len(stu["subjects"]), 4) or 1)
                for col, sub in zip(btn_cols, stu["subjects"][:4]):
                    col.button(f"Analytics: {sub['code']}", key=f"gw_stu_{stu['id']}_{sub['subject_id']}",
                               type="tertiary", on_click=_go_teacher,
                               args=("student_analytics", f"{sub['name']} - {sub['code']}"), width="stretch")

        # --- student: own subjects ---
        if role == "student":
            for s in _student_stats(user["student_id"]):
                if not _match(query, s["name"], s["code"], s["section"]):
                    continue
                found = True
                if s["pct"] is None:
                    detail = "no attendance recorded yet"
                else:
                    detail = f"{s['attended']}/{s['total']} attended · {s['pct']}% · {s['tier']}"
                st.markdown(f"📘 **{s['name']}** ({s['code']}) · Section {s['section']} · {detail}")

        if not found:
            st.info("Nothing found. Try another word, or click **Ask AI** to ask the assistant.")


# ---------------------------------------------------------------- chatbot

def _build_system_prompt(role, user):
    if role == "teacher":
        data = _teacher_context(user["teacher_id"], user["name"])
    elif role == "student":
        data = _student_context(user)
    else:
        data = "Nobody is logged in. You have NO user data; answer only app-help or general questions."

    return f"""You are the AttendAI assistant, built into a classroom attendance web app.
You can help with: (1) how to use AttendAI, (2) the logged-in user's own attendance data shown below,
and (3) general questions (study help, concepts, writing, etc.).

Rules:
- Be friendly, clear and concise (a few short sentences or a short list unless asked for more).
- For anything about the user's attendance, use ONLY the data below. If it isn't there, say you don't have it. Never invent numbers.
- Never reveal or guess data about other students/teachers beyond what is below.
- You cannot perform actions in the app (mark attendance, enroll, etc.); explain where to click instead.
- Attendance threshold is 75%.

{APP_GUIDE}

CURRENT USER DATA:
{data}
"""


def _ask_gemini(history, role, user):
    api_key = _secret("GEMINI_API_KEY")
    if not api_key:
        return "The chatbot isn't configured yet: add `GEMINI_API_KEY` to the app's secrets."

    client = genai.Client(api_key=api_key)
    contents = [
        types.Content(role="user" if m["role"] == "user" else "model",
                      parts=[types.Part(text=m["content"])])
        for m in history[-12:]
    ]
    config = types.GenerateContentConfig(
        system_instruction=_build_system_prompt(role, user),
        temperature=0.4,
    )

    models = GEMINI_MODELS[:]
    custom = _secret("GEMINI_MODEL")
    if custom:
        models.insert(0, custom)

    last_error = None
    for model in models:
        try:
            resp = client.models.generate_content(model=model, contents=contents, config=config)
            return (resp.text or "").strip() or "I couldn't come up with an answer. Please try rephrasing."
        except Exception as e:  # rate limit, bad model name, network...
            last_error = e

    msg = str(last_error).lower()
    if "429" in msg or "quota" in msg or "rate" in msg:
        return "I'm getting too many requests right now (free-tier limit). Please try again in a minute."
    return "Sorry, I couldn't reach the AI service. Please try again shortly."


@st.dialog("AttendAI Assistant", width="large")
def chat_dialog():
    role, user = _identity()

    # Keep chats private to whoever is logged in
    owner = f"{role}:{(user or {}).get('student_id') or (user or {}).get('teacher_id') or 'guest'}"
    if st.session_state.get("gw_chat_owner") != owner:
        st.session_state.gw_chat_owner = owner
        st.session_state.gw_chat = []
    history = st.session_state.gw_chat

    examples = {
        "teacher": "e.g. “Which students are at risk?”, “How do I share a subject code?”",
        "student": "e.g. “How many classes can I skip in DBMS?”, “How do I enroll in a subject?”",
        "guest": "e.g. “How does AttendAI work?”, “Explain bubble sort”",
    }[role]
    st.caption(f"Ask about the app, your attendance, or anything else. {examples}")

    if history and st.button("Clear chat", type="tertiary", key="gw_clear_chat"):
        history.clear()

    box = st.container(height=360)

    with st.form("gw_chat_form", clear_on_submit=True):
        q = st.text_input("Your message", placeholder="Type your question…", label_visibility="collapsed")
        sent = st.form_submit_button("Send", type="primary")

    if sent and q.strip():
        history.append({"role": "user", "content": q.strip()})
        with box:
            st.chat_message("user").write(q.strip())
            with st.spinner("Thinking…"):
                answer = _ask_gemini(history, role, user)
        history.append({"role": "assistant", "content": answer})

    with box:
        if not history:
            st.chat_message("assistant").write("Hi! I'm the AttendAI assistant. How can I help?")
        for m in history:
            st.chat_message(m["role"]).write(m["content"])


# ------------------------------------------------------------ entry point

def render_global_widgets():
    role, user = _identity()

    # Keep the toolbar columns transparent (home page styles every column as a white card)
    st.markdown("""
        <style>
        .stApp .st-key-gw_bar div[data-testid="stColumn"] {
            background: transparent !important;
            padding: 0 !important;
            box-shadow: none !important;
            border-radius: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    placeholder = {
        "teacher": "Search subjects, students, or features…",
        "student": "Search your subjects or features…",
        "guest": "Search features or help…",
    }[role]

    with st.container(key="gw_bar"):
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        with c1:
            query = st.text_input("Search", placeholder=placeholder, key="gw_search",
                                  label_visibility="collapsed", icon=":material/search:")
        with c2:
            if st.button("Ask AI", key="gw_chat_btn", icon=":material/smart_toy:", width="stretch"):
                chat_dialog()

    if query and query.strip():
        _render_results(query.strip(), role, user)