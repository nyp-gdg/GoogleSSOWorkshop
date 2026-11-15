import os
import time
import secrets
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for, jsonify, Response
from authlib.integrations.flask_client import OAuth
from authlib.jose import jwt
from google.oauth2.credentials import Credentials
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from googleapiclient.discovery import build

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")
JWT_SECRET = os.environ.get("JWT_SECRET", app.secret_key)

# -----------------------------------------------------------------------------
# In-Memory Server-Side Session Table (Act 1 Demo)
# Stores session_id -> { "user": username, "created_at": timestamp }
# Resets in memory whenever the server reboots!
# -----------------------------------------------------------------------------
DEMO_SESSIONS = {}

# -----------------------------------------------------------------------------
# OAuth Configuration
# -----------------------------------------------------------------------------
SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/tasks.readonly",
]

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
        "scope": " ".join(SCOPES),
        "access_type": "offline",      # Requests a refresh token
        "prompt": "consent",           # Forces consent screen so refresh token is returned
    },
)

# -----------------------------------------------------------------------------
# Helper: Login Required Decorator
# -----------------------------------------------------------------------------
def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("index"))
        return view_func(*args, **kwargs)
    return wrapped

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    user = session.get("user")
    return render_template("index.html", user=user)

@app.route("/demos")
def demos():
    user = session.get("user")
    return render_template("demos.html", user=user)

# -----------------------------------------------------------------------------
# Act 1 Demo Endpoints (Demonstrating Auth Concepts on the same logical path)
# -----------------------------------------------------------------------------

# 1. Basic Auth Demo
@app.route("/demo/basic-auth")
def demo_basic_auth():
    auth = request.authorization
    if not auth or auth.username != "sofia" or auth.password != "secret":
        headers = {}
        # Only attach WWW-Authenticate challenge header if browser prompt is explicitly desired.
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

# 2. Stateful Session Auth Demo (Server-Side In-Memory Session Table)
@app.route("/demo/session-login", methods=["POST"])
def demo_session_login():
    username = request.form.get("username", "student")
    # Generate an unguessable opaque session ID
    session_id = secrets.token_hex(16)
    
    # Store user in the in-memory server-side session table
    DEMO_SESSIONS[session_id] = {
        "user": username,
        "created_at": int(time.time()),
    }

    resp = jsonify({
        "status": "session_created",
        "session_id": session_id,
        "user": username,
        "active_sessions_count": len(DEMO_SESSIONS),
        "message": f"Server stored session_id in memory and sent 'demo_session_id' cookie to client.",
        "note": "State is stored in DEMO_SESSIONS server memory. If the server reboots, this memory is wiped!"
    })
    # Set an HttpOnly cookie containing only the opaque session ID
    resp.set_cookie("demo_session_id", session_id, httponly=True, samesite="Lax")
    return resp

@app.route("/demo/session-profile")
def demo_session_profile():
    session_id = request.cookies.get("demo_session_id")
    if not session_id or session_id not in DEMO_SESSIONS:
        return jsonify({
            "status": "unauthenticated",
            "message": "Session ID not found in server memory. (Server may have rebooted, or session expired/not set).",
            "received_cookie": session_id,
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

    resp = jsonify({
        "status": "reset",
        "message": "Session invalidated from server-side memory and cookie cleared.",
        "active_sessions_count": len(DEMO_SESSIONS)
    })
    resp.delete_cookie("demo_session_id")
    return resp

# 3. Stateless Bearer Auth Demo
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

# -----------------------------------------------------------------------------
# Act 2: Sign in with Google (SSO & ID Token)
# -----------------------------------------------------------------------------
@app.route("/login")
def login():
    redirect_uri = url_for("callback", _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/callback")
def callback():
    try:
        token = google.authorize_access_token()
    except Exception as e:
        return f"Authentication failed: {str(e)}", 400

    # User info comes from decoded and verified ID Token
    user_info = token.get("userinfo")
    session["user"] = user_info
    session["access_token"] = token.get("access_token")
    if token.get("refresh_token"):
        session["refresh_token"] = token.get("refresh_token")

    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# -----------------------------------------------------------------------------
# Act 3: OAuth2 & Google Tasks API
# -----------------------------------------------------------------------------
@app.route("/tasks")
@login_required
def tasks():
    access_token = session.get("access_token")
    if not access_token:
        return redirect(url_for("login"))

    creds = Credentials(
        token=access_token,
        refresh_token=session.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    )

    try:
        service = build("tasks", "v1", credentials=creds)
        results = service.tasklists().list().execute()
        raw_tasklists = results.get("items", [])

        # Fetch tasks for each task list (showing both pending and completed tasks)
        tasklists = []
        for tl in raw_tasklists:
            tasklist_id = tl.get("id")
            tasks_res = service.tasks().list(
                tasklist=tasklist_id,
                showCompleted=True,
                showHidden=True,
                maxResults=100
            ).execute()
            items = tasks_res.get("items", [])
            tasklists.append({
                "id": tasklist_id,
                "title": tl.get("title", "Untitled List"),
                "updated": tl.get("updated", ""),
                "tasks": items
            })

        return render_template("tasks.html", user=session.get("user"), tasklists=tasklists)
    except Exception as e:
        return render_template("tasks.html", user=session.get("user"), error=str(e), tasklists=[])



# -----------------------------------------------------------------------------
# Google One Tap Sign-In
# -----------------------------------------------------------------------------

@app.route("/onetap")
def onetap():
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    onetap_user = session.get("user")
    return render_template("onetap.html", client_id=client_id, user=onetap_user)

@app.route("/onetap/callback", methods=["POST"])
def onetap_callback():
    # Support both JSON payload (from JavaScript client callback) and Form POST
    if request.is_json:
        data = request.get_json() or {}
        credential = data.get("credential")
    else:
        credential = request.form.get("credential")
        csrf_token_cookie = request.cookies.get("g_csrf_token")
        csrf_token_body = request.form.get("g_csrf_token")
        if not csrf_token_cookie or not csrf_token_body or csrf_token_cookie != csrf_token_body:
            return jsonify({"status": "error", "message": "CSRF validation failed."}), 400

    if not credential:
        return jsonify({"status": "error", "message": "Missing credential in request."}), 400

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    try:
        # Verify the integrity and claims of the Google ID token
        idinfo = id_token.verify_oauth2_token(credential, google_requests.Request(), client_id)
        session["user"] = idinfo
        if request.is_json:
            return jsonify({
                "status": "success",
                "message": "Authenticated successfully via Google One Tap",
                "user": idinfo
            })
        return redirect(url_for("onetap"))
    except ValueError as e:
        return jsonify({"status": "error", "message": f"Invalid ID token: {str(e)}"}), 400

@app.route("/onetap/logout")
def onetap_logout():
    session.pop("user", None)
    session.pop("access_token", None)
    return redirect(url_for("onetap"))


if __name__ == "__main__":
    # Host on 127.0.0.1:5000 (matches Google Cloud OAuth redirect URI)
    app.run(host="127.0.0.1", port=5000, debug=True)
