import streamlit as st
import openai

# Cấu hình API Key của OpenAI
openai.api_key = "YOUR_OPENAI_API_KEY"

def get_response(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

# Giao diện Streamlit
st.title("Simple Chatbot with Streamlit")

# Lịch sử hội thoại
if "messages" not in st.session_state:
    st.session_state.messages = []

# Hiển thị tin nhắn trước đó
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Nhập câu hỏi từ người dùng
prompt = st.chat_input("Type your message...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Lấy phản hồi từ chatbot
    response = prompt
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)
        st.markdown(response)
