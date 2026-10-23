import streamlit as st
from src.components.global_widgets import render_global_widgets
from src.ui.base_layout import style_background_dashboard, style_base_layout

from src.components.header import header_dashboard
from src.components.footer import footer_dashboard
from PIL import Image
import numpy as np
from src.pipelines.face_pipeline import predict_attendance, get_face_embeddings, train_classifier
from src.pipelines.voice_pipeline import get_voice_embedding
from src.database.db import get_all_students, create_student, get_student_subjects, get_student_attendance, unenroll_student_to_subject
from src.pipelines.analytics import analyze_student_subject
import time

from src.components.dialog_enroll import enroll_dialog
from src.components.subject_card import subject_card

def student_dashboard():
    student_data = st.session_state.student_data
    student_id = student_data['student_id']
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        st.subheader(f"""Welcome, {student_data['name']} """)
        if st.button("Logout", type='secondary', key='loginbackbtn', shortcut="control+backspace"):
            st.session_state['is_logged_in'] = False
            del st.session_state.student_data 
            st.rerun()


    st.space()

    c1, c2 =st.columns(2)
    with c1:
        st.header('Your Enrolled Subjects')
    with c2:
        if st.button('Enroll in Subject', type='primary', width='stretch'):
            enroll_dialog()


    st.divider()


    with st.spinner('Loading your enrolled subjects..'):
        subjects = get_student_subjects(student_id)
        logs = get_student_attendance(student_id)

    stats_map = {}

    for log in logs:
        sid = log['subject_id']

        if sid not in stats_map:
            stats_map[sid] = {"total":0, "attended": 0}

        stats_map[sid]['total'] +=1

        if log.get('is_present'):
            stats_map[sid]['attended'] += 1


    cols = st.columns(2)
    for i, sub_node in enumerate(subjects):
        sub = sub_node['subjects']
        sid = sub['subject_id']


        stats = stats_map.get(sid,{"total":0, "attended": 0} )
        def unenroll_button():
                if st.button("Unenroll from this course", type='tertiary', width='stretch', icon=':material/delete_forever:',key=f'unenroll_{sid}'):
                    unenroll_student_to_subject(student_id, sid)
                    st.toast(f"Unenrolled from {sub['name']} successfully!")
                    st.rerun()

        with cols[i % 2]:

            subject_card(
                name = sub['name'],
                code =sub['subject_code'],
                section = sub['section'],
                stats = [
                    ('📅', 'Total', stats['total']),
                    ('✅', 'Attended', stats['attended']),
                ],
                footer_callback=unenroll_button
            )

    student_analytics_section(subjects, logs)
    footer_dashboard()


def student_analytics_section(subjects, logs):
    """
    Student Attendance Analysis add-on: recovery calculator, bunk
    calculator, semester-end projection, and risk tier - for one
    selected subject at a time, chosen via dropdown (same pattern as
    the teacher-side Student Analytics tab).
    """
    if not subjects:
        return

    st.header('My Attendance Analytics')
    st.caption('Based on your attendance logs across each subject you\'re enrolled in.')

    subject_options = {
        f"{sub_node['subjects']['name']} - {sub_node['subjects']['subject_code']}": sub_node['subjects']
        for sub_node in subjects
    }
    selected_label = st.selectbox(
        'Select Subject', options=list(subject_options.keys()),
        key='student_analytics_subject_select',
    )
    selected_subject = subject_options[selected_label]
    sid = selected_subject['subject_id']

    logs_by_subject = {}
    for log in logs:
        logs_by_subject.setdefault(log['subject_id'], []).append(log)

    subject_logs = logs_by_subject.get(sid, [])

    with st.container(border=True):
        st.subheader(selected_subject['name'])

        if not subject_logs:
            st.info('No attendance recorded yet for this subject.')
        else:
            remaining = st.number_input(
                'Estimated lectures remaining this semester', min_value=0, value=20,
                key=f'remaining_{sid}',
            )
            result = analyze_student_subject(subject_logs, remaining_lectures=remaining)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric('Attendance', f"{result['percentage']}%")
            c2.metric('Classes to recover', result['recovery_needed'],
                       help='Consecutive classes needed to reach 75%, if below it.')
            c3.metric('Can safely miss', result['can_bunk'],
                       help='Classes you can miss going forward and stay at/above 75%.')
            c4.metric('Semester-end projection', f"{result['projection']}%",
                       help='Based on your recent attendance trend, not just the lifetime average.')

            tier = result['tier']
            st.markdown(f"<span style='color:{tier.color}; font-weight:600;'>● {tier.label}</span>",
                        unsafe_allow_html=True)

    st.divider()


def student_screen():

    style_background_dashboard()
    style_base_layout(accent="#2FA88F")   # soft teal on Student Login + Dashboard
    render_global_widgets()

    if "student_data" in st.session_state:
        student_dashboard()
        return
    
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        if st.button("Go back to Home", type='secondary', key='loginbackbtn', shortcut="control+backspace"):
            st.session_state['login_type'] = None
            st.rerun()

    st.header('Login using FaceID', text_alignment='center')
    st.space()
    st.space()

    show_registration = False

    if 'student_photo_source' not in st.session_state:
        st.session_state.student_photo_source = 'camera'

    t1, t2 = st.columns(2)
    with t1:
        type_camera = "primary" if st.session_state.student_photo_source == 'camera' else 'tertiary'
        if st.button('Use Camera', type=type_camera, width='stretch', key='face_id_camera_toggle'):
            st.session_state.student_photo_source = 'camera'
            st.rerun()
    with t2:
        type_upload = "primary" if st.session_state.student_photo_source == 'upload' else 'tertiary'
        if st.button('Upload Photo', type=type_upload, width='stretch', key='face_id_upload_toggle'):
            st.session_state.student_photo_source = 'upload'
            st.rerun()

    if st.session_state.student_photo_source == 'camera':
        photo_source = st.camera_input("Position your face in the center")
    else:
        photo_source = st.file_uploader(
            "Upload a clear, front-facing photo", type=['jpg', 'jpeg', 'png'], key='face_id_upload',
        )

    if photo_source:
        img = np.array(Image.open(photo_source))

        with st.spinner('AI is scanning..'):
            detected, all_ids, num_faces = predict_attendance(img)

            if num_faces == 0:
                st.warning('Face not found!')
            elif num_faces >1:
                st.warning('Multiple faces found')
            else:
                if detected:
                    student_id = list(detected.keys())[0]
                    all_students = get_all_students()
                    student = next((s for s in all_students if s['student_id']==student_id), None)

                    if student:
                        st.session_state.is_logged_in = True
                        st.session_state.user_role = 'student'
                        st.session_state.student_data = student
                        st.toast(f"Welcome Back {student['name']}")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.info('Face not recognized! You might be a new student!')
                    show_registration = True
    if show_registration:
        with st.container(border=True):
            st.header('Register new Profile')
            new_name = st.text_input("Enter your name", placeholder='E.g. Ramanand Tiwari')

            st.subheader('Optional : Voice Enrollment')
            st.info("Enroll your for voice only attendance")

            audio_data = None

            try:
                audio_data = st.audio_input('Record a short phrase like I am present, My name is Akash.')
            except Exception:
                st.error('Audio Data failed!')

            if st.button('Create Account', type='primary'):
                if new_name:
                    with st.spinner('Creating profile..'):
                        img = np.array(Image.open(photo_source))
                        encodings= get_face_embeddings(img)
                        if encodings:
                            face_emb = encodings[0].tolist()

                            voice_emb = None
                            if audio_data:
                                voice_emb = get_voice_embedding(audio_data.read())

                            response_data = create_student(new_name, face_embedding=face_emb, voice_embedding=voice_emb)

                            if response_data:
                                train_classifier()
                                st.session_state.is_logged_in = True
                                st.session_state.user_role = 'student'
                                st.session_state.student_data = response_data[0]
                                st.toast(f'Profile Created! Hi {new_name}!')
                                time.sleep(1)
                                st.rerun()
                        else:
                            st.error('Couldnt capture your facial features for registration')

                else:
                    st.warning('Please enter your name!')

    footer_dashboard()