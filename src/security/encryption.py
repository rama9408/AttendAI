"""
src/security/encryption.py
Privacy-preserving design component.

Face and voice embeddings are encrypted before being written to Supabase,
and decrypted only in memory when needed for matching. The database never
holds a usable raw embedding at rest - a leaked table alone doesn't expose
biometric data.

Key handling:
  - In deployment, set EMBEDDING_KEY in Streamlit secrets (.streamlit/secrets.toml
    locally, or the Secrets panel on Streamlit Community Cloud).
  - For local dev without secrets configured, a key is generated once and
    cached in st.session_state so the app still runs end-to-end - but note
    this means encrypted data from a previous session won't decrypt after
    a restart unless EMBEDDING_KEY is set explicitly. Set it for anything
    beyond a quick local test.
"""

import json
import streamlit as st
from cryptography.fernet import Fernet


@st.cache_resource(show_spinner=False)
def _get_fernet() -> Fernet:
    key = None
    try:
        key = st.secrets.get("EMBEDDING_KEY")
    except Exception:
        # No secrets.toml configured at all (e.g. first local run before
        # you've set one up) - fall through to the local-dev fallback below.
        pass
    if not key:
        # Local-dev fallback so the app still runs without secrets configured.
        # Cached for the lifetime of the process only - not persisted to disk,
        # so restarting the app invalidates previously encrypted data. This is
        # intentional: it nudges you to set a real EMBEDDING_KEY before your
        # data actually needs to persist (e.g. before your demo/submission).
        key = Fernet.generate_key().decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_embedding(embedding: list) -> str:
    """Takes a plain Python list (as produced by .tolist() in the pipelines) and
    returns an encrypted string safe to store in a `text` column."""
    if embedding is None:
        return None
    payload = json.dumps(embedding).encode("utf-8")
    return _get_fernet().encrypt(payload).decode("utf-8")


def decrypt_embedding(token) -> list:
    """Reverses encrypt_embedding. Returns None if given None/empty, and
    passes through unchanged if the value doesn't look encrypted (so old,
    pre-encryption rows don't crash the app - see the migration note)."""
    if not token:
        return None
    if isinstance(token, list):
        # Already a plain list - e.g. a row written before encryption was added.
        return token
    try:
        payload = _get_fernet().decrypt(token.encode("utf-8"))
        return json.loads(payload.decode("utf-8"))
    except Exception:
        # Not decryptable with the current key (or not actually encrypted) -
        # surfaced as None rather than crashing the classifier/matcher.
        return None
