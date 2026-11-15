# Sign In with Google with Python Flask

**GDGoC NYP workshop · Saturday, 21 November 2026 · Online via Google Meet**

Notes for anyone who gets lost, falls behind, or wants to redo the session later. Everything here matches the live workshop progression and template app.

- Starter repo: `/home/azlancoding/GitHub/google-sso-workshop`  
- Questions after the session: ping us on Discord or reply to the workshop email

---

## Workshop Agenda

- [Part 4 — Environment Setup](#part-4--environment-setup)
- [Part 5 — Explain Basic Auth](#part-5--explain-basic-auth)
- [Part 6 — Demo Basic Auth](#part-6--demo-basic-auth)
- [Part 7 — Explain Stateful Session Auth](#part-7--explain-stateful-session-auth)
- [Part 8 — Demo Stateful Session Auth](#part-8--demo-stateful-session-auth)
- [Part 9 — Explain Stateless JWT Auth](#part-9--explain-stateless-jwt-auth)
- [Part 10 — Demo Stateless JWT Auth](#part-10--demo-stateless-jwt-auth)
- [Part 11 — Short Break!](#part-11--short-break)
- [Part 12 — Google Cloud Console Setup & `.env`](#part-12--google-cloud-console-setup--env)
- [Part 13 — Trying Out the Google Tasks App](#part-13--trying-out-the-google-tasks-app)
- [Part 14 — How Does Everything Work? (OpenID Connect & OAuth 2.0)](#part-14--how-does-everything-work-openid-connect--oauth-20)
- [Part 15 — Google One Tap Sign-In Demo](#part-15--google-one-tap-sign-in-demo)
- [Part 16 — Explain Google One Tap Sign-In](#part-16--explain-google-one-tap-sign-in)
- [Appendix: Troubleshooting & Security Checklist](#appendix-troubleshooting--security-checklist)

---

## Part 4 — Environment Setup

> **Note**: For this initial phase, we only set up Flask and local dependencies. Leave Google Cloud credentials untouched for now — we will configure them after the break in Part 12!

### 4.1 Prerequisites
- Python 3.10 or newer (`python3 --version`)
- Standard `pip` and `venv`
- A **personal Google Account** (`@gmail.com`).

### 4.2 Clone & Set Up Virtual Environment

```sh
cd /home/azlancoding/GitHub/google-sso-workshop

# 1. Create virtual environment
python3 -m venv .venv

# 2. Activate virtual environment
# Linux / macOS:
source .venv/bin/activate
# Windows (Command Prompt):
# .venv\Scripts\activate.bat
# Windows (PowerShell):
# .venv\Scripts\Activate.ps1

# 3. Install core dependencies
pip install -r requirements.txt
```

`requirements.txt`:
```
Flask>=3.0.0
Authlib>=1.3.0
requests>=2.31.0
python-dotenv>=1.0.0
google-auth>=2.28.0
google-auth-oauthlib>=1.2.0
google-api-python-client>=2.120.0
```

### 4.3 Minimal Initial `.env` (Flask Only)

Copy `.env.example` to `.env`:

```sh
cp .env.example .env
```

At this stage, only `FLASK_SECRET_KEY` needs to be set (leave `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` as placeholders for now):

```ini
FLASK_SECRET_KEY=change-this-to-any-random-secret-key-12345
GOOGLE_CLIENT_ID=leave-blank-until-part-12
GOOGLE_CLIENT_SECRET=leave-blank-until-part-12
GOOGLE_DISCOVERY=https://accounts.google.com/.well-known/openid-configuration
```

### 4.4 Run the Development Server

```sh
python app.py
```

Open your browser to:
- **Home**: [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **Demo Showcase**: [http://127.0.0.1:5000/demos](http://127.0.0.1:5000/demos)

---

## Part 5 — Explain Basic Auth

### 5.1 HTTP Has No Memory
HTTP is fundamentally stateless: every request is independent. To know who is making a request, the client must present proof of identity.

### 5.2 What is Basic Auth?
In **HTTP Basic Authentication**, the client sends the raw username and password on **every single request** inside the `Authorization` header:

```http
GET /demo/basic-auth HTTP/1.1
Host: 127.0.0.1:5000
Authorization: Basic c29maWE6c2VjcmV0
```

- Format: `Authorization: Basic base64(username:password)`
- For `sofia:secret`, `btoa("sofia:secret")` produces `c29maWE6c2VjcmV0`.

### 5.3 Critical Limitations of Basic Auth
1. **Encoded, NOT Encrypted**: Base64 is trivial to decode (`atob("c29maWE6c2VjcmV0")` &rarr; `sofia:secret`). Anyone inspecting traffic or logs sees the raw credentials.
2. **Sent on Every Request**: Your actual password traverses the network repeatedly with every single click or fetch.
3. **No Revocation / Expiration**: There is no server-side invalidation. Browsers aggressively cache credentials for the realm until the browser window is closed.

---

## Part 6 — Demo Basic Auth

Navigate to [http://127.0.0.1:5000/demos](http://127.0.0.1:5000/demos) &rarr; **1. Basic Auth**.

### 6.1 Server Implementation (`app.py`)

```py
@app.route("/demo/basic-auth")
def demo_basic_auth():
    auth = request.authorization
    if not auth or auth.username != "sofia" or auth.password != "secret":
        headers = {}
        if request.args.get("prompt") == "1":
            headers["WWW-Authenticate"] = 'Basic realm="Login Required"'
        return jsonify({
            "status": "unauthenticated",
            "error": "Could not verify your access. Login with sofia:secret."
        }), 401, headers

    return jsonify({
        "status": "authenticated",
        "method": "Basic Auth",
        "user": auth.username,
        "note": "Credentials were sent in plain Base64 in Authorization header on this request."
    })
```

### 6.2 Try It Out:
1. Keep the default `sofia` and `secret` in the form and click **Send with Credentials**.
   - Result: `HTTP 200 - OK` with user `"sofia"`.
2. Change the password to `wrongpassword` and click **Send with Credentials**.
   - Result: `HTTP 401 - UNAUTHORIZED`.

---

## Part 7 — Explain Session Auth

### 7.1 Why Sessions?
Instead of sending your password on every request, send your credentials **once** to log in. In return, the server gives you an opaque session reference ticket stored in a browser **Cookie**.

### 7.2 How Stateful Sessions Work
```
1. Client POSTs credentials -> /login
2. Server validates credentials
3. Server generates an unguessable Session ID: "9a2f7e..."
4. Server saves state: DEMO_SESSIONS["9a2f7e..."] = { user: "student" }
5. Server sends response with header: Set-Cookie: demo_session_id=9a2f7e...; HttpOnly
6. Subsequent requests automatically attach: Cookie: demo_session_id=9a2f7e...
7. Server looks up "9a2f7e..." in its memory/database table
```

> **Disclaimer (Simplified Workshop Session Auth):**  
> In this workshop, the server maintains an **in-memory dictionary** (`DEMO_SESSIONS = {}`) to clearly demonstrate stateful sessions. In production systems, sessions are typically stored in persistent databases or shared caches like Redis.

### 7.3 The Stateful Tradeoff (Server Reboot Impact)
Because the session table lives in server memory:
- **Server Reboot / Crash**: If the Flask server process restarts, the in-memory session table is wiped clean.
- When the client makes a request with their existing cookie, the server cannot find that session ID in memory and rejects it with `HTTP 401`.
- Scaling across multiple servers requires distributed session synchronization (e.g., Redis).

---

## Part 8 — Demo Session Auth

Navigate to [http://127.0.0.1:5000/demos](http://127.0.0.1:5000/demos) &rarr; **2. Stateful Session Auth**.

### 8.1 Server Implementation (`app.py`)

```py
# In-memory session store (wiped on server reboot)
DEMO_SESSIONS = {}

@app.route("/demo/session-login", methods=["POST"])
def demo_session_login():
    username = request.form.get("username", "student")
    session_id = secrets.token_hex(16)
    DEMO_SESSIONS[session_id] = {
        "user": username,
        "created_at": int(time.time()),
    }
    resp = jsonify({
        "status": "session_created",
        "session_id": session_id,
        "user": username,
        "active_sessions_count": len(DEMO_SESSIONS),
        "note": "State is stored in DEMO_SESSIONS server memory. If the server reboots, this memory is wiped!"
    })
    resp.set_cookie("demo_session_id", session_id, httponly=True, samesite="Lax")
    return resp

@app.route("/demo/session-profile")
def demo_session_profile():
    session_id = request.cookies.get("demo_session_id")
    if not session_id or session_id not in DEMO_SESSIONS:
        return jsonify({
            "status": "unauthenticated",
            "message": "Session ID not found in server memory (server rebooted or session expired).",
            "active_sessions_in_memory": len(DEMO_SESSIONS)
        }), 401

    session_data = DEMO_SESSIONS[session_id]
    return jsonify({
        "status": "authenticated",
        "method": "Stateful Session Auth",
        "user": session_data["user"],
        "session_id": session_id,
        "created_at": session_data["created_at"],
        "note": "Browser sent opaque cookie demo_session_id, which server resolved against in-memory DEMO_SESSIONS table."
    })

@app.route("/demo/session-reset", methods=["POST"])
def demo_session_reset():
    session_id = request.cookies.get("demo_session_id")
    if session_id:
        DEMO_SESSIONS.pop(session_id, None)
    resp = jsonify({"status": "reset", "message": "Session invalidated from server-side memory."})
    resp.delete_cookie("demo_session_id")
    return resp
```

### 8.2 Try It Out:
1. Click **1. Set Session Cookie**:
   - The server creates an entry in `DEMO_SESSIONS` and returns `demo_session_id` in `Set-Cookie`.
2. Click **2. Check Session Profile**:
   - The browser sends the cookie; server returns `HTTP 200 - OK` with your stored user profile!
3. **Test Server Reboot**:
   - In your terminal, stop Flask (`Ctrl + C`) and restart it (`python app.py`).
   - Click **2. Check Session Profile** again.
   - Result: `HTTP 401 - UNAUTHORIZED`! The server's memory was cleared, showing why stateful in-memory sessions are bound to server lifecycle.
4. Click **Reset / Invalidate Session** to clear the session on demand.

---

## Part 9 — Explain JWT Auth

### 9.1 The Need for Statelessness
What if you have dozens of microservices or mobile clients and don't want every single API call checking a shared database/session table? Enter **Stateless Bearer Tokens (JWT)**.

### 9.2 Anatomy of a JSON Web Token (JWT)
A JWT consists of 3 Base64URL-encoded parts separated by dots (`.`):
$$\text{Header} . \text{Payload} . \text{Signature}$$

1. **Header**: Algorithm and token type (`{"alg": "HS256", "typ": "JWT"}`).
2. **Payload**: User identity & claims (`{"sub": "alex", "exp": 1794762500, "iss": "gdgoc"}`).
3. **Signature**: Cryptographic HMAC-SHA256 signature calculated using a secret key:
   $$\text{HMACSHA256}(\text{base64UrlEncode}(\text{Header}) + "." + \text{base64UrlEncode}(\text{Payload}), \text{SECRET})$$

### 9.3 Why Stateless Bearer Auth Wins for APIs
- **Zero DB Lookups**: Any backend server that knows the secret key can verify the signature and trust the payload instantly.
- **Self-Contained Expiry**: The `exp` claim guarantees automatic expiration.
- **Works Everywhere**: Ideal for SPAs, mobile applications, and cross-domain APIs.

---

## Part 10 — Demo JWT Auth

Navigate to [http://127.0.0.1:5000/demos](http://127.0.0.1:5000/demos) &rarr; **3. Stateless Bearer Auth**.

### 10.1 Server Implementation (`app.py`)

```py
# Step 1: Issue Token
@app.route("/demo/bearer-token", methods=["POST"])
def demo_bearer_create_token():
    username = request.form.get("username", "student")
    expires_in = int(request.form.get("expires_in", 3600))
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": username,
        "iss": "gdgoc-nyp-workshop",
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in,
    }
    token = jwt.encode(header, payload, JWT_SECRET).decode("utf-8")
    return jsonify({
        "status": "token_issued",
        "token": token,
        "payload": payload,
        "note": "A stateless signed JSON Web Token (JWT) created and returned to client."
    })

# Step 2: Verify Token
@app.route("/demo/bearer-auth")
def demo_bearer_auth():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({
            "status": "unauthenticated",
            "error": "Missing or invalid Bearer token in Authorization header."
        }), 401
    
    token = auth_header.split(" ")[1].strip()
    try:
        claims = jwt.decode(token, JWT_SECRET)
        claims.validate()
        return jsonify({
            "status": "authenticated",
            "method": "Stateless Bearer Auth",
            "user": claims.get("sub"),
            "claims": dict(claims),
            "note": "Token verified statelessly with HMAC signature check & exp claim validation."
        })
    except Exception as e:
        return jsonify({
            "status": "unauthenticated",
            "error": f"Invalid or expired token: {str(e)}"
        }), 401
```

### 10.2 Try It Out:
1. Enter your name in the username field and click **1. Create Token (POST)**.
   - The server encodes a signed JWT and populates the Bearer Token box.
2. Click **2. Verify Token (GET)**:
   - The token is sent in `Authorization: Bearer <token>`.
   - Result: `HTTP 200 - OK` with verified payload claims!
3. **Test Tamper Detection**:
   - Change a single letter inside the token input box and click **2. Verify Token (GET)**.
   - Result: `HTTP 401 - Invalid or expired token: Bad signature`!
4. Click **Send Without Token**:
   - Result: `HTTP 401 - Missing or invalid Bearer token`.

---

## Part 11 — Short Break!

Grab some water, stretch your legs, and get ready for Google Cloud Console setup! (10 Minutes) ☕

---

## Part 12 — Google Cloud Console Setup & `.env`

Now we connect our Flask application to real Google Identity & API infrastructure!

### 12.1 Create Project in Google Cloud Console
1. Go to [https://console.cloud.google.com](https://console.cloud.google.com) (log in with your personal `@gmail.com`).
2. Click the project dropdown at the top &rarr; **New Project**.
3. Name it `gdgoc-sso-workshop` &rarr; Click **Create**.

### 12.2 Configure OAuth Consent Screen
1. In the left navigation, go to **APIs & Services &rarr; OAuth consent screen**.
2. Select User Type: **External** &rarr; Click **Create**.
3. Fill in App Information:
   - **App name**: `GDGoC NYP Workshop`
   - **User support email**: Your Gmail address
   - **Developer contact information**: Your Gmail address
4. Click **Save and Continue** through Scopes (we request scopes dynamically in code).
5. **Test users (MANDATORY)**:
   - Click **+ Add Users**.
   - Add your own `@gmail.com` address. *(In testing mode, unlisted users cannot sign in).*
6. Click **Save and Continue** &rarr; **Back to Dashboard**.

### 12.3 Create OAuth 2.0 Client Credentials
1. Go to **APIs & Services &rarr; Credentials**.
2. Click **+ Create Credentials &rarr; OAuth client ID**.
3. Application type: **Web application**.
4. Name: `Flask Web Client`.
5. **Authorised JavaScript origins**:
   - `http://127.0.0.1:5000`
6. **Authorised redirect URIs**:
   - `http://127.0.0.1:5000/callback`
   > **Warning:** Must match character-for-character. Do not use `localhost` if your app runs on `127.0.0.1`.
7. Click **Create**.
8. Copy the **Client ID** and **Client Secret**.

### 12.4 Enable Google Tasks API
1. In the left navigation, go to **APIs & Services &rarr; Library**.
2. Search for `Google Tasks API`.
3. Click **Enable**.

### 12.5 Update your `.env` File
Paste your newly generated credentials into `.env`:

```ini
FLASK_SECRET_KEY=change-this-to-any-random-secret-key-12345
GOOGLE_CLIENT_ID=xxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_DISCOVERY=https://accounts.google.com/.well-known/openid-configuration
```

Restart your Flask server:
```sh
python app.py
```

---

## Part 13 — Trying Out the Tasks App

1. Visit [http://127.0.0.1:5000](http://127.0.0.1:5000).
2. Click **Sign in with Google**:
   - You will see Google's consent dialog requesting permission to access your profile and read your Google Tasks (`tasks.readonly`).
   - *(Note: Since the app is in testing mode, click "Advanced" &rarr; "Go to GDGoC NYP Workshop (unsafe)" if prompted).*
3. Upon completing sign-in, you are redirected back to the app:
   - You will see your profile photo, full name, email, and Google `sub` ID.
   - Click **View Decoded ID Token Claims** to see the raw verified OpenID Connect claims!
4. Click **View My Google Tasks** (or navigate to `/tasks`):
   - The app uses your OAuth 2.0 Access Token to fetch your Google Task lists and display all your tasks, due dates, notes, and completion checkboxes.
5. Create a new task on [Google Calendar / Tasks](https://calendar.google.com) and refresh the `/tasks` page to see it update live!

---

## Part 14 — How Does Everything Work? (OpenID Connect & OAuth 2.0)

### 14.1 Authentication vs. Authorization
- **OpenID Connect (OIDC)**: Answers **"Who is this user?"** (Identity & Authentication &rarr; issues an **ID Token**).
- **OAuth 2.0**: Answers **"What data is this app allowed to access?"** (Delegated Authorization &rarr; issues an **Access Token**).

### 14.2 The Authorization Code Flow

```
User's Browser                Flask App (app.py)              Google Accounts
     |                               |                               |
     |--- 1. Click "Sign in" ------->|                               |
     |                               |--- 2. Redirect to Google ---->|
     |<-- 3. Show Google Login ------|                               |
     |                                                               |
     |=== 4. User logs in & grants consent =========================>|
     |                                                               |
     |<-- 5. Redirect to /callback?code=AUTH_CODE -------------------|
     |                                                               |
     |--- 6. GET /callback?code=AUTH_CODE -------------------------->|
     |                               |                               |
     |                               |--- 7. POST code + secret ---->|
     |                               |<-- 8. ID Token + Access Token-|
     |                               |                               |
     |<-- 9. Logged In Profile UI ---|                               |
```

#### Step-by-Step Flask Implementation in `app.py`:

##### Step A: Register the OAuth Provider
Authlib uses Google's OpenID Connect discovery document (`https://accounts.google.com/.well-known/openid-configuration`) to automatically locate the authorization, token, and userinfo endpoints:

```py
oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url=os.environ.get(
        "GOOGLE_DISCOVERY",
        "https://accounts.google.com/.well-known/openid-configuration"
    ),
    client_kwargs={
        "scope": "openid email profile https://www.googleapis.com/auth/tasks.readonly",
        "access_type": "offline",      # Requests a refresh token
        "prompt": "consent",           # Forces consent screen so refresh token is returned
    },
)
```

##### Step B: Trigger the Authorization Redirect (Steps 1 & 2)
When the user clicks **Sign in with Google**, `/login` asks Authlib to construct the Google authorization URL with your `client_id`, requested `scope`s, and `redirect_uri`:

```py
@app.route("/login")
def login():
    redirect_uri = url_for("callback", _external=True)
    return google.authorize_redirect(redirect_uri)
```

##### Step C: Code Exchange & Token Verification (Steps 6, 7 & 8)
Google redirects the user back to `/callback?code=...`. The Flask server exchanges this code directly with Google's token endpoint over a secure back-channel using your `client_secret`. Authlib automatically validates the cryptographic signature of the ID Token and returns user claims in `userinfo`:

```py
@app.route("/callback")
def callback():
    try:
        # Exchanges authorization code for ID token, access token, and refresh token
        token = google.authorize_access_token()
    except Exception as e:
        return f"Authentication failed: {str(e)}", 400

    # User identity claims decoded and verified from ID Token
    user_info = token.get("userinfo")
    session["user"] = user_info
    session["access_token"] = token.get("access_token")
    if token.get("refresh_token"):
        session["refresh_token"] = token.get("refresh_token")

    return redirect(url_for("index"))
```

##### Step D: Clean Logout
Logging out simply clears the Flask session:

```py
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
```

### 14.3 Tokens Explained

| Token | Type | Format | Lifetime | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **ID Token** | Authentication | JWT (signed by Google) | ~1 hour | Proves identity to your Flask app (`sub`, `email`, `name`). Never sent to third-party APIs. |
| **Access Token** | Authorization | Bearer Token string | ~1 hour | Sent in `Authorization: Bearer <token>` to Google APIs (Tasks API). |
| **Refresh Token** | Delegation Key | Opaque String | Long-lived | Exchanged automatically in the background for new Access Tokens when they expire. |

### 14.4 Google Tasks API Call Code (`app.py`)

```py
creds = Credentials(
    token=access_token,
    refresh_token=session.get("refresh_token"),
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
)

service = build("tasks", "v1", credentials=creds)
results = service.tasklists().list().execute()
```

### 14.5 Revoking Access
To test what happens when a user revokes application permissions:
1. Visit [https://myaccount.google.com/permissions](https://myaccount.google.com/permissions).
2. Locate `GDGoC NYP Workshop` and click **Remove Access**.
3. Refresh `/tasks` &rarr; observe how the app handles revoked authorization gracefully!

---

## Part 15 — Google One Tap Sign-In Demo

> [!IMPORTANT]
> To prevent issues later, please click the `i` icon in your browser to access this site's site settings and set the permission `Third-party sign-in` to `Allow`. This is because our current site is HTTP and Chrome might want to try and prevent tracking on the site.

Navigate to the dedicated One Tap showcase page:  
👉 **[http://127.0.0.1:5000/onetap](http://127.0.0.1:5000/onetap)**

### 15.1 Experience One Tap
1. Open [http://127.0.0.1:5000/onetap](http://127.0.0.1:5000/onetap) in a browser where you are logged into your Google Account.
2. In the top-right corner of the webpage, Google Identity Services displays an inline floating prompt card:
   - *"Continue as [Your Name]"*.
3. Click your account once (one single tap!).
4. The page immediately transitions to authenticated state without any full-page redirect to Google!
5. Inspect the decoded ID token claims on screen, including verified Google `sub`, email, and full name.

---

## Part 16 — Explain Google One Tap Sign-In

### 16.1 Why One Tap?
Standard OAuth 2.0 / OpenID Connect redirect flows pull users away from your site to an external Google Accounts consent page and redirect them back through a code exchange.

**Google One Tap (part of Google Identity Services)** solves friction by letting users sign in or sign up with a single click directly inside your website layout:
- **Zero Page Navigation**: The prompt runs as a native Google iframe floating over the page.
- **Immediate Credential Delivery**: Instead of an authorization code, Google returns a signed **ID Token (JWT)** immediately upon user confirmation.
- **Cross-Platform**: Works smoothly on Chrome, Android, macOS, Windows, and iOS Safari.

### 16.2 Client-Side Setup (`templates/onetap.html`)

Include the Google Identity Services client script and use a JavaScript callback via `data-callback`:

```html
<script src="https://accounts.google.com/gsi/client" async defer></script>

<div id="g_id_onload"
     data-client_id="{{ client_id }}"
     data-callback="handleOneTapResponse"
     data-auto_prompt="true"
     data-auto_select="true"
     data-itp_support="true">
</div>

<script>
  async function handleOneTapResponse(response) {
    // response.credential is the verified Google ID Token (JWT)
    const res = await fetch('/onetap/callback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential: response.credential })
    });
    if (res.ok) {
      window.location.reload();
    }
  }
</script>
```

> **Why `data-callback` instead of `data-login_uri`?**  
> Google's library requires `https://` for `data-login_uri` (except for literal `http://localhost`). Using `http://127.0.0.1` with `data-login_uri` triggers `[GSI_LOGGER]: Unsecured login_uri provided`. Using `data-callback` bypasses this limitation during local development by receiving the ID Token in JavaScript and `fetch`ing your Flask backend directly!

### 16.3 Backend Verification in Flask (`app.py`)

When the user taps the prompt, the ID Token is posted to `/onetap/callback`:

```py
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

@app.route("/onetap/callback", methods=["POST"])
def onetap_callback():
    data = request.get_json() or {}
    credential = data.get("credential")

    if not credential:
        return jsonify({"status": "error", "message": "Missing credential in request."}), 400

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    try:
        # Cryptographic signature and claim verification via Google SDK
        idinfo = id_token.verify_oauth2_token(credential, google_requests.Request(), client_id)
        session["onetap_user"] = idinfo
        return jsonify({"status": "success", "user": idinfo})
    except ValueError as e:
        return jsonify({"status": "error", "message": f"Invalid ID token: {str(e)}"}), 400
```

1. **Double Submit CSRF**: Validates that `g_csrf_token` cookie matches the body parameter.
2. **`id_token.verify_oauth2_token`**: Uses Google's public certificates (fetched automatically by the SDK) to cryptographically verify the signature, ensure `aud == client_id`, and check `exp`.


### 16.4 Key Differences: Google One Tap vs. The Earlier OAuth Flow

A common point of confusion for developers is when to use **Google One Tap** versus the **OAuth 2.0 Authorization Code Flow** we implemented in Parts 12–14. 

The core distinction comes down to **Authentication (Identity)** versus **Authorization (API Access)**:

| Feature / Property | Earlier Workshop Flow (Parts 12–14) | Google One Tap (Parts 15–16) |
| :--- | :--- | :--- |
| **Primary Goal** | **Authentication + Delegated Authorization** | **Pure Authentication (Identity Only)** |
| **Tokens Received** | **ID Token**, **Access Token**, & **Refresh Token** | **ID Token only** (credential JWT) |
| **Third-Party API Access** | ✅ **Yes** (e.g. Google Tasks, Drive, Calendar via Access Token) | ❌ **No** (Cannot call Google APIs directly with One Tap alone) |
| **User Experience** | Full-page redirect to Google Accounts consent screen | Instant floating inline UI overlay (zero page redirects) |
| **Scopes Requested** | Broad permissions (e.g., `tasks.readonly`, `profile`, `email`) | Standard identity scopes only (`openid`, `profile`, `email`) |
| **Token Refreshing** | Background refresh via long-lived **Refresh Token** | User re-authenticates or session is refreshed in browser |

#### 1. Authentication vs. Authorization in Practice
- **What Google One Tap did:** It only proved **who the user is** (Authentication). Google signed an **ID Token** containing the user's name, email, avatar, and unique `sub`. It gave our application **zero permission** to read their Google Tasks or act on their behalf.
- **What our earlier flow did:** In `/login` & `/callback`, we asked the user for explicit permission to manage their Google Tasks. In exchange, Google gave us an **Access Token** (to query `tasks.googleapis.com`) and a **Refresh Token** (to get new access tokens when they expire).

#### 2. Production Patterns: How Real Apps Combine Both
In modern web applications, you rarely choose only one:
1. **Frictionless Onboarding (One Tap First):** When a new or returning user visits your site, display **Google One Tap**. This logs them into your app instantly with 1 tap and creates their local user account in your database.
2. **Incremental Authorization (Ask Later):** Only when the user explicitly clicks a feature requiring Google APIs (e.g., *"Import My Google Tasks"* or *"Sync with Google Drive"*), you trigger the **OAuth 2.0 Authorization Code Flow** to request that specific permission scope.
3. **Token Persistence in Production:** In production applications, the **Refresh Token** obtained during the authorization step is stored securely in your database (encrypted at rest) associated with the user's `sub`. This allows your backend to perform background tasks or sync data without repeatedly asking the user to re-authorize every time they visit. 

---

## Appendix: Troubleshooting Guide

### Common Issues:
- **`redirect_uri_mismatch`**: The redirect URI in Google Cloud Console must match `http://127.0.0.1:5000/callback` character-for-character. Make sure your browser is using `http://127.0.0.1:5000` instead of `http://localhost:5000`.
- **`Error 403: access_denied`**: Your account was not added as a test user in Google Cloud Console (**OAuth consent screen &rarr; Test users**).
- **Google Tasks returns 403**: You forgot to enable the **Google Tasks API** under **APIs & Services &rarr; Library**.

### Production Checklist:
- [ ] `.env` is listed in `.gitignore` and never committed.
- [ ] Use `sub` (unique immutable identifier), not email, as the primary key for users in your database.
- [ ] `FLASK_SECRET_KEY` is a strong random secret.
- [ ] Revoke test app permissions at [myaccount.google.com/permissions](https://myaccount.google.com/permissions) after the workshop.
