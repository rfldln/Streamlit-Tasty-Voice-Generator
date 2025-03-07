import streamlit as st
import requests
import json
import os
import base64
import hashlib
import pickle
from io import BytesIO
from pathlib import Path
import time

# Multi-account API key handling
def get_elevenlabs_accounts():
    """Get all configured ElevenLabs accounts from secrets or environment variables"""
    accounts = {}
    
    # For local development with .env file
    try:
        from dotenv import load_dotenv
        if Path(".env").exists():
            load_dotenv()
    except ImportError:
        pass
    
    # Try to get accounts from Streamlit secrets
    try:
        if "elevenlabs" in st.secrets:
            # Get accounts configured in secrets
            elevenlabs_secrets = st.secrets["elevenlabs"]
            
            # Process each account (expecting pairs of account#_name and account#_key)
            account_indices = set()
            for key in elevenlabs_secrets:
                if key.startswith("account") and key.endswith("_name"):
                    idx = key.replace("account", "").replace("_name", "")
                    account_indices.add(idx)
            
            # Create account entries
            for idx in account_indices:
                name_key = f"account{idx}_name"
                api_key_key = f"account{idx}_key"
                
                if name_key in elevenlabs_secrets and api_key_key in elevenlabs_secrets:
                    account_name = elevenlabs_secrets[name_key]
                    account_api_key = elevenlabs_secrets[api_key_key]
                    accounts[account_name] = account_api_key
    except Exception as e:
        st.warning(f"Error loading accounts from secrets: {e}")
    
    # Fallback to environment variables if no accounts found
    if not accounts:
        # Try from .env or environment variables with multiple account format
        env_accounts = {}
        for i in range(1, 10):  # Check for up to 9 accounts
            name_env = os.environ.get(f"ELEVENLABS_ACCOUNT{i}_NAME")
            key_env = os.environ.get(f"ELEVENLABS_ACCOUNT{i}_KEY")
            
            if name_env and key_env:
                env_accounts[name_env] = key_env
        
        if env_accounts:
            accounts = env_accounts
        else:
            # Final fallback to legacy single API key
            default_api_key = os.environ.get("ELEVENLABS_API_KEY")
            if default_api_key:
                accounts["Default Account"] = default_api_key
    
    return accounts

# User authentication functions - adapted for cloud
def init_authentication():
    """Initialize the authentication system"""
    # Check if we have existing session state users
    if "users_dict" in st.session_state:
        return st.session_state.users_dict
    
    # Create data directory if it doesn't exist (for local development)
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Create users file if it doesn't exist
    users_file = data_dir / "users.pkl"
    
    # Default admin credentials - in production, use more secure methods
    default_username = "admin"
    # Use environment variable for admin password if available
    default_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    
    # Try to get from secrets if available
    try:
        if "admin" in st.secrets and "password" in st.secrets.admin:
            default_password = st.secrets.admin.password
    except:
        pass
    
    if users_file.exists():
        try:
            # Try to load from file first
            with open(users_file, "rb") as f:
                users = pickle.load(f)
                st.session_state.users_dict = users
                return users
        except Exception as e:
            st.warning(f"Could not load users from file: {e}")
            # Fall back to default user
    
    # Create default admin user
    admin_user = {
        "username": default_username,
        "password_hash": hash_password(default_password),
        "is_admin": True,
        "created_at": time.time()
    }
    users = {default_username: admin_user}
    st.session_state.users_dict = users
    
    # Try to save locally for development (might fail in cloud)
    try:
        with open(users_file, "wb") as f:
            pickle.dump(users, f)
    except Exception as e:
        pass  # Silent fail in cloud environment
    
    return users

def hash_password(password):
    """Create a SHA-256 hash of the password"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_hash, provided_password):
    """Verify that the provided password matches the stored hash"""
    return stored_hash == hash_password(provided_password)

def save_users(users):
    """Save the users dictionary to session state and try to save to disk"""
    st.session_state.users_dict = users
    # Try to save locally for development (might fail in cloud)
    try:
        with open(Path("data") / "users.pkl", "wb") as f:
            pickle.dump(users, f)
    except Exception:
        pass  # Silent fail in cloud environment

def login_user(username, password, users):
    """Attempt to log in a user"""
    if username in users and verify_password(users[username]["password_hash"], password):
        return True
    return False

def create_user(username, password, is_admin, users):
    """Create a new user"""
    if username in users:
        return False, "Username already exists"
    
    users[username] = {
        "username": username,
        "password_hash": hash_password(password),
        "is_admin": is_admin,
        "created_at": time.time()
    }
    save_users(users)
    return True, "User created successfully"

def delete_user(username, users, current_user):
    """Delete a user"""
    # Don't allow deleting your own account
    if username == current_user:
        return False, "You cannot delete your own account"
    
    # Check if user exists
    if username not in users:
        return False, "User doesn't exist"
    
    # Delete the user
    del users[username]
    save_users(users)
    return True, f"User '{username}' deleted successfully"

# Function to get all voices for a specific account
@st.cache_data(ttl=3600)  # Cache for one hour
def get_voices_for_account(api_key):
    """Get all voices available for the specified API key"""
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {
        "Accept": "application/json",
        "xi-api-key": api_key
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        voices_data = response.json()
        return voices_data
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching voices: {str(e)}")
        return {"voices": []}

# Function to display account information
def show_account_info(account_name, voices_data):
    """Display information about the selected account and its voices"""
    total_voices = len(voices_data.get("voices", []))
    
    # Display the information in a nice card
    st.markdown("""
    <div style="background-color: rgba(40, 40, 80, 0.6); 
                border-radius: 8px; 
                padding: 15px; 
                margin-bottom: 20px; 
                border: 1px solid rgba(123, 97, 255, 0.3);">
        <h3 style="margin-top: 0; color: #aa80ff;">Account Information</h3>
        <p><strong>Name:</strong> {account_name}</p>
        <p><strong>Total Voices:</strong> {total_voices}</p>
    </div>
    """.format(
        account_name=account_name,
        total_voices=total_voices,
    ), unsafe_allow_html=True)

# Function to categorize voices
def categorize_voices(voices_data):
    """Organize voices by category for easier selection"""
    categories = {}
    
    for voice in voices_data.get("voices", []):
        # Try to get category from the voice data
        category = voice.get("category", "Other")
        
        # Initialize category if not exists
        if category not in categories:
            categories[category] = []
        
        # Add voice to category
        categories[category].append(voice)
    
    return categories

# Login page - with space theme
def show_login_page():
    """Show the styled login page with space theme"""
    # Apply universal CSS at the beginning of the app
    st.markdown("""
    <style>
    /* Global app styling */
    .stApp {
        font-family: 'Poppins', 'Inter', sans-serif !important;
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e) !important;
        color: #e0e0ff !important;
    }

    /* Custom background - creates a subtle starfield effect */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: 
            radial-gradient(1px 1px at 25% 15%, white, transparent),
            radial-gradient(1px 1px at 50% 35%, rgba(255, 255, 255, 0.8), transparent),
            radial-gradient(1px 1px at 75% 50%, rgba(255, 255, 255, 0.9), transparent),
            radial-gradient(2px 2px at 20% 65%, rgba(255, 255, 255, 0.7), transparent),
            radial-gradient(2px 2px at 40% 80%, rgba(255, 255, 255, 0.8), transparent),
            radial-gradient(1px 1px at 60% 25%, rgba(255, 255, 255, 0.9), transparent),
            radial-gradient(1px 1px at 85% 85%, rgba(255, 255, 255, 0.8), transparent);
        background-repeat: repeat;
        background-size: 250px 250px;
        opacity: 0.15;
        z-index: -1;
        pointer-events: none;
    }

    /* Main content container */
    .block-container {
        background-color: rgba(30, 30, 60, 0.7) !important;
        border-radius: 16px !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        border: 1px solid rgba(123, 97, 255, 0.2) !important;
        padding: 2rem !important;
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
    }

    /* Title styling */
    h1, h2, h3, h4, h5, h6 {
        color: #aa80ff !important;
        font-weight: 600 !important;
        text-shadow: 0 0 10px rgba(170, 128, 255, 0.5) !important;
        letter-spacing: 0.02em !important;
    }

    .login-title {
        font-size: 2.2rem !important;
        font-weight: 600 !important;
        text-align: center !important;
        margin-bottom: 1.5rem !important;
        color: #aa80ff !important;
        text-shadow: 0 0 15px rgba(170, 128, 255, 0.6) !important;
    }

    /* Logo styling */
    .logo-container {
        text-align: center !important;
        margin-bottom: 2rem !important;
        filter: drop-shadow(0 0 8px rgba(170, 128, 255, 0.7)) !important;
    }

    /* Input field styling - space-themed */
    .stTextInput input,
    [data-baseweb="input"] input,
    .css-1n76uvr input,
    input[type="text"],
    input[type="password"] {
        border-radius: 8px !important;
        padding: 12px 16px !important;
        background-color: rgba(30, 30, 70, 0.6) !important;
        border: 1px solid rgba(123, 97, 255, 0.4) !important;
        color: #e0e0ff !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 0 5px rgba(123, 97, 255, 0.1) inset !important;
    }

    /* Focus states */
    .stTextInput [data-baseweb="input"]:focus-within,
    .stTextInput div[data-focused="true"],
    [data-baseweb="input"]:focus-within {
        border-color: #aa80ff !important;
        box-shadow: 0 0 8px rgba(170, 128, 255, 0.6) !important;
    }

    /* Cosmic button styling */
    .stButton > button,
    button[kind="primaryFormSubmit"],
    [data-testid="stFormSubmitButton"] > button,
    form [data-testid="stFormSubmitButton"] button {
        width: 100% !important;
        background: linear-gradient(135deg, #8e2de2, #4a00e0) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 0 !important;
        font-weight: 500 !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        margin-top: 10px !important;
        margin-bottom: 10px !important;
        display: block !important;
        text-align: center !important;
        box-shadow: 0 4px 15px rgba(138, 43, 226, 0.4) !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        font-size: 0.9rem !important;
    }

    /* Hover styles for buttons */
    .stButton > button:hover,
    button[kind="primaryFormSubmit"]:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(138, 43, 226, 0.6) !important;
        background: linear-gradient(135deg, #9b4dff, #4a00e0) !important;
    }

    /* Error and success messages - space-themed */
    .stAlert {
        border-radius: 8px !important;
        margin-top: 1.5rem !important;
        padding: 1rem !important;
        border: none !important;
        box-shadow: 0 0 15px rgba(0, 0, 0, 0.2) !important;
        background-color: rgba(40, 40, 80, 0.7) !important;
        backdrop-filter: blur(4px) !important;
        -webkit-backdrop-filter: blur(4px) !important;
    }

    /* Footer styling */
    .footer {
        text-align: center !important;
        margin-top: 3rem !important;
        font-size: 0.9rem !important;
        color: rgba(224, 224, 255, 0.7) !important;
        padding-bottom: 2rem !important;
    }
    
    /* Theme note styling */
    .theme-note {
        text-align: center !important;
        margin-top: 1.2rem !important;
        font-size: 0.85rem !important;
        color: rgba(224, 224, 255, 0.7) !important;
        background-color: rgba(30, 30, 70, 0.6) !important;
        border-radius: 6px !important;
        padding: 8px 12px !important;
        border-left: 3px solid #8e2de2 !important;
    }

    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}

    /* Center the login form */
    .centered-content {
        margin-top: 10vh !important;
        padding: 2.5rem !important;
        background-color: rgba(30, 30, 60, 0.7) !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
        max-width: 400px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        border: 1px solid rgba(123, 97, 255, 0.2) !important;
    }

    /* Add a subtle cosmic pulse animation to the login button */
    form [data-testid="stFormSubmitButton"] button {
        animation: cosmicPulse 4s infinite alternate !important;
    }

    @keyframes cosmicPulse {
        0% {
            box-shadow: 0 4px 15px rgba(138, 43, 226, 0.4);
        }
        100% {
            box-shadow: 0 4px 25px rgba(138, 43, 226, 0.7);
        }
    }

    /* Logo color modification to match the space theme */
    .logo-container svg circle,
    .logo-container svg path {
        stroke: #aa80ff !important;
    }

    .logo-container svg path[fill="#1E88E5"] {
        fill: #8e2de2 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize users
    if "users" not in st.session_state:
        st.session_state.users = init_authentication()
    
    # Create a more compact centered layout
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col2:
        st.markdown('<div class="centered-content">', unsafe_allow_html=True)
        
        # Logo (you can replace with an actual logo)
        st.markdown('''
        <div class="logo-container">
            <svg width="70" height="70" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" stroke="#aa80ff" stroke-width="2"/>
                <path d="M8 12C8 10.8954 8.89543 10 10 10H14C15.1046 10 16 10.8954 16 12V16C16 17.1046 15.1046 18 14 18H10C8.89543 18 8 17.1046 8 16V12Z" fill="#8e2de2"/>
                <path d="M10 7L14 7" stroke="#aa80ff" stroke-width="2" stroke-linecap="round"/>
                <path d="M12 10V7" stroke="#aa80ff" stroke-width="2" stroke-linecap="round"/>
            </svg>
        </div>
        ''', unsafe_allow_html=True)
        
        # Title
        st.markdown('<h1 class="login-title">Tasty Voice Generator</h1>', unsafe_allow_html=True)

        # Use a form for Enter key functionality with styled button
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            submit_button = st.form_submit_button("Sign in", use_container_width=True)
            
            if submit_button:
                if login_user(username, password, st.session_state.users):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.is_admin = st.session_state.users[username]["is_admin"]
                    st.success("Login successful! Redirecting...")
                    time.sleep(1)  # Short delay for better UX
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        # Add the dark theme note
        st.markdown('<div class="theme-note">💡 This app looks best in dark theme!</div>', unsafe_allow_html=True)
        
        # Footer
        st.markdown('<div class="footer">© 2025 Tasty Voice Generator</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)  # Close the centered content

def show_admin_panel():
    """Show the admin panel for user management"""
    st.title("Admin Control Panel")
    
    # Additional CSS for admin panel
    st.markdown("""
    <style>
    /* Admin panel specific styles */
    .admin-header {
        color: #aa80ff !important;
        margin-bottom: 1.5rem !important;
        text-shadow: 0 0 10px rgba(170, 128, 255, 0.5) !important;
    }
    
    /* Table styling - space themed */
    .stTable {
        background-color: rgba(30, 30, 70, 0.6) !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }

    .stTable th {
        background-color: rgba(60, 50, 100, 0.7) !important;
        color: #d4c0ff !important;
        padding: 1rem !important;
        text-align: left !important;
        font-weight: 500 !important;
    }

    .stTable td {
        background-color: rgba(40, 40, 80, 0.5) !important;
        color: #e0e0ff !important;
        padding: 0.75rem 1rem !important;
        border-bottom: 1px solid rgba(123, 97, 255, 0.2) !important;
    }
    
    /* Form spacing */
    form {
        margin-bottom: 2rem !important;
    }
    
    /* Checkbox styling */
    .stCheckbox [data-baseweb="checkbox"] {
        margin-bottom: 1rem !important;
    }

    .stCheckbox [data-baseweb="checkbox"] div[data-testid="stMarkdownContainer"] p {
        font-size: 1rem !important;
        color: #d4c0ff !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Go back to main app
    if st.button("Return to Voice Generator"):
        st.session_state.show_admin = False
        st.rerun()
    
    st.header("Create New User")
    with st.form("create_user_form"):
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        is_admin = st.checkbox("Is Admin")
        create_button = st.form_submit_button("CREATE USER")
        
        if create_button:
            if new_password != confirm_password:
                st.error("Passwords do not match")
            elif not new_username or not new_password:
                st.error("Username and password are required")
            else:
                success, message = create_user(
                    new_username, new_password, is_admin, st.session_state.users
                )
                if success:
                    st.success(message)
                else:
                    st.error(message)
    
    # Show existing users
    st.header("Existing Users")
    users_df = []
    for username, user in st.session_state.users.items():
        users_df.append({
            "Username": username,
            "Admin": "Yes" if user["is_admin"] else "No",
            "Created": time.strftime("%Y-%m-%d", time.localtime(user["created_at"]))
        })
    
    st.table(users_df)
    
    # Delete user section
    st.header("Delete User")
    
    # Exclude current user from the deletion options
    delete_options = [username for username in st.session_state.users.keys() 
                      if username != st.session_state.username]
    
    if not delete_options:
        st.info("No other users to delete.")
    else:
        with st.form("delete_user_form"):
            user_to_delete = st.selectbox("Select User to Delete", options=delete_options)
            delete_button = st.form_submit_button("DELETE USER")
            
            if delete_button:
                success, message = delete_user(
                    user_to_delete, st.session_state.users, st.session_state.username
                )
                if success:
                    st.success(message)
                    
                    # Clean up any user-specific data in session state
                    user_gen_key = f"recent_generations_{user_to_delete}"
                    if user_gen_key in st.session_state:
                        del st.session_state[user_gen_key]
                    
                    # Refresh the page after successful deletion
                    st.rerun()
                else:
                    st.error(message)

# Function to generate voice
def generate_voice(api_key, voice_id, text, model_id, voice_settings):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    data = {
        "text": text,
        "model_id": model_id,
        "voice_settings": voice_settings
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        st.error(f"Error generating voice: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            st.error(f"API response: {e.response.text}")
        return None

# Function to convert voice
def convert_voice(api_key, voice_id, audio_data, model_id, voice_settings):
    url = f"https://api.elevenlabs.io/v1/speech-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "xi-api-key": api_key
    }
    
    # Handle different audio formats
    content_type = "audio/mpeg"
    if isinstance(audio_data, bytes):
        # Try to detect the content type based on first few bytes
        if audio_data.startswith(b'RIFF'):
            content_type = "audio/wav"
        elif audio_data.startswith(b'ID3') or audio_data.startswith(b'\xff\xfb'):
            content_type = "audio/mpeg"
        
    files = {
        "audio": ("input_audio", audio_data, content_type)
    }
    
    data = {
        "model_id": model_id,
        "voice_settings": json.dumps(voice_settings)
    }
    
    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        st.error(f"Error converting voice: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            st.error(f"API response: {e.response.text}")
        return None

# Function to create download link with enhanced styling
def get_audio_download_link(audio_data, filename="generated_voice.mp3"):
    b64 = base64.b64encode(audio_data).decode()
    href = f'<a href="data:audio/mpeg;base64,{b64}" download="{filename}">DOWNLOAD GENERATED AUDIO</a>'
    return href

# Main function to run the Streamlit app
def main():
    # Set page config
    st.set_page_config(
        page_title="Tasty Voice Generator",
        page_icon="🌌",
        layout="wide"
    )
    
    # Apply global app CSS with space theme
    st.markdown("""
    <style>
    /* Global app styling */
    .stApp {
        font-family: 'Poppins', 'Inter', sans-serif !important;
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e) !important;
        color: #e0e0ff !important;
    }

    /* Custom background - creates a subtle starfield effect */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: 
            radial-gradient(1px 1px at 25% 15%, white, transparent),
            radial-gradient(1px 1px at 50% 35%, rgba(255, 255, 255, 0.8), transparent),
            radial-gradient(1px 1px at 75% 50%, rgba(255, 255, 255, 0.9), transparent),
            radial-gradient(2px 2px at 20% 65%, rgba(255, 255, 255, 0.7), transparent),
            radial-gradient(2px 2px at 40% 80%, rgba(255, 255, 255, 0.8), transparent),
            radial-gradient(1px 1px at 60% 25%, rgba(255, 255, 255, 0.9), transparent),
            radial-gradient(1px 1px at 85% 85%, rgba(255, 255, 255, 0.8), transparent);
        background-repeat: repeat;
        background-size: 250px 250px;
        opacity: 0.15;
        z-index: -1;
        pointer-events: none;
    }

    /* Main content container */
    .block-container {
        background-color: rgba(30, 30, 60, 0.7) !important;
        border-radius: 16px !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        border: 1px solid rgba(123, 97, 255, 0.2) !important;
        padding: 2rem !important;
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
    }

    /* Title styling */
    h1, h2, h3, h4, h5, h6 {
        color: #aa80ff !important;
        font-weight: 600 !important;
        text-shadow: 0 0 10px rgba(170, 128, 255, 0.5) !important;
        letter-spacing: 0.02em !important;
    }

    /* Input field styling - space-themed */
    .stTextInput input,
    [data-baseweb="input"] input,
    .css-1n76uvr input,
    input[type="text"],
    input[type="password"] {
        border-radius: 8px !important;
        padding: 12px 16px !important;
        background-color: rgba(30, 30, 70, 0.6) !important;
        border: 1px solid rgba(123, 97, 255, 0.4) !important;
        color: #e0e0ff !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 0 5px rgba(123, 97, 255, 0.1) inset !important;
    }

    /* Focus states */
    .stTextInput [data-baseweb="input"]:focus-within,
    .stTextInput div[data-focused="true"],
    [data-baseweb="input"]:focus-within {
        border-color: #aa80ff !important;
        box-shadow: 0 0 8px rgba(170, 128, 255, 0.6) !important;
    }

    /* Cosmic button styling */
    .stButton > button,
    button[kind="primaryFormSubmit"],
    [data-testid="stFormSubmitButton"] > button,
    form [data-testid="stFormSubmitButton"] button {
        width: 100% !important;
        background: linear-gradient(135deg, #8e2de2, #4a00e0) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 0 !important;
        font-weight: 500 !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        margin-top: 10px !important;
        margin-bottom: 10px !important;
        display: block !important;
        text-align: center !important;
        box-shadow: 0 4px 15px rgba(138, 43, 226, 0.4) !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        font-size: 0.9rem !important;
    }

    /* Hover styles for buttons */
    .stButton > button:hover,
    button[kind="primaryFormSubmit"]:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(138, 43, 226, 0.6) !important;
        background: linear-gradient(135deg, #9b4dff, #4a00e0) !important;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 500 !important;
        color: #d4c0ff !important;
        background-color: rgba(60, 50, 100, 0.6) !important;
        border-radius: 8px !important;
        padding: 0.75rem 1rem !important;
        border-left: 3px solid #8e2de2 !important;
    }

    /* Slider styling */
    .stSlider > div[data-baseweb="slider"] {
        margin-top: 2rem !important;
        margin-bottom: 2rem !important;
    }

    .stSlider [data-testid="stThumbValue"] {
        background-color: #8e2de2 !important;
        color: white !important;
    }

    .stSlider [data-testid="stThumbValue"]::before {
        border-bottom-color: #8e2de2 !important;
    }

    /* Style the track of the slider */
    .stSlider [role="slider"] {
        background-color: #aa80ff !important;
        box-shadow: 0 0 8px rgba(170, 128, 255, 0.8) !important;
    }

    /* Sidebar styling - space-themed */
    .css-1d391kg, .css-1lcbmhc {
        background: linear-gradient(180deg, #302b63, #24243e) !important;
        border-right: 1px solid rgba(123, 97, 255, 0.2) !important;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        border-bottom: 1px solid rgba(123, 97, 255, 0.3);
        background-color: rgba(40, 40, 80, 0.6) !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 0 16px !important;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 8px 8px 0 0;
        gap: 1px;
        padding: 10px 16px;
        font-weight: 500;
        color: #aa80ff;
        border: none;
        transition: all 0.3s ease;
    }

    .stTabs [aria-selected="true"] {
        background-color: rgba(123, 97, 255, 0.2) !important;
        color: #d4c0ff !important;
        box-shadow: 0 -2px 8px rgba(123, 97, 255, 0.3) !important;
    }

    /* Cards for recent generations */
    .stExpander {
        background-color: rgba(40, 40, 80, 0.6) !important;
        border-radius: 8px !important;
        border: 1px solid rgba(123, 97, 255, 0.3) !important;
        margin-bottom: 1rem !important;
        transition: all 0.3s ease !important;
        backdrop-filter: blur(4px) !important;
        -webkit-backdrop-filter: blur(4px) !important;
    }

    .stExpander:hover {
        box-shadow: 0 0 15px rgba(123, 97, 255, 0.3) !important;
        border: 1px solid rgba(123, 97, 255, 0.5) !important;
    }

    /* Audio player styling */
    audio {
        width: 100% !important;
        margin-top: 15px !important;
        margin-bottom: 15px !important;
        border-radius: 8px !important;
        background-color: rgba(40, 40, 80, 0.6) !important;
        box-shadow: 0 0 10px rgba(123, 97, 255, 0.2) !important;
    }

    /* Custom audio player controls */
    audio::-webkit-media-controls-panel {
        background-color: rgba(30, 30, 70, 0.8) !important;
    }

    audio::-webkit-media-controls-current-time-display,
    audio::-webkit-media-controls-time-remaining-display {
        color: #d4c0ff !important;
    }

    /* Download link styling */
    a[download] {
        display: inline-block !important;
        background: linear-gradient(135deg, #8e2de2, #4a00e0) !important;
        color: white !important;
        padding: 8px 16px !important;
        text-decoration: none !important;
        border-radius: 8px !important;
        margin-top: 10px !important;
        margin-bottom: 10px !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 10px rgba(123, 97, 255, 0.4) !important;
        text-transform: uppercase !important;
        font-size: 0.8rem !important;
        letter-spacing: 1px !important;
    }

    a[download]:hover {
        background: linear-gradient(135deg, #9b4dff, #4a00e0) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 15px rgba(123, 97, 255, 0.6) !important;
    }

    /* Error and success messages - space-themed */
    .stAlert {
        border-radius: 8px !important;
        margin-top: 1.5rem !important;
        padding: 1rem !important;
        border: none !important;
        box-shadow: 0 0 15px rgba(0, 0, 0, 0.2) !important;
        background-color: rgba(40, 40, 80, 0.7) !important;
        backdrop-filter: blur(4px) !important;
        -webkit-backdrop-filter: blur(4px) !important;
    }

    /* Text area styling */
    .stTextArea textarea {
        border-radius: 8px !important;
        border: 1px solid rgba(123, 97, 255, 0.4) !important;
        background-color: rgba(30, 30, 70, 0.6) !important;
        padding: 12px 16px !important;
        min-height: 120px !important;
        transition: all 0.3s ease !important;
        color: #e0e0ff !important;
        box-shadow: 0 0 5px rgba(123, 97, 255, 0.1) inset !important;
    }

    .stTextArea textarea:focus {
        border-color: #aa80ff !important;
        box-shadow: 0 0 8px rgba(170, 128, 255, 0.6) !important;
    }

    /* File uploader styling */
    .stFileUploader div[data-testid="stFileUploader"] {
        padding: 1.5rem !important;
        border: 2px dashed rgba(123, 97, 255, 0.4) !important;
        border-radius: 8px !important;
        background-color: rgba(30, 30, 70, 0.4) !important;
        transition: all 0.3s ease !important;
    }

    .stFileUploader div[data-testid="stFileUploader"]:hover {
        border-color: #aa80ff !important;
        box-shadow: 0 0 15px rgba(123, 97, 255, 0.3) inset !important;
    }

    /* Select box styling */
    .stSelectbox > div[data-baseweb="select"] > div {
        background-color: rgba(30, 30, 70, 0.6) !important;
        border: 1px solid rgba(123, 97, 255, 0.4) !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
        color: #e0e0ff !important;
    }

    .stSelectbox > div[data-baseweb="select"] > div:hover {
        border-color: #aa80ff !important;
    }

    /* Dropdown menu items */
    div[role="listbox"] {
        background-color: rgba(30, 30, 70, 0.95) !important;
        border: 1px solid rgba(123, 97, 255, 0.4) !important;
        border-radius: 8px !important;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
    }

    div[role="option"] {
        color: #e0e0ff !important;
    }

    div[role="option"]:hover {
        background-color: rgba(123, 97, 255, 0.2) !important;
    }

    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}

    /* Cosmic glow effect for the app title */
    .stApp h1:first-child {
        position: relative;
        display: inline-block;
    }

    .stApp h1:first-child::after {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 100%;
        height: 100%;
        transform: translate(-50%, -50%);
        z-index: -1;
        filter: blur(20px);
        background: radial-gradient(circle, rgba(170, 128, 255, 0.6) 0%, rgba(138, 43, 226, 0) 70%);
    }

    /* Label coloring */
    label {
        color: #d4c0ff !important;
        font-weight: 500 !important;
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(30, 30, 70, 0.3);
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #8e2de2, #4a00e0);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #9b4dff, #4a00e0);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Check if user is logged in
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        show_login_page()
        return
    
    # Session state variables
    if "show_admin" not in st.session_state:
        st.session_state.show_admin = False
    
    # Show admin panel if requested (and user is admin)
    if st.session_state.show_admin and st.session_state.is_admin:
        show_admin_panel()
        return
    
    # Define model options
    # Separate models for TTS and voice conversion
    tts_model_options = {
        "Multilingual v2 (Enhanced)": "eleven_multilingual_v2",
        "Monolingual v1 (English only)": "eleven_monolingual_v1",
        "Multilingual v1 (Multiple languages)": "eleven_multilingual_v1",
        "Turbo (Faster generation)": "eleven_turbo_v2"
    }
    
    voice_conversion_model_options = {
        "Multilingual Voice Conversion": "eleven_multilingual_sts_v2",
        "English Conversion Model": "eleven_english_sts_v2"
    }
    
    # Store both model selections in session state
    if "tts_model" not in st.session_state:
        st.session_state.tts_model = list(tts_model_options.keys())[0]
    
    if "vc_model" not in st.session_state:
        st.session_state.vc_model = list(voice_conversion_model_options.keys())[0]
    
    # Get available ElevenLabs accounts
    elevenlabs_accounts = get_elevenlabs_accounts()
    
    if not elevenlabs_accounts:
        st.error("No ElevenLabs accounts configured. Please set up at least one account.")
        st.stop()
    
    # Get account selection from session state or default to first account
    if "selected_account" not in st.session_state:
        st.session_state.selected_account = list(elevenlabs_accounts.keys())[0]

    # Main app sidebar
    with st.sidebar:
        st.write(f"Logged in as: **{st.session_state.username}**")
        
        if st.session_state.is_admin:
            if st.button("Control Panel"):
                st.session_state.show_admin = True
                st.rerun()
        
        if st.button("Exit"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.is_admin = False
            st.rerun()
            
        st.markdown("---")
        
        # Account selection
        st.header("Account Selection")
        selected_account = st.selectbox(
            "ElevenLabs Account", 
            options=list(elevenlabs_accounts.keys()),
            index=list(elevenlabs_accounts.keys()).index(st.session_state.selected_account)
        )
        
        # Get the selected API key and update session state
        current_api_key = elevenlabs_accounts[selected_account]
        st.session_state.selected_account = selected_account
        
        # Voice settings
        st.header("Voice Settings")
        stability = st.slider("Stability", min_value=0.0, max_value=1.0, value=0.5, step=0.01,
                            help="The voice will sound more consistent among re-generations if stability is increased, but it may also sound a little monotonous.  We advise reducing this value for lengthy text passages.")
        
        similarity_boost = st.slider("Similarity Boost", min_value=0.0, max_value=1.0, value=0.75, step=0.01,
                                    help="High enhancement improves target speaker resemblance and overall voice clarity.  It is advised to change this option to find the ideal value because very high values may result in artifacts.")
        
        # Speed setting
        speed = st.slider("Speed", min_value=0.7, max_value=1.2, value=1.0, step=0.05,
                        help="regulates the generated speech's pace.  Speech will be slower with values below 1.0 and faster with values above 1.0.  Extreme values could have an impact on the resulting speech's quality.")
        
        style_exaggeration = st.slider("Style Exaggeration", min_value=0.0, max_value=1.0, value=0.0, step=0.01,
                                    help="High values are recommended if the style of the speech should be exaggerated compared to the uploaded audio. Higher values can lead to more instability in the generated speech. Setting this to 0.0 will greatly increase generation speed and is the default setting.")
        
        st.markdown("---")
        st.markdown("Made with ❤️ by raffyboi")

    # Get available voices for the selected account
    voices_data = get_voices_for_account(current_api_key)
    
    if not voices_data.get("voices"):
        st.error(f"Could not fetch voices for account '{selected_account}'. Please check if the API key is valid.")
        st.stop()
    
    # Extract all voice options for dropdown
    voice_options = {voice["name"]: voice["voice_id"] for voice in voices_data["voices"]}
    
    # Main app title
    st.title("Tasty Voice Generator")
    
    # Show account information
    show_account_info(selected_account, voices_data)
    
    # Create tabs
    tab1, tab2 = st.tabs(["Text to Voice", "Voice Changer"])
    
    with tab1:
        st.markdown("Generate realistic AI voices based on our models")
        
        # Add TTS model selection to this tab
        st.header("Engine Selection")
        selected_tts_model = st.selectbox(
            "Select Text-to-Speech Engine", 
            options=list(tts_model_options.keys()),
            key="tts_model_select",
            index=list(tts_model_options.keys()).index(st.session_state.tts_model)
        )
        st.session_state.tts_model = selected_tts_model
        selected_tts_model_id = tts_model_options[selected_tts_model]
        
        # Text input area
        st.header("Enter Your Message")
        text_input = st.text_area("Type or paste text here", height=150)

        # Voice selection
        selected_voice_name = st.selectbox("Select Voice", options=list(voice_options.keys()))
        selected_voice_id = voice_options[selected_voice_name]

        # Generate button
        if st.button("GENERATE VOICE", key="generate_tts"):
            if not text_input.strip():
                st.warning("Please enter some text to convert to speech.")
            else:
                with st.spinner("Generating voice..."):
                    # Prepare voice settings with all parameters
                    voice_settings = {
                        "stability": stability,
                        "similarity_boost": similarity_boost,
                        "style": style_exaggeration,
                        "speaker_boost": True,  # Always set to True
                        "speed": speed
                    }
                    
                    audio_data = generate_voice(
                        current_api_key,  # Use the selected account's API key 
                        selected_voice_id, 
                        text_input, 
                        selected_tts_model_id,
                        voice_settings
                    )
                    
                    if audio_data:
                        # Display audio player
                        st.audio(audio_data, format="audio/mp3")
                        
                        # Display download link
                        st.markdown(get_audio_download_link(audio_data), unsafe_allow_html=True)
                        
                        # Create a user-specific key for recent generations
                        user_gen_key = f"recent_generations_{st.session_state.username}"
                        
                        # Save recent generation info to user-specific list
                        if user_gen_key not in st.session_state:
                            st.session_state[user_gen_key] = []
                            
                        st.session_state[user_gen_key].append({
                            "text": text_input[:50] + "..." if len(text_input) > 50 else text_input,
                            "voice": selected_voice_name,
                            "model": selected_tts_model,
                            "audio_data": audio_data,
                            "type": "tts",
                            "account": selected_account
                        })

        # Recent generations section
        st.markdown("---")
        st.header("Recent Generations")

        # Get user-specific generations for TTS
        user_gen_key = f"recent_generations_{st.session_state.username}"

        if user_gen_key in st.session_state and st.session_state[user_gen_key]:
            # Filter to show only TTS generations
            tts_generations = [gen for gen in st.session_state[user_gen_key] if gen.get("type", "tts") == "tts"]
            
            if tts_generations:
                for i, gen in enumerate(reversed(tts_generations[-5:])):  # Show last 5
                    with st.expander(f"{gen['voice']} ({gen.get('model', 'Default Engine')}) - {gen['account']}"):
                        st.audio(gen["audio_data"], format="audio/mp3")
                        st.markdown(get_audio_download_link(gen["audio_data"], f"{gen['voice']}_{i}.mp3"), unsafe_allow_html=True)
            else:
                st.info("Your voice recordings will appear here.")
        else:
            st.info("Your voice recordings will appear here.")

        # Tips for text-to-speech
        with st.expander("Tips for better text-to-speech"):
            st.markdown("""
            - For more natural sounding speech, include punctuation in your text
            - Use commas and periods to control pacing
            - Add question marks for rising intonation
            - Try different stability and similarity boost settings for different effects
            - Higher stability makes the voice more consistent but less expressive
            - Higher similarity boost makes the voice sound more like the original sample
            - Adjust speed to make speech faster or slower
            - Use style exaggeration to emphasize the unique characteristics of the voice
            """)

    with tab2:
        st.markdown("Transform your voice into another voice")
        
        # Add Voice Conversion model selection to this tab
        st.header("Engine Selection")
        selected_vc_model = st.selectbox(
            "Select Voice Conversion Engine", 
            options=list(voice_conversion_model_options.keys()),
            key="vc_model_select",
            index=list(voice_conversion_model_options.keys()).index(st.session_state.vc_model)
        )
        st.session_state.vc_model = selected_vc_model
        selected_vc_model_id = voice_conversion_model_options[selected_vc_model]
        
        # Upload audio
        st.header("Upload Audio")
        uploaded_file = st.file_uploader("Upload an audio file (MP3, WAV, M4A)", type=["mp3", "wav", "m4a"])
        
        # Target voice selection
        st.header("Select Target Voice")
        target_voice_name = st.selectbox("Voice to transform into", options=list(voice_options.keys()), key="target_voice")
        target_voice_id = voice_options[target_voice_name]
        
        # Convert button
        if st.button("Convert Voice", key="convert_voice"):
            if uploaded_file is None:
                st.warning("Please upload an audio file to transform.")
            else:
                with st.spinner("Converting voice..."):
                    # Read the uploaded file
                    audio_bytes = uploaded_file.read()
                    
                    # Display original audio
                    st.subheader("Original Voice")
                    st.audio(audio_bytes, format=f"audio/{uploaded_file.type.split('/')[1]}")
                    
                    # Prepare voice settings with all parameters
                    voice_settings = {
                        "stability": stability,
                        "similarity_boost": similarity_boost,
                        "style": style_exaggeration,
                        "speaker_boost": True,  # Always set to True
                        "speed": speed
                    }
                    
                    # Convert voice using the specific voice conversion model
                    converted_audio = convert_voice(
                        current_api_key,  # Use the selected account's API key
                        target_voice_id,
                        audio_bytes,
                        selected_vc_model_id,
                        voice_settings
                    )
                    
                    if converted_audio:
                        # Display converted audio
                        st.subheader("Converted Audio")
                        st.audio(converted_audio, format="audio/mp3")
                        
                        # Display download link
                        st.markdown(get_audio_download_link(converted_audio, f"{target_voice_name}.mp3"), unsafe_allow_html=True)
                        
                        # Create a user-specific key for recent conversions
                        user_gen_key = f"recent_generations_{st.session_state.username}"
                        
                        # Save recent conversion info to user-specific list
                        if user_gen_key not in st.session_state:
                            st.session_state[user_gen_key] = []
                            
                        st.session_state[user_gen_key].append({
                            "text": f"Transformation to {target_voice_name}",
                            "voice": target_voice_name,
                            "model": selected_vc_model,
                            "audio_data": converted_audio,
                            "type": "voice_conversion",
                            "account": selected_account
                        })
        
        # Recent conversions section
        st.markdown("---")
        st.header("Recent Generations")
        
        # Get user-specific generations for voice conversions
        user_gen_key = f"recent_generations_{st.session_state.username}"
        
        if user_gen_key in st.session_state and st.session_state[user_gen_key]:
            # Filter to show only voice conversion generations
            voice_conversions = [gen for gen in st.session_state[user_gen_key] if gen.get("type") == "voice_conversion"]
            
            if voice_conversions:
                for i, gen in enumerate(reversed(voice_conversions[-5:])):  # Show last 5
                    with st.expander(f"Transformation to {gen['voice']} ({gen.get('model', 'Default Engine')}) - {gen['account']}"):
                        st.audio(gen["audio_data"], format="audio/mp3")
                        st.markdown(get_audio_download_link(gen["audio_data"], f"{gen['voice']}_{i}.mp3"), unsafe_allow_html=True)
            else:
                st.info("Your voice recordings will appear here.")
        else:
            st.info("Your voice recordings will appear here.")
        
        # Tips for voice conversion
        with st.expander("Tips for better voice conversion"):
            st.markdown("""
            - For best results, use high-quality audio recordings with clear speech
            - Keep the audio under 30 seconds for faster processing
            - Avoid background noise in your input audio
            - Try different voices to find the best match for your voice type
            - Adjust stability and similarity boost settings for different effects
            - Use a consistent speaking pace for more natural-sounding conversions
            - When recording your voice, speak clearly and at a consistent volume
            - For professional results, record in a quiet environment with minimal echo
            """)

if __name__ == "__main__":
    main()
