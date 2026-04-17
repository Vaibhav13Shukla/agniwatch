"""
GEE Authentication Handler
Supports: Streamlit (Service Account), Colab (OAuth), Auto-detection
"""

import ee
import os
import json
import streamlit as st
from typing import Optional


def auth_streamlit(project_id: str) -> bool:
    """
    Authenticate GEE in Streamlit using Service Account from secrets.
    """
    try:
        if hasattr(st, 'secrets') and 'gee' in st.secrets:
            credentials = ee.ServiceAccountCredentials(
                email=st.secrets['gee']['service_account'],
                key_data=st.secrets['gee']['private_key']
            )
            ee.Initialize(credentials=credentials, project=project_id)
            return True
    except Exception:
        pass

    try:
        sa_json = os.environ.get('GEE_SERVICE_ACCOUNT_JSON')
        if sa_json:
            key_data = json.loads(sa_json)
            credentials = ee.ServiceAccountCredentials(
                email=key_data['client_email'],
                key_data=json.dumps(key_data)
            )
            ee.Initialize(credentials=credentials, project=project_id)
            return True
    except Exception:
        pass

    try:
        ee.Initialize(project=project_id)
        ee.Number(1).getInfo()
        return True
    except Exception:
        pass

    return False


def auth_colab(project_id: str, force: bool = False) -> bool:
    """Interactive OAuth flow for Colab."""
    try:
        if not force:
            ee.Initialize(project=project_id)
            if ee.Number(42).getInfo() == 42:
                return True
    except Exception:
        pass

    SCOPES = [
        'https://www.googleapis.com/auth/earthengine',
        'https://www.googleapis.com/auth/cloud-platform',
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/devstorage.full_control',
    ]
    ee.Authenticate(auth_mode='notebook', scopes=SCOPES, force=force)
    ee.Initialize(project=project_id)
    return ee.Number(42).getInfo() == 42


def initialize_gee(project_id: str, environment: str = 'auto') -> bool:
    """
    Smart GEE initializer — detects environment automatically.
    """
    if environment == 'auto':
        try:
            import google.colab  # noqa
            environment = 'colab'
        except ImportError:
            environment = 'streamlit'

    if environment == 'colab':
        return auth_colab(project_id)
    else:
        return auth_streamlit(project_id)