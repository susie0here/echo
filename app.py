import streamlit as st
import requests

# ==========================================
# 頁面基本配置
# ==========================================
st.set_page_config(
    page_title="時光復刻",
    page_icon="",
    layout="centered"
)

st.title("時光復刻")

# ==========================================
# Session State 初始化 (記憶對話與 Prompt 狀態)
# ==========================================
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = ""
if "revision_history" not in st.session_state:
    st.session_state.revision_history = []

# ==========================================
# 側邊欄：API 配置 (支援 Gemini 或 OpenAI 相容接口)
# ==========================================
with st.sidebar:
    st.header("⚙️ API 設定")
    api_key = st.text_input("key", type="password", help="可在 Google AI Studio 免費申請")
    model_name = st.selectbox("選擇模型", ["gemini-1.5-flash", "gemini-1.5-pro"])
    
    st.markdown("---")
    st.markdown("### 使用說明")
    st.markdown("1. **第一步**：輸入記憶碎片，生成初始繪圖 Prompt。\n2. **第二步**：對 Prompt 提出修改（如：*把陽光改為下雨，其餘保持不變*）。\n3. 系統將嚴格執行外科手術式修訂。")

# ==========================================
# LLM 呼叫函式 (REST API 原生串接)
# ==========================================
def call_gemini_api(system_prompt: str, user_prompt: str) -> str:
    """呼叫 Gemini REST API 的通用函式"""
    if not api_key:
        st.error("請先在側邊欄輸入有效的 Gemini API Key！")
        return ""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        if response.status_code == 200:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            st.error(f"API 請求失敗: {data.get('error', {}).get('message', '未知錯誤')}")
            return ""
    except Exception as e:
        st.error(f"連線異常: {str(e)}")
        return ""

# ==========================================
# System Prompts 設計 (Prompt Engineering 核心)
# ==========================================

# 1. 初始提煉 System Prompt
BASE_PE_SYSTEM_PROMPT = """你是一位頂尖的 AI 繪圖 Prompt 工程師。
你的任務是將用戶提供的感性記憶描述，轉化為適用於 Flux / Midjourney / SDXL 的高質量英文生圖 Prompt。

【輸出結構要求】
[Subject & Action], [Environment & Details], [Lighting & Atmosphere], [Camera Style & Quality tags: 35mm film, nostalgic tones, cinematic lighting, highly detailed, 8k resolution].

【嚴格規則】
1. 只輸出英文 Prompt 本文，絕對不要包含任何中文、開場白、解釋或 Markdown 代碼塊。
"""

# 2. 外科手術式「增刪改查」修訂 System Prompt (核心邏輯)
REVISION_SYSTEM_PROMPT = """你是一位嚴謹的 AI 生圖 Prompt 「外科手術式修訂專家」。
你會收到：
1. 當前的英文生圖 Prompt (Original Prompt)
2. 用戶的增改刪減要求 (User Feedback)

【最高指令 (STRICT RULE)】：
- 你必須【嚴格只修改】用戶明確要求變動的部分。
- 未提及的所有物件、人物、背景、光線、相機風格、視角、詞序描述，【絕對必須 100% 原封不動保留】！
- 嚴禁擅自優化、潤色、增添未指定的修飾詞。
- 刪除元素：僅精準移除用戶指定的詞彙。
- 修改元素：僅將指定元素替換，其餘描述不動。
- 新增元素：將新元素自然插入對應位置，其餘描述不動。

【輸出規則】：
只輸出修改後的最終完整英文 Prompt 本文，禁止輸出任何解釋或多餘文字。
"""

# ==========================================
# 主介面 UI 佈局
# ==========================================
tab1, tab2 = st.tabs(["階段一：生成初始 Prompt", "階段二：精準增刪修改"])

# ------------------------------------------
# Tab 1: 記憶輸入與初始 Prompt 生成
# ------------------------------------------
with tab1:
    st.subheader("1. 輸入你的記憶碎片")
    memory_input = st.text_area(
        "請描述那段想復刻的時光（例如：小時候黃昏時，爸爸騎單車載我回家，街道兩旁是老舊的店舖）：",
        height=120,
        placeholder="輸入越詳細，初始生成越精準..."
    )
    
    if st.button("生成初始生圖 Prompt", type="primary"):
        if memory_input.strip():
            with st.spinner("正在進行 Prompt Engineering 提煉中..."):
                generated_prompt = call_gemini_api(BASE_PE_SYSTEM_PROMPT, memory_input)
                if generated_prompt:
                    st.session_state.current_prompt = generated_prompt
                    st.session_state.revision_history = [("初始版本", generated_prompt)]
                    st.success("初始 Prompt 生成成功！請切換至「階段二」進行檢視與微調。")
        else:
            st.warning("請先輸入記憶描述！")

# ------------------------------------------
# Tab 2: 外科手術式 Prompt 增刪修訂
# ------------------------------------------
with tab2:
    st.subheader("2. 當前 Prompt 檢視與局部微調")
    
    if not st.session_state.current_prompt:
        st.info("請先在「階段一」生成初始 Prompt。")
    else:
        # 顯示當前 Prompt
        st.markdown("** 當前生效的生圖 Prompt：**")
        st.code(st.session_state.current_prompt, language="text")
        
        st.markdown("---")
        st.subheader("輸入反饋（局部修訂）")
        
        feedback_input = st.text_input(
            "請說明要修改的地方（系統將嚴格只修改你提到的部分）：",
            placeholder="例如：把天氣改為下雨天，並把爸爸的衣服改成紅色，其餘保持不變。"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            submit_revision = st.button("執行精準修訂", type="primary")
            
        if submit_revision and feedback_input.strip():
            revision_request = f"""
[Original Prompt]:
{st.session_state.current_prompt}

[User Feedback]:
{feedback_input}
"""
            with st.spinner("正在進行修訂..."):
                updated_prompt = call_gemini_api(REVISION_SYSTEM_PROMPT, revision_request)
                if updated_prompt:
                    # 更新當前 Prompt 並記錄歷史
                    st.session_state.current_prompt = updated_prompt
                    st.session_state.revision_history.append((f"修訂: {feedback_input}", updated_prompt))
                    st.rerun()

        # 展示修訂歷史軌跡
        with st.expander("查看修訂歷史版本記錄"):
            for idx, (action, p_text) in enumerate(st.session_state.revision_history):
                st.caption(f"**V{idx+1} - {action}**")
                st.code(p_text, language="text")
