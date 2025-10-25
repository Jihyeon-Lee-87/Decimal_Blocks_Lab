# pages/1_교사_대시보드.py
import streamlit as st
import pandas as pd
import sqlite3
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

st.set_page_config(page_title="교사 대시보드", page_icon="📊", layout="wide")

# --- 접근 제어 ---
if not st.session_state.get("teacher_ok", False):
    st.error("교사 전용 페이지입니다. 좌측 사이드바에서 '교사' 선택 후 비밀번호를 입력하세요.")
    st.stop()

# --- 30초 자동 새로고침 ---
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30_000, key="teacher_dash_autorefresh")
except Exception:
    st.caption("⏱ 자동 새로고침을 사용하려면 requirements.txt에 `streamlit-autorefresh>=0.0.2`를 추가하세요.")

# --- DB 유틸 (프로젝트 루트의 같은 파일을 바라보도록 절대경로 고정) ---
ROOT_DIR = Path(__file__).resolve().parents[1]  # 프로젝트 루트
DB_PATH  = str(ROOT_DIR / "submissions.db")

@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                class TEXT,
                nickname TEXT,
                quest TEXT,
                rubric_1 INTEGER,
                rubric_2 INTEGER,
                rubric_3 INTEGER,
                rubric_total INTEGER
            )
        """)
    return conn

def fetch_all() -> pd.DataFrame:
    conn = get_conn()
    with closing(conn.cursor()) as cur:
        cur.execute("""
            SELECT timestamp, class, nickname, quest,
                   rubric_1, rubric_2, rubric_3, rubric_total
            FROM submissions
            ORDER BY datetime(timestamp) DESC
        """)
        cols = ["timestamp","class","nickname","quest",
                "rubric_1","rubric_2","rubric_3","rubric_total"]
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)

st.title("📊 교사 대시보드")
# 진단용: 필요시 경로 노출(확인 후 주석/삭제 가능)
# st.caption(f"DB 파일 경로: {DB_PATH}")

df = fetch_all()
if df.empty:
    st.warning("아직 제출이 없습니다. 학생 화면에서 제출 후 좌측 상단 'Rerun' 또는 새로고침하세요.")
    st.stop()

# 전처리(날짜 컬럼)
df["dt"] = pd.to_datetime(df["timestamp"], errors="coerce")
df["date"] = df["dt"].dt.date

# 필터 UI
flt = st.container()
with flt:
    left, mid, right = st.columns([2,2,3])
    with left:
        max_day = df["date"].max()
        min_day = df["date"].min()
        default_start = max(min_day, (max_day or date.today()) - timedelta(days=14))
        start_day = st.date_input("시작일", value=default_start,
                                  min_value=min_day, max_value=max_day or date.today())
    with mid:
        end_day = st.date_input("종료일", value=max_day or date.today(),
                                min_value=min_day, max_value=max_day or date.today())
    with right:
        class_options = ["4-사랑","4-기쁨","4-보람","4-행복","기타"]
        sel_classes = st.multiselect("학급(복수 선택)", class_options, default=class_options)

if start_day > end_day:
    st.error("시작일이 종료일보다 늦을 수 없습니다.")
    st.stop()

mask = (df["date"] >= start_day) & (df["date"] <= end_day) & (df["class"].isin(sel_classes))
fdf = df.loc[mask].copy()

if fdf.empty:
    st.info("선택한 조건에 해당하는 제출이 없습니다. 필터를 조정해 주세요.")
    st.stop()

# 상단 지표
topL, topR = st.columns([2,3])
with topL:
    st.metric("총 제출", len(fdf))
    st.metric("평균 자기평가 총점", round(fdf["rubric_total"].mean(), 2))
    st.write("### 학급별 제출")
    st.dataframe(fdf["class"].value_counts().rename_axis("class").reset_index(name="count"))
with topR:
    st.write("### 최근 제출 10건")
    st.dataframe(
        fdf[["timestamp","class","nickname","quest","rubric_total"]]
          .sort_values("timestamp", ascending=False)
          .head(10),
        use_container_width=True
    )

st.divider()
st.write("### 루브릭/제출 현황")

# 그래프 데이터
hist = (fdf["rubric_total"].value_counts()
        .sort_index()
        .rename_axis("자기평가 총점(0–6)")
        .reset_index(name="학생 수"))
by_day = fdf.groupby("date").size().rename("제출 수").reset_index()
by_class = fdf["class"].value_counts().rename_axis("학급").reset_index(name="제출 수")

c1, c2, c3 = st.columns(3)
try:
    import altair as alt
    with c1:
        st.write("**총점 히스토그램**")
        st.altair_chart(
            alt.Chart(hist).mark_bar().encode(
                x=alt.X("자기평가 총점(0–6):O", title="자기평가 총점(0–6)"),
                y=alt.Y("학생 수:Q", title="학생 수"),
                tooltip=["자기평가 총점(0–6)", "학생 수"]
            ).properties(height=280),
            use_container_width=True
        )
    with c2:
        st.write("**날짜별 제출 추이**")
        st.altair_chart(
            alt.Chart(by_day).mark_line(point=True).encode(
                x=alt.X("date:T", title="날짜"),
                y=alt.Y("제출 수:Q", title="제출 수"),
                tooltip=["date:T","제출 수:Q"]
            ).properties(height=280),
            use_container_width=True
        )
    with c3:
        st.write("**학급별 제출 수**")
        st.altair_chart(
            alt.Chart(by_class).mark_bar().encode(
                x=alt.X("학급:N", sort="-y"),
                y=alt.Y("제출 수:Q"),
                tooltip=["학급","제출 수"]
            ).properties(height=280),
            use_container_width=True
        )
except Exception:
    with c1:
        st.write("**총점 히스토그램**")
        st.bar_chart(hist.set_index("자기평가 총점(0–6)"))
    with c2:
        st.write("**날짜별 제출 추이**")
        st.line_chart(by_day.set_index("date"))
    with c3:
        st.write("**학급별 제출 수**")
        st.bar_chart(by_class.set_index("학급"))

# CSV 다운로드(필터 적용본)
csv = fdf.drop(columns=["dt"]).to_csv(index=False).encode("utf-8-sig")
st.download_button("CSV 다운로드(필터 적용)", csv, file_name="submissions_filtered.csv", mime="text/csv")



