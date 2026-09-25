from src.database.config import supabase
import bcrypt
from src.security.encryption import encrypt_embedding, decrypt_embedding



def hash_pass(pwd):
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()

def check_pass(pwd, hashed):
    return bcrypt.checkpw(pwd.encode(), hashed.encode())


def check_teacher_exists(username):
    # Check for unique username, returns false when username is already taken
    response = supabase.table("teachers").select("username").eq("username", username).execute()
    return len(response.data) > 0 



def create_teacher(username, password, name):

    data = { "username" : username, "password": hash_pass(password), "name": name}
    response = supabase.table("teachers").insert(data).execute()
    return response.data


def teacher_login(username, password):
    response = supabase.table("teachers").select("*").eq("username", username).execute()
    if response.data:
        teacher = response.data[0]
        if check_pass(password, teacher['password']):
            return teacher
    return None


def get_all_students():
    response = supabase.table('students').select("*").execute()
    students = response.data
    # Decrypt embeddings in memory only - never written back to disk in
    # plaintext, and never logged.
    for s in students:
        s['face_embedding'] = decrypt_embedding(s.get('face_embedding'))
        s['voice_embedding'] = decrypt_embedding(s.get('voice_embedding'))
    return students

def create_student(new_name, face_embedding=None, voice_embedding=None):
    data = {
        'name': new_name,
        'face_embedding': encrypt_embedding(face_embedding),
        'voice_embedding': encrypt_embedding(voice_embedding),
    }
    response = supabase.table('students').insert(data).execute()
    if response.data:
        # Return the plaintext embeddings to the caller for this request only
        # (e.g. student_screen.py immediately uses response_data[0] as
        # session state) - the DB row itself stays encrypted.
        response.data[0]['face_embedding'] = face_embedding
        response.data[0]['voice_embedding'] = voice_embedding
    return response.data


def get_enrolled_students_with_voice(subject_id):
    """
    Same enrolled-students-with-embeddings query dialog_voice_attendance.py
    needs, centralized here so decryption only happens in one place instead
    of being duplicated at every call site.
    """
    enrolled_res = supabase.table('subject_students').select("*, students(*)").eq('subject_id', subject_id).execute()
    enrolled_students = enrolled_res.data
    for node in enrolled_students:
        node['students']['voice_embedding'] = decrypt_embedding(node['students'].get('voice_embedding'))
    return enrolled_students


def create_subject(subject_code, name, section, teacher_id):
    data = {"subject_code": subject_code, "name": name, "section": section, "teacher_id": teacher_id}
    response = supabase.table("subjects").insert(data).execute()
    return response.data

def get_teacher_subjects(teacher_id):
    response = supabase.table('subjects').select("*, subject_students(count), attendance_logs(timestamp)").eq("teacher_id", teacher_id).execute()
    subjects = response.data


    for sub in subjects:
        sub['total_students'] = sub.get("subject_students", [{}])[0].get('count', 0) if sub.get('subject_students') else 0
        attendance = sub.get('attendance_logs', [])
        unique_sessions = len(set(log['timestamp'] for log in attendance))
        sub['total_classes'] = unique_sessions


        sub.pop('subject_student', None)
        sub.pop('attendance_logs', None)

    return subjects


def  enroll_student_to_subject(student_id, subject_id):
    data = {'student_id': student_id, "subject_id": subject_id}
    response= supabase.table('subject_students').insert(data).execute()
    return response.data


def  unenroll_student_to_subject(student_id, subject_id):
    response= supabase.table('subject_students').delete().eq('student_id', student_id).eq('subject_id', subject_id).execute()
    return response.data



def get_student_subjects(student_id):
    response = supabase.table('subject_students').select('*, subjects(*)').eq('student_id', student_id).execute()
    return response.data


def get_student_attendance(student_id):
    response = supabase.table('attendance_logs').select('*, subjects(*)').eq('student_id', student_id).execute()
    return response.data


def create_attendance(logs):
    response = supabase.table('attendance_logs').insert(logs).execute()
    return response.data

def get_attendance_for_teacher(teacher_id):
    response = supabase.table('attendance_logs').select("*, subjects!inner(*), students(name)").eq('subjects.teacher_id', teacher_id).execute()
    return response.data


def get_subject_roster_with_logs(subject_id):
    """
    For the teacher-facing at-risk list: every student enrolled in a subject,
    each with their own attendance_logs for that subject specifically
    (not mixed with their logs from other subjects).
    """
    enrolled_res = supabase.table('subject_students').select("*, students(*)").eq('subject_id', subject_id).execute()
    enrolled_students = [node['students'] for node in enrolled_res.data]

    logs_res = supabase.table('attendance_logs').select("*").eq('subject_id', subject_id).execute()
    logs_by_student = {}
    for log in logs_res.data:
        logs_by_student.setdefault(log['student_id'], []).append(log)

    for student in enrolled_students:
        student['logs'] = logs_by_student.get(student['student_id'], [])

    return enrolled_students

