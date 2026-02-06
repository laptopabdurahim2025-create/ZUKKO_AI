import streamlit as st
import io
import random
import time
from openai import OpenAI
import sqlite3
import hashlib
import datetime
import pandas as pd
from gtts import gTTS

# ⚠️ Streamlit Secrets
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("GROQ_API_KEY topilmadi! .streamlit/secrets.toml faylini tekshiring.")
    st.stop()

MODEL_NAME = "llama-3.3-70b-versatile"

st.set_page_config(page_title="Zukko AI", page_icon="⚡", layout="wide")

# ==========================================
# 🗄️ BAZA (BACKEND) - YANGILANGAN
# ==========================================
def init_db():
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    # Users jadvaliga 'coins' ustuni qo'shildi
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT, coins INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (username TEXT, action TEXT, time TEXT)''')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def add_user(username, password, role="student"):
    username = username.lower().strip()
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    try:
        # Yangi userga 0 coin beramiz
        c.execute('INSERT INTO users(username, password, role, coins) VALUES (?,?,?,?)', 
                  (username, make_hashes(password), role, 0))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def login_user(username, password):
    username = username.lower().strip()
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username =? AND password = ?', 
              (username, make_hashes(password)))
    data = c.fetchall()
    conn.close()
    return data

# --- COIN QO'SHISH FUNKSIYASI ---
def add_coins(username, amount):
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins + ? WHERE username = ?", (amount, username))
    conn.commit()
    conn.close()
    st.toast(f"🎉 Tabriklaymiz! +{amount} Coin oldingiz!", icon="💰")

def get_user_coins(username):
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE username = ?", (username,))
    data = c.fetchone()
    conn.close()
    return data[0] if data else 0

def get_leaderboard():
    conn = sqlite3.connect('zukko_school.db')
    df = pd.read_sql_query("SELECT username, coins FROM users ORDER BY coins DESC LIMIT 10", conn)
    conn.close()
    return df

def add_log(username, action):
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO logs(username, action, time) VALUES (?,?,?)', (username, action, now))
    conn.commit()
    conn.close()

def view_all_users():
    conn = sqlite3.connect('zukko_school.db')
    df = pd.read_sql_query("SELECT username, role, coins FROM users", conn)
    conn.close()
    return df

def view_logs():
    conn = sqlite3.connect('zukko_school.db')
    df = pd.read_sql_query("SELECT * FROM logs ORDER BY time DESC", conn)
    conn.close()
    return df

init_db()

# Admin parolini serverdan olamiz
if "ADMIN_PASSWORD" in st.secrets:
    real_pass = st.secrets["ADMIN_PASSWORD"]
    add_user("admin", real_pass, "admin")

# ==========================================
# 🎵 OVOZ FUNKSIYASI
# ==========================================
def text_to_audio(text):
    try:
        if len(text) > 500: text = text[:500] + "..." 
        tts = gTTS(text=text, lang='tr', slow=False) 
        audio_bytes = io.BytesIO()
        tts.write_to_fp(audio_bytes)
        return audio_bytes
    except:
        return None

# ==========================================
# 🧠 AI ENGINE
# ==========================================
class ZukkoEngine:
    def __init__(self):
        self.client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)

    def generate(self, messages, system_prompt):
        full_history = [{"role": "system", "content": system_prompt}] + messages
        try:
            stream = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=full_history,
                temperature=0.6,
                max_tokens=1500,
                stream=True,
            )
            return stream
        except Exception as e:
            return str(e)

# ==========================================
# 🎨 DIZAYN (CSS)
# ==========================================
st.markdown("""
<style>
    .metric-card {
        background-color: rgba(128, 128, 128, 0.1);
        padding: 20px;
        border-radius: 10px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        text-align: center;
        margin-bottom: 10px;
    }
    .stChatMessage {
        background-color: transparent;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    div[data-testid="stChatMessage"][data-author="user"] {
        background-color: rgba(76, 175, 80, 0.1);
    }
    div[data-testid="stChatMessage"][data-author="assistant"] {
        background-color: rgba(33, 150, 243, 0.1);
    }
    /* Google Button Stili */
    .google-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: white;
        color: #757575;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
        width: 100%;
        cursor: pointer;
        font-weight: bold;
        margin-top: 10px;
    }
    .google-btn:hover {
        background-color: #f1f1f1;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🏠 DASHBOARD
# ==========================================
def show_dashboard(username):
    # User coinlarini olish
    coins = get_user_coins(username)
    
    st.header(f"👋 Xush kelibsiz, {username.title()}!")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="metric-card"><h3>💰 Mening Tangalarim</h3><h2>{coins} 🟡</h2></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""<div class="metric-card"><h3>⚡ Status</h3><h2>Online</h2></div>""", unsafe_allow_html=True)
    with col3:
        role_display = "Admin 🛡️" if st.session_state.role == "admin" else "O'quvchi 🎓"
        st.markdown(f"""<div class="metric-card"><h3>🏆 Rolingiz</h3><h2>{role_display}</h2></div>""", unsafe_allow_html=True)

    # Kun hikmati
    quotes = ["Bilim — boylikdan ustun. 💰", "Har bir coin — bilim belgisi! 🟡", "O'rganishdan to'xtama! 🚀"]
    st.info(f"💡 **Kun hikmati:** {random.choice(quotes)}")

# ==========================================
# 🖥️ ASOSIY DASTUR
# ==========================================

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""

    # --- KIRISH QISMI ---
    if not st.session_state.logged_in:
        col_c = st.container()
        
        with col_c:
            st.title("🎓 Zukko AI")
            st.markdown("### O'qing, Coin yig'ing va Reytingda birinchi bo'ling!")
            
            tab1, tab2 = st.tabs(["🔑 Kirish", "📝 Ro'yxatdan o'tish"])
            with tab1:
                username = st.text_input("Login", key="login_user")
                password = st.text_input("Parol", type='password', key="login_pass")
                if st.button("Kirish", use_container_width=True):
                    result = login_user(username, password)
                    if result:
                        st.session_state.logged_in = True
                        st.session_state.username = result[0][0] 
                        st.session_state.role = result[0][2]     
                        add_log(username, "Kirdi")
                        st.rerun()
                    else:
                        st.error("Login xato!")
                
                # FAKE GOOGLE BUTTON (Dizayn uchun)
                st.markdown("""
                <button class="google-btn">
                    <img src="https://img.icons8.com/color/16/000000/google-logo.png" style="margin-right:8px;"> Google orqali kirish (Tez kunda)
                </button>
                """, unsafe_allow_html=True)

            with tab2:
                new_user = st.text_input("Yangi Login", key="reg_user")
                new_pass = st.text_input("Yangi Parol", type='password', key="reg_pass")
                if st.button("Yaratish", use_container_width=True):
                    if add_user(new_user, new_pass):
                        st.success("Yaratildi! 50 Coin bonus berildi 🟡")
                        add_coins(new_user, 50) # Bonus
                        add_log(new_user, "Ro'yxatdan o'tdi")
                    else:
                        st.error("Login band!")

    # --- TIZIM ICHIDA ---
    else:
        with st.sidebar:
            st.title("Zukko AI")
            my_coins = get_user_coins(st.session_state.username)
            st.metric("Balans", f"{my_coins} Coin", "🟡")
            st.caption(f"Foydalanuvchi: {st.session_state.username}")
            
            # MENYU (YANGI BO'LIMLAR)
            page = st.radio("Bo'limlar:", ["🏠 Dashboard", "🤖 AI Chat", "🏆 Reyting", "🛒 Do'kon", "🛡️ Admin Panel"])
            
            st.markdown("---")
            if st.button("Chiqish 🚪"):
                st.session_state.logged_in = False
                st.rerun()

        if page == "🏠 Dashboard":
            show_dashboard(st.session_state.username)

        # --- 🏆 REYTING (LEADERBOARD) ---
        elif page == "🏆 Reyting":
            st.header("🏆 Eng kuchli bilimdonlar")
            st.markdown("Kim eng ko'p Coin yig'sa, shu yerda turadi!")
            
            df = get_leaderboard()
            # Chiroyli jadval
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            if st.session_state.username in df['username'].values:
                st.balloons()

        # --- 🛒 DO'KON (SHOP) ---
        elif page == "🛒 Do'kon":
            st.header("🛒 Zukko Market")
            st.info("Yig'gan tangalaringizni shu yerda ishlating (Tez kunda ochiladi!)")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.image("https://cdn-icons-png.flaticon.com/512/4140/4140048.png", width=100)
                st.write("**Pro Avatar**")
                st.button("Sotib olish (500 🟡)", key="b1", disabled=True)
            with c2:
                st.image("https://cdn-icons-png.flaticon.com/512/6422/6422206.png", width=100)
                st.write("**Oltin Ramka**")
                st.button("Sotib olish (1000 🟡)", key="b2", disabled=True)
            with c3:
                st.image("https://cdn-icons-png.flaticon.com/512/616/616490.png", width=100)
                st.write("**Admin bilan suhbat**")
                st.button("Sotib olish (5000 🟡)", key="b3", disabled=True)

        elif page == "🛡️ Admin Panel":
            if st.session_state.role == "admin":
                st.header("🛡️ Admin Panel")
                st.dataframe(view_all_users(), use_container_width=True)
                st.dataframe(view_logs(), use_container_width=True)
            else:
                st.error("⛔ Siz Admin emassiz!")

        # --- AI CHAT ---
        elif page == "🤖 AI Chat":
            st.subheader("🤖 AI Mentor")
            
            mentor_type = st.selectbox("Yordamchi turini tanlang:", [
                "🌐 Universal Yordamchi", "🇬🇧 Ingliz tili", "💻 IT va Dasturlash", 
                "📚 Ona tili", "📐 Matematika va Fizika", "🏫 Boshlang'ich Sinflar"
            ])

            # Promptlar
            system_prompt = "Sen Zukko AIsan."
            if mentor_type == "🇬🇧 Ingliz tili": system_prompt = "You are an English teacher. Correct mistakes."
            elif mentor_type == "💻 IT va Dasturlash": system_prompt = "Sen IT mentorsan. Python va Web o'rgat."
            elif mentor_type == "🏫 Boshlang'ich Sinflar": system_prompt = "Sen boshlang'ich sinf o'qituvchisisan. Sodda gapir."

            # Chat tarixi
            if "messages" not in st.session_state: st.session_state.messages = []
            
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("🗑️ Tozalash"):
                    st.session_state.messages = []
                    st.rerun()
            with c2:
                if st.button("📝 Test tuzish (+10 Coin)"):
                    st.session_state.messages.append({"role": "user", "content": "Mavzu bo'yicha 3 ta test tuzib ber."})
                    add_coins(st.session_state.username, 10) # Test so'rasa coin beramiz

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])

            if prompt := st.chat_input("Yozing..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)

                with st.chat_message("assistant"):
                    engine = ZukkoEngine()
                    placeholder = st.empty()
                    full_text = ""
                    stream = engine.generate(st.session_state.messages, system_prompt)
                    
                    if isinstance(stream, str):
                        st.error(stream)
                    else:
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full_text += chunk.choices[0].delta.content
                                placeholder.markdown(full_text + "▌")
                        placeholder.markdown(full_text)
                        
                        audio = text_to_audio(full_text)
                        if audio: st.audio(audio, format="audio/mp3")
                
                # Chatlashgani uchun ham Coin beramiz (+1)
                add_coins(st.session_state.username, 1) 
                st.session_state.messages.append({"role": "assistant", "content": full_text})

if __name__ == "__main__":
    main()