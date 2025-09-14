import streamlit as st
import requests
import json
import time

# ---------------- CONFIG ---------------- #
API_BASE = "http://127.0.0.1:5000"

st.set_page_config(page_title="Smart Room Search Chatbot", page_icon="🤖", layout="centered")

st.title("Smart Room Search Assistant")

# ---------------- SESSION STATE ---------------- #
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "role" not in st.session_state:
    st.session_state.role = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------- LOGIN FORM ---------------- #
if st.session_state.conversation_id is None:
    st.subheader(" Login")
    with st.form("login_form"):
        user_id = st.text_input("User ID")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if user_id and password:
            try:
                response = requests.post(
                    f"{API_BASE}/login",
                    data={"user_id": user_id, "password": password},
                    timeout=10,
                )
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.conversation_id = data["conversation_id"]
                    st.session_state.role = data["role"]
                    st.success(f" Logged in as {st.session_state.role}")
                else:
                    st.error(" Invalid credentials")
            except Exception as e:
                st.error(f" Error connecting to API: {e}")
        else:
            st.warning(" Please enter both User ID and Password.")

# ---------------- CHAT UI ---------------- #
else:
    st.subheader(f" Welcome, {st.session_state.role}")

    # Display past conversation
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input box for new message
    if user_input := st.chat_input("Type your message..."):
        # Save user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Send message to backend
        try:
            payload = {
                "conversation_id": st.session_state.conversation_id,
                "user_message": user_input,
            }

            with st.chat_message("assistant"):
                with st.spinner(" Assistant is typing..."):
                    response = requests.post(f"{API_BASE}/chat", data=payload, timeout=30)

                    if response.status_code == 200:
                        reply = response.json()

                        # Extract reply text
                        if isinstance(reply, dict):
                            bot_msg_raw = reply.get("message") or reply.get("reply") or json.dumps(reply, indent=2)
                        else:
                            bot_msg_raw = str(reply)

                        # Typing effect
                        placeholder = st.empty()
                        bot_msg = ""
                        for char in bot_msg_raw:
                            bot_msg += char
                            placeholder.markdown(bot_msg)
                            time.sleep(0.02)

                        # Save final message
                        st.session_state.messages.append({"role": "assistant", "content": bot_msg})

                    else:
                        st.error(f" API Error: {response.text}")

        except Exception as e:
            st.error(f"⚠️ Error: {e}")
