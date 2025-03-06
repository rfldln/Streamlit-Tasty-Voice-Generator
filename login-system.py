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

# API key handling for both local and cloud
api_key = os.environ.get("ELEVENLABS_API_KEY")
# Only use dotenv in local development if available
try:
    from dotenv import load_dotenv
    if Path(".env").exists():
        load_dotenv()
        api_key = os.environ.get("ELEVENLABS_API_KEY")
except ImportError:
    pass

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

# Define modern color scheme
COLOR_PRIMARY = "#FF5722"       # Deep Orange - primary brand color
COLOR_SECONDARY = "#2196F3"     # Blue - secondary accent
COLOR_BACKGROUND = "#121212"    # Dark background
COLOR_CARD = "#1E1E1E"          # Slightly lighter card background
COLOR_TEXT = "#FFFFFF"          # White text for dark theme
COLOR_TEXT_SECONDARY = "#B0BEC5" # Lighter text for secondary elements
COLOR_SUCCESS = "#4CAF50"       # Green for success
COLOR_WARNING = "#FFC107"       # Amber for warnings
COLOR_ERROR = "#F44336"         # Red for errors
COLOR_GRAY = "#78909C"          # Blue-gray for neutral elements

# Login page with modern design
def show_login_page():
    """Show a beautifully styled login page"""
    
    # Apply global CSS
    st.markdown(f"""
    <style>
        /* Reset and base styles */
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        /* Dark theme overrides for Streamlit */
        .stApp {{
            background-color: {COLOR_BACKGROUND};
            color: {COLOR_TEXT};
        }}
        
        /* Login form styling */
        .login-container {{
            max-width: 400px;
            margin: 80px auto 0 auto;
            padding: 30px;
            background-color: {COLOR_CARD};
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
            animation: fadeIn 0.6s ease-out;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .login-header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        
        .app-logo {{
            width: 80px;
            height: 80px;
            margin: 0 auto 20px auto;
            display: block;
        }}
        
        .app-title {{
            font-size: 28px;
            font-weight: 700;
            color: {COLOR_PRIMARY};
            margin: 0;
            letter-spacing: 0.5px;
        }}
        
        .app-subtitle {{
            font-size: 14px;
            color: {COLOR_TEXT_SECONDARY};
            margin-top: 8px;
        }}
        
        /* Input fields styling */
        .stTextInput input, 
        [data-baseweb="input"] input, 
        div[data-testid="stTextInput"] input {{
            background-color: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            color: {COLOR_TEXT} !important;
            font-size: 16px !important;
            padding: 12px 16px !important;
            height: 48px !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
        }}
        
        .stTextInput input:focus, 
        [data-baseweb="input"] input:focus,
        div[data-testid="stTextInput"] input:focus {{
            border-color: {COLOR_PRIMARY} !important;
            box-shadow: 0 0 0 2px rgba(255, 87, 34, 0.2) !important;
            background-color: rgba(255, 255, 255, 0.07) !important;
        }}
        
        .stTextInput label, 
        [data-baseweb="input"] label,
        div[data-testid="stTextInput"] label {{
            color: {COLOR_TEXT} !important;
            font-weight: 500 !important;
            font-size: 14px !important;
        }}
        
        /* Submit button styling */
        .stButton > button,
        button[kind="primaryFormSubmit"],
        [data-testid="stFormSubmitButton"] > button {{
            background: linear-gradient(90deg, {COLOR_PRIMARY}, #FF8A65) !important;
            color: white !important;
            font-weight: 600 !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 20px !important;
            height: 48px !important;
            width: 100% !important;
            font-size: 16px !important;
            letter-spacing: 0.5px !important;
            cursor: pointer !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 12px rgba(255, 87, 34, 0.3) !important;
            margin-top: 10px !important;
            text-transform: uppercase !important;
        }}
        
        .stButton > button:hover,
        button[kind="primaryFormSubmit"]:hover,
        [data-testid="stFormSubmitButton"] > button:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 16px rgba(255, 87, 34, 0.4) !important;
        }}
        
        /* Footer styling */
        .app-footer {{
            text-align: center;
            font-size: 12px;
            color: {COLOR_TEXT_SECONDARY};
            margin-top: 30px;
        }}
        
        /* Hide Streamlit default elements */
        #MainMenu, header, footer {{display: none !important;}}
        div[data-testid="stDecoration"] {{display: none !important;}}
        
        /* Animations */
        @keyframes pulse {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.05); }}
            100% {{ transform: scale(1); }}
        }}
        
        .stButton > button:active,
        button[kind="primaryFormSubmit"]:active,
        [data-testid="stFormSubmitButton"] > button:active {{
            animation: pulse 0.3s ease-in-out;
        }}
        
        /* Message styling */
        div[data-testid="stAlert"] {{
            background-color: rgba(0, 0, 0, 0.2) !important;
            border-left: 4px solid {COLOR_PRIMARY} !important;
            color: {COLOR_TEXT} !important;
            border-radius: 8px !important;
            padding: 15px !important;
            margin: 20px 0 !important;
            display: flex !important;
            align-items: center !important;
        }}
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize users
    if "users" not in st.session_state:
        st.session_state.users = init_authentication()
    
    # Create centered login container
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # Logo and app title
    st.markdown(f'''
    <div class="login-header">
        <svg class="app-logo" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <circle cx="50" cy="50" r="45" fill="#1E1E1E" stroke="{COLOR_PRIMARY}" stroke-width="2"/>
            <path d="M32 50 A 18 18 0 0 1 68 50" stroke="{COLOR_SECONDARY}" stroke-width="3" fill="none"/>
            <circle cx="40" cy="45" r="5" fill="{COLOR_PRIMARY}"/>
            <circle cx="60" cy="45" r="5" fill="{COLOR_PRIMARY}"/>
            <path d="M40 65 Q 50 75 60 65" stroke="{COLOR_TEXT}" stroke-width="3" fill="none"/>
        </svg>
        <h1 class="app-title">Tasty Voice Generator</h1>
        <p class="app-subtitle">Create stunning AI voices with ease</p>
    </div>
    ''', unsafe_allow_html=True)
    
    # Login form
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        submit_button = st.form_submit_button("Sign In")
        
        if submit_button:
            if login_user(username, password, st.session_state.users):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.is_admin = st.session_state.users[username]["is_admin"]
                st.success("Login successful! Redirecting...")
                time.sleep(0.7)  # Short delay for better UX
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    # Footer
    st.markdown('<div class="app-footer">© 2025 Tasty Voice Generator | Privacy Policy | Terms of Service</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # Close login container

# Admin panel with modern design
def show_admin_panel():
    """Show the admin panel with enhanced styling"""
    
    # Admin panel specific CSS
    st.markdown(f"""
    <style>
        /* Admin panel specific styling */
        .admin-container {{
            background-color: {COLOR_CARD};
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        }}
        
        .admin-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 15px;
        }}
        
        .admin-title {{
            font-size: 24px;
            font-weight: 700;
            color: {COLOR_PRIMARY};
            margin: 0;
            padding: 0;
        }}
        
        /* Section styling */
        .admin-section {{
            margin-bottom: 40px;
        }}
        
        .section-title {{
            font-size: 18px;
            font-weight: 600;
            color: {COLOR_SECONDARY};
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        /* Table styling */
        .stTable {{
            width: 100%;
        }}
        
        .stTable th {{
            background-color: rgba(255, 255, 255, 0.05) !important;
            color: {COLOR_TEXT} !important;
            font-weight: 600 !important;
            text-align: left !important;
            padding: 15px !important;
        }}
        
        .stTable td {{
            border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
            padding: 15px !important;
            color: {COLOR_TEXT} !important;
        }}
        
        /* Back button */
        .back-button {{
            background-color: rgba(255, 255, 255, 0.1) !important;
            color: {COLOR_TEXT} !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 8px 16px !important;
            font-size: 14px !important;
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
            cursor: pointer !important;
            transition: all 0.2s !important;
        }}
        
        .back-button:hover {{
            background-color: rgba(255, 255, 255, 0.15) !important;
        }}
        
        /* Form styling */
        .stForm {{
            background-color: rgba(255, 255, 255, 0.03);
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        
        /* Checkbox styling */
        [data-testid="stCheckbox"] label {{
            color: {COLOR_TEXT} !important;
        }}
    </style>
    """, unsafe_allow_html=True)
    
    # Admin panel header
    st.markdown(f"""
    <div class="admin-header">
        <h1 class="admin-title">Admin Dashboard</h1>
        <button class="back-button" id="back-button">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M19 12H5M5 12L12 19M5 12L12 5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Return to App
        </button>
    </div>
    """, unsafe_allow_html=True)
    
    # JavaScript for back button
    st.markdown("""
    <script>
        document.getElementById('back-button').addEventListener('click', function() {
            // We'll handle this with Streamlit's button below
        });
    </script>
    """, unsafe_allow_html=True)
    
    # Actual back button (hidden but functional)
    if st.button("Return to Voice Generator", key="back_button"):
        st.session_state.show_admin = False
        st.rerun()
    
    # Create new user section
    st.markdown('<div class="admin-section">', unsafe_allow_html=True)
    st.markdown('<h2 class="section-title">Create New User</h2>', unsafe_allow_html=True)
    
    with st.form("create_user_form"):
        new_username = st.text_input("Username", placeholder="Enter username")
        new_password = st.text_input("Password", type="password", placeholder="Enter password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm password")
        is_admin = st.checkbox("Grant Admin Privileges")
        create_button = st.form_submit_button("Create User")
        
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
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close admin section
    
    # Existing users section
    st.markdown('<div class="admin-section">', unsafe_allow_html=True)
    st.markdown('<h2 class="section-title">User Management</h2>', unsafe_allow_html=True)
    
    # Show existing users
    users_df = []
    for username, user in st.session_state.users.items():
        users_df.append({
            "Username": username,
            "Admin": "Yes" if user["is_admin"] else "No",
            "Created": time.strftime("%Y-%m-%d", time.localtime(user["created_at"]))
        })
    
    st.table(users_df)
    
    # Delete user section
    delete_options = [username for username in st.session_state.users.keys() 
                     if username != st.session_state.username]
    
    if not delete_options:
        st.info("No other users to delete.")
    else:
        with st.form("delete_user_form"):
            user_to_delete = st.selectbox("Select User to Delete", options=delete_options)
            st.warning("This action cannot be undone.")
            delete_button = st.form_submit_button("Delete User")
            
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
                    
                    # Refresh after deletion
                    st.rerun()
                else:
                    st.error(message)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close admin section

# Main function with modern UI
def main():
    # Set page config
    st.set_page_config(
        page_title="Tasty Voice Generator",
        page_icon="🔊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Global app CSS - dark modern theme
    st.markdown(f"""
    <style>
        /* Global theme settings */
        :root {{
            --font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        
        /* Modern dark theme */
        .stApp {{
            background-color: {COLOR_BACKGROUND};
            color: {COLOR_TEXT};
            font-family: var(--font-family);
        }}
        
        /* Typography */
        h1, h2, h3, h4, h5, h6 {{
            font-family: var(--font-family);
            color: {COLOR_TEXT} !important;
            font-weight: 600 !important;
        }}
        
        h1 {{
            font-size: 32px !important;
            margin-bottom: 20px !important;
            background: linear-gradient(90deg, {COLOR_PRIMARY}, {COLOR_SECONDARY});
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            display: inline-block !important;
        }}
        
        h2 {{
            font-size: 24px !important;
            margin-top: 30px !important;
            margin-bottom: 15px !important;
        }}
        
        h3 {{
            font-size: 20px !important;
            color: {COLOR_SECONDARY} !important;
            margin-top: 25px !important;
            margin-bottom: 10px !important;
        }}
        
        p, div, span {{
            font-family: var(--font-family);
        }}
        
        /* Sidebar */
        [data-testid="stSidebar"] {{
            background-color: {COLOR_CARD};
            border-right: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 2rem;
        }}
        
        [data-testid="stSidebarNav"] {{
            background-color: {COLOR_CARD};
        }}
        
        [data-testid="stSidebarNav"] span {{
            color: {COLOR_TEXT};
        }}
        
        /* Sidebar title */
        .sidebar-title {{
            font-size: 18px;
            font-weight: 600;
            color: {COLOR_PRIMARY};
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        /* User info */
        .user-info {{
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            padding: 15px;
            background-color: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
        }}
        
        .user-avatar {{
            width: 40px;
            height: 40px;
            border-radius: 20px;
            background-color: {COLOR_PRIMARY};
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            margin-right: 12px;
        }}
        
        .user-name {{
            font-weight: 500;
            font-size: 16px;
        }}
        
        .user-role {{
            font-size: 12px;
            color: {COLOR_TEXT_SECONDARY};
        }}
        
        /* Sidebar divider */
        .sidebar-divider {{
            height: 1px;
            background-color: rgba(255, 255, 255, 0.1);
            margin: 20px 0;
        }}
        
        /* Card styling */
        .app-card {{
            background-color: {COLOR_CARD};
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        /* Button styling */
        .stButton > button {{
            background-color: {COLOR_PRIMARY} !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 20px !important;
            font-size: 16px !important;
            font-weight: 500 !important;
            cursor: pointer !important;
            transition: all 0.2s !important;
            box-shadow: 0 2px 8px rgba(255, 87, 34, 0.3) !important;
        }}
        
        .stButton > button:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(255, 87, 34, 0.4) !important;
        }}
        
        /* Slider styling */
        [data-testid="stSlider"] {{
            padding: 10px 0 !important;
        }}
        
        [data-testid="stSlider"] > div > div {{
            background-color: rgba(255, 255, 255, 0.1) !important;
        }}
        
        [data-testid="stSlider"] > div > div > div {{
            background-color: {COLOR_PRIMARY} !important;
        }}
        
        [data-testid="stSlider"] > div > div > div > div {{
            background-color: {COLOR_PRIMARY} !important;
            border-color: {COLOR_PRIMARY} !important;
            box-shadow: 0 0 0 6px rgba(255, 87, 34, 0.2) !important;
        }}
        
        /* Text area */
        [data-testid="stTextArea"] textarea {{
            background-color: rgba(255, 255, 255, 0.05) !important;
            color: {COLOR_TEXT} !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            padding: 15px !important;
            font-size: 16px !important;
            font-family: var(--font-family) !important;
        }}
        
        [data-testid="stTextArea"] textarea:focus {{
            border-color: {COLOR_PRIMARY} !important;
            box-shadow: 0 0 0 2px rgba(255, 87, 34, 0.2) !important;
        }}
        
        /* Radio buttons */
        .stRadio > div {{
            margin-bottom: 12px !important;
        }}
        
        /* Select box */
        [data-baseweb="select"] {{
            background-color: rgba(255, 255, 255, 0.05) !important;
            border-radius: 8px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            color: {COLOR_TEXT} !important;
        }}
        
        [data-baseweb="select"]:focus-within {{
            border-color: {COLOR_PRIMARY} !important;
            box-shadow: 0 0 0 2px rgba(255, 87, 34, 0.2) !important;
        }}
        
        [data-baseweb="select"] div {{
            background-color: transparent !important;
        }}
        
        /* Pills in select */
        [data-baseweb="tag"] {{
            background-color: {COLOR_PRIMARY} !important;
            color: white !important;
            border-radius: 4px !important;
        }}
        
        /* Audio player */
        audio {{
            width: 100% !important;
            border-radius: 8px !important;
            background-color: rgba(255, 255, 255, 0.05) !important;
            margin: 15px 0 !important;
        }}
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            background-color: transparent !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
            gap: 8px !important;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background-color: transparent !important;
            color: {COLOR_TEXT} !important;
            border-radius: 8px 8px 0 0 !important;
            padding: 12px 24px !important;
            font-weight: 500 !important;
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: rgba(255, 87, 34, 0.1) !important;
            color: {COLOR_PRIMARY} !important;
            border-bottom: 2px solid {COLOR_PRIMARY} !important;
        }}
        
        /* File uploader */
        [data-testid="stFileUploader"] {{
            background-color: rgba(255, 255, 255, 0.05) !important;
            border: 2px dashed rgba(255, 255, 255, 0.1) !important;
            border-radius: 12px !important;
            padding: 20px !important;
            text-align: center !important;
            margin-bottom: 20px !important;
            transition: all 0.3s ease !important;
        }}
        
        [data-testid="stFileUploader"]:hover {{
            border-color: {COLOR_PRIMARY} !important;
            background-color: rgba(255, 87, 34, 0.05) !important;
        }}
        
        [data-testid="stFileUploader"] button {{
            background-color: {COLOR_PRIMARY} !important;
            color: white !important;
        }}
        
        /* Expander */
        .streamlit-expanderHeader {{
            background-color: rgba(255, 255, 255, 0.03) !important;
            border-radius: 8px !important;
            padding: 15px !important;
            font-weight: 500 !important;
            color: {COLOR_TEXT} !important;
            font-size: 16px !important;
            margin-bottom: 10px !important;
        }}
        
        /* Success/Info/Warning/Error banners */
        [data-testid="stSuccessMessage"] {{
            background-color: rgba(76, 175, 80, 0.1) !important;
            color: #81C784 !important;
            border: none !important;
            border-left: 4px solid #4CAF50 !important;
            border-radius: 4px !important;
            padding: 15px 20px !important;
        }}
        
        [data-testid="stInfoMessage"] {{
            background-color: rgba(33, 150, 243, 0.1) !important;
            color: #64B5F6 !important;
            border: none !important;
            border-left: 4px solid #2196F3 !important;
            border-radius: 4px !important;
            padding: 15px 20px !important;
        }}
        
        [data-testid="stWarningMessage"] {{
            background-color: rgba(255, 152, 0, 0.1) !important;
            color: #FFB74D !important;
            border: none !important;
            border-left: 4px solid #FF9800 !important;
            border-radius: 4px !important;
            padding: 15px 20px !important;
        }}
        
        [data-testid="stErrorMessage"] {{
            background-color: rgba(244, 67, 54, 0.1) !important;
            color: #E57373 !important;
            border: none !important;
            border-left: 4px solid #F44336 !important;
            border-radius: 4px !important;
            padding: 15px 20px !important;
        }}
        
        /* Spinner */
        [data-testid="stSpinner"] {{
            color: {COLOR_PRIMARY} !important;
        }}
        
        /* Download link */
        a[download] {{
            display: inline-block !important;
            background-color: {COLOR_SUCCESS} !important;
            color: white !important;
            text-decoration: none !important;
            padding: 10px 20px !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            margin-top: 10px !important;
            transition: all 0.2s !important;
            box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3) !important;
        }}
        
        a[download]:hover {{
            background-color: #3B9D3B !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4) !important;
        }}
        
        /* Hide default Streamlit elements */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        
        /* Animations for elements */
        .animated-card {{
            animation: cardFadeIn 0.5s ease-out;
        }}
        
        @keyframes cardFadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: rgba(255, 255, 255, 0.05);
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: rgba(255, 255, 255, 0.2);
        }}
        
        /* Helper classes */
        .text-center {{
            text-align: center !important;
        }}
        
        .mt-0 {{ margin-top: 0 !important; }}
        .mt-1 {{ margin-top: 0.25rem !important; }}
        .mt-2 {{ margin-top: 0.5rem !important; }}
        .mt-3 {{ margin-top: 1rem !important; }}
        .mt-4 {{ margin-top: 1.5rem !important; }}
        .mt-5 {{ margin-top: 2rem !important; }}
        
        .mb-0 {{ margin-bottom: 0 !important; }}
        .mb-1 {{ margin-bottom: 0.25rem !important; }}
        .mb-2 {{ margin-bottom: 0.5rem !important; }}
        .mb-3 {{ margin-bottom: 1rem !important; }}
        .mb-4 {{ margin-bottom: 1.5rem !important; }}
        .mb-5 {{ margin-bottom: 2rem !important; }}
