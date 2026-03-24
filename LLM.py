import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
import uuid

# 載入環境變數
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

st.set_page_config(page_title="My Own ChatGPT", layout="wide")
st.title("🤖 Your Own ChatGPT")

# --- 1. 初始化 Session State ---
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
# 用於撤回訊息的暫存緩衝
if "input_buffer" not in st.session_state:
    st.session_state.input_buffer = ""

# --- 2. 側邊欄：管理功能 ---
with st.sidebar:
    st.header("💬 聊天室管理")
    
    if st.button("➕ 開啟新對話", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.chat_sessions[new_id] = {"name": f"新對話 {len(st.session_state.chat_sessions)+1}", "messages": []}
        st.session_state.current_chat_id = new_id
        st.session_state.input_buffer = "" # 清空輸入緩衝
        st.rerun()

    st.divider()
    
    # 顯示對話列表
    for chat_id, chat_data in list(st.session_state.chat_sessions.items()):
        cols = st.columns([0.8, 0.2])
        # 使用動態 Key 確保切換時狀態清空
        if cols[0].button(chat_data["name"], key=f"btn_{chat_id}", use_container_width=True):
            st.session_state.current_chat_id = chat_id
            st.session_state.input_buffer = "" 
            st.rerun()
        if cols[1].button("🗑️", key=f"del_{chat_id}"):
            del st.session_state.chat_sessions[chat_id]
            if st.session_state.current_chat_id == chat_id:
                st.session_state.current_chat_id = None
            st.rerun()

    st.divider()
    st.header("⚙️ 模型設定")
    api_source = st.selectbox("API 來源", ["Groq", "NVIDIA NIM"])
    
    if api_source == "Groq":
        current_key, base_url = GROQ_API_KEY, "https://api.groq.com/openai/v1"
        model_options = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
    else:
        current_key, base_url = NVIDIA_API_KEY, "https://integrate.api.nvidia.com/v1"
        model_options = ["nvidia/llama-3.1-nemotron-70b-instruct", "meta/llama-3.1-405b-instruct"]

    model_name = st.selectbox("選擇模型", model_options)
    use_streaming = st.checkbox("開啟串流輸出 (Streaming)", value=True)
    system_prompt = st.text_area("System Prompt", value="你是一個專業助理。")
    temperature = st.slider("Temperature (隨機性)", 0.0, 2.0, 0.7)

# --- 3. 主要對話區域 ---
if st.session_state.current_chat_id is None:
    st.info("💡 請點擊左側「開啟新對話」或選擇既有對話開始。")
else:
    cid = st.session_state.current_chat_id
    current_chat = st.session_state.chat_sessions[cid]
    messages = current_chat["messages"]

    # 顯示訊息 (加上 cid 作為 key 的一部分，防止串軌)
    for i, msg in enumerate(messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 功能 2：撤回/編輯最後一則訊息按鈕
    if len(messages) >= 2:
        if st.button("↩️ 撤回最後一則訊息並修改"):
            # 取出最後一則 user 訊息內容
            last_user_msg = messages[-2]["content"] if messages[-2]["role"] == "user" else ""
            # 刪除最後兩則 (User & Assistant)
            st.session_state.chat_sessions[cid]["messages"] = messages[:-2]
            # 將內容存入緩衝，準備填入輸入框
            st.session_state.input_buffer = last_user_msg
            st.rerun()

    # --- 4. 輸入處理 ---
    # 使用 placeholder 技巧來預填撤回的內容
    prompt = st.chat_input("輸入訊息...", key=f"input_{cid}")
    
    # 處理「剛撤回」的情況：如果 input 為空但 buffer 有值，提示使用者
    if st.session_state.input_buffer:
        st.warning(f"已撤回。原訊息：{st.session_state.input_buffer}")
        # 如果使用者沒有輸入新東西，我們可以用這段文字當預設值，
        # 但 Streamlit 的 chat_input 不支援預填 value，所以顯示在上方提醒。

    if prompt:
        # 重置緩衝
        st.session_state.input_buffer = ""
        
        # 自動命名聊天室
        if not messages:
            current_chat["name"] = prompt[:15] + "..."
        
        # 加入紀錄
        messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 呼叫 API
        client = OpenAI(api_key=current_key, base_url=base_url)
        # 【優化重點】：確保 System Prompt 是當下側邊欄最新的內容
        # 並且將它放在 messages 的最首位
        full_history = [
            {"role": "system", "content": system_prompt} 
        ] + [
            {"role": m["role"], "content": m["content"]} for m in messages
        ]

        with st.chat_message("assistant"):
            res_placeholder = st.empty()
            full_res = ""
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=full_history,
                    temperature=temperature, # 使用拉桿數值
                    stream=use_streaming
                )
                
                if use_streaming:
                    for chunk in response:
                        if chunk.choices and len(chunk.choices) > 0:
                            content = chunk.choices[0].delta.content
                            if content:
                                full_res += content
                                res_placeholder.markdown(full_res + "▌")
                    res_placeholder.markdown(full_res)
                else:
                    full_res = response.choices[0].message.content
                    st.markdown(full_res)
                
                # 儲存 AI 回應
                messages.append({"role": "assistant", "content": full_res})
            except Exception as e:
                st.error(f"發生錯誤: {e}")