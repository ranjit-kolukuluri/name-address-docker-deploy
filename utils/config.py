# utils/config.py
"""
Simplified configuration for Docker testing
"""

import os
from pathlib import Path
from typing import Tuple, Optional


def load_usps_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Load USPS credentials - simplified for Docker"""
    
    print("🔍 Loading USPS credentials...")
    
    # Try environment variables first (Docker priority)
    client_id = os.getenv('USPS_CLIENT_ID', '')
    client_secret = os.getenv('USPS_CLIENT_SECRET', '')
    
    if client_id and client_secret:
        print("✅ USPS credentials loaded from environment variables")
        return client_id, client_secret
    
    # Try .env file as backup
    try:
        env_path = Path('.env')
        if env_path.exists():
            print("🔍 Trying .env file...")
            env_vars = {}
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"').strip("'")
            
            client_id = env_vars.get('USPS_CLIENT_ID', '')
            client_secret = env_vars.get('USPS_CLIENT_SECRET', '')
            if client_id and client_secret:
                print("✅ USPS credentials loaded from .env file")
                return client_id, client_secret
    except Exception as e:
        print(f"⚠️ Failed to load from .env file: {str(e)}")
    
    # Try Streamlit secrets only if streamlit is available
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            client_id = st.secrets.get("USPS_CLIENT_ID", "")
            client_secret = st.secrets.get("USPS_CLIENT_SECRET", "")
            if client_id and client_secret:
                print("✅ USPS credentials loaded from Streamlit secrets")
                return client_id, client_secret
    except ImportError:
        # Streamlit not available (probably in API container)
        print("ℹ️ Streamlit not available - skipping Streamlit secrets")
    except Exception as e:
        print(f"⚠️ Failed to load from Streamlit secrets: {str(e)}")
    
    # Try TOML files only if toml is available
    try:
        import toml
        
        # Try .streamlit/secrets.toml
        secrets_toml_path = Path('.streamlit/secrets.toml')
        if secrets_toml_path.exists():
            print("🔍 Trying .streamlit/secrets.toml...")
            config = toml.load(secrets_toml_path)
            client_id = config.get('USPS_CLIENT_ID', '')
            client_secret = config.get('USPS_CLIENT_SECRET', '')
            if client_id and client_secret:
                print("✅ USPS credentials loaded from .streamlit/secrets.toml")
                return client_id, client_secret
                
    except ImportError:
        # TOML not available (probably in API container)
        print("ℹ️ TOML not available - skipping TOML files")
    except Exception as e:
        print(f"⚠️ Failed to load TOML files: {str(e)}")
    
    print("❌ USPS credentials not found in any location")
    print("💡 Available methods: environment variables, .env file")
    print(f"🔍 Environment check - USPS_CLIENT_ID: {'SET' if os.getenv('USPS_CLIENT_ID') else 'NOT SET'}")
    print(f"🔍 Environment check - USPS_CLIENT_SECRET: {'SET' if os.getenv('USPS_CLIENT_SECRET') else 'NOT SET'}")
    return None, None


class Config:
    """Application configuration"""
    
    # API Settings
    API_VERSION = "2.0.0"
    MAX_BATCH_RECORDS = 1000
    MAX_FILES_PER_UPLOAD = 10
    VALIDATION_TIMEOUT = 60
    MAX_SUGGESTIONS = 5
    
    # File Upload Settings
    MAX_FILE_SIZE_MB = 50
    SUPPORTED_CSV_ENCODINGS = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
    
    # UI Settings
    ENABLE_DEBUG_LOGGING = True
    PERFORMANCE_TRACKING = True
    
    # USPS Settings
    USPS_AUTH_URL = 'https://apis.usps.com/oauth2/v3/token'
    USPS_VALIDATE_URL = 'https://apis.usps.com/addresses/v3/address'
    
    # US States
    US_STATES = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
    }