import streamlit as st
import io
import random
# ⚠️ Streamlit Secrets dan API keyni olish
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    # Agar lokalda ishlatayotgan bo'lsangiz va xato bersa, shunchaki pastdagi qatorni ochib, kalitni yozing:
    # GROQ_API_KEY = "gsk_..." 
    st.error("GROQ_API_KEY topilmadi! .streamlit/secrets.toml faylini tekshiring.")
    st.stop()

from openai import OpenAI
import sqlite3
import hashlib
import datetime
import pandas as pd
from gtts import gTTS

MODEL_NAME = "llama-3.3-70b-versatile"

st.set_page_config(page_title="Zukko AI", page_icon="⚡", layout="wide")

# ==========================================
# 🗄️ BAZA (BACKEND)
# ==========================================
def init_db():
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (username TEXT, action TEXT, time TEXT)''')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def add_user(username, password, role="student"):
    # Har doim kichik harfda saqlaymiz
    username = username.lower().strip()
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password, role) VALUES (?,?,?)', 
                  (username, make_hashes(password), role))
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

def add_log(username, action):
    conn = sqlite3.connect('zukko_school.db')
    c = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO logs(username, action, time) VALUES (?,?,?)', (username, action, now))
    conn.commit()
    conn.close()

def view_all_users():
    conn = sqlite3.connect('zukko_school.db')
    df = pd.read_sql_query("SELECT username, role FROM users", conn)
    conn.close()
    return df

def view_logs():
    conn = sqlite3.connect('zukko_school.db')
    df = pd.read_sql_query("SELECT * FROM logs ORDER BY time DESC", conn)
    conn.close()
    return df

init_db()

# Parolni faqat serverdan olamiz.
# Agar serverda parol bo'lmasa, Admin umuman yaratilmaydi (yoki xato beradi).
if "ADMIN_PASSWORD" in st.secrets:
    real_pass = st.secrets["ADMIN_PASSWORD"]
    add_user("admin", real_pass, "admin")
else:
    # Bu yerga hech narsa yozma yoki shunchaki print qil
    print("Diqqat: Admin paroli topilmadi!")

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
                temperature=0.7,
                max_tokens=1500,
                stream=True,
            )
            return stream
        except Exception as e:
            return str(e)

# ==========================================
# 🎨 DIZAYN (TUZATILGAN CSS)
# ==========================================
st.markdown("""
<style>
    /* Dashboard Kartochkalari - Universal Ranglar */
    .metric-card {
        background-color: rgba(128, 128, 128, 0.1); /* Shaffof kulrang */
        padding: 20px;
        border-radius: 10px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        text-align: center;
        margin-bottom: 10px;
    }
    
    /* Sidebar matnlarini majburan oq qilishni OLIB TASHLADIM. 
       Endi Streamlit o'zi hal qiladi (Darkda oq, Lightda qora bo'ladi) */
       
    /* Chat Pufakchalari (Bubbles) */
    .stChatMessage {
        background-color: transparent;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    
    /* Foydalanuvchi xabari */
    div[data-testid="stChatMessage"][data-author="user"] {
        background-color: rgba(76, 175, 80, 0.1); /* Och yashil fon */
    }
    
    /* AI xabari */
    div[data-testid="stChatMessage"][data-author="assistant"] {
        background-color: rgba(33, 150, 243, 0.1); /* Och ko'k fon */
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🏠 DASHBOARD SAHIFASI
# ==========================================
def show_dashboard(username):
    st.header(f"👋 Xush kelibsiz, {username.title()}!")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📅 Bugungi Sana</h3>
            <h2>{datetime.datetime.now().strftime("%d-%m-%Y")}</h2>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>⚡ Status</h3>
            <h2>Online</h2>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        # Rolni chiroyli ko'rsatish
        role_display = "Admin 🛡️" if st.session_state.role == "admin" else "O'quvchi 🎓"
        st.markdown(f"""
        <div class="metric-card">
            <h3>🏆 Rolingiz</h3>
            <h2>{role_display}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    quotes = [
        "Bilim — bu kuch! 🚀",
        "Kodni xato qilishdan qo'rqma, xato — bu ustoz. 💻",
        "Bugun kechagidan yaxshiroq bo'lishga harakat qiling. ⭐",
        "Kelajak bugun yaratiladi. 🔥"
    ]
    st.info(f"💡 **Kun hikmati:** {random.choice(quotes)}")

    with st.expander("ℹ️ Loyiha haqida"):
        st.write("""
        **Zukko AI** — bu O'zbekistondagi eng zamonaviy ta'lim yordamchisi.
        Admin Panel va Sun'iy Intellekt integratsiyasi.
        """)

# ==========================================
# 🖥️ ASOSIY DASTUR
# ==========================================

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""

    # --- LOGIN OYNASI ---
    if not st.session_state.logged_in:
        st.title("🎓 Zukko AI Kirish")
        
        tab1, tab2 = st.tabs(["Kirish", "Ro'yxatdan o'tish"])
        
        with tab1:
            username = st.text_input("Login", key="login_user")
            password = st.text_input("Parol", type='password', key="login_pass")
            if st.button("Kirish"):
                result = login_user(username, password)
                if result:
                    st.session_state.logged_in = True
                    st.session_state.username = result[0][0] # Bazadagi to'g'ri nom
                    st.session_state.role = result[0][2]     # Bazadagi rol
                    add_log(username, "Kirdi")
                    st.rerun()
                else:
                    st.error("Login yoki parol xato!")

        with tab2:
            new_user = st.text_input("Yangi Login", key="reg_user")
            new_pass = st.text_input("Yangi Parol", type='password', key="reg_pass")
            if st.button("Yaratish"):
                if add_user(new_user, new_pass):
                    st.success("Yaratildi! Endi 'Kirish' bo'limidan kiring.")
                    add_log(new_user, "Ro'yxatdan o'tdi")
                else:
                    st.error("Bu login band!")

    # --- TIZIM ICHIDA ---
    else:
        # Sidebar
        with st.sidebar:
            st.title("Zukko AI")
            st.caption(f"Foydalanuvchi: {st.session_state.username}")
            
            # Navigatsiya
            page = st.radio("Bo'limlar:", ["🏠 Dashboard", "🤖 AI Chat", "🛡️ Admin Panel"])
            
            st.markdown("---")
            if st.button("Chiqish 🚪"):
                st.session_state.logged_in = False
                st.rerun()

        # 1. DASHBOARD
        if page == "🏠 Dashboard":
            show_dashboard(st.session_state.username)

        # 2. ADMIN PANEL
        elif page == "🛡️ Admin Panel":
            # Admin ekanligini tekshirish (aniq tekshirish)
            if st.session_state.role == "admin":
                st.header("🛡️ Admin Boshqaruv Paneli")
                
                tab_users, tab_logs = st.tabs(["Foydalanuvchilar", "Loglar"])
                with tab_users:
                    st.dataframe(view_all_users(), use_container_width=True)
                with tab_logs:
                    st.dataframe(view_logs(), use_container_width=True)
            else:
                st.error("⛔ Siz Admin emassiz! Bu bo'limga kirish taqiqlangan.")
                st.image("https://cdn-icons-png.flaticon.com/512/6897/6897039.png", width=100)

        # 3. AI CHAT
        elif page == "🤖 AI Chat":
            st.subheader("🤖 AI bilan suhbat")
            
            mode_choice = st.selectbox("Mavzuni tanlang:", 
                ["🌐 Universal Yordamchi", "1-sinf", "2-sinf", "3-sinf", "4-sinf"]
            )
            
            prompts = {
                "🌐 Universal Yordamchi": {"role": "AI", "prompt": "Sen Zukko AIsan. Do'stona yordamchisan."},
                "1-sinf": {"role": "O'qituvchi", "prompt": "Sen 1-sinf o'qituvchisisan. Oddiy gapir."},
                "2-sinf": {"role": "Matematik", "prompt": "Matematika o'rgat."},
                "3-sinf": {"role": "Tabiatshunos", "prompt": "Tabiat haqida gapir."},
                "4-sinf": {"role": "IT Ustoz", "prompt": "Ingliz tili va IT o'rgat."}
            }
            
            if "messages" not in st.session_state: st.session_state.messages = []
            
            # Tugmalar paneli
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🗑️ Tozalash"):
                    st.session_state.messages = []
                    st.rerun()
            with col2:
                if st.button("📝 Test tuzish"):
                    st.session_state.messages.append({"role": "user", "content": "Mavzu bo'yicha 3 ta test tuzib ber."})

            # Chat tarixi
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            # Input
            if prompt := st.chat_input("Yozing..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)

                with st.chat_message("assistant"):
                    engine = ZukkoEngine()
                    placeholder = st.empty()
                    full_text = ""
                    stream = engine.generate(st.session_state.messages, prompts[mode_choice]['prompt'])
                    
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
                
                st.session_state.messages.append({"role": "assistant", "content": full_text})

if __name__ == "__main__":
    main()