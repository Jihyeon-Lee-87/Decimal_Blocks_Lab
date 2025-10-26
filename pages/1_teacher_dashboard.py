import streamlit as st
st.set_page_config(page_title="교사 대시보드", page_icon="📊", layout="wide")

if not st.session_state.get("teacher_ok", False):
    st.error("교사 전용 페이지입니다. 메인에서 교사 인증 후 다시 오세요.")
    st.stop()

st.title("📊 교사 대시보드 — 테스트 OK")
st.write("이 페이지가 보이면 경로 문제는 해결된 겁니다.")
