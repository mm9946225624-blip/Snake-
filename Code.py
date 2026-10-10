import streamlit as st
from database import init_db, create_user, verify_user
from game import new_game, roll_turn, board_html

st.set_page_config(
    page_title="Snake & Ladder",
    page_icon="🐍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Keep startup errors visible instead of leaving a blank page.
try:
    init_db()
except Exception as exc:
    st.error("Could not initialise the user database.")
    st.exception(exc)
    st.stop()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800&family=Poppins:wght@400;500;600;700;800&display=swap');
:root { color-scheme: dark; }
html, body, [data-testid="stAppViewContainer"] {
  background: #06172c; color: #f5f9ff; font-family: 'Poppins', sans-serif;
}
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer { visibility: hidden; }
.block-container { max-width: 1450px; padding: 1rem 1.2rem 2rem; }
.brand { font-family: 'Baloo 2', sans-serif; font-weight: 800;
  font-size: clamp(2rem, 4vw, 3.8rem); line-height: .95;
  color: #ffe2a0; text-shadow: 0 4px 0 #99451d, 0 7px 15px #0008; }
.brand .red { color: #ff5552; }
.sub { color: #b5d9f6; margin: .65rem 0 1.1rem; }
.panel { background: linear-gradient(145deg,#0b315c,#071e3b);
  border: 2px solid #145a94; border-radius: 22px; padding: 17px;
  box-shadow: 0 8px 28px #0003; margin-bottom: 14px; }
.player { display:flex; align-items:center; gap:12px; background:#0b3b70;
  border:1px solid #277bc0; padding:12px; border-radius:15px; margin:8px 0; }
.dot { width:25px; height:25px; flex:0 0 25px; border-radius:50%;
  box-shadow: inset -4px -4px 0 #0003; }
.muted { color:#b6d1eb; font-size:.88rem; }
.board-wrap { border:4px solid #10cfff; border-radius:22px; padding:5px;
  background:#063f75; box-shadow:0 0 24px #00c8ff33; }
.board { display:grid; grid-template-columns:repeat(10,minmax(0,1fr));
  overflow:hidden; border-radius:12px; border:1px solid #39bfff; }
.cell { aspect-ratio:1/1; min-width:0; position:relative; display:flex;
  align-items:center; justify-content:center; border:1px solid #d6e2eb;
  background:#fff4dd; color:#16446b; font-weight:800;
  font-size:clamp(9px,1.1vw,16px); }
.cell.blue { background:#1386dc; color:white; }
.num { position:absolute; left:4px; top:3px; font-size:clamp(7px,.8vw,12px); }
.pieces { text-align:center; font-size:clamp(12px,1.8vw,24px); line-height:1.1; }
.cell.start, .cell.finish { background:#ffd45d !important; color:#16395d !important; }
div.stButton > button, div.stFormSubmitButton > button {
  border-radius:14px; min-height:3rem; font-weight:800;
  color:white; border:1px solid #29c9ff;
  background:linear-gradient(135deg,#087ef5,#0750c9);
}
div.stButton > button:hover, div.stFormSubmitButton > button:hover {
  color:white; border-color:#a2edff; box-shadow:0 0 15px #00c8ff55;
}
.auth { max-width:600px; margin:3vh auto; padding:24px;
  background:#111e2e; border:1px solid #29415d; border-radius:22px; }
[data-testid="stTextInput"] input { border-radius:10px; }
@media(max-width:700px) {
  .block-container { padding:.6rem .6rem 1.5rem; }
  .num { left:2px; top:1px; }
  .panel { padding:12px; }
}
</style>
""", unsafe_allow_html=True)

def auth_screen():
    st.markdown(
        '<div class="auth"><div class="brand"><span class="red">🐍 SNAKE</span><br>AND LADDER</div>'
        '<p class="sub">Sign in or create an account to play.</p></div>',
        unsafe_allow_html=True,
    )
    login_tab, signup_tab = st.tabs(["Sign in", "Create account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email address", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            if verify_user(email, password):
                st.session_state["user"] = email.strip().lower()
                st.session_state["game"] = new_game()
                st.rerun()
            else:
                st.error("Email or password is incorrect.")

    with signup_tab:
        with st.form("signup_form"):
            email = st.text_input("Email address", key="signup_email", placeholder="you@example.com")
            password = st.text_input("Password (at least 8 characters)", type="password", key="signup_password")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create account", use_container_width=True)
        if submitted:
            if password != confirm:
                st.error("The passwords do not match.")
            elif len(password) < 8:
                st.error("Please use at least 8 characters.")
            else:
                success, message = create_user(email, password)
                if success:
                    st.success("Account created. Please sign in.")
                else:
                    st.error(message)

    st.caption("Note: this version uses email + password but does not send email OTP or verification links.")

if "user" not in st.session_state:
    auth_screen()
    st.stop()

if "game" not in st.session_state:
    st.session_state["game"] = new_game()

game = st.session_state["game"]
left, right = st.columns([3.2, 1.15], gap="large")

with left:
    st.markdown(
        '<div class="brand"><span class="red">🐍 SNAKE</span><br>AND LADDER</div>'
        '<div class="sub">A classic board game · Roll the dice · Race to 100</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="board-wrap">', unsafe_allow_html=True)
    st.markdown(board_html(game), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<p class="muted">🪜 Ladders move you up · 🐍 Snakes send you down · Reach exactly 100 to win.</p>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="panel"><h3>⚙️ Game room</h3><p class="muted">Signed in as ' +
                st.session_state["user"] + '</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="panel"><h3>Players</h3>', unsafe_allow_html=True)
    colors = ["#1ba8ff", "#ff454d", "#ffc928", "#2cdb61"]
    for i, name in enumerate(game["names"]):
        st.markdown(
            f'<div class="player"><div class="dot" style="background:{colors[i]}"></div>'
            f'<div><b>{name}</b><br><span class="muted">Position: {game["positions"][i]}</span></div></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="muted">Current turn</div><h3>{game["names"][game["turn"]]}</h3>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:4.2rem;text-align:center">{game["die"] or "🎲"}</div>', unsafe_allow_html=True)
    if game["winner"] is not None:
        st.success(f'{game["names"][game["winner"]]} wins!')
        if st.button("Play again", use_container_width=True):
            st.session_state["game"] = new_game(game["names"])
            st.rerun()
    elif st.button("🎲 ROLL DICE", use_container_width=True):
        st.session_state["game"] = roll_turn(game)
        st.rerun()
    if game["message"]:
        st.info(game["message"])
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("↻ New game", use_container_width=True):
        st.session_state["game"] = new_game(game["names"])
        st.rerun()
    if st.button("Sign out", use_container_width=True):
        st.session_state.pop("user", None)
        st.session_state.pop("game", None)
        st.rerun()

with st.expander("📖 How to play — Rules"):
    st.markdown("""
    1. Players take turns rolling the dice.
    2. Move forward by the number on the dice.
    3. Landing at the bottom of a ladder takes you to its top.
    4. Landing on a snake sends you down to its tail.
    5. You must land exactly on square 100 to win.
    """)
