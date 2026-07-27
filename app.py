import streamlit as st
import google.generativeai as genai
import requests
import urllib.parse

# -----------------------------------------------------------------------------
# 1. 頁面配置與樣式
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="時光復刻機 Time Capsule",
    layout="wide"
)

st.markdown("""
<style>
    .main { background-color: #faf8f5; }
    .stApp { max-width: 1100px; margin: 0 auto; }
    .memory-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border: 1px solid #eee;
    }
    .stButton>button {
        background-color: #8c6d58;
        color: white;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. API 配置與模型自動偵測
# -----------------------------------------------------------------------------
st.sidebar.title("系統設定")
api_key = st.sidebar.text_input("輸入 Gemini API Key (免費)", type="password")
st.sidebar.caption("可至 Google AI Studio 免費申請 Gemini API Key")

# 這裡設計一個函數來自動找尋你帳號支援的模型
@st.cache_data(show_spinner=False)
def get_best_model_name(api_key):
    genai.configure(api_key=api_key)
    try:
        # 列出所有支援生成內容的模型
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 優先尋找 1.5-flash 系列
        for preferred in ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-1.5-flash-001', 'gemini-1.5-flash']:
            if preferred in available_models:
                return preferred
                
        # 找不到的話，挑選列表裡第一個帶有 flash 的模型
        fallback = next((m for m in available_models if 'flash' in m), None)
        return fallback if fallback else available_models[0]
    except Exception as e:
        return "gemini-1.5-flash-latest" # 最後的保底寫法

# -----------------------------------------------------------------------------
# 3. 初始化 Session 與設定
# -----------------------------------------------------------------------------
SYSTEM_PROMPT = """记住你現在是「時光復刻機」的記憶嚮導。你的任務是幫助用戶回想並補全他們珍貴但模糊的記憶，以便後續生成畫面。
你的性格：溫柔、充滿同理心、有耐心、像一位老朋友。
你的任務：
用戶會提供一個記憶碎片，你需要肯定這段記憶的價值。
每次只問 1 到 2 個問題，避免給用戶壓力。
循序漸進地引導他們回想視覺細節：例如發生的時間（白天 / 黃昏 / 夜晚）、光線、環境佈置、人物的衣著、物品的材質與顏色、當時的表情與氛圍。
如果用戶說「忘記了」，安慰他們「沒關係，模糊的記憶也有獨特的美感」，並自動幫他們補上合理且溫馨的預設細節。
當收集到足夠的畫面細節（人物、場景、光線、氛圍）後，溫柔地詢問：「我們現在要把這個美好的時刻沖印出來嗎？」"""

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "model", "parts": ["你好，我是時光復刻機的記憶嚮導。請告訴我，今天你想回想哪一段珍貴的時光？"]}
    ]
if "image_url" not in st.session_state:
    st.session_state.image_url = None
if "final_prompt" not in st.session_state:
    st.session_state.final_prompt = ""

# -----------------------------------------------------------------------------
# 4. 核心邏輯函數
# -----------------------------------------------------------------------------
def generate_image_prompt(chat_history, target_model):
    """根據對話歷史提取特徵並生成英文生圖 Prompt"""
    model = genai.GenerativeModel(target_model)
    prompt_engineer_instruction = """
    你是一位專業的 AI 繪圖 Prompt 專家。請總結以下用戶與記憶嚮導的對話內容，提取關鍵的場景、人物、光線、年代感與物品細節。
    將其轉化為一段高質量的英文 Midjourney / Stable Diffusion Prompt。
    風格預設為：Nostalgic 35mm film photograph, warm atmospheric lighting, highly detailed, emotional tone.
    只輸出英文 Prompt 文字本身，不要加上任何導語或標點符號之外的說明。
    """
    
    formatted_history = "\n".join([f"{m['role']}: {m['parts'][0]}" for m in chat_history])
    response = model.generate_content([prompt_engineer_instruction, formatted_history])
    return response.text.strip()

def fetch_free_image(prompt):
    """使用 Pollinations.ai 免費生成圖片"""
    encoded_prompt = urllib.parse.quote(prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed=42"
    return image_url

# -----------------------------------------------------------------------------
# 5. 主介面 UI 設計
# -----------------------------------------------------------------------------
st.title("時光復刻機 — 喚醒模糊的珍貴記憶")
st.subheader("透過溫暖的對話，還原那些留在時光深處的畫面。")

if api_key:
    genai.configure(api_key=api_key)
    # 取得當前帳號可用的模型
    active_model_name = get_best_model_name(api_key)
    st.sidebar.success(f"已連接模型：{active_model_name}")
else:
    active_model_name = None
    st.sidebar.warning("請先輸入 API Key")

col1, col2 = st.columns([1, 1], gap="large")

# 左側：Chat 訪談對話框
with col1:
    st.markdown("### 記憶引導對話")
    
    chat_container = st.container(height=450)
    with chat_container:
        for msg in st.session_state.messages:
            role = "user" if msg["role"] == "user" else "assistant"
            with st.chat_message(role):
                st.write(msg["parts"][0])

    if user_input := st.chat_input("請輸入你的回憶細節..."):
        if not api_key or not active_model_name:
            st.error("請先在左側欄輸入 Gemini API Key。")
        else:
            st.session_state.messages.append({"role": "user", "parts": [user_input]})
            
            try:
                # 使用系統自動偵測到的模型
                model = genai.GenerativeModel(
                    model_name=active_model_name,
                    system_instruction=SYSTEM_PROMPT
                )
                
                history_for_gemini = [
                    {"role": m["role"], "parts": m["parts"]} for m in st.session_state.messages
                ]
                
                response = model.generate_content(history_for_gemini)
                
                st.session_state.messages.append({"role": "model", "parts": [response.text]})
                st.rerun()
                
            except Exception as e:
                st.error(f"調用 API 時發生錯誤：{e}")

    if st.button("記憶細節已足夠，沖印這個美好時刻", use_container_width=True):
        if not api_key or not active_model_name:
            st.error("請輸入 API Key。")
        else:
            with st.spinner("嚮導正在梳理記憶碎片，繪製畫幅中..."):
                try:
                    prompt = generate_image_prompt(st.session_state.messages, active_model_name)
                    st.session_state.final_prompt = prompt
                    img_url = fetch_free_image(prompt)
                    st.session_state.image_url = img_url
                except Exception as e:
                    st.error(f"生成圖片提示詞時發生錯誤：{e}")

# 右側：記憶重現結果卡片
with col2:
    st.markdown("### 重現的記憶畫面")
    if st.session_state.image_url:
        st.markdown('<div class="memory-card">', unsafe_allow_html=True)
        st.image(st.session_state.image_url, caption="根據你的記憶碎片重現的畫面", use_container_width=True)
        
        with st.expander("檢視背後生成的 Prompt"):
            st.write(st.session_state.final_prompt)
            
        try:
            st.download_button(
                label="保存珍貴記憶",
                data=requests.get(st.session_state.image_url).content,
                file_name="time_capsule_memory.jpg",
                mime="image/jpeg",
                use_container_width=True
            )
        except Exception as e:
            st.error("圖片下載失敗，請稍後重試。")
            
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("請在左側與嚮導聊天，當收集到足夠細節時，點擊按鈕沖印畫面。")
