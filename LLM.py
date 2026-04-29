import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
import uuid
import base64
from datetime import datetime
import json

# Import our custom modules
from database import PersistenceManager
from model_router import ModelRouter
from multimodal import ImageProcessor
from tools import ToolExecutor, get_tools_for_api
from utilities import SessionAnalytics, SessionManager

# Helper to render chat content with code blocks as proper code components
import re

def render_chat_content(content):
    if isinstance(content, str):
        # Render markdown text and code fences with Streamlit code blocks to ensure copy works.
        parts = re.split(r"```(\w*)\n", content)
        if len(parts) > 1:
            for i in range(0, len(parts), 2):
                text_part = parts[i].strip()
                if text_part:
                    st.markdown(text_part)
                if i + 1 < len(parts):
                    lang = parts[i + 1].strip() or None
                    code_part = parts[i + 2].rstrip("\n") if i + 2 < len(parts) else ""
                    st.code(code_part, language=lang)
        else:
            st.markdown(content)
    else:
        st.markdown(content)

# 載入環境變數
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

st.set_page_config(page_title="Advanced GenAI Chat System v2.0", layout="wide")
st.title("🚀 Advanced GenAI Chat System v2.0")

# Initialize managers
db_manager = PersistenceManager()
model_router = ModelRouter()
image_processor = ImageProcessor()
tool_executor = ToolExecutor()
analytics = SessionAnalytics(db_manager)
session_manager = SessionManager(db_manager)

# --- 1. 初始化 Session State ---
if "chat_sessions" not in st.session_state:
    # Load from database on startup
    st.session_state.chat_sessions = db_manager.load_sessions()
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "input_buffer" not in st.session_state:
    st.session_state.input_buffer = ""
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None
if "auto_routing" not in st.session_state:
    st.session_state.auto_routing = True

# --- 2. 側邊欄：管理功能 ---
with st.sidebar:
    st.header("💬 聊天室管理")

    if st.button("➕ 開啟新對話", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.chat_sessions[new_id] = {
            "name": f"新對話 {len(st.session_state.chat_sessions)+1}",
            "messages": [],
            "model_used": "",
            "api_source": ""
        }
        st.session_state.current_chat_id = new_id
        st.session_state.input_buffer = ""
        st.session_state.uploaded_image = None
        st.rerun()

    st.divider()

    # 顯示對話列表
    for chat_id, chat_data in list(st.session_state.chat_sessions.items()):
        cols = st.columns([0.7, 0.15, 0.15])
        if cols[0].button(chat_data["name"], key=f"btn_{chat_id}", use_container_width=True):
            st.session_state.current_chat_id = chat_id
            st.session_state.input_buffer = ""
            st.session_state.uploaded_image = None
            st.rerun()
        if cols[1].button("📊", key=f"stats_{chat_id}"):
            stats = analytics.get_session_stats(chat_id)
            st.info(f"訊息: {stats['total_messages']}, Tokens: {stats['total_tokens']}")
        if cols[2].button("🗑️", key=f"del_{chat_id}"):
            db_manager.delete_session(chat_id)
            del st.session_state.chat_sessions[chat_id]
            if st.session_state.current_chat_id == chat_id:
                st.session_state.current_chat_id = None
            st.rerun()

    st.divider()
    st.header("⚙️ 模型設定")

    # Auto-routing toggle
    st.session_state.auto_routing = st.checkbox("啟用自動模型路由", value=st.session_state.auto_routing)

    api_source = st.selectbox("API 來源", ["Groq", "NVIDIA NIM"])

    if api_source == "Groq":
        current_key, base_url = GROQ_API_KEY, "https://api.groq.com/openai/v1"
        model_options = ["llama-3.3-70b-versatile", "meta-llama/llama-4-scout-17b-16e-instruct"]
    else:
        current_key, base_url = NVIDIA_API_KEY, "https://integrate.api.nvidia.com/openai/v1"
        model_options = ["GPT-OSS-120b"]

    if st.session_state.auto_routing:
        model_name = st.selectbox("建議模型 (自動路由)", model_options, disabled=True)
        st.info("模型將根據您的輸入自動選擇")
    else:
        model_name = st.selectbox("選擇模型", model_options)

    use_streaming = st.checkbox("開啟串流輸出 (Streaming)", value=True)
    use_tools = st.checkbox("啟用工具調用 (Tools)", value=True)
    system_prompt = st.text_area("System Prompt", value="你是一個專業助理，可以使用各種工具來幫助用戶。")
    temperature = st.slider("Temperature (隨機性)", 0.0, 2.0, 0.7)

    st.divider()
    st.header("📊 使用統計")
    user_stats = analytics.get_user_stats()
    st.metric("總對話數", user_stats["total_sessions"])
    st.metric("總訊息數", user_stats["total_messages"])
    st.metric("最常用模型", user_stats["most_used_model"])

# --- 3. 主要對話區域 ---
if st.session_state.current_chat_id is None:
    st.info("💡 請點擊左側「開啟新對話」或選擇既有對話開始。")

    # Show search functionality
    st.header("🔍 搜尋對話")
    search_query = st.text_input("搜尋關鍵字")
    if search_query:
        results = db_manager.search_messages(search_query)
        if results:
            for result in results[:10]:  # Show top 10 results
                with st.expander(f"{result['session_name']} - {result['timestamp'][:19]}"):
                    st.write(f"**{result['role'].upper()}**: {result['content']}")
        else:
            st.info("沒有找到相關訊息")

else:
    cid = st.session_state.current_chat_id
    current_chat = st.session_state.chat_sessions[cid]
    raw_messages = current_chat["messages"]

    # Process messages: filter fields and parse JSON content
    messages = []
    api_source_lower = api_source.lower().replace(" nim", "")
    for msg in raw_messages:
        content = msg["content"]
        # Try to parse JSON content for multimodal messages
        try:
            parsed_content = json.loads(content)
            content = parsed_content
        except (json.JSONDecodeError, TypeError):
            pass  # Keep as string if not JSON

        # If content is multimodal but current model doesn't support vision, convert to text
        if isinstance(content, list) and not model_router.is_vision_supported(model_name, api_source_lower):
            text_parts = [item.get("text", "") for item in content if item.get("type") == "text"]
            content = " ".join(text_parts) + " [圖片已省略，因為當前模型不支援視覺]"

        messages.append({
            "role": msg["role"],
            "content": content
        })

    # 顯示訊息
    for i, msg in enumerate(messages):
        with st.chat_message(msg["role"]):
            if isinstance(msg["content"], list):  # 處理多模態顯示
                for item in msg["content"]:
                    if item["type"] == "text":
                        render_chat_content(item["text"])
                    elif item["type"] == "image_url":
                        st.image(item["image_url"]["url"])
            else:
                render_chat_content(msg["content"])

    # 撤回功能
    if len(messages) >= 2:
        if st.button("↩️ 撤回最後一則訊息並修改"):
            last_user_msg = messages[-2]["content"] if messages[-2]["role"] == "user" else ""
            st.session_state.chat_sessions[cid]["messages"] = raw_messages[:-2]
            st.session_state.input_buffer = last_user_msg
            st.rerun()

    # Export functionality
    if st.button("📤 匯出對話"):
        export_data = session_manager.export_session(cid, "json")
        st.download_button(
            label="下載 JSON",
            data=export_data,
            file_name=f"chat_session_{cid}.json",
            mime="application/json"
        )

    # --- 4. 多模態輸入 ---
    col1, col2 = st.columns([0.8, 0.2])

    with col1:
        prompt = st.chat_input("輸入訊息...", key=f"input_{cid}")

    with col2:
        uploaded_file = st.file_uploader("上傳圖片", type=["png", "jpg", "jpeg", "gif", "webp"], key=f"upload_{cid}")

    # Process uploaded image
    if uploaded_file:
        if image_processor.validate_image(uploaded_file):
            st.session_state.uploaded_image = uploaded_file
            st.success("圖片已上傳！")
            st.image(uploaded_file, caption="已上傳的圖片", width=200)
            api_source_lower = api_source.lower().replace(" nim", "")
            if not model_router.is_vision_supported(model_name, api_source_lower):
                st.warning("目前選擇的模型不支援影像分析；請改用 meta-llama/llama-4-scout-17b-16e-instruct 或啟用自動路由。")
        else:
            st.error("不支援的圖片格式")

    # Handle input buffer
    if st.session_state.input_buffer:
        st.warning(f"已撤回。原訊息：{st.session_state.input_buffer}")

    if prompt:
        # Reset buffer
        st.session_state.input_buffer = ""

        # Auto-rename chat
        if not messages:
            current_chat["name"] = prompt[:15] + "..."

        # Auto-routing logic
        has_image = st.session_state.uploaded_image is not None
        api_source_lower = api_source.lower().replace(" nim", "")
        if st.session_state.auto_routing:
            selected_model = model_router.analyze_input(prompt, has_image, api_source_lower)
            if selected_model in model_router.get_available_models(api_source_lower):
                model_name = selected_model
                st.info(f"自動選擇模型: {model_name}")
            else:
                st.warning(f"建議模型 {selected_model} 在當前API中不可用，使用 {model_name}")

        if has_image:
            if api_source_lower == "groq":
                vision_model = "meta-llama/llama-4-scout-17b-16e-instruct"
                if model_name != vision_model:
                    model_name = vision_model
                    st.info(f"偵測到影像輸入，已自動改用 {model_name} 進行多模態處理。")
            else:
                st.warning("目前 NVIDIA 模型不支援影像分析，圖片已被移除，僅傳送文字內容。")
                st.session_state.uploaded_image = None
                has_image = False

        # Prepare message
        if has_image:
            image_base64 = image_processor.process_uploaded_image(st.session_state.uploaded_image)
            if image_base64 is None:
                st.error("圖片處理失敗，請重新上傳圖片。")
                st.session_state.uploaded_image = None
                has_image = False
                message = {"role": "user", "content": prompt}
            else:
                message = image_processor.create_image_message(prompt, image_base64, model_name)
        else:
            message = {"role": "user", "content": prompt}

        # Add to messages and persist state
        current_chat["messages"].append(message)
        messages.append(message)
        with st.chat_message("user"):
            if isinstance(message["content"], str):
                render_chat_content(message["content"])
            else:
                for content_item in message["content"]:
                    if content_item["type"] == "text":
                        render_chat_content(content_item["text"])
                    elif content_item["type"] == "image_url":
                        st.image(content_item["image_url"]["url"])

        # Clear uploaded image
        st.session_state.uploaded_image = None

        # Call API with tools
        client = OpenAI(api_key=current_key, base_url=base_url)

        # Ensure model_name is valid for current API source
        if model_name not in model_options:
            model_name = model_options[0]
            st.warning(f"模型 {model_name} 在當前 API 中不可用，已切換至 {model_name}")

        full_history = [{"role": "system", "content": system_prompt}] + messages

        with st.chat_message("assistant"):
            res_placeholder = st.empty()
            full_res = ""

            try:
                # Prepare API call
                api_params = {
                    "model": model_name,
                    "messages": full_history,
                    "temperature": temperature,
                    "stream": use_streaming
                }

                if use_tools:
                    api_params["tools"] = get_tools_for_api()
                    api_params["tool_choice"] = "auto"

                response = client.chat.completions.create(**api_params)

                # Handle tool calls
                tool_calls_accumulated = []
                if use_tools and use_streaming:
                    # In streaming mode, accumulate tool calls
                    for chunk in response:
                        if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                            delta = chunk.choices[0].delta
                            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                                for tool_call_delta in delta.tool_calls:
                                    if len(tool_calls_accumulated) <= tool_call_delta.index:
                                        tool_calls_accumulated.extend([None] * (tool_call_delta.index + 1 - len(tool_calls_accumulated)))
                                    if tool_calls_accumulated[tool_call_delta.index] is None:
                                        tool_calls_accumulated[tool_call_delta.index] = {
                                            "id": "",
                                            "type": "",
                                            "function": {"name": "", "arguments": ""}
                                        }
                                    if hasattr(tool_call_delta, 'id') and tool_call_delta.id:
                                        tool_calls_accumulated[tool_call_delta.index]["id"] = tool_call_delta.id
                                    if hasattr(tool_call_delta, 'type') and tool_call_delta.type:
                                        tool_calls_accumulated[tool_call_delta.index]["type"] = tool_call_delta.type
                                    if hasattr(tool_call_delta, 'function'):
                                        if hasattr(tool_call_delta.function, 'name') and tool_call_delta.function.name:
                                            tool_calls_accumulated[tool_call_delta.index]["function"]["name"] += tool_call_delta.function.name
                                        if hasattr(tool_call_delta.function, 'arguments') and tool_call_delta.function.arguments:
                                            tool_calls_accumulated[tool_call_delta.index]["function"]["arguments"] += tool_call_delta.function.arguments
                            content = delta.content
                            if content:
                                full_res += content
                                res_placeholder.markdown(full_res + "▌")
                    res_placeholder.markdown(full_res)

                    # Process accumulated tool calls
                    if tool_calls_accumulated:
                        for tool_call in tool_calls_accumulated:
                            if tool_call:
                                tool_name = tool_call["function"]["name"]
                                tool_args = json.loads(tool_call["function"]["arguments"])
                                tool_result = tool_executor.process_tool_call(tool_name, tool_args)

                                # Add tool response to conversation
                                messages.append({"role": "assistant", "content": f"使用工具 {tool_name}..."})
                                messages.append({"role": "user", "content": f"工具結果: {tool_result}"})

                        # Get final response
                        final_response = client.chat.completions.create(
                            model=model_name,
                            messages=full_history + [
                                {"role": "assistant", "content": f"使用工具 {tool_name}..."},
                                {"role": "user", "content": f"工具結果: {tool_result}"}
                            ],
                            temperature=temperature,
                            stream=use_streaming
                        )
                        if use_streaming:
                            full_res = ""
                            for chunk in final_response:
                                if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                                    content = chunk.choices[0].delta.content
                                    if content:
                                        full_res += content
                                        res_placeholder.markdown(full_res + "▌")
                            res_placeholder.markdown(full_res)
                        else:
                            full_res = final_response.choices[0].message.content
                            render_chat_content(full_res)
                        response = final_response  # Update response for saving

                elif use_tools and not use_streaming:
                    if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                        # Process tool calls
                        tool_call = response.choices[0].message.tool_calls[0]
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)

                        tool_result = tool_executor.process_tool_call(tool_name, tool_args)

                        # Add tool response to conversation
                        messages.append({"role": "assistant", "content": f"使用工具 {tool_name}..."})
                        messages.append({"role": "user", "content": f"工具結果: {tool_result}"})

                        # Get final response
                        final_response = client.chat.completions.create(
                            model=model_name,
                            messages=full_history + [
                                {"role": "assistant", "content": f"使用工具 {tool_name}..."},
                                {"role": "user", "content": f"工具結果: {tool_result}"}
                            ],
                            temperature=temperature,
                            stream=use_streaming
                        )
                        response = final_response

                # Display response
                if not use_streaming:
                    full_res = response.choices[0].message.content
                    render_chat_content(full_res)

                # Save response
                assistant_message = {"role": "assistant", "content": full_res}
                messages.append(assistant_message)
                current_chat["messages"].append(assistant_message)

                # Save to database
                db_manager.save_session(cid, current_chat["name"], model_name, api_source)
                for msg in [message, {"role": "assistant", "content": full_res}]:
                    if isinstance(msg["content"], str):
                        db_manager.save_message(cid, msg["role"], msg["content"])
                    else:
                        # For multimodal messages, save as JSON
                        db_manager.save_message(cid, msg["role"], json.dumps(msg["content"]))

            except Exception as e:
                st.error(f"發生錯誤: {e}")
                # Save error message
                messages.append({"role": "assistant", "content": f"錯誤: {e}"})