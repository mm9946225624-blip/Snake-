
import streamlit as st
import sqlite3
import os
import re
import secrets
import hashlib
import hmac
import random
import html
import smtplib
import time
from email.message import EmailMessage

st.set_page_config(
    page_title="Snake & Ladder",
    page_icon="🐍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "users.db"
)

OTP_SECONDS = 300
MAX_OTP_ATTEMPTS = 5


# ---------------- DATABASE ----------------

def init_db():
    with sqlite3.connect(DB_PATH, timeout=15) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                email_verified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        columns = {
            row[1]
            for row in con.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }

        if "email_verified" not in columns:
            # Existing accounts from the previous app version
            # remain usable.
            con.execute("""
                ALTER TABLE users
                ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 1
            """)


def valid_email(email):
    email = (email or "").strip()
    return bool(
        re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
    )


def password_digest(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        300_000
    )


def create_user(email, password):
    email = (email or "").strip().lower()

    if not valid_email(email):
        return False, "Please enter a valid email address."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    salt = secrets.token_bytes(16)
    digest = password_digest(password, salt)

    try:
        with sqlite3.connect(DB_PATH, timeout=15) as con:
            con.execute("""
                INSERT INTO users
                (email, salt, password_hash, email_verified)
                VALUES (?, ?, ?, 1)
            """, (email, salt, digest))

        return True, "Account created successfully."

    except sqlite3.IntegrityError:
        return False, "This email is already registered."

    except sqlite3.Error:
        return False, "Database error while creating account."


def verify_user(email, password):
    email = (email or "").strip().lower()

    try:
        with sqlite3.connect(DB_PATH, timeout=15) as con:
            row = con.execute("""
                SELECT salt, password_hash, email_verified
                FROM users
                WHERE email = ?
            """, (email,)).fetchone()

        if not row:
            return False, "Email or password is incorrect."

        salt, stored_hash, verified = row
        calculated_hash = password_digest(password, salt)

        if not hmac.compare_digest(calculated_hash, stored_hash):
            return False, "Email or password is incorrect."

        if not verified:
            return False, "Please verify your email first."

        return True, "Login successful."

    except sqlite3.Error:
        return False, "Database error. Please try again."


# ---------------- EMAIL OTP ----------------

def get_smtp_credentials():
    email = ""
    password = ""

    # Recommended: Streamlit Community Cloud Secrets.
    try:
        email = str(
            st.secrets.get("SMTP_EMAIL", "")
        ).strip()

        password = str(
            st.secrets.get("SMTP_APP_PASSWORD", "")
        ).strip().replace(" ", "")
    except Exception:
        pass

    # Optional environment-variable fallback.
    email = email or os.environ.get("SMTP_EMAIL", "").strip()
    password = (
        password
        or os.environ.get("SMTP_APP_PASSWORD", "")
    ).strip().replace(" ", "")

    return email, password


def send_otp_email(recipient, otp):
    sender, app_password = get_smtp_credentials()

    if not sender or not app_password:
        return False, (
            "Email sending is not configured. Open Streamlit "
            "Cloud → Manage app → Settings → Secrets and add "
            "SMTP_EMAIL and SMTP_APP_PASSWORD."
        )

    message = EmailMessage()
    message["Subject"] = "Snake & Ladder - Email Verification"
    message["From"] = sender
    message["To"] = recipient

    message.set_content(
        f"Your Snake & Ladder verification code is: {otp}\n\n"
        "This code expires in 5 minutes. "
        "If you did not request it, ignore this email."
    )

    try:
        with smtplib.SMTP(
            "smtp.gmail.com", 587, timeout=20
        ) as server:
            server.starttls()
            server.login(sender, app_password)
            server.send_message(message)

        return True, "OTP sent. Check your inbox and spam folder."

    except Exception as exc:
        # Do not expose SMTP credentials in the UI.
        return False, (
            "Could not send OTP. Check your Gmail address, "
            "Google App Password, and SMTP access. "
            f"Error type: {type(exc).__name__}"
        )


def start_registration(email, password):
    email = (email or "").strip().lower()

    if not valid_email(email):
        return False, "Please enter a valid email address."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    try:
        with sqlite3.connect(DB_PATH, timeout=15) as con:
            existing = con.execute(
                "SELECT 1 FROM users WHERE email = ?",
                (email,)
            ).fetchone()

        if existing:
            return False, (
                "This email is already registered. "
                "Please use the Sign in tab."
            )

    except sqlite3.Error:
        return False, "Could not check the database."

    otp = f"{secrets.randbelow(1_000_000):06d}"

    sent, message = send_otp_email(email, otp)

    if not sent:
        return False, message

    st.session_state["pending_signup"] = {
        "email": email,
        "password": password,
        "otp_hash": hashlib.sha256(
            otp.encode("utf-8")
        ).hexdigest(),
        "expires": time.time() + OTP_SECONDS,
        "attempts": 0
    }

    return True, message


def verify_signup_otp(entered_otp):
    pending = st.session_state.get("pending_signup")

    if not pending:
        return False, "Request a new verification code."

    if time.time() > pending["expires"]:
        st.session_state.pop("pending_signup", None)
        return False, "Code expired. Please register again."

    if pending["attempts"] >= MAX_OTP_ATTEMPTS:
        st.session_state.pop("pending_signup", None)
        return False, "Too many attempts. Request a new code."

    pending["attempts"] += 1

    expected = pending["otp_hash"]
    actual = hashlib.sha256(
        (entered_otp or "").strip().encode("utf-8")
    ).hexdigest()

    if not re.fullmatch(r"\d{6}", (entered_otp or "").strip()):
        return False, "Enter the six-digit code."

    if not hmac.compare_digest(actual, expected):
        return False, "Incorrect code. Check your email."

    success, message = create_user(
        pending["email"],
        pending["password"]
    )

    st.session_state.pop("pending_signup", None)

    if success:
        st.session_state["signup_success"] = True
        return True, "Email verified! Your account is created."

    return False, message


# ---------------- GAME ----------------

LADDERS = {
    4: 14, 9: 31, 20: 38, 28: 84,
    40: 59, 63: 81, 71: 91, 80: 99
}

SNAKES = {
    17: 7, 54: 34, 62: 19, 64: 60,
    87: 24, 93: 73, 95: 75, 98: 79
}

COLORS = ["#1ba8ff", "#ff454d", "#ffc928", "#2cdb61"]


def new_game():
    return {
        "names": ["Player 1", "Player 2", "Player 3", "Player 4"],
        "positions": [1, 1, 1, 1],
        "turn": 0,
        "die": None,
        "winner": None,
        "message": ""
    }


def roll_turn(game):
    g = dict(game)
    g["positions"] = list(game["positions"])

    player = g["turn"]
    roll = random.randint(1, 6)
    target = g["positions"][player] + roll

    message = f'{g["names"][player]} rolled {roll}.'

    if target <= 100:
        g["positions"][player] = target

        if target in LADDERS:
            g["positions"][player] = LADDERS[target]
            message += f' Ladder! Climb to {LADDERS[target]}.'

        elif target in SNAKES:
            g["positions"][player] = SNAKES[target]
            message += f' Snake! Slide down to {SNAKES[target]}.'

        if g["positions"][player] == 100:
            g["winner"] = player
            message += " You win!"

    else:
        message += " You need an exact roll to reach 100."

    g["die"] = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"][roll - 1]
    g["message"] = message

    if g["winner"] is None:
        g["turn"] = (player + 1) % len(g["names"])

    return g


def board_html(game):
    pieces = {}

    for i, pos in enumerate(game["positions"]):
        pieces.setdefault(pos, []).append(
            f'<span style="color:{COLORS[i]};'
            'text-shadow:0 1px 3px #000;'
            'font-size:1.15em">●</span>'
        )

    cells = ['<div class="board">']

    for row in range(9, -1, -1):
        nums = list(range(row * 10 + 1, row * 10 + 11))

        if row % 2:
            nums.reverse()

        for col, n in enumerate(nums):
            classes = ["cell", "blue" if (row + col) % 2 else ""]

            if n == 1:
                classes.append("start")

            if n == 100:
                classes.append("finish")

            symbols = []

            if n in LADDERS:
                symbols.append("🪜")

            if n in SNAKES:
                symbols.append("🐍")

            symbols.extend(pieces.get(n, []))

            label = "WINNER" if n == 100 else ("START" if n == 1 else "")
            bottom = (
                f'<small class="bottom">{label}</small>'
                if label else ""
            )

            class_text = " ".join(c for c in classes if c)

            cells.append(
                f'<div class="{class_text}">'
                f'<span class="num">{n}</span>'
                f'<span class="pieces">{" ".join(symbols)}</span>'
                f'{bottom}</div>'
            )

    cells.append("</div>")
    return "".join(cells)


# ---------------- DESIGN ----------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800&family=Poppins:wght@400;500;600;700;800&display=swap');
html,body,[data-testid="stAppViewContainer"]{
    background:#06172c;color:#f5f9ff;font-family:Poppins,sans-serif
}
[data-testid="stHeader"],[data-testid="stToolbar"],#MainMenu,footer{
    visibility:hidden
}
.block-container{max-width:1450px;padding:1rem 1.1rem 2rem}
.brand{
    font-family:'Baloo 2',sans-serif;font-weight:800;
    font-size:clamp(2rem,4vw,3.8rem);line-height:.95;
    color:#ffe2a0;text-shadow:0 4px 0 #99451d,0 7px 15px #0008
}
.red{color:#ff5552}
.sub,.muted{color:#b5d9f6}
.sub{margin:.7rem 0 1rem}
.panel{
    background:linear-gradient(145deg,#0b315c,#071e3b);
    border:2px solid #145a94;border-radius:22px;
    padding:16px;margin-bottom:14px
}
.player{
    display:flex;align-items:center;gap:12px;
    background:#0b3b70;border:1px solid #277bc0;
    padding:12px;border-radius:15px;margin:8px 0
}
.dot{width:25px;height:25px;flex:0 0 25px;border-radius:50%}
.board-wrap{
    border:4px solid #10cfff;border-radius:22px;
    padding:5px;background:#063f75;box-shadow:0 0 24px #00c8ff33
}
.board{
    display:grid;grid-template-columns:repeat(10,minmax(0,1fr));
    overflow:hidden;border-radius:12px;border:1px solid #39bfff
}
.cell{
    aspect-ratio:1/1;min-width:0;position:relative;
    display:flex;align-items:center;justify-content:center;
    border:1px solid #d6e2eb;background:#fff4dd;color:#16446b;
    font-weight:800;font-size:clamp(9px,1.1vw,16px)
}
.cell.blue{background:#1386dc;color:white}
.num{position:absolute;left:4px;top:3px;font-size:clamp(7px,.8vw,12px)}
.pieces{text-align:center;font-size:clamp(12px,1.8vw,24px);line-height:1.1}
.bottom{position:absolute;bottom:2px;font-size:8px}
.cell.start,.cell.finish{background:#ffd45d!important;color:#16395d!important}
div.stButton>button,div.stFormSubmitButton>button{
    border-radius:14px;min-height:3rem;font-weight:800;
    color:white;border:1px solid #29c9ff;
    background:linear-gradient(135deg,#087ef5,#0750c9)
}
.auth{
    max-width:600px;margin:3vh auto;padding:24px;
    background:#111e2e;border:1px solid #29415d;border-radius:22px
}
@media(max-width:700px){
    .block-container{padding:.5rem}
    .num{left:2px;top:1px}
    .panel{padding:12px}
}
</style>
""", unsafe_allow_html=True)


# ---------------- START DATABASE ----------------

try:
    init_db()
except Exception:
    st.error(
        "Could not start the database. Check app logs "
        "and filesystem permissions."
    )
    st.stop()


# ---------------- LOGIN / REGISTRATION ----------------

def auth_screen():
    st.markdown(
        '<div class="auth"><div class="brand">'
        '<span class="red">🐍 SNAKE</span><br>AND LADDER</div>'
        '<p class="sub">Sign in or create an account to play.</p></div>',
        unsafe_allow_html=True
    )

    with st.expander("Email OTP setup help"):
        st.markdown("""
        To send real OTP emails, configure these values in
        Streamlit Cloud → Manage app → Settings → Secrets:

        ```toml
        SMTP_EMAIL = "yourgmail@gmail.com"
        SMTP_APP_PASSWORD = "your_google_app_password"
        ```

        Use a Google App Password, not your regular Gmail password.
        Enable 2-Step Verification on your Google account first.
        """)

    login_tab, signup_tab = st.tabs(["Sign in", "Create account"])

    with login_tab:
        with st.form("login_form"):
            login_email = st.text_input(
                "Email address",
                key="login_email",
                placeholder="you@example.com"
            )

            login_password = st.text_input(
                "Password",
                key="login_password",
                type="password"
            )

            login_submit = st.form_submit_button(
                "Sign in",
                use_container_width=True
            )

        if login_submit:
            ok, message = verify_user(login_email, login_password)

            if ok:
                st.session_state["user"] = login_email.strip().lower()
                st.session_state["game"] = new_game()
                st.rerun()
            else:
                st.error(message)

    with signup_tab:
        st.caption(
            "Create your account and verify your email "
            "with a six-digit code."
        )

        with st.form("signup_form"):
            signup_email = st.text_input(
                "Email address",
                key="signup_email",
                placeholder="you@example.com"
            )

            signup_password = st.text_input(
                "Create password (at least 8 characters)",
                key="signup_password",
                type="password"
            )

            signup_confirm = st.text_input(
                "Confirm password",
                key="signup_confirm",
                type="password"
            )

            signup_submit = st.form_submit_button(
                "Send verification code",
                use_container_width=True
            )

        if signup_submit:
            if not hmac.compare_digest(
                signup_password, signup_confirm
            ):
                st.error(
                    "Passwords do not match. Enter both passwords "
                    "carefully, including uppercase letters, spaces "
                    "and symbols."
                )
            else:
                ok, message = start_registration(
                    signup_email, signup_password
                )

                if ok:
                    st.success(message)
                else:
                    st.error(message)

        pending = st.session_state.get("pending_signup")

        if pending:
            st.info(
                f"Code sent to {pending['email']}. "
                "It expires in 5 minutes."
            )

            with st.form("verify_otp_form"):
                entered_otp = st.text_input(
                    "Six-digit verification code",
                    key="entered_otp",
                    max_chars=6
                )

                verify_submit = st.form_submit_button(
                    "Verify email and create account",
                    use_container_width=True
                )

            if verify_submit:
                ok, message = verify_signup_otp(entered_otp)

                if ok:
                    st.success(message)
                    st.info("Now open the Sign in tab to log in.")
                else:
                    st.error(message)

    if st.session_state.pop("signup_success", False):
        st.success("Registration completed. You can now sign in.")

    st.caption(
        "Email verification requires working SMTP credentials. "
        "This app does not send an OTP unless email is configured."
    )


if "user" not in st.session_state:
    auth_screen()
    st.stop()


# ---------------- GAME SCREEN ----------------

if "game" not in st.session_state:
    st.session_state["game"] = new_game()

game = st.session_state["game"]

left, right = st.columns([3.2, 1.15], gap="large")

with left:
    st.markdown(
        '<div class="brand"><span class="red">🐍 SNAKE</span>'
        '<br>AND LADDER</div>'
        '<div class="sub">A classic board game · Roll the dice · Race to 100</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="board-wrap">' + board_html(game) + '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<p class="muted">🪜 Ladders move you up · 🐍 Snakes send you down · '
        'Reach exactly 100 to win.</p>',
        unsafe_allow_html=True
    )

with right:
    st.markdown(
        '<div class="panel"><h3>⚙️ Game room</h3>'
        f'<p class="muted">Signed in as '
        f'{html.escape(st.session_state["user"])}</p></div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="panel"><h3>Players</h3>',
        unsafe_allow_html=True
    )

    for i, name in enumerate(game["names"]):
        st.markdown(
            f'<div class="player">'
            f'<div class="dot" style="background:{COLORS[i]}"></div>'
            f'<div><b>{name}</b><br>'
            f'<span class="muted">Position: {game["positions"][i]}</span>'
            f'</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="panel"><div class="muted">Current turn</div>'
        f'<h3>{game["names"][game["turn"]]}</h3>'
        f'<div style="font-size:4rem;text-align:center">'
        f'{game["die"] or "🎲"}</div>',
        unsafe_allow_html=True
    )

    if game["winner"] is not None:
        st.success(f'{game["names"][game["winner"]]} wins!')

        if st.button("Play again", use_container_width=True):
            st.session_state["game"] = new_game()
            st.rerun()

    elif st.button("🎲 ROLL DICE", use_container_width=True):
        st.session_state["game"] = roll_turn(game)
        st.rerun()

    if game["message"]:
        st.info(game["message"])

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("↻ New game", use_container_width=True):
        st.session_state["game"] = new_game()
        st.rerun()

    if st.button("Sign out", use_container_width=True):
    
