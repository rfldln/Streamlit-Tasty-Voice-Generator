# Tasty Voice Generator

A Streamlit app that uses ElevenLabs API to generate realistic AI voices.

## Features

- Realistic AI voice generation
- Multiple voice models
- Customizable voice settings (stability, similarity boost, speed, style)
- User authentication system
- Admin panel for user management
- Recent generations history

## Setup & Deployment

### Local Development

1. Clone this repository
2. cd to the repository
3. Create a venv and activate it
   ```bash
   python -m venv venv
   venv/Scripts/activate
   ```
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6. Create a `.env` file with your ElevenLabs API key:
   ```
   ELEVENLABS_API_KEY=your_api_key_here
   ADMIN_PASSWORD=your_admin_password
   ```
7. Run the app:
   ```bash
   streamlit run app.py
   ```

### Streamlit Cloud Deployment

1. Fork/push this repository to your GitHub account
2. Go to [Streamlit Community Cloud](https://share.streamlit.io/)
3. Sign in with GitHub
4. Deploy a new app, selecting this repository
5. Add the following secrets in the Streamlit Cloud deployment settings:
   - `ELEVENLABS_API_KEY`: Your ElevenLabs API key
   - `ADMIN_PASSWORD`: Password for the admin account

## Usage

1. Log in using the default credentials:
   - Username: `admin`
   - Password: Value of `ADMIN_PASSWORD` environment variable (default: `admin123`)
2. Use the admin panel to create additional users if needed
3. Enter text, select a voice and customize settings
4. Click "Generate Voice" to create and play the AI voice

## Note

This app uses Streamlit's session state for user management in the cloud deployment. User data will reset when the Streamlit instance restarts, so this is intended for demonstration purposes. For a production environment, consider implementing a proper database backend.

## Credits

Created by raffyboi
