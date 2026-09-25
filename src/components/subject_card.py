import streamlit as st

def subject_card(name, code, section, stats=None, footer_callback=None):
    html = f"""
        <div style="background:var(--surface); border-left: 6px solid var(--primary); padding:25px; border-radius: 1.5rem; border: 1px solid var(--border); box-shadow: 0 4px 14px rgba(0,0,0,0.06); margin-bottom:20px;">
        <h3 style="margin:0; color: var(--ink); font-size: 1.4rem; font-family:'Fredoka', sans-serif;">{name}</h3>
        <p style="color:var(--ink-muted); margin:10px 0;">Code : <span style="background:var(--surface); border:1px solid var(--border); color:var(--primary); padding:2px 10px; border-radius:8px; font-weight:600;">{code} </span> | Section : {section}</p>
        
        """

    if stats:
        html+= """
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
        """
        for icon, label, value in stats:
            html+= f'<div style="background:var(--border); color:var(--ink); padding:5px 12px; border-radius:12px; font-size:0.9rem">{icon} <b>{value}</b> {label} </div>'

        html+= "</div>"

    st.markdown(html, unsafe_allow_html=True)

    if footer_callback:
        footer_callback()