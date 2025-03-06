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
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: #f0f2f6;
            border-radius: 4px 4px 0 0;
            gap: 1px;
            padding-top: 10px;
            padding-bottom: 10px;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #1E88E5 !important;
            color: white !important;
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
    
    # Function to convert voice
    def convert_voice(api_key, voice_id, audio_data, model_id):
        url = f"https://api.elevenlabs.io/v1/speech-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "xi-api-key": api_key
        }
        
        files = {
            "audio": ("input.mp3", audio_data, "audio/mpeg")
        }
        
        data = {
            "model_id": model_id,
            "voice_settings": json.dumps({
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style_exaggeration,
                "speaker_boost": True,
                "speed": speed
            })
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

    # App title
    st.title("Tasty Voice Generator")
    
    # Create tabs
    tab1, tab2 = st.tabs(["Text to Speech", "Voice Changer"])
    
    with tab1:
        st.markdown("Generate realistic AI voices from text")
        
        # Text input area
        st.header("Enter Text to Convert")
        text_input = st.text_area("Type or paste text here", height=150)

        # Voice selection
        selected_voice_name = st.selectbox("Select Voice", options=list(voice_options.keys()))
        selected_voice_id = voice_options[selected_voice_name]

        # Generate button
        if st.button("Generate Voice", key="generate_tts"):
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
                            "audio_data": audio_data,
                            "type": "tts"
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
                    with st.expander(f"{gen['voice']} ({gen.get('model', 'Default Model')}): {gen['text']}"):
                        st.audio(gen["audio_data"], format="audio/mp3")
                        st.markdown(get_audio_download_link(gen["audio_data"], f"{gen['voice']}_{i}.mp3"), unsafe_allow_html=True)
            else:
                st.info("Your recent text-to-speech generations will appear here.")
        else:
            st.info("Your recent voice generations will appear here.")

    with tab2:
        st.markdown("Transform your voice into another voice")
        
        # Upload audio
        st.header("Upload Audio")
        uploaded_file = st.file_uploader("Upload an audio file (MP3, WAV, M4A)", type=["mp3", "wav", "m4a"])
        
        # Target voice selection
        st.header("Select Target Voice")
        target_voice_name = st.selectbox("Voice to convert to", options=list(voice_options.keys()), key="target_voice")
        target_voice_id = voice_options[target_voice_name]
        
        # Convert button
        if st.button("Convert Voice", key="convert_voice"):
            if uploaded_file is None:
                st.warning("Please upload an audio file to convert.")
            else:
                with st.spinner("Converting voice..."):
                    # Read the uploaded file
                    audio_bytes = uploaded_file.read()
                    
                    # Display original audio
                    st.subheader("Original Audio")
                    st.audio(audio_bytes, format=f"audio/{uploaded_file.type.split('/')[1]}")
                    
                    # Convert voice
                    converted_audio = convert_voice(
                        api_key,
                        target_voice_id,
                        audio_bytes,
                        selected_model_id
                    )
                    
                    if converted_audio:
                        # Display converted audio
                        st.subheader("Converted Audio")
                        st.audio(converted_audio, format="audio/mp3")
                        
                        # Display download link
                        st.markdown(get_audio_download_link(converted_audio, f"converted_{target_voice_name}.mp3"), unsafe_allow_html=True)
                        
                        # Create a user-specific key for recent conversions
                        user_gen_key = f"recent_generations_{st.session_state.username}"
                        
                        # Save recent conversion info to user-specific list
                        if user_gen_key not in st.session_state:
                            st.session_state[user_gen_key] = []
                            
                        st.session_state[user_gen_key].append({
                            "text": f"Conversion to {target_voice_name}",
                            "voice": target_voice_name,
                            "model": selected_model,
                            "audio_data": converted_audio,
                            "type": "voice_conversion"
                        })
        
        # Recent conversions section
        st.markdown("---")
        st.header("Recent Conversions")
        
        # Get user-specific generations for voice conversions
        user_gen_key = f"recent_generations_{st.session_state.username}"
        
        if user_gen_key in st.session_state and st.session_state[user_gen_key]:
            # Filter to show only voice conversion generations
            voice_conversions = [gen for gen in st.session_state[user_gen_key] if gen.get("type") == "voice_conversion"]
            
            if voice_conversions:
                for i, gen in enumerate(reversed(voice_conversions[-5:])):  # Show last 5
                    with st.expander(f"Conversion to {gen['voice']} ({gen.get('model', 'Default Model')})"):
                        st.audio(gen["audio_data"], format="audio/mp3")
                        st.markdown(get_audio_download_link(gen["audio_data"], f"conversion_{gen['voice']}_{i}.mp3"), unsafe_allow_html=True)
            else:
                st.info("Your recent voice conversions will appear here.")
        else:
            st.info("Your recent voice conversions will appear here.")
        
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
