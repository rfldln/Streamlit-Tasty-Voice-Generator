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

# Login page - clean light theme styling to match screenshot
def show_login_page():
    """Show a clean light-themed login page styled to match the provided screenshot"""
    # Apply minimal styling for light theme
    st.markdown("""
    <style>
        /* Clean container styling */
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #f0f0f0;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            background: white;
            margin-top: 50px;
        }
        
        /* Logo styling */
        .logo-container {
            text-align: center;
            margin-bottom: 20px;
        }
        
        /* Title styling */
        .login-title {
            font-size: 1.7rem;
            font-weight: 500;
            text-align: center;
            margin-bottom: 30px;
            color: #2196F3;
        }
        
        /* Input field labels */
        .stTextInput > label {
            font-weight: 500;
            margin-bottom: 5px;
            color: #333;
        }
        
        /* Button styling for light theme */
        [data-testid="stFormSubmitButton"] button {
            background-color: #2196F3 !important;
            color: white !important;
            border: none !important;
            border-radius: 4px !important;
            padding: 10px 0 !important;
            font-weight: 500 !important;
            width: 100% !important;
            margin-top: 10px !important;
        }
        
        /* Footer styling */
        .footer {
            text-align: center;
            margin-top: 40px;
            font-size: 0.8rem;
            color: #757575;
        }
        
        /* Hide default streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize users
    if "users" not in st.session_state:
        st.session_state.users = init_authentication()
    
    # Use full width with appropriate margins
    st.markdown('<div style="max-width: 450px; margin: 0 auto;">', unsafe_allow_html=True)
    
    # Create a login container div
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # Logo - using bottle icon to match the screenshot
    st.markdown('''
    <div class="logo-container">
        <svg width="50" height="50" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="12" fill="#2196F3"/>
            <path d="M8 8.5C8 7.67157 8.67157 7 9.5 7H14.5C15.3284 7 16 7.67157 16 8.5V15.5C16 16.3284 15.3284 17 14.5 17H9.5C8.67157 17 8 16.3284 8 15.5V8.5Z" fill="white"/>
            <path d="M12 7V5" stroke="white" stroke-width="2" stroke-linecap="round"/>
            <path d="M10 5H14" stroke="white" stroke-width="2" stroke-linecap="round"/>
        </svg>
    </div>
    ''', unsafe_allow_html=True)
    
    # Title
    st.markdown('<h1 class="login-title">Tasty Voice Generator</h1>', unsafe_allow_html=True)

    # Use a form for Enter key functionality with styled button
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        # Custom CSS for the submit button using HTML
        st.markdown("""
        <style>
        /* Additional specific styling for THIS form's submit button */
        [data-testid="stFormSubmitButton"] button {
            background-color: #2196F3 !important;
            color: white !important;
            border: none !important;
            border-radius: 4px !important;
            padding: 10px 0 !important;
            font-weight: 500 !important;
            width: 100% !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        submit_button = st.form_submit_button("Sign In", use_container_width=True)
        
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
    
    # Close the login container and the centered div
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown('<div class="footer">© 2025 Tasty Voice Generator</div>', unsafe_allow_html=True)

def show_admin_panel():
    """Show the admin panel for user management"""
    st.title("Admin Panel - User Management")
    
    # Additional CSS for admin panel
    st.markdown("""
    <style>
        /* Admin panel specific styles */
        .admin-header {
            color: #1E88E5 !important;
            margin-bottom: 1rem !important;
        }
        
        /* Table styling */
        .stTable {
            border-collapse: collapse !important;
        }
        
        .stTable th {
            background-color: #f5f5f5 !important;
            font-weight: 600 !important;
        }
        
        .stTable td, .stTable th {
            padding: 8px 12px !important;
            border: 1px solid #e0e0e0 !important;
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
                    
                    # Refresh the page after successful deletion
                    st.rerun()
                else:
                    st.error(message)

# Main function to run the Streamlit app
def main():
    # Set page config
    st.set_page_config(
        page_title="Tasty Voice Generator",
        page_icon="🔊",
        layout="wide"
    )
    
    # Apply global app CSS
    st.markdown("""
    <style>
        /* Global app styling */
        .stApp {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        }
        
        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            color: #1E88E5 !important;
            font-weight: 600 !important;
        }
        
        /* Form elements */
        .stSlider > div[data-baseweb="slider"] {
            margin-top: 10px !important;
            margin-bottom: 10px !important;
        }
        
        .stSelectbox > div[data-baseweb="select"] {
            cursor: pointer !important;
        }
        
        /* Audio player styling */
        audio {
            width: 100% !important;
            margin-top: 10px !important;
            margin-bottom: 10px !important;
        }
        
        /* Download link styling */
        a[download] {
            display: inline-block !important;
            background-color: #4CAF50 !important;
            color: white !important;
            padding: 8px 16px !important;
            text-decoration: none !important;
            border-radius: 4px !important;
            margin-top: 10px !important;
            margin-bottom: 10px !important;
            font-weight: 500 !important;
            transition: background-color 0.3s !important;
        }
        
        a[download]:hover {
            background-color: #3e8e41 !important;
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            font-weight: 500 !important;
            color: #424242 !important;
        }
        
        /* Sidebar styling */
        .css-1d391kg, .css-1lcbmhc {
            background-color: #f5f5f5 !important;
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
    
    # Main app logic starts here
    # Adding a sidebar for user management
    with st.sidebar:
        st.write(f"Logged in as: **{st.session_state.username}**")
        
        if st.session_state.is_admin:
            if st.button("User Management"):
                st.session_state.show_admin = True
                st.rerun()
        
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.is_admin = False
            st.rerun()
            
        st.markdown("---")
        
        st.header("Model Selection")
        model_options = {
            "Multilingual v2 (Enhanced)": "eleven_multilingual_v2",
            "Monolingual v1 (English only)": "eleven_monolingual_v1",
            "Multilingual v1 (Multiple languages)": "eleven_multilingual_v1",
            "Turbo (Faster generation)": "eleven_turbo_v2"
        }
        selected_model = st.selectbox(
            "Select Model", 
            options=list(model_options.keys())
        )
        selected_model_id = model_options[selected_model]
        
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

    # Function to get available voices
    @st.cache_data(ttl=3600)  # Cache for one hour
    def get_voices(api_key):
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {
            "Accept": "application/json",
            "xi-api-key": api_key
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching voices: {str(e)}")
            return {"voices": []}

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

    # Function to create download link with enhanced styling
    def get_audio_download_link(audio_data, filename="generated_voice.mp3"):
        b64 = base64.b64encode(audio_data).decode()
        href = f'<a href="data:audio/mpeg;base64,{b64}" download="{filename}">Download MP3</a>'
        return href

    # Check if API key is valid
    if not api_key:
        st.error("API key not found. Please set the ELEVENLABS_API_KEY in your environment variables or .env file.")
        st.stop()

    # Get available voices
    voices_data = get_voices(api_key)
    if not voices_data.get("voices"):
        st.error("Could not fetch voices. Please check if the API key is valid.")
        st.stop()

    # Extract voice options for dropdown
    voice_options = {voice["name"]: voice["voice_id"] for voice in voices_data["voices"]}

    # App title and description
    st.title("Tasty Voice Generator")
    st.markdown("Generate realistic AI voices of our models")

    # Text input area
    st.header("Enter Text to Convert")
    text_input = st.text_area("Type or paste text here", height=150)

    # Voice selection
    selected_voice_name = st.selectbox("Select Voice", options=list(voice_options.keys()))
    selected_voice_id = voice_options[selected_voice_name]

    # Generate button
    if st.button("Generate Voice"):
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
                    api_key, 
                    selected_voice_id, 
                    text_input, 
                    selected_model_id,
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
                        "model": selected_model,
                        "audio_data": audio_data
                    })

    # Recent generations section
    st.markdown("---")
    st.header("Recent Generations")

    # Get user-specific generations
    user_gen_key = f"recent_generations_{st.session_state.username}"

    if user_gen_key in st.session_state and st.session_state[user_gen_key]:
        for i, gen in enumerate(reversed(st.session_state[user_gen_key][-5:])):  # Show last 5
            with st.expander(f"{gen['voice']} ({gen.get('model', 'Default Model')}): {gen['text']}"):
                st.audio(gen["audio_data"], format="audio/mp3")
                st.markdown(get_audio_download_link(gen["audio_data"], f"{gen['voice']}_{i}.mp3"), unsafe_allow_html=True)
    else:
        st.info("Your recent voice generations will appear here.")

    # Add some additional tips
    with st.expander("Tips for better voice generation"):
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

if __name__ == "__main__":
    main()
