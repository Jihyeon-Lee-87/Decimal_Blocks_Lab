# -*- coding: utf-8 -*-
# 교사 대시보드(강화판)
# - KST 기준 타임스탬프 표시
# - 날짜/학급 필터
# - KPI + 최근 제출/학급별 제출 표
# - 탭 5개: 정답여부 비율, 자기평가 총점 분포, 학급별 정답률, 학급별 제출 수, 날짜별 제출 추이
# - NEW: 자유응답 키워드(상위 빈도) 탭 추가
# - 자동 새로고침 토글, 수동 새로고침 버튼

import re
import sqlite3
from pathlib import Path
from contextlib import closing
from datetime import date, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="교사 대시보드", page_icon="📊", layout="wide")

# --- 접근 제어 ---
if not st.session_state.get("teacher_ok", False):
    st.error("교사 전용 페이지입니다. 메인 화면 사이드바에서 '교사' 선택 후 비밀번호를 입력하세요.")
    st.stop()

# --- 30초 자동 새로고침 토글 ---
try:
    from streamlit_autorefresh import st_autorefresh
    if st.toggle("30초 자동 새로고침", value=False, key="teacher_autorefresh"):
        st_autorefresh(interval=30_000, key="teacher_dash_autorefresh_tabs")
except Exception:
    st.caption("⏱ `streamlit-autorefresh` 미설치 상태(선택 사항). requirements.txt에 추가하면 자동 새로고침 사용 가능.")

# --- DB 유틸 (루트/submissions.db 고정) ---
ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH  = str(ROOT_DIR / "submissions.db")

@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              timestamp TEXT,
              class TEXT,
              nickname TEXT,
              quest TEXT,
              rubric_1 INTEGER,
              rubric_2 INTEGER,
              rubric_3 INTEGER,
              rubric_total INTEGER,
              guess_mode TEXT,
              guess_value TEXT,
              guess_correct INTEGER,
              correct_answer TEXT
            )
        """)
    return conn

def fetch_all() -> pd.DataFrame:
    conn = get_conn()
    with closing(conn.cursor()) as cur:
        cur.execute("""
          SELECT timestamp, class, nickname, quest,
                 rubric_1, rubric_2, rubric_3, rubric_total,
                 guess_mode, guess_value, guess_correct, correct_answer
          FROM submissions
          ORDER BY datetime(timestamp) DESC
        """)
        cols = ["timestamp","class","nickname","quest",
                "rubric_1","rubric_2","rubric_3","rubric_total",
                "guess_mode","guess_value","guess_correct","correct_answer"]
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)

def altair_available() -> bool:
    try:
        import altair as alt  # noqa
        return True
    except Exception:
        return False

st.title("📊 교사 대시보드")
st.caption("모든 시간은 KST(Asia/Seoul) 기준으로 저장·표시됩니다.")

# 수동 새로고침
if st.button("🔄 새로고침"):
    st.rerun()

# 데이터 로딩 및 전처리
df = fetch_all()
if df.empty:
    st.warning("아직 제출이 없습니다. 학생 화면에서 제출 후 다시 새로고침하세요.")
    st.stop()

df["dt"] = pd.to_datetime(df["timestamp"], errors="coerce")
df["date"] = df["dt"].dt.date
df["rubric_total"] = pd.to_numeric(df["rubric_total"], errors="coerce")
df["guess_correct_num"] = pd.to_numeric(df["guess_correct"], errors="coerce")

# 필터
fltL, fltM, fltR = st.columns([2,2,3])
with fltL:
    max_day = df["date"].max()
    min_day = df["date"].min()
    default_start = max(min_day, (max_day or date.today()) - timedelta(days=14))
    start_day = st.date_input("시작일", value=default_start,
                              min_value=min_day, max_value=max_day or date.today())
with fltM:
    end_day = st.date_input("종료일", value=max_day or date.today(),
                            min_value=min_day, max_value=max_day or date.today())
with fltR:
    class_options = ["4-사랑","4-기쁨","4-보람","4-행복","기타"]
    sel_classes = st.multiselect("학급(복수 선택)", class_options, default=class_options)

if start_day > end_day:
    st.error("시작일이 종료일보다 늦을 수 없습니다."); st.stop()

mask = (df["date"] >= start_day) & (df["date"] <= end_day) & (df["class"].isin(sel_classes))
fdf = df.loc[mask].copy()
if fdf.empty:
    st.info("선택한 조건에 해당하는 제출이 없습니다. 필터를 조정해 주세요.")
    st.stop()

# KPI
K1, K2, K3, K4 = st.columns(4)
with K1:
    st.metric("총 제출", len(fdf))
with K2:
    st.metric("평균 자기평가 총점", round(fdf["rubric_total"].dropna().astype(int).mean(), 2))
with K3:
    if fdf["guess_correct_num"].notna().any():
        st.metric("전체 정답률(필터 범위)", f"{(fdf['guess_correct_num'].fillna(0).astype(int).mean()*100):.0f}%")
    else:
        st.metric("전체 정답률(필터 범위)", "—")
with K4:
    st.metric("최근 제출 시각", str(fdf.sort_values("dt").iloc[-1]["timestamp"]))

# 최근 제출 & 학급별 제출 표
T1, T2 = st.columns([2.1, 2.9])
with T1:
    st.write("### 학급별 제출")
    st.dataframe(fdf["class"].value_counts().rename_axis("학급").reset_index(name="제출 수"),
                 use_container_width=True, height=260)
with T2:
    st.write("### 최근 제출 10건")
    temp = fdf.copy()
    temp["정답 유형"] = temp["guess_mode"].map({"add":"합","sub":"차"}).fillna("-")
    temp["정답여부"] = temp["guess_correct_num"].map({1:"정답",0:"오답"}).fillna("-")
    cols_show = ["timestamp","class","nickname","quest","정답 유형","guess_value","정답여부","correct_answer","rubric_total"]
    cols_show = [c for c in cols_show if c in temp.columns]
    st.dataframe(
        temp[cols_show].sort_values("timestamp", ascending=False).head(10),
        use_container_width=True, height=260
    )

st.divider()
st.write("### 시각화 & 텍스트 분석(탭)")

# ===== 차트용 데이터 =====
correct_counts = fdf["guess_correct_num"].map({1:"정답",0:"오답"}).value_counts().rename_axis("정답여부").reset_index(name="명")
hist = (fdf["rubric_total"].dropna().astype(int)
        .value_counts().sort_index().rename_axis("총점(0–6)").reset_index(name="명"))
by_class_acc = (fdf.groupby("class")["guess_correct_num"].mean().mul(100).round(1)
                .rename("정답률(%)").reset_index())
by_class_cnt = fdf["class"].value_counts().rename_axis("학급").reset_index(name="제출 수")
by_day = (fdf.groupby("date").size().rename("제출 수").reset_index().sort_values("date"))

# ===== 자유응답(quest) 키워드 처리 =====
def tokenize_korean_en(s: str):
    """
    한글/영문/숫자를 단어로 추출. 한글은 2글자 이상, 영문/숫자는 2자 이상만 카운트.
    """
    if not isinstance(s, str):
        return []
    # 한글, 영문, 숫자 블록 추출
    tokens = re.findall(r"[가-힣]{2,}|[A-Za-z0-9]{2,}", s)
    return [t for t in tokens if t.strip()]

stop_default = "에서\n그리고\n그러면\n하지만\n때문에\n다시\n또는\n그리고\n입니다\n예를\n예:".split("\n")
with st.expander("🔎 자유응답(문항 요약) 키워드 분석 설정", expanded=False):
    st.caption("불용어를 줄바꿈으로 입력하세요. (선택)")
    stop_user = st.text_area("불용어 목록(선택, 줄바꿈 구분)", value="\n".join(stop_default))
    stopwords = set([w.strip() for w in stop_user.splitlines() if w.strip()])

from collections import Counter
texts = fdf["quest"].dropna().astype(str).tolist()
counter = Counter()
for line in texts:
    for tok in tokenize_korean_en(line):
        if tok not in stopwords:
            counter[tok] += 1
kw_df = pd.DataFrame(counter.most_common(30), columns=["단어","빈도"]) if counter else pd.DataFrame(columns=["단어","빈도"])

# ===== 탭(요청 순서 + 키워드) =====
tabs = st.tabs(["정답여부 비율", "자기평가 총점 분포", "학급별 정답률", "학급별 제출 수", "날짜별 제출 추이", "자유응답 키워드"])

# 1) 정답여부 비율
with tabs[0]:
    if correct_counts.empty:
        st.info("정답/오답 데이터가 충분하지 않습니다.")
    else:
        if altair_available():
            import altair as alt
            chart = alt.Chart(correct_counts).mark_arc(innerRadius=50).encode(
                theta="명:Q",
                color=alt.Color("정답여부:N", scale=alt.Scale(scheme="tableau10")),
                tooltip=["정답여부","명"]
            ).properties(height=360)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.bar_chart(correct_counts.set_index("정답여부"))

# 2) 자기평가 총점 분포
with tabs[1]:
    if hist.empty:
        st.info("총점 데이터가 없습니다.")
    else:
        if altair_available():
            import altair as alt
            chart = alt.Chart(hist).mark_bar().encode(
                x=alt.X("총점(0–6):O", title="자기평가 총점(0–6)"),
                y=alt.Y("명:Q", title="학생 수"),
                tooltip=["총점(0–6)","명"]
            ).properties(height=360)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.bar_chart(hist.set_index("총점(0–6)"))

# 3) 학급별 정답률
with tabs[2]:
    if by_class_acc.empty:
        st.info("학급별 정답률 데이터가 없습니다.")
    else:
        if altair_available():
            import altair as alt
            chart = alt.Chart(by_class_acc).mark_bar().encode(
                x=alt.X("class:N", title="학급", sort="-y"),
                y=alt.Y("정답률(%):Q"),
                tooltip=["class","정답률(%)"]
            ).properties(height=360)
            st.altair_chart(chart, use_container_width=True)
        else:
            # 컬럼명 한국어로 바꾸지 않고 index 기반으로도 표시 가능
            st.bar_chart(by_class_acc.set_index("class"))

# 4) 학급별 제출 수
with tabs[3]:
    if by_class_cnt.empty:
        st.info("학급별 데이터가 없습니다.")
    else:
        if altair_available():
            import altair as alt
            chart = alt.Chart(by_class_cnt).mark_bar().encode(
                y=alt.Y("학급:N", sort="-x"),
                x=alt.X("제출 수:Q"),
                tooltip=["학급","제출 수"]
            ).properties(height=360)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.bar_chart(by_class_cnt.set_index("학급"))

# 5) 날짜별 제출 추이
with tabs[4]:
    if by_day.empty:
        st.info("날짜별 제출 데이터가 없습니다.")
    else:
        if altair_available():
            import altair as alt
            chart = alt.Chart(by_day).mark_line(point=True).encode(
                x=alt.X("date:T", title="날짜"),
                y=alt.Y("제출 수:Q"),
                tooltip=["date:T","제출 수:Q"]
            ).properties(height=360)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.line_chart(by_day.set_index("date"))

# 6) 자유응답 키워드
with tabs[5]:
    st.write("**문항 요약(quest)에서 많이 등장한 단어 TOP 30**")
    if kw_df.empty:
        st.info("자유응답 데이터가 없거나, 유효한 단어가 없습니다.")
    else:
        ckw1, ckw2 = st.columns([2,3])
        with ckw1:
            st.dataframe(kw_df, use_container_width=True, height=360)
        with ckw2:
            if altair_available():
                import altair as alt
                chart = alt.Chart(kw_df).mark_bar().encode(
                    y=alt.Y("단어:N", sort="-x"),
                    x=alt.X("빈도:Q"),
                    tooltip=["단어","빈도"]
                ).properties(height=360)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.bar_chart(kw_df.set_index("단어"))

st.divider()
csv = fdf.drop(columns=["dt"]).to_csv(index=False).encode("utf-8-sig")
st.download_button("CSV 다운로드(필터 적용)", csv, file_name="submissions_filtered.csv", mime="text/csv")













