import streamlit as st
import io
import random
# ⚠️ Streamlit Secrets dan API keyni olish
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("GROQ_API_KEY topilmadi! .streamlit/secrets.toml faylini tekshiring.")
    st.stop()

from openai import OpenAI
import sqlite3
import hashlib
import datetime
import pandas as pd
from gtts import gTTS # Ovoz uchun

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
add_user("admin", "admin123", "admin")

# ==========================================
# 🎵 OVOZ FUNKSIYASI
# ==========================================
def text_to_audio(text):
    try:
        # Qisqa javoblar uchun tezroq ishlashi uchun
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
# 🎨 DIZAYN (CSS)
# ==========================================
st.markdown("""
<style>
    /* Asosiy fon */
    .stApp { background-color: #f8f9fa; }
    
    /* Dashboard kartochkalari */
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        border-left: 5px solid #4CAF50;
    }
    .metric-card h3 { color: #888; font-size: 16px; margin: 0;}
    .metric-card h2 { color: #333; font-size: 28px; margin: 10px 0;}
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #1e293b;
        color: white;
    }
    .stSidebar .stMarkdown { color: white; }
    
    /* Chat bubbles */
    .stChatMessage {
        border-radius: 15px;
        background-color: white;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🏠 DASHBOARD SAHIFASI
# ==========================================
def show_dashboard(username):
    st.header(f"👋 Xush kelibsiz, {username}!")
    st.markdown("---")

    # 1. Statistika (Metrikalar)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>📅 Bugungi Sana</h3>
            <h2>{}</h2>
        </div>
        """.format(datetime.datetime.now().strftime("%d-%m")), unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>⚡ AI bilan suhbatlar</h3>
            <h2>Faol</h2>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>🏆 Darajangiz</h3>
            <h2>Boshlovchi</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 2. Kun hikmati (Random Motivatsiya)
    quotes = [
        "Bilim — bu kuch! 🚀",
        "Kodni xato qilishdan qo'rqma, xato — bu ustoz. 💻",
        "Bugun kechagidan yaxshiroq bo'lishga harakat qiling. ⭐",
        "Kelajak bugun yaratiladi. 🔥"
    ]
    st.info(f"💡 **Kun hikmati:** {random.choice(quotes)}")

    # 3. Biz haqimizda
    with st.expander("ℹ️ Loyiha haqida (Biz kimmiz?)"):
        st.write("""
        **Zukko AI** — bu O'zbekistondagi eng zamonaviy ta'lim yordamchisi.
        
        **Bizning maqsadimiz:**
        - Har bir o'quvchiga shaxsiy AI o'qituvchi berish.
        - Ta'limni qiziqarli va interaktiv qilish.
        - 24/7 davomida savollaringizga javob berish.
        
        *Loyiha muallifi: [Sizning Ismingiz]*
        """)

# ==========================================
# 🖥️ ASOSIY DASTUR LOGIKASI
# ==========================================

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""

    # --- LOGIN OYNASI ---
    if not st.session_state.logged_in:
        st.title("🎓 Zukko AI Kirish")
        menu = ["Kirish", "Ro'yxatdan o'tish"]
        choice = st.sidebar.selectbox("Menyu", menu)

        if choice == "Kirish":
            username = st.text_input("Login")
            password = st.text_input("Parol", type='password')
            if st.button("Kirish"):
                result = login_user(username, password)
                if result:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.role = result[0][2]
                    add_log(username, "Kirdi")
                    st.rerun()
                else:
                    st.error("Xato login!")

        elif choice == "Ro'yxatdan o'tish":
            new_user = st.text_input("Yangi Login")
            new_pass = st.text_input("Yangi Parol", type='password')
            if st.button("Yaratish"):
                if add_user(new_user, new_pass):
                    st.success("Yaratildi! Kiring.")
                    add_log(new_user, "Ro'yxatdan o'tdi")
                else:
                    st.error("Login band!")

    # --- TIZIM ICHIDA ---
    else:
        # Sidebar menyu
        with st.sidebar:
            st.title("Zukko AI")
            st.caption(f"Foydalanuvchi: {st.session_state.username}")
            
            # Navigatsiya
            page = st.radio("Bo'limlar:", ["🏠 Dashboard", "🤖 AI Chat", "🛡️ Admin Panel"])
            
            st.markdown("---")
            if st.button("Chiqish"):
                st.session_state.logged_in = False
                st.rerun()

        # 1. DASHBOARD
        if page == "🏠 Dashboard":
            show_dashboard(st.session_state.username)

        # 2. ADMIN PANEL (Faqat Adminga)
        elif page == "🛡️ Admin Panel":
            if st.session_state.role == "admin":
                st.header("Admin Panel")
                st.dataframe(view_all_users())
                st.dataframe(view_logs())
            else:
                st.warning("Siz Admin emassiz! 🚫")

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
            
            # Chat tarixi
            if "messages" not in st.session_state: st.session_state.messages = []
            
            # Tozalash va Test tugmalari
            c1, c2 = st.columns([1, 5])
            with c1:
                if st.button("🗑️ Tozalash"):
                    st.session_state.messages = []
                    st.rerun()
            with c2:
                if st.button("📝 Test tuzish"):
                    st.session_state.messages.append({"role": "user", "content": "Mavzu bo'yicha 3 ta test tuzib ber."})

            # Tarixni chiqarish
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
                        
                        # Ovoz chiqarish
                        audio = text_to_audio(full_text)
                        if audio: st.audio(audio, format="audio/mp3")
                
                st.session_state.messages.append({"role": "assistant", "content": full_text})

if __name__ == "__main__":
    main()