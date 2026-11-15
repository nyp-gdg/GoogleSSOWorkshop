# Sign In with Google with Python Flask - Workshop Template

This is the official hands-on starter code for the **Google Developer Groups on Campus (GDGoC) NYP** workshop.

---

## 🚀 Quick Setup (Using `pip`)

### 1. Prerequisites
- Python 3.10 or newer (`python3 --version`)
- A **personal Google Account** (`@gmail.com`). *(School Workspace accounts often restrict Google Cloud project creation).*

### 2. Set Up Virtual Environment & Dependencies
```bash
# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows (Command Prompt / PowerShell):
# .venv\Scripts\activate

# Install dependencies using pip
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in your credentials from [Google Cloud Console](https://console.cloud.google.com):
```env
FLASK_SECRET_KEY=any-random-secret-key-for-session-signing
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-client-secret
GOOGLE_DISCOVERY=https://accounts.google.com/.well-known/openid-configuration
```

### 4. Run the Flask App
```bash
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser!

---

## 📂 Project Structure

```
google-sso-workshop/
├── app.py              # Main Flask application with Auth routes
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .gitignore
├── templates/
│   ├── index.html      # Login and user profile dashboard
│   ├── demos.html      # Interactive showcase of all workshop demo endpoints
│   └── tasks.html      # Google Tasks API viewer
└── static/
    └── style.css       # Clean Google Developer brand styling
```

---

## 🛠️ Workshop Roadmap

- **Act 1: Authentication Concepts**  
  Explore headers, cookies, and tokens. Test `/demo/basic-auth`, `/demo/session-login`, and `/demo/bearer-auth`.
- **Act 2: Sign In with Google**  
  Authenticate via OAuth 2.0 / OpenID Connect, verify the Google ID token, and decode user identity claims.
- **Act 3: OAuth 2.0 & Google Tasks**  
  Request user authorization for `tasks.readonly`, obtain an Access Token, and call Google Tasks API to read task lists.
