import streamlit as st
import sqlite3
import datetime
import json
import os

# --- 1. 页面极速配置 ---
st.set_page_config(page_title="VocabPro", layout="centered")

# 注入 CSS：优化手机端触感并隐藏多余组件
st.markdown("""
<style>
    .block-container { max-width: 450px !important; padding: 1rem !important; }
    #MainMenu, footer { visibility: hidden; }
    .stButton>button { 
        border-radius: 12px; height: 3.5em; font-weight: 500; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stProgress > div > div > div > div { background-color: #1f538d; }
</style>
""", unsafe_allow_html=True)

# --- 2. 数据库性能加速 ---
@st.cache_resource
def init_db():
    conn = sqlite3.connect("vocab_ultimate_pro.db", check_same_thread=False)
    # WAL模式：显著提升局域网并发访问稳定性
    conn.execute('PRAGMA journal_mode=WAL') 
    conn.execute('CREATE TABLE IF NOT EXISTS words (id INTEGER PRIMARY KEY, en TEXT, hu TEXT, en_sent TEXT, hu_sent TEXT, level INTEGER DEFAULT 0, next_review DATETIME)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_review ON words(next_review)')
    return conn

# --- 3. 语音引擎补丁 (支持 iOS 自动播放尝试) ---
def render_pro_card(main_t, sent_t, lang):
    t1, t2 = main_t.replace("'", "\\'"), sent_t.replace("'", "\\'")
    is_hu = (lang == 'hu-HU')
    theme = '#1f538d' if is_hu else '#4a90e2'
    bg = '#f0f7ff' if is_hu else '#ffffff'
    
    html_code = f"""
    <div id="v-card" style="background:{bg}; border:2.4px solid {theme}; padding:25px; border-radius:20px; text-align:center; cursor:pointer; -webkit-tap-highlight-color:transparent;">
        <h1 style="margin:5px 0; font-size:28px; color:{theme}; font-family: -apple-system, sans-serif;">{main_t}</h1>
        <p style="margin:10px 0 0 0; color:#444; font-size:16px; font-family: -apple-system, sans-serif;">{sent_t}</p>
    </div>
    <script>
        var card = document.getElementById('v-card');
        function speak() {{
            var s = window.speechSynthesis;
            if (s.speaking) s.cancel();
            var u1 = new SpeechSynthesisUtterance('{t1}');
            var u2 = new SpeechSynthesisUtterance('{t2}');
            u1.lang = u2.lang = '{lang}';
            u1.rate = 0.85; u2.rate = 0.8;
            
            // 匹配高级语音包
            var voices = s.getVoices();
            var target = voices.find(v => v.name.includes("Tunde") || v.name.includes("Enhanced"));
            if(target && '{lang}'==='hu-HU') {{ u1.voice = target; u2.voice = target; }}
            
            s.speak(u1);
            u1.onend = function() {{ setTimeout(function() {{ s.speak(u2); }}, 400); }};
        }}
        card.onclick = speak;
        
        // iOS 自动播放尝试：在页面加载后稍作延迟触发
        window.addEventListener('load', function() {{
            setTimeout(speak, 300);
        }});
    </script>
    """
    st.components.v1.html(html_code, height=195)

# --- 4. 业务逻辑核心 ---
conn = init_db()

# 数据统计（缓存1分钟以提升响应速度）
@st.cache_data(ttl=60)
def get_stats(_conn):
    stats = _conn.execute("SELECT COUNT(*), (SELECT COUNT(*) FROM words WHERE next_review > ?) FROM words", (datetime.datetime.now(),)).fetchone()
    return stats if stats else (0, 0)

total, done = get_stats(conn)

# 顶部进度条
st.progress(done/total if total > 0 else 0)
st.caption(f"📊 今日进度: {done}/{total} 词")

if 'show_ans' not in st.session_state:
    st.session_state.show_ans = False

# 查询下一个单词
word_data = conn.execute("SELECT * FROM words WHERE next_review <= ? ORDER BY level ASC LIMIT 1", (datetime.datetime.now(),)).fetchone()

if word_data:
    w_id, en, hu, en_s, hu_s, level, _ = word_data
    
    if not st.session_state.show_ans:
        # 正面：英文
        render_pro_card(en, en_s, 'en-US')
        if st.button("🔍 查看翻译 (或点击上方听音)", use_container_width=True):
            st.session_state.show_ans = True
            st.rerun()
    else:
        # 反面：匈牙利文
        render_pro_card(hu, hu_s, 'hu-HU')
        st.divider()
        # 评分按钮组
        cols = st.columns(4)
        grades = [("❌",0), ("❓",1), ("✅",3), ("🌟",5)]
        for i, (icon, val) in enumerate(grades):
            if cols[i].button(icon, key=f"gr_{val}", use_container_width=True):
                # 更新复习时间
                days = {0:0, 1:1, 3:7, 5:30}[val]
                next_t = datetime.datetime.now() + datetime.timedelta(days=days)
                conn.execute("UPDATE words SET level=?, next_review=? WHERE id=?", (val, next_t, w_id))
                conn.commit()
                st.session_state.show_ans = False
                st.rerun()
else:
    st.balloons()
    st.success("🎉 太棒了！今日任务已全部扫清！")
    if st.button("重新复习已掌握词汇"):
        conn.execute("UPDATE words SET next_review = ?", (datetime.datetime.now(),))
        conn.commit()
        st.rerun()
