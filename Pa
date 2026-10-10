import streamlit as st
import sqlite3, os, re, secrets, hashlib, hmac, random, html, smtplib, time
from email.message import EmailMessage

st.set_page_config(page_title="Snake & Ladder", page_icon="🐍", layout="wide", initial_sidebar_state="collapsed")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")
OTP_SECONDS = 300

def init_db():
    with sqlite3.connect(DB_PATH, timeout=15) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            salt BLOB NOT NULL,
            password_hash BLOB NOT NULL,
            email_verified INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        # Support databases created by the previous version.
        columns = {row[1] for row in con.execute("PRAGMA table_info(users)").fetchall()}
        if "email_verified" not in columns:
            con.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 1")

def valid_email(email):
    email = (email or "").strip()
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))

def send_otp_email(email, otp):
    """Configure SMTP_EMAIL and SMTP_APP_PASSWORD in Streamlit secrets."""
    try:
        smtp_email = st.secrets["SMTP_EMAIL"]
        smtp_password = st.secrets["SMTP_APP_PASSWORD"]
    except Exception:
        return False, ("Email sending is not configured. Add SMTP_EMAIL and "
                       "SMTP_APP_PASSWORD in Streamlit app Secrets.")
    msg = EmailMessage()
    msg["Subject"] = "Your Snake & Ladder verification code"
    msg["From"] = smtp_email
    msg["To"] = email
    msg.set_content(
        f"Your Snake & Ladder verification code is: {otp}\n\n"
        f"This code expires in {OTP_SECONDS // 60} minutes. If you did not request it, ignore this email."
    )
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.send_message(msg)
        return True, "Verification code sent. Check your inbox and spam folder."
    except Exception:
        return False, "Could not send the email. Check SMTP secrets and the Gmail app password."

def create_user(email, password):
    email = (email or "").strip().lower()
    if not valid_email(email):
        return False, "Please enter a valid email address."
    if len(password) < 8:
        return False, "Password must contain at least 8 characters."
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 300_000)
    try:
        with sqlite3.connect(DB_PATH, timeout=15) as con:
            con.execute(
                "INSERT INTO users(email,salt,password_hash,email_verified) VALUES(?,?,?,1)",
                (email, salt, password_hash)
            )
        return True, "Account created and email verified."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists. Please sign in."
    except sqlite3.Error:
        return False, "Database error while creating the account."

def verify_user(email, password):
    email = (email or "").strip().lower()
    try:
        with sqlite3.connect(DB_PATH, timeout=15) as con:
            row = con.execute(
                "SELECT salt,password_hash,email_verified FROM users WHERE email=?", (email,)
            ).fetchone()
        if not row:
            return False, "Email or password is incorrect."
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), row[0], 300_000)
        if not hmac.compare_digest(digest, row[1]):
            return False, "Email or password is incorrect."
        if not row[2]:
            return False, "This email address has not been verified."
        return True, "Signed in successfully."
    except sqlite3.Error:
        return False, "Database error. Please try again."

LADDERS = {4:14, 9:31, 20:38, 28:84, 40:59, 63:81, 71:91, 80:99}
SNAKES = {17:7, 54:34, 62:19, 64:60, 87:24, 93:73, 95:75, 98:79}
COLORS = ["#1ba8ff", "#ff454d", "#ffc928", "#2cdb61"]

def new_game():
    return {"names":["Player 1","Player 2","Player 3","Player 4"], "positions":[1,1,1,1],
            "turn":0, "die":None, "winner":None, "message":""}

def roll_turn(game):
    g = dict(game)
    g["positions"] = list(game["positions"])
    player = g["turn"]
    roll = random.randint(1,6)
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
    g["die"] = ["⚀","⚁","⚂","⚃","⚄","⚅"][roll-1]
    g["message"] = message
    if g["winner"] is None:
        g["turn"] = (player + 1) % len(g["names"])
    return g

def board_html(game):
    pieces = {}
    for i, pos in enumerate(game["positions"]):
        pieces.setdefault(pos, []).append(f'<span style="color:{COLORS[i]};text-shadow:0 1px 3px #000;font-size:1.15em">●</span>')
    cells = ['<div class="board">']
    for row in range(9,-1,-1):
        nums = list(range(row*10+1,row*10+11))
        if row % 2:
            nums.reverse()
        for col, n in enumerate(nums):
            classes = ["cell", "blue" if (row+col)%2 else ""]
            if n == 1: classes.append("start")
            if n == 100: classes.append("finish")
            symbols = []
            if n in LADDERS: symbols.append("🪜")
            if n in SNAKES: symbols.append("🐍")
            symbols.extend(pieces.get(n, []))
            label = "WINNER" if n == 100 else ("START" if n == 1 else "")
            bottom = f'<small class="bottom">{label}</small>' if label else ""
            cells.append(f'<div class="{" ".join(c for c in classes if c)}"><span class="num">{n}</span><span class="pieces">{" ".join(symbols)}</span>{bottom}</div>')
    cells.append("</div>")
    return "".join(cells)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800&family=Poppins:wght@400;500;600;700;800&display=swap');
html,body,[data-testid="stAppViewContainer"]{background:#06172c;color:#f5f9ff;font-family:Poppins,sans-serif}
[data-testid="stHeader"],[data-testid="stToolbar"],#MainMenu,footer{visibility:hidden}
.block-container{max-width:1450px;padding:1rem 1.1rem 2rem}
.brand{font-family:'Baloo 2',sans-serif;font-weight:800;font-size:clamp(2rem,4vw,3.8rem);line-height:.95;color:#ffe2a0;text-shadow:0 4px 0 #99451d,0 7px 15px #0008}
.red{color:#ff5552}.sub,.muted{color:#b5d9f6}.sub{margin:.7rem 0 1rem}
.panel{background:linear-gradient(145deg,#0b315c,#071e3b);border:2px solid #145a94;border-radius:22px;padding:16px;margin-bottom:14px}
.player{display:flex;align-items:center;gap:12px;background:#0b3b70;border:1px solid #277bc0;padding:12px;border-radius:15px;margin:8px 0}
.dot{width:25px;height:25px;flex:0 0 25px;border-radius:50%}
.board-wrap{border:4px solid #10cfff;border-radius:22px;padding:5px;background:#063f75;box-shadow:0 0 24px #00c8ff33}
.board{display:grid;grid-template-columns:repeat(10,minmax(0,1fr));overflow:hidden;border-radius:12px;border:1px solid #39bfff}
.cell{aspect-ratio:1/1;min-width:0;position:relative;display:flex;align-items:center;justify-content:center;border:1px solid #d6e2eb;background:#fff4dd;color:#16446b;font-weight:800;font-size:clamp(9px,1.1vw,16px)}
.cell.blue{background:#1386dc;color:white}.num{position:absolute;left:4px;top:3px;font-size:clamp(7px,.8vw,12px)}
.pieces{text-align:center;font-size:clamp(12px,1.8vw,24px);line-height:1.1}.bottom{position:absolute;bottom:2px;font-size:8px}
.cell.start,.cell.finish{background:#ffd45d!important;color:#16395d!important}
div.stButton>button,div.stFormSubmitButton>button{border-radius:14px;min-height:3rem;font-weight:800;color:white;border:1px solid #29c9ff;background:linear-gradient(135deg,#087ef5,#0750c9)}
.auth{max-width:600px;margin:3vh auto;padding:24px;background:#111e2e;border:1px solid #29415d;border-radius:22px}
@media(max-width:700px){.block-container{padding:.5rem}.num{left:2px;top:1px}.panel{padding:12px}}
</style>
""", unsafe_allow_html=True)

try:
    init_db()
except Exception:
    st.error("Could not start the database. Check app logs and filesystem permissions.")
    st.stop()

def auth_screen():
    st.markdown('<div class="auth"><div class="brand"><span class="red">🐍 SNAKE</span><br>AND LADDER</div><p class="sub">Sign in or create an account to play.</p></div>', unsafe_allow_html=True)
    tab_login, tab_signup = st.tabs(["Sign in","Create account"])
    with tab_login:
        with st.form("login_form"):
            login_email = st.text_input("Email address", key="login_email", placeholder="you@example.com")
            login_password = st.text_input("Password", key="login_password", type="password")
            login_submit = st.form_submit_button("Sign in", use_container_width=True)
        if login_submit:
            ok, message = verify_user(login_email, login_password)
            if ok:
                st.session_state["user"] = login_email.strip().lower()
                st.session_state["game"] = new_game()
                st.rerun()
            else:
                st.error(message)

    with tab_signup:
        st.caption("Create an account with a password, then verify the 6-digit code sent to your email.")
        with st.form("signup_form"):
            signup_email = st.text_input("Email address", key="signup_email", placeholder="you@example.com")
            signup_password = st.text_input("Create password (at least 8 characters)", key="signup_password", type="password")
            signup_confirm = st.text_input("Confirm password", key="signup_confirm", type="password")
            signup_submit = st.form_submit_button("Send verification code", use_container_width=True)
        if signup_submit:
            email = signup_email.strip().lower()
            # Compare the exact entered password strings; no trimming changes the password.
            if not valid_email(email):
                st.error("Enter a valid email address, such as name@gmail.com.")
            elif len(signup_password) < 8:
                st.error("Password must contain at least 8 characters.")
            elif not hmac.compare_digest(signup_password, signup_confirm):
                st.error("Passwords do not match. Re-enter both password fields carefully.")
            else:
                try:
                    with sqlite3.connect(DB_PATH, timeout=15) as con:
                        exists = con.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone()
                except sqlite3.Error:
                    exists = True
                if exists:
                    st.error("This email is already registered. Use Sign in instead.")
                else:
                    otp = f"{secrets.randbelow(1_000_000):06d}"
                    sent, message = send_otp_email(email, otp)
                    if sent:
                        st.session_state["pending_signup"] = {
                            "email": email,
                            "password": signup_password,
                            "otp_hash": hashlib.sha256(otp.encode()).hexdigest(),
                            "expires": time.time() + OTP_SECONDS,
                            "attempts": 0
                        }
                        st.success(message)
                    else:
                        st.error(message)

        pending = st.session_state.get("pending_signup")
        if pending:
            st.info(f"Verification code sent to {pending['email']}. It expires in 5 minutes.")
            with st.form("verify_otp_form"):
                entered_otp = st.text_input("6-digit email verification code", max_chars=6, key="entered_otp")
                verify_submit = st.form_submit_button("Verify email and create account", use_container_width=True)
            if verify_submit:
                if time.time() > pending["expires"]:
                    st.session_state.pop("pending_signup", None)
                    st.error("Code expired. Please submit the registration form again.")
                elif pending["attempts"] >= 5:
                    st.session_state.pop("pending_signup", None)
                    st.error("Too many attempts. Please request a new code.")
                else:
                    pending["attempts"] += 1
                    expected = pending["otp_hash"]
                    actual = hashlib.sha256(entered_otp.strip().encode()).hexdigest()
                    if hmac.compare_digest(actual, expected):
                        success, message = create_user(pending["email"], pending["password"])
                        st.session_state.pop("pending_signup", None)
                        if success:
                            st.success("Email verified and account created. Now use the Sign in tab.")
                        else:
                            st.error(message)
                    else:
                        st.error("Incorrect verification code. Check the email and try again.")

    st.caption("Email OTP requires SMTP settings. No OTP is sent until SMTP is configured.")

if "user" not in st.session_state:
    auth_screen()
    st.stop()
if "game" not in st.session_state:
    st.session_state["game"] = new_game()
game = st.session_state["game"]

left,right = st.columns([3.2,1.15],gap="large")
with left:
    st.markdown('<div class="brand"><span class="red">🐍 SNAKE</span><br>AND LADDER</div><div class="sub">A classic board game · Roll the dice · Race to 100</div>',unsafe_allow_html=True)
    st.markdown('<div class="board-wrap">'+board_html(game)+'</div>',unsafe_allow_html=True)
    st.markdown('<p class="muted">🪜 Ladders move you up · 🐍 Snakes send you down · Reach exactly 100 to win.</p>',unsafe_allow_html=True)
with right:
    st.markdown(f'<div class="panel"><h3>⚙️ Game room</h3><p class="muted">Signed in as {html.escape(st.session_state["user"])}</p></div>',unsafe_allow_html=True)
    st.markdown('<div class="panel"><h3>Players</h3>',unsafe_allow_html=True)
    for i,name in enumerate(game["names"]):
        st.markdown(f'<div class="player"><div class="dot" style="background:{COLORS[i]}"></div><div><b>{name}</b><br><span class="muted">Position: {game["positions"][i]}</span></div></div>',unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="panel"><div class="muted">Current turn</div><h3>{game["names"][game["turn"]]}</h3><div style="font-size:4rem;text-align:center">{game["die"] or "🎲"}</div>',unsafe_allow_html=True)
    if game["winner"] is not None:
        st.success(f'{game["names"][game["winner"]]} wins!')
        if st.button("Play again",use_container_width=True):
            st.session_state["game"]=new_game(); st.rerun()
    elif st.button("🎲 ROLL DICE",use_container_width=True):
        st.session_state["game"]=roll_turn(game); st.rerun()
    if game["message"]: st.info(game["message"])
    st.markdown('</div>',unsafe_allow_html=True)
    if st.button("↻ New game",use_container_width=True):
        st.session_state["game"]=new_game(); st.rerun()
    if st.button("Sign out",use_container_width=True):
        st.session_state.pop("user",None); st.session_state.pop("game",None); st.rerun()
with st.expander("📖 How to play — Rules"):
    st.markdown("1. Players take turns rolling the dice.\n2. Move forward by the dice number.\n3. Ladders take you up.\n4. Snakes send you down.\n5. Land exactly on 100 to win.")
