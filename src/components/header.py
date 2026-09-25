import streamlit as st

LOGO_URL = "https://i.ibb.co/YTYGn5qV/logo.png"


def header_home():
    st.markdown(f"""
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; margin-bottom:10px; margin-top:5px">
            <img src='{LOGO_URL}' style='height:60px;' />
            <h1 style='text-align:center; color:var(--ink); font-family: Fredoka, sans-serif; font-size:2.25rem !important; margin:0;'>ATTEND AI</h1>
            <p style='text-align:center; color:var(--ink); font-family: Quicksand, sans-serif; font-size:1.5rem; margin:0.75rem 0 0.35rem 0; font-weight:600;'>Smart attendance, zero hassle</p>
            <p style='text-align:center; color:var(--ink-muted); font-family: Quicksand, sans-serif; font-size:1rem; margin:0;'>Face and voice recognition attendance for our classroom</p>
        </div>   
                
                """, unsafe_allow_html=True)


def header_dashboard():
    st.markdown(f"""
        <div style="display:flex; align-items:center; justify-content:center; gap:10px">
            <img src='{LOGO_URL}' style='height:85px;' />
            <h2 style='text-align:left; color:var(--primary); font-family: Fredoka, sans-serif;'>ATTEND<br/>AI</h2>
        </div>   
                
                """, unsafe_allow_html=True)