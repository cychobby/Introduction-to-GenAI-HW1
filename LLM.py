import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

# 載入 .env 檔案中的變數
load_dotenv()

# 從環境變數中讀取 Key，如果讀不到則為 None
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

# 檢查 Key 是否存在，若無則顯示警告
if not GROQ_API_KEY or not NVIDIA_API_KEY:
    st.error("找不到 API Key，請檢查環境變數設定。")

# 設定頁面
st.set_page_config(page_title="My Own ChatGPT", layout="wide")
st.title("🤖 Your Own ChatGPT")

# 1. 側邊欄設定
with st.sidebar:
    st.header("設定中心")
    
    # 選擇 API 來源
    api_source = st.selectbox("選擇 API 來源", ["Groq", "NVIDIA NIM"])
    
    # 根據來源自動分配 Key 與 URL
    if api_source == "Groq":
        current_key = GROQ_API_KEY
        base_url = "https://api.groq.com/openai/v1"
        model_options = ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
    else:
        current_key = NVIDIA_API_KEY
        base_url = "https://integrate.api.nvidia.com/v1"
        model_options = ["nvidia/llama-3.1-nemotron-70b-instruct", "meta/llama-3.1-405b-instruct"]

    model_name = st.selectbox("選擇模型", model_options)
    
    # 功能 3: 增加 Streaming 勾選處
    use_streaming = st.checkbox("開啟串流輸出 (Streaming)", value=True)

    system_prompt = st.text_area("System Prompt", value="你是一個專業的助理。")
    temperature = st.slider("Temperature", 0.0, 2.0, 0.7)
    
    if st.button("清除對話記憶"):
        st.session_state.messages = []
        st.rerun()

# 2. 初始化對話短期記憶
if "messages" not in st.session_state:
    st.session_state.messages = []

# 顯示歷史訊息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. 對話輸入處理
if prompt := st.chat_input("有什麼我可以幫你的嗎？"):
    # 存入並顯示使用者訊息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 初始化 OpenAI Client
    client = OpenAI(api_key=current_key, base_url=base_url)
    
    # 組合訊息 (System + History)
    messages_to_send = [{"role": "system", "content": system_prompt}] + [
        {"role": m["role"], "content": m["content"]} for m in st.session_state.messages
    ]

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # 呼叫 API
            response = client.chat.completions.create(
                model=model_name,
                messages=messages_to_send,
                temperature=temperature,
                stream=use_streaming, # 根據勾選決定是否串流
            )
            
            if use_streaming:
                # 串流處理：加入防錯機制解決 list index out of range
                for chunk in response:
                    # 確保 chunk 有內容且 choices 不為空
                    if len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content is not None:
                            full_response += delta.content
                            response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
            else:
                # 非串流處理
                full_response = response.choices[0].message.content
                st.markdown(full_response)
            
            # 成功結束後才存入記憶，確保對話不遺失
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"發生錯誤: {e}")
            # 若發生錯誤，印出更詳細的資訊供除錯
            print(f"Debug Error Details: {e}")