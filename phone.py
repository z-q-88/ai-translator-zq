import streamlit as st
from groq import Groq
from streamlit_mic_recorder import mic_recorder
import streamlit.components.v1 as components
import os

# --- 1. 初始化设置 ---
st.set_page_config(page_title="🧞‍♂️ AI 智能传译 (严格传声筒版)", layout="centered")

# ⚠️⚠️⚠️ 安全修改：不要直接在代码里写 Key ⚠️⚠️⚠️
# 原来的代码：API_KEY = "gsk_xxxx..." (删掉！)

# 新的代码：告诉程序去“云端保险箱 (Secrets)”里找钥匙
try:
    API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=API_KEY)
except Exception as e:
    st.error("🚨 还没配置密钥！部署后请在 Streamlit Secrets 里填入 GROQ_API_KEY。")
    st.stop()

# 初始化 Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None

# --- 2. 核心大脑 (Translation - 严格模式) 🧠 ---
def ai_translator(text_input, target_lang="en"):
    if target_lang == "en":
        # 🟢 核心修改：中 -> 英 (严格传声筒模式)
        system_prompt = """
        You are a neutral real-time translation tool, NOT an assistant or a salesperson.
        
        YOUR MISSION:
        Translate the user's Chinese text directly and accurately into English.
        
        CRITICAL RULES (DO NOT IGNORE):
        1. NO Interpretation: Do not explain the context (e.g., do not mention shipping, FOB, or software speed).
        2. NO Answering: Do not answer the user's question. If the user asks "Can you be faster?", translate that question into English, do not answer "Yes I can".
        3. NO Additions: Do not add polite phrases or sales terminology (like "Dear customer") unless they are in the original text.
        4. Output ONLY the translated English text.
        """
    else:
        # 🔵 英 -> 中 (保持简体中文 + 准确翻译)
        system_prompt = """
        You are a translator. Translate the English text into clear, natural Simplified Chinese (简体中文).
        Output ONLY the translation. Do NOT use Traditional Chinese.
        Do NOT answer the question, just translate it.
        """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_input}
            ],
            temperature=0.6,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# --- 3. 核心耳朵 (Auto-Detect Language) ---
def transcribe_auto_detect(file_path):
    try:
        with open(file_path, "rb") as file:
            result = client.audio.transcriptions.create(
                file=(file_path, file.read()),
                model="whisper-large-v3",
                response_format="verbose_json" 
            )
        return result.text, result.language
    except Exception as e:
        st.error(f"听觉故障: {str(e)}")
        return "", ""

# --- 4. 极速发音 (JS) ---
def speak_instant(text, lang="en"):
    safe_text = text.replace('"', '\\"').replace("'", "\\'").replace("\n", " ")
    lang_code = 'en-US' if lang == 'en' else 'zh-CN'
    js_code = f"""
    <script>
        window.speechSynthesis.cancel();
        var msg = new SpeechSynthesisUtterance("{safe_text}");
        msg.lang = "{lang_code}";
        window.speechSynthesis.speak(msg);
    </script>
    """
    components.html(js_code, height=0)

# --- 5. 界面布局 ---
st.title("🧞‍♂️ AI 智能传译 (严格版)")

status_area = st.empty()
status_area.info("💡 提示：点击下方按钮开始，说完话后【必须再次点击】按钮来发送。")

# A. 聊天记录
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# B. 底部操作区
st.divider()

audio_data = mic_recorder(
    start_prompt="🔴 点击开始录音", 
    stop_prompt="⏹️ 录音中... (说完点此发送)", 
    key='auto_rec'
)

# --- C. 智能逻辑处理 ---
if audio_data:
    current_bytes = audio_data['bytes']
    if current_bytes != st.session_state.last_processed_audio:
        
        status_area.warning("⏳ 正在处理音频，请稍候...")
        
        with open("temp_audio.wav", "wb") as f: f.write(current_bytes)
        
        text_origin, detected_lang = transcribe_auto_detect("temp_audio.wav")
        
        if text_origin:
            # 🟢 情况一：中文 -> 我 -> 翻译并播放
            if "chinese" in detected_lang.lower():
                status_area.success("✅ 识别为中文：语音已发送给客户！")
                
                st.session_state.messages.append({"role": "user", "content": f"我(CN): {text_origin}"})
                text_translated = ai_translator(text_origin, target_lang="en")
                st.session_state.messages.append({"role": "assistant", "content": f"AI(EN): {text_translated}"})
                speak_instant(text_translated, lang="en")

            # 🔵 情况二：英文 -> 客户 -> 仅翻译文字
            elif "english" in detected_lang.lower():
                status_area.info("📩 识别为英文：收到客户消息（静音模式）")
                
                st.session_state.messages.append({"role": "user", "content": f"👱 客户(EN): {text_origin}"})
                text_translated = ai_translator(text_origin, target_lang="zh")
                st.session_state.messages.append({"role": "assistant", "content": f"👀 翻译(CN): {text_translated}"})
                
            else:
                status_area.error(f"⚠️ 未识别语言 ({detected_lang})，请重试。")

            st.session_state.last_processed_audio = current_bytes
            st.rerun()