"""
app2.py - A minimal login system using Flask's built-in session.

app.py already showed session auth by hand (DEMO_SESSIONS + a cookie we set
ourselves). This file shows the easier way: let Flask's `session` object store
the logged-in user for us.

Run:
    python app2.py
Then open:
    http://127.0.0.1:5001
"""

from functools import wraps

from flask import Flask, redirect, request, session, url_for

app = Flask(__name__)

# Flask uses this key to sign the session cookie. Change it in a real app and
# keep it secret -- anyone with this key can forge a logged-in session.
app.secret_key = "dev-secret-key-change-me"

# A fake "database" of users. Passwords are plain text ONLY to keep this demo
# simple. In a real app, store hashed passwords (see notes.md).
USERS = {
    "sofia": "secret",
    "alex": "password123",
}


def page(title, body):
    """Return a complete but very basic HTML page."""
    # Show different links depending on whether the user is logged in.
    if "user" in session:
        nav = (
            f'<a href="{url_for("index")}">Home</a> | '
            f'<a href="{url_for("profile")}">Profile</a> | '
            f'<a href="{url_for("logout")}">Logout</a>'
        )
    else:
        nav = (
            f'<a href="{url_for("index")}">Home</a> | '
            f'<a href="{url_for("login")}">Login</a>'
        )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{title}</title>
  </head>
  <body>
    <h1>{title}</h1>
    {body}
    <hr>
    <p>{nav}</p>
  </body>
</html>"""


def login_required(view_func):
    """Send visitors to /login if they are not in the session."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


@app.route("/")
def index():
    user = session.get("user")  # None if nobody is logged in
    if user:
        body = f"""
        <p>You are logged in as <strong>{user}</strong>.</p>
        <p>Try the protected <a href="{url_for('profile')}">profile page</a>.</p>
        """
    else:
        body = f"""
        <p>You are not logged in.</p>
        <p><a href="{url_for('login')}">Log in</a> to start a session.</p>
        """
    return page("Home", body)


@app.route("/login", methods=["GET", "POST"])
def login():
    # Already logged in? Send the user home instead of showing the form again.
    if "user" in session:
        return redirect(url_for("index"))

    error = ""

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        # Check the submitted details against our fake user table.
        if username in USERS and USERS[username] == password:
            # Correct! Save the user in Flask's session. Flask signs this
            # data and stores it in the browser's `session` cookie.
            session["user"] = username
            return redirect(url_for("index"))

        error = "<p><strong>Invalid username or password.</strong></p>"

    # On GET (or a failed POST) show the login form again.
    body = f"""
    {error}
    <form method="post">
      <p>
        <label for="username">Username</label>
        <input id="username" name="username" required>
      </p>
      <p>
        <label for="password">Password</label>
        <input id="password" name="password" type="password" required>
      </p>
      <button type="submit">Log in</button>
    </form>
    <p>Try <code>sofia</code> / <code>secret</code>.</p>
    """
    return page("Login", body)


@app.route("/profile")
@login_required
def profile():
    user = session["user"]
    body = f"""
    <p>Hello, <strong>{user}</strong>!</p>
    <p>Only logged-in users can see this page.</p>
    """
    return page("Profile", body)


@app.route("/logout")
def logout():
    # Remove the logged-in user from the session. session.clear() would also
    # work, but it would delete everything else we might have stored.
    session.pop("user", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    # Port 5001 so this can run at the same time as app.py (port 5000).
    app.run(host="127.0.0.1", port=5001, debug=True)
