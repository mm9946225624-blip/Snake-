
import streamlit as st
import sqlite3
import random
from pathlib import Path

# ==========================================
# DATABASE CODE - INCLUDED IN THIS SAME FILE
# ==========================================

DB_FILE = Path(__file__).resolve().parent / "game_history.db"


def create_database():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                result TEXT NOT NULL,
                dice_rolls INTEGER NOT NULL,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_game(player_name, result, dice_rolls):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            INSERT INTO game_history
            (player_name, result, dice_rolls)
            VALUES (?, ?, ?)
        """, (player_name, result, dice_rolls))


def get_history():
    with sqlite3.connect(DB_FILE) as conn:
        return conn.execute("""
            SELECT player_name, result, dice_rolls, played_at
            FROM game_history
            ORDER BY id DESC
            LIMIT 20
        """).fetchall()


# Create the database automatically
create_database()


# ==========================================
# GAME SETTINGS
# ==========================================

SNAKES = {
    99: 54,
    70: 55,
    52: 42,
    25: 2,
    95: 72,
    64: 60,
    89: 68
}

LADDERS = {
    6: 25,
    11: 40,
    17: 69,
    46: 90,
    60: 85,
    63: 81,
    71: 92
}


# ==========================================
# STREAMLIT INTERFACE
# ==========================================

st.set_page_config(
    page_title="Snake and Ladder",
    page_icon="🎲",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: #101b2d;
    color: white;
}
h1, h2, h3, p, label {
    color: white !important;
}
div.stButton > button {
    width: 100%;
    min-height: 45px;
    border-radius: 10px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

st.title("🐍 Snake & Ladder 🎲")
st.write("Play the classic game — no login or registration required.")

player_name = st.text_input("Enter player name", "Player 1").strip()
if not player_name:
    player_name = "Player 1"


# ==========================================
# GAME STATE
# ==========================================

def new_game():
    st.session_state.position = 1
    st.session_state.rolls = 0
    st.session_state.last_roll = "-"
    st.session_state.message = "Roll the dice to begin!"
    st.session_state.finished = False
    st.session_state.saved = False


if "position" not in st.session_state:
    new_game()


# ==========================================
# DRAW BOARD
# ==========================================

def draw_board(position):
    st.subheader("🎮 Game Board")

    for row in range(9, -1, -1):
        numbers = list(range(row * 10 + 1, row * 10 + 11))

        # Alternate row direction
        if row % 2 == 1:
            numbers.reverse()

        columns = st.columns(10)

        for column, number in zip(columns, numbers):
            if number == position:
                label = f"🧍 {number}"
                background = "#ffc857"
            elif number in SNAKES:
                label = f"🐍 {number}"
                background = "#ffb4b4"
            elif number in LADDERS:
                label = f"🪜 {number}"
                background = "#a8f0c6"
            elif number == 100:
                label = f"🏆 {number}"
                background = "#b9fbc0"
            else:
                label = str(number)
                background = "#e6edf5"

            column.markdown(
                f"""
                <div style="
                    background:{background};
                    color:#172238;
                    text-align:center;
                    padding:8px 0;
                    margin:2px 0;
                    border-radius:6px;
                    font-weight:bold;
                    min-height:22px;">
                    {label}
                </div>
                """,
                unsafe_allow_html=True
            )


draw_board(st.session_state.position)


# ==========================================
# PLAYER INFORMATION
# ==========================================

left, right = st.columns(2)

with left:
    st.metric("📍 Current Position", st.session_state.position)
    st.metric("🎲 Total Dice Rolls", st.session_state.rolls)

with right:
    st.metric("🎲 Last Dice Roll", st.session_state.last_roll)
    st.info(st.session_state.message)


# ==========================================
# ROLL DICE AND MOVE
# ==========================================

if not st.session_state.finished:

    if st.button("🎲 ROLL THE DICE", type="primary"):
        dice = random.randint(1, 6)
        st.session_state.last_roll = dice
        st.session_state.rolls += 1

        target = st.session_state.position + dice

        if target > 100:
            st.session_state.message = (
                f"You rolled {dice}. You need an exact roll to reach 100!"
            )

        else:
            st.session_state.position = target

            if target in SNAKES:
                destination = SNAKES[target]
                st.session_state.position = destination
                st.session_state.message = (
                    f"🐍 Snake! You slid from {target} to {destination}."
                )

            elif target in LADDERS:
                destination = LADDERS[target]
                st.session_state.position = destination
                st.session_state.message = (
                    f"🪜 Ladder! You climbed from {target} to {destination}."
                )

            elif target == 100:
                st.session_state.finished = True
                st.session_state.message = (
                    f"🏆 Congratulations, {player_name}! You won!"
                )

                if not st.session_state.saved:
                    save_game(
                        player_name,
                        "WIN",
                        st.session_state.rolls
                    )
                    st.session_state.saved = True

            else:
                st.session_state.message = (
                    f"You rolled {dice} and moved to {target}."
                )

        st.rerun()


# ==========================================
# WIN MESSAGE AND RESTART
# ==========================================

if st.session_state.finished:
    st.success(
        f"🎉 Congratulations, {player_name}! "
        f"You won in {st.session_state.rolls} rolls!"
    )

if st.button("🔄 NEW GAME"):
    new_game()
    st.rerun()


# ==========================================
# DATABASE HISTORY
# ==========================================

st.divider()
st.subheader("📚 Recent Game History")

history = get_history()

if history:
    st.dataframe(
        [
            {
                "Player": row[0],
                "Result": row[1],
                "Dice Rolls": row[2],
                "Played At": row[3]
            }
            for row in history
        ],
        use_container_width=True,
        hide_index=True
    )
else:
    st.write("No completed games yet. Win a game to save your history.")
