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
# 2. API 配置
# -----------------------------------------------------------------------------
st.sidebar.title("系統設定")
api_key = st.sidebar.text_input("輸入 Gemini API Key (免費)", type="password")
st.sidebar.caption("可至 Google AI Studio 免費申請 Gemini API Key")

if api_key:
    genai.configure(api_key=api_key)

# 自訂的 System Prompt
SYSTEM_PROMPT = """记住你現在是「時光復刻機」的記憶嚮導。你的任務是幫助用戶回想並補全他們珍貴但模糊的記憶，以便後續生成畫面。
你的性格：溫柔、充滿同理心、有耐心、像一位老朋友。
你的任務：
用戶會提供一個記憶碎片，你需要肯定這段記憶的價值。
每次只問 1 到 2 個問題，避免給用戶壓力。
循序漸進地引導他們回想視覺細節：例如發生的時間（白天 / 黃昏 / 夜晚）、光線、環境佈置、人物的衣著、物品的材質與顏色、當時的表情與氛圍。
如果用戶說「忘記了」，安慰他們「沒關係，模糊的記憶也有獨特的美感」，並自動幫他們補上合理且溫馨的預設細節。
當收集到足夠的畫面細節（人物、場景、光線、氛圍）後，溫柔地詢問：「我們現在要把這個美好的時刻沖印出來嗎？」"""

# 初始化 Session State
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "model", "parts": ["你好，我是時光復刻機的記憶嚮導。請告訴我，今天你想回想哪一段珍貴的時光？"]}
    ]
if "image_url" not in st.session_state:
    st.session_state.image_url = None
if "final_prompt" not in st.session_state:
    st.session_state.final_prompt = ""

# -----------------------------------------------------------------------------
# 3. 核心邏輯函數
# -----------------------------------------------------------------------------
def generate_image_prompt(chat_history):
    """根據對話歷史提取特徵並生成英文生圖 Prompt"""
    # 統一使用 gemini-1.5-flash
    model = genai.GenerativeModel("gemini-1.5-flash")
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
# 4. 主介面 UI 設計
# -----------------------------------------------------------------------------
st.title("時光復刻機 — 喚醒模糊的珍貴記憶")
st.subheader("透過溫暖的對話，還原那些留在時光深處的畫面。")

col1, col2 = st.columns([1, 1], gap="large")

# 左側：Chat 訪談對話框
with col1:
    st.markdown("### 記憶引導對話")
    
    # 顯示歷史對話
    chat_container = st.container(height=450)
    with chat_container:
        for msg in st.session_state.messages:
            # Streamlit 的 chat_message 支援 assistant 與 user
            role = "user" if msg["role"] == "user" else "assistant"
            with st.chat_message(role):
                st.write(msg["parts"][0])

    # 輸入框
    if user_input := st.chat_input("請輸入你的回憶細節..."):
        if not api_key:
            st.error("請先在左側欄輸入 Gemini API Key。")
        else:
            # 先將用戶輸入加入 UI 記錄
            st.session_state.messages.append({"role": "user", "parts": [user_input]})
            
            try:
                # 建立 Gemini 模型
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=SYSTEM_PROMPT
                )
                
                # 格式化給 Gemini API 的對話歷史（必須是 user 和 model 交替）
                history_for_gemini = []
                for m in st.session_state.messages:
                    history_for_gemini.append({
                        "role": m["role"],
                        "parts": m["parts"]
                    })
                
                response = model.generate_content(history_for_gemini)
                
                # 將 AI 回復存入 state
                st.session_state.messages.append({"role": "model", "parts": [response.text]})
                st.rerun()
                
            except Exception as e:
                st.error(f"調用 API 時發生錯誤：{e}")

    # 一鍵生成圖片按鈕
    if st.button("記憶細節已足夠，沖印這個美好時刻", use_container_width=True):
        if not api_key:
            st.error("請輸入 API Key。")
        else:
            with st.spinner("嚮導正在梳理記憶碎片，繪製畫幅中..."):
                try:
                    prompt = generate_image_prompt(st.session_state.messages)
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
