import streamlit as st

from src.ui.base_layout import style_background_dashboard, style_base_layout

from src.components.header import header_dashboard
from src.components.footer import footer_dashboard
from src.components.subject_card import subject_card
from src.database.db import check_teacher_exists, create_teacher, teacher_login, get_teacher_subjects, get_attendance_for_teacher, get_subject_roster_with_logs
from src.pipelines.analytics import analyze_student_subject
from src.components.dialog_create_subject import create_subject_dialog
from src.components.dialog_share_subject import share_subject_dialog
from src.components.dialog_add_photo import add_photos_dialog

from src.pipelines.face_pipeline import predict_attendance
from src.components.dialog_attendance_results import attendance_result_dialog
import numpy as np
import io
import csv
from collections import defaultdict

from datetime import datetime

import pandas as pd

from src.database.config import supabase


from src.components.dialog_voice_attendance import voice_attendance_dialog

def teacher_screen():

    style_background_dashboard()
    style_base_layout(accent="#D97A55")   # muted terracotta on Teacher Login + Dashboard

    if "teacher_data" in st.session_state:
        teacher_dashboard()
    elif 'teacher_login_type' not in st.session_state or st.session_state.teacher_login_type=="login":
        teacher_screen_login()
    elif st.session_state.teacher_login_type == "register":
        teacher_screen_register()


def teacher_dashboard():
    teacher_data = st.session_state.teacher_data

    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        st.subheader(f"""Welcome, {teacher_data['name']} """)
        if st.button("Logout", type='secondary', key='loginbackbtn', shortcut="control+backspace"):
            st.session_state['is_logged_in'] = False
            del st.session_state.teacher_data
            st.rerun()

    st.space()

    if "current_teacher_tab" not in st.session_state:
        st.session_state.current_teacher_tab = 'take_attendance'

    tab1, tab2, tab3, tab4 = st.columns(4)

    with tab1:
        if st.button('Take Attendance', type='primary' if st.session_state.current_teacher_tab=='take_attendance' else 'tertiary', width='stretch', icon=':material/ar_on_you:'):
            st.session_state.current_teacher_tab = 'take_attendance'
            st.rerun()

    with tab2:
        if st.button('Manage Subjects', type='primary' if st.session_state.current_teacher_tab=='manage_subjects' else 'tertiary', width='stretch', icon=':material/book_ribbon:'):
            st.session_state.current_teacher_tab = 'manage_subjects'
            st.rerun()

    with tab3:
        if st.button('Attendance Records', type='primary' if st.session_state.current_teacher_tab=='attendance_records' else 'tertiary', width='stretch', icon=':material/cards_stack:'):
            st.session_state.current_teacher_tab = 'attendance_records'
            st.rerun()

    with tab4:
        if st.button('Student Analytics', type='primary' if st.session_state.current_teacher_tab=='student_analytics' else 'tertiary', width='stretch', icon=':material/warning:'):
            st.session_state.current_teacher_tab = 'student_analytics'
            st.rerun()

    st.divider()

    if st.session_state.current_teacher_tab == "take_attendance":
        teacher_tab_take_attendance()
    if st.session_state.current_teacher_tab == "manage_subjects":
        teacher_tab_manage_subjects()
    if st.session_state.current_teacher_tab == "attendance_records":
        teacher_tab_attendance_records()
    if st.session_state.current_teacher_tab == "student_analytics":
        teacher_tab_student_analytics()



    footer_dashboard()

def teacher_tab_take_attendance():
    teacher_id = st.session_state.teacher_data['teacher_id']
    st.header('Take AI Attendance')


    if 'attendance_images' not in st.session_state:
        st.session_state.attendance_images = []

    subjects = get_teacher_subjects(teacher_id)

    if not subjects:
        st.warning('You havent created any subjects yet! Please create one to begin!')
        return
    
    subject_options = {f"{s['name']} - {s['subject_code']}": s['subject_id'] for s in subjects}

    col1, col2 = st.columns([3,1], vertical_alignment='bottom')

    with col1:
        selected_subject_label = st.selectbox('Select Subject', options=list(subject_options.keys()))

    with col2:
        if st.button('Add Photos', type='primary', icon=':material/photo_prints:', width='stretch'):
            add_photos_dialog()

    selected_subject_id = subject_options[selected_subject_label]

    st.divider()

    if st.session_state.attendance_images:
        st.header('Added Photos')
        gallery_cols = st.columns(4)

        for idx, img in enumerate(st.session_state.attendance_images):
            with gallery_cols[idx % 4 ]:
                st.image(img, width='stretch', caption=f'Photo {idx+1}')
    has_photos = bool(st.session_state.attendance_images)
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button('Clear all photos', width='stretch', type='tertiary', icon=':material/delete:', disabled=not has_photos):
            st.session_state.attendance_images = []
            st.rerun()


    with c2:
        
        if st.button('Run Face Analysis', width='stretch', type='secondary', icon=':material/analytics:', disabled=not has_photos):
            with st.spinner('Deep scanning classroom photos...'):
                all_detected_ids = {}

                for idx, img in enumerate(st.session_state.attendance_images):
                    img_np = np.array(img.convert('RGB'))
                    detected, _, _ = predict_attendance(img_np)


                    if detected:
                        for sid in detected.keys():
                            student_id = int(sid)

                            all_detected_ids.setdefault(student_id, []).append(f"Photo {idx+1}")

                enrolled_res = supabase.table('subject_students').select("*, students(*)").eq('subject_id',selected_subject_id ).execute()
                enrolled_students = enrolled_res.data

                if not enrolled_students:
                    st.warning('No students enrolled in this course')
                else:

                    results, attendance_to_log  = [], []

                    current_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


                    for node in enrolled_students:
                        student = node['students']
                        sources = all_detected_ids.get(int(student['student_id']), [])
                        is_present= len(sources) > 0

                        results.append({
                            "Name": student['name'],
                            "ID": student['student_id'],
                            "Source": ", ".join(sources) if is_present else "-",
                            "Status": "✅ Present" if is_present else "❌ Absent"
                        })

                        attendance_to_log.append({
                            'student_id': student['student_id'],
                            'subject_id': selected_subject_id,
                            'timestamp': current_timestamp,
                            'is_present': bool(is_present)
                        })

                attendance_result_dialog(pd.DataFrame(results), attendance_to_log)

    with c3:
        if st.button('Use Voice Attendance', type='primary', width='stretch', icon=':material/mic:'):
            voice_attendance_dialog(selected_subject_id)


def teacher_tab_manage_subjects():
    teacher_id = st.session_state.teacher_data['teacher_id']
    col1, col2 = st.columns(2)
    with col1:
        st.header('Manage Subjects', width='stretch')

    with col2:
        if st.button('Create New Subject', width='stretch'):
            create_subject_dialog(teacher_id)


    # LIST all SUBJECTS
    subjects = get_teacher_subjects(teacher_id)
    if subjects:
        for sub in subjects:
            stats = [
                ("🫂", "Students", sub['total_students']),
                ("🕰️", "Classes", sub['total_classes']),
            ]
        def share_btn():
            if st.button(f"Share Code: {sub['name']}", key=f"share_{sub['subject_code']}", icon=":material/share:"):
                share_subject_dialog(sub['name'], sub['subject_code'])
            st.space()

        subject_card(
            name = sub['name'],
            code = sub['subject_code'],
            section = sub['section'],
            stats=stats,
            footer_callback=share_btn
        )
    else:
        st.info("NO SUBJECTS FOUND. CREATE ONE ABOVE")


def _session_attendance_csv(students):
    """students: list of (name, is_present) tuples for one attendance session."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['Name', 'Status'])
    for name, is_present in sorted(students, key=lambda s: s[0] or ''):
        writer.writerow([name, 'Present' if is_present else 'Absent'])
    return buf.getvalue().encode('utf-8')


def teacher_tab_attendance_records():
    st.header('Attendance Records')

    teacher_id = st.session_state.teacher_data['teacher_id']

    subjects = get_teacher_subjects(teacher_id)

    if not subjects:
        st.info('Create a subject first to see attendance records.')
        return

    subject_options = {f"{s['name']} - {s['subject_code']}": s['subject_id'] for s in subjects}
    selected_label = st.selectbox(
        'Select Subject', options=list(subject_options.keys()),
        key='attendance_records_subject_select',
    )
    selected_subject_id = subject_options[selected_label]

    records = get_attendance_for_teacher(teacher_id)

    if not records:
        return

    records = [r for r in records if r['subjects']['subject_id'] == selected_subject_id]

    if not records:
        st.info('No attendance records yet for this subject.')
        return

    data = []
    session_students = defaultdict(list)  # ts_group -> [(name, is_present), ...]

    for r in records:
        ts = r.get('timestamp')
        ts_group = ts.split(".")[0] if ts else None
        is_present = bool(r.get('is_present', False))
        student_name = (r.get('students') or {}).get('name', 'Unknown')

        data.append({
            "ts_group": ts_group,
            "Time": datetime.fromisoformat(ts).strftime("%Y-%m-%d %I:%M %p") if ts else "N'A",
            "Subject": r['subjects']['name'],
            "Subject Code": r['subjects']['subject_code'],
            "is_present": is_present,
        })

        session_students[ts_group].append((student_name, is_present))

    df = pd.DataFrame(data)

    summary = (
        df.groupby(['ts_group', 'Time', 'Subject', 'Subject Code'])
        .agg(
            Present_Count = ('is_present', 'sum'),
            Total_Count =('is_present', 'count')
        ).reset_index()
    )

    summary['Attendance Stats'] = (
        "✅ " + summary['Present_Count'].astype(str) + " /"
        + summary['Total_Count'].astype(str) + ' Students'
    )

    display_df = (
        summary.sort_values(by='ts_group', ascending=False)
        [['ts_group', 'Time', 'Subject', 'Subject Code', 'Attendance Stats']]
        .reset_index(drop=True)
    )

    event = st.dataframe(
        display_df.drop(columns=['ts_group']),
        width='stretch',
        hide_index=True,
        on_select='rerun',
        selection_mode='single-row',
        key=f'attendance_records_table_{selected_subject_id}',
    )

    selected_rows = event.selection.rows if event and event.selection else []
    selected_rows = [r for r in selected_rows if r < len(display_df)]

    if selected_rows:
        selected_session = display_df.iloc[selected_rows[0]]
        csv_bytes = _session_attendance_csv(session_students.get(selected_session['ts_group'], []))
        st.download_button(
            label=f"Download CSV — {selected_session['Time']} ({selected_session['Subject Code']})",
            data=csv_bytes,
            file_name=f"attendance_{selected_session['Subject Code']}_{selected_session['ts_group']}.csv",
            mime='text/csv',
            icon=':material/download:',
        )
    else:
        st.caption("Select a row above to download that session's present/absent list as CSV.")


TIER_ORDER = {"Critical": 0, "At-Risk": 1, "Watch": 2, "Safe": 3}


def teacher_tab_student_analytics():
    """
    Teacher-facing add-on: a risk-sorted view of every student in a subject,
    so at-risk students surface first instead of the teacher scanning a flat
    roster. Reuses the same recovery/bunk/projection/risk-tier logic shown
    to students, computed per-subject from that subject's own attendance_logs.
    """
    st.header('Student Analytics - At-Risk List')

    teacher_id = st.session_state.teacher_data['teacher_id']
    subjects = get_teacher_subjects(teacher_id)

    if not subjects:
        st.info('Create a subject first to see student analytics.')
        return

    subject_options = {f"{s['name']} - {s['subject_code']}": s['subject_id'] for s in subjects}
    selected_label = st.selectbox('Select Subject', options=list(subject_options.keys()), key='analytics_subject_select')
    subject_id = subject_options[selected_label]

    with st.spinner('Computing attendance analytics...'):
        roster = get_subject_roster_with_logs(subject_id)

    if not roster:
        st.info('No students enrolled in this subject yet.')
        return

    rows = []
    for student in roster:
        result = analyze_student_subject(student['logs'])
        rows.append({
            'Name': student['name'],
            'ID': student['student_id'],
            'Attendance %': result['percentage'],
            'Tier': result['tier'].label,
            'Classes to Recover': result['recovery_needed'],
            'Can Safely Miss': result['can_bunk'],
            '_sort': TIER_ORDER[result['tier'].label],
        })

    rows.sort(key=lambda r: (r['_sort'], r['Attendance %']))
    for r in rows:
        del r['_sort']

    st.dataframe(rows, width='stretch', hide_index=True)

    needs_attention = [r for r in rows if r['Tier'] in ('Critical', 'At-Risk')]
    if needs_attention:
        st.warning(f"{len(needs_attention)} student(s) need attention: "
                   + ", ".join(r['Name'] for r in needs_attention))
    else:
        st.success('No students currently in Critical or At-Risk tiers.')


def login_teacher(username, password):
    if not username or not password:
        return False
    
    teacher = teacher_login(username, password)

    if teacher:
        st.session_state.user_role ='teacher'
        st.session_state.teacher_data = teacher
        st.session_state.is_logged_in = True
        return True
    

    return False
def teacher_screen_login():
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        if st.button("Go back to Home", type='secondary', key='loginbackbtn', shortcut="control+backspace"):
            st.session_state['login_type'] = None
            st.rerun()

    st.header('Login using password', text_alignment='center')
    st.space()
    st.space()


    teacher_username = st.text_input("Enter username", placeholder='ananyaroy')

    teacher_pass = st.text_input("Enter password", type='password', placeholder="Enter password")

    st.divider()

    btnc1, btnc2 = st.columns(2)

    with btnc1:
        if st.button('Login', icon=':material/passkey:', shortcut='control+enter', width='stretch'):
            if login_teacher(teacher_username, teacher_pass):
                st.toast("welcome back!", icon="👋")
                import time
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid username and password combo")

    with btnc2:
        if st.button('Register Instead', type="primary", icon=':material/passkey:', width='stretch'):
            st.session_state.teacher_login_type = 'register'

    footer_dashboard()



def register_teacher(teacher_username, teacher_name, teacher_pass, teacher_pass_confirm):
    if not teacher_username or not teacher_name or not teacher_pass:
        return False, "All Fields are required!"
    if check_teacher_exists(teacher_username):
        return False, "Username already taken"
    if teacher_pass != teacher_pass_confirm:
        return False, "Password doesn't match"
    
    try:
        create_teacher(teacher_username, teacher_pass, teacher_name)
        return True, "Sucessfully Created! Login Now"
    except Exception as e:
        return False, "Unexpected Error!"
    

def teacher_screen_register():
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        if st.button("Go back to Home", type='secondary', key='loginbackbtn', shortcut="control+backspace"):
            st.session_state['login_type'] = None
            st.rerun()

    st.header('Register your teacher profile')

    st.space()
    st.space()

    
    teacher_username = st.text_input("Enter username", placeholder='ananyaroy')

    teacher_name = st.text_input("Enter name", placeholder='Ananya Roy')

    teacher_pass = st.text_input("Enter password", type='password', placeholder="Enter password")

    teacher_pass_confirm = st.text_input("Confirm your password", type='password', placeholder="Enter password")

    st.divider()

    btnc1, btnc2 = st.columns(2)

    with btnc1:
        if st.button('Register now', icon=':material/passkey:', shortcut='control+enter', width='stretch'):
            success, message = register_teacher(teacher_username, teacher_name, teacher_pass, teacher_pass_confirm)
            if success:
                st.success(message)
                import time
                time.sleep(2)
                st.session_state.teacher_login_type = "login"
                st.rerun()
            else:
                st.error(message)


    with btnc2:
        if st.button('Login Instead', type="primary", icon=':material/passkey:', width='stretch'):
            st.session_state.teacher_login_type = 'login'

    footer_dashboard()