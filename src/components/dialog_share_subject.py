import streamlit as st

import segno
import io


@st.dialog("Share Class Link")
def share_subject_dialog(subject_name, subject_code):
    try:
        app_url = st.secrets.get("APP_URL")
    except Exception:
        app_url = None
    app_url = (app_url or "http://localhost:8501").rstrip("/")

    join_url = f"{app_url}/?join-code={subject_code}"

    st.header("Scan to Join")

    qr = segno.make(join_url)

    out = io.BytesIO()

    qr.save(out, kind='png', scale=10, border=1)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('### Copy Link')
        st.code(join_url, language="text")
        st.code(subject_code, language="text")
        st.info('Copy this link to share on Whatsapp or Email')

    with col2:
        st.markdown('### Scan to Join')
        st.image(out.getvalue(), caption='QRCODE for class joining')
        # if app_url.startswith("http://localhost"):
        #     st.warning(
        #         "APP_URL isn't set - this QR points to localhost, which only "
        #         "works if the scanning device is the same machine. Deploy the "
        #         "app and set APP_URL in secrets.toml for QR codes that work on "
        #         "students' phones."
        #     )

        
