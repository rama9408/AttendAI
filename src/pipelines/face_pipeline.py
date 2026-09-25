import dlib
import numpy as np
import face_recognition_models
import streamlit as st
import logging

from src.database.db import get_all_students


@st.cache_resource
def load_dlib_models():
    detector = dlib.get_frontal_face_detector() 


    sp = dlib.shape_predictor(
        face_recognition_models.pose_predictor_model_location()
    )

    facerec = dlib.face_recognition_model_v1(
        face_recognition_models.face_recognition_model_location()
    )

    return detector, sp, facerec

def get_face_embeddings(image_np):
    detector, sp, facerec = load_dlib_models()
    faces = detector(image_np, 1)

    encodings= []

    for face in faces:
        shape = sp(image_np, face)
        face_descriptor = facerec.compute_face_descriptor(image_np, shape, 1) #128 embedding

        encodings.append(np.array(face_descriptor))
    return encodings

@st.cache_resource
def get_trained_model():
    X = []
    y = []


    student_db = get_all_students()

    if not student_db:
        return None
    
    for student in student_db:
        embedding = student.get('face_embedding')
        

        if embedding:
            X.append(np.array(embedding))
            y.append(student.get('student_id'))
            


    if len(X) == 0:
        return 0

    # Nearest-neighbor matching: just keep the embeddings/ids around.
    # No classifier training is needed (and none of its per-class
    # sample-count requirements apply), so there's nothing here that
    # can silently fail the way CalibratedClassifierCV.fit() did.
    return {'X': X, "y": y}


def train_classifier():
    st.cache_resource.clear()
    model_data = get_trained_model()
    return bool(model_data)

def predict_attendance(class_image_np):
    encodings = get_face_embeddings(class_image_np)

    detected_student = {}


    model_data = get_trained_model()

    if not model_data:
        return detected_student, [], len(encodings)

    X_train = model_data['X']
    y_train = model_data['y']

    all_students = sorted(list(set(y_train)))

    resemblance_threshold = 0.55
    margin_ratio = 0.85  # best match must be at least 15% closer than the runner-up

    for encoding in encodings:
        # Compare against every registered student's embedding(s) and
        # rank all of them by distance.
        scored = []
        for student_embedding, student_id in zip(X_train, y_train):
            score = np.linalg.norm(student_embedding - encoding)
            scored.append((score, student_id))
        scored.sort(key=lambda item: item[0])

        best_score, best_id = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else None

        # Two conditions must both hold:
        # 1) the closest student is still within an absolute distance
        #    of the scanned face (resemblance_threshold)
        # 2) that closest student is a clear standout, not just
        #    marginally closer than everyone else (margin_ratio) -
        #    this is what stops an unknown face's "least-wrong" guess
        #    among a growing roster from sneaking under the threshold
        is_confident_match = best_score <= resemblance_threshold and (
            second_score is None or best_score <= second_score * margin_ratio
        )

        if is_confident_match:
            detected_student[int(best_id)] = True

    return detected_student, all_students, len(encodings)