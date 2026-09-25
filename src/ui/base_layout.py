import streamlit as st


def style_background_home():
    st.markdown("""
        <style>
                .stApp {
                    background: linear-gradient(135deg, #FFF3E6 0%, #FFE1CC 55%, #FFD1B0 100%) !important;
                }

                .stApp div[data-testid="stColumn"]{
                    background-color:#FFFFFF !important;
                    padding:1.5rem !important;
                    border-radius: 2rem !important;
                    box-shadow: 0 20px 40px rgba(217, 122, 85, 0.14) !important;
                    }

                .block-container {
                    padding-top: 0.5rem !important;
                    padding-bottom: 0.5rem !important;
                }
        </style>
                """
            ,unsafe_allow_html=True)


def style_background_dashboard():
    st.markdown("""
        <style>
                .stApp {
                    background: #FDF6EC !important;
                }
        </style>
                """
            ,unsafe_allow_html=True)


def style_base_layout(accent="#D97A55"):
    """
    accent: the page's primary button/logo/badge color. Every component
    that needs it (header, subject_card, buttons) reads it via the
    var(--primary) CSS variable set here, so a page only needs to pass
    one hex value to fully re-theme.
    """
    secondary = "#D97A55" if accent == "#2FA88F" else "#2FA88F"

    st.markdown(f"""
        <style>
        :root {{
            --ink:        #3A2E2A;
            --ink-muted:  #8A7568;
            --surface:    #FFFFFF;
            --border:     #F0E4D3;
            --primary:    {accent};
            --secondary:  {secondary};
        }}
        </style>
                """
            ,unsafe_allow_html=True)

    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap');

        /* Hide Streamlit's default chrome */
        #MainMenu, footer, header {
            visibility: hidden;
        }

        .block-container {
            padding-top: 1.5rem !important;
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: 'Fredoka', sans-serif !important;
            color: var(--ink) !important;
            font-weight: 600 !important;
        }

        h1 { font-size: 2.75rem !important; line-height: 1.15 !important; margin-bottom: 0.25rem !important; }
        h2 { font-size: 1.75rem !important; line-height: 1.2  !important; margin-bottom: 0.25rem !important; }
        h3 { font-size: 1.25rem !important; }

        p, span, li, label, div {
            font-family: 'Quicksand', sans-serif;
        }

        .stApp, .stApp p, .stApp span, .stApp li, .stMarkdown {
            color: var(--ink) !important;
        }

        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] p {
            color: var(--ink-muted) !important;
        }

        [data-testid="stWidgetLabel"] p,
        label {
            color: var(--ink) !important;
            font-weight: 600 !important;
        }

        [data-testid="stMetricValue"] {
            color: var(--ink) !important;
            font-family: 'Fredoka', sans-serif !important;
        }
        [data-testid="stMetricLabel"] {
            color: var(--ink-muted) !important;
        }

        div[data-testid="stAlertContentInfo"],
        div[data-testid="stAlertContentWarning"],
        div[data-testid="stAlertContentSuccess"],
        div[data-testid="stAlertContentError"] {
            color: var(--ink) !important;
        }

        [data-testid="stDataFrame"] * {
            color: var(--ink) !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: 1.5rem !important;
            padding: 0.5rem !important;
        }

        input, textarea, select,
        [data-baseweb="input"] input,
        [data-baseweb="select"] * {
            color: var(--ink) !important;
        }
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea {
            background: var(--surface) !important;
            border: 1.5px solid var(--border) !important;
            border-radius: 0.9rem !important;
        }

        /* ---------- Buttons ---------- */

        button {
            border-radius: 1.25rem !important;
            background-color: var(--primary) !important;
            color: #FFFFFF !important;
            padding: 10px 20px !important;
            border: none !important;
            font-weight: 700 !important;
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out !important;
        }

        button[kind="secondary"] {
            background-color: var(--secondary) !important;
            color: #FFFFFF !important;
        }

        button[kind="tertiary"] {
            background-color: var(--surface) !important;
            color: var(--ink) !important;
            border: 1.5px solid var(--border) !important;
        }

        button p {
            color: inherit !important;
            font-weight: 700 !important;
        }

        button:hover {
            transform: scale(1.03);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
        }

        button[kind="icon"] {
            background: transparent !important;
            color: var(--ink-muted) !important;
            padding: 4px !important;
            border-radius: 999px !important;
            box-shadow: none !important;
        }
        button[kind="icon"]:hover {
            background: var(--border) !important;
            transform: none !important;
            box-shadow: none !important;
        }

        [data-baseweb="select"] > div {
            background: var(--surface) !important;
            border: 1.5px solid var(--border) !important;
            box-shadow: none !important;
        }
        [data-baseweb="select"] > div:focus-within {
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 1px var(--primary) !important;
        }
        [data-baseweb="select"] * {
            color: var(--ink) !important;
        }
        [data-baseweb="popover"] [data-baseweb="menu"] {
            background: var(--surface) !important;
        }
        [data-baseweb="menu"] li,
        [data-baseweb="menu"] li * {
            color: var(--ink) !important;
        }
        [data-baseweb="menu"] li:hover {
            background: var(--border) !important;
        }

        div[role="dialog"] {
            background: var(--surface) !important;
        }
        div[role="dialog"] h1, div[role="dialog"] h2, div[role="dialog"] h3,
        div[role="dialog"] p, div[role="dialog"] span, div[role="dialog"] label,
        div[role="dialog"] [data-testid="stWidgetLabel"] p {
            color: var(--ink) !important;
        }

        [data-testid="stFileUploaderDropzone"] {
            background: var(--surface) !important;
            border: 1.5px dashed var(--border) !important;
        }
        [data-testid="stFileUploaderDropzone"] * {
            color: var(--ink-muted) !important;
        }

        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] p {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: unset !important;
        }
        </style>
                """
            ,unsafe_allow_html=True)