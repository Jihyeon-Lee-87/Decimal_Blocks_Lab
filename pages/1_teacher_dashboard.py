# -*- coding: utf-8 -*-
# 교사 대시보드 (KPIs + 탭 시각화 5종)
# - 접근 제어: st.session_state["teacher_ok"] 필요
# - 필터: 날짜 / 학급
# - KPIs: 총 제출, 평균 자기평가, 전체 정답률, 최근 제출 시각
# - 탭:
#   1) 전체 정답률(도넛) + 분포
#   2) 학급별 정답률(막대)
#   3) 학급별 제출 수(막대)
#   4) 날짜별 제출 추이(선)
#   5) 학생 답변 키워드(상위 30, 가벼운 토크나이저)

import re
import sqlite3
from pathlib import Path
from contextlib import closing
from datetime import date, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="교사 대시보드", page_icon="📊", layout="wide")

# ────────── 접근 제어 ──────────
if not st.session_state.get("teacher_ok", False):
    st.error("교사 전용 페이지입니다. 메인 화면 사이드바에서 '교사' 선택 후 비밀번호를 입력하세요.")
    st.stop()

# ────────── 자동 새로고침(선택) ──────────
try:
    from streamlit_autorefresh import st_autorefresh
    if st.toggle("30초 자동 새로고침", value=False, key="teacher_autorefresh"):
        st_autorefresh(interval=30_000, key="teacher_dash_autorefresh_tabs")
except Exception:
    st.caption("⏱ `streamlit-autorefresh` 미설치 상태(선택). requirements.txt에 `streamlit-autorefresh>=0.0.2` 추가 시 사용 가능.")

# ────────── DB 유틸 (/mount/data 우선) ──────────
def _writable_data_dir() -> Path:
    for p in [Path("/mount/data"), Path.cwd() / ".data"]:
        try:
            p.mkdir(parents=True, exist_ok=True)
            t = p / "_wtest"
            with open(t, "w") as f: f.write("ok")
            t.unlink(missing_ok=True)
            return p
        except Exception:
            continue
    Path.cwd().mkdir(parents=True, exist_ok=True)
    return Path.cwd()

DATA_DIR = _writable_data_dir()
DB_PATH  = str(DATA_DIR / "submissions.db")

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
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
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

# ────────── 상단 제목/버튼 ──────────
st.title("📊 교사 대시보드")
st.caption("모든 시간은 KST(Asia/Seoul) 기준으로 저장·표시됩니다.")
if st.button("🔄 새로고침"):
    st.rerun()

# ────────── 데이터 로딩 ──────────
df = fetch_all()
if df.empty:
    st.warning("아직 제출이 없습니다. 학생 화면에서 제출 후 다시 새로고침하세요.")
    st.stop()

# 전처리
df["dt"] = pd.to_datetime(df["timestamp"], errors="coerce")
df["date"] = df["dt"].dt.date
df["rubric_total"] = pd.to_numeric(df["rubric_total"], errors="coerce")
df["guess_correct_num"] = pd.to_numeric(df["guess_correct"], errors="coerce")

# ────────── 필터 ──────────
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
    st.error("시작일이 종료일보다 늦을 수 없습니다.")
    st.stop()

mask = (df["date"] >= start_day) & (df["date"] <= end_day) & (df["class"].isin(sel_classes))
fdf = df.loc[mask].copy()
if fdf.empty:
    st.info("선택한 조건에 해당하는 제출이 없습니다. 필터를 조정해 주세요.")
    st.stop()

# ────────── KPI ──────────
K1, K2, K3, K4 = st.columns(4)
with K1:
    st.metric("총 제출", len(fdf))
with K2:
    st.metric("평균 자기평가 총점", round(fdf["rubric_total"].dropna().astype(int).mean(), 2))
with K3:
    if fdf["guess_correct_num"].notna().any():
        acc = fdf["guess_correct_num"].fillna(0).astype(int).mean() * 100
        st.metric("전체 정답률", f"{acc:.0f}%")
    else:
        st.metric("전체 정답률", "—")
with K4:
    st.metric("최근 제출 시각", str(fdf.sort_values("dt").iloc[-1]["timestamp"]))

st.divider()

# ────────── 탭 5종 ──────────
tabs = st.tabs(["전체 정답률", "학급별 정답률", "학급별 제출 수", "날짜별 제출 추이", "학생 답변 키워드"])

def altair_available() -> bool:
    try:
        import altair as alt  # noqa
        return True
    except Exception:
        return False

# 공통 파생 데이터
correct_counts = fdf["guess_correct_num"].map({1:"정답",0:"오답"}).value_counts().rename_axis("정답여부").reset_index(name="명")
by_class_acc = (fdf.groupby("class")["guess_correct_num"]
                .mean().mul(100).round(1).rename("정답률(%)").reset_index())
by_class_acc = by_class_acc.rename(columns={"class": "학급"})
by_class_cnt = fdf["class"].value_counts().rename_axis("학급").reset_index(name="제출 수")
by_day = (fdf.groupby("date").size().rename("제출 수").reset_index().sort_values("date"))
hist = (fdf["rubric_total"].dropna().astype(int)
        .value_counts().sort_index().rename_axis("총점(0–6)").reset_index(name="명"))

# 1) 전체 정답률
with tabs[0]:
    st.subheader("전체 정답률")
    if correct_counts.empty:
        st.info("정답/오답 데이터가 없습니다.")
    else:
        if altair_available():
            import altair as alt
            # 도넛
            donut = alt.Chart(correct_counts).mark_arc(innerRadius=60).encode(
                theta="명:Q",
                color=alt.Color("정답여부:N", sort=["정답","오답"]),
                tooltip=["정답여부","명"]
            ).properties(height=320)
            st.altair_chart(donut, use_container_width=True)
        else:
            st.bar_chart(correct_counts.set_index("정답여부"))
    st.caption("왼쪽 KPI에도 전체 정답률이 표시됩니다.")

# 2) 학급별 정답률
with tabs[1]:
    st.subheader("학급별 정답률")
    if by_class_acc.empty:
        st.info("학급별 정답률 데이터가 없습니다.")
    else:
        if altair_available():
            import altair as alt
            chart = alt.Chart(by_class_acc).mark_bar().encode(
                x=alt.X("학급:N", sort="-y"),
                y=alt.Y("정답률(%):Q"),
                tooltip=["학급","정답률(%)"]
            ).properties(height=360)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.bar_chart(by_class_acc.set_index("학급"))

# 3) 학급별 제출 수
with tabs[2]:
    st.subheader("학급별 제출 수")
    if by_class_cnt.empty:
        st.info("학급별 제출 데이터가 없습니다.")
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

# 4) 날짜별 제출 추이
with tabs[3]:
    st.subheader("날짜별 제출 추이")
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

# 5) 학생 답변 키워드
with tabs[4]:
    st.subheader("학생 답변 키워드(상위 30)")
    # 아주 가벼운 토크나이저(한/영/숫자 연속 토큰 추출)
    texts = fdf["quest"].dropna().astype(str)
    if texts.empty:
        st.info("문항/과제(학생 자유 입력)가 없습니다.")
    else:
        tokens = []
        hangul_re = re.compile(r"[가-힣A-Za-z0-9]+")
        stop = set([
            "그리고","그래서","하지만","혹은","또는","또","즉","이건","저는","제가","우리는","너무",
            "정답","오답","받아올림","받아내림","합","차","문제","과제","설명","으로","에서","하다","했다",
            "입니다","예","아니오","예시","같은","이번","오늘","합니다","했던","있는","없는","어떻게","왜",
            "수","숫자","자리","소수","첫째","둘째","셋째","자리수","계산","빌리다","더하다","빼다"
        ])
        for line in texts:
            for tok in hangul_re.findall(line.lower()):
                # 너무 짧은 토큰/숫자만 토큰 제외
                if len(tok) < 2: 
                    continue
                if tok.isdigit():
                    continue
                if tok in stop:
                    continue
                tokens.append(tok)

        if not tokens:
            st.info("유의미한 키워드를 찾기 어려웠습니다.")
        else:
            freq = pd.Series(tokens).value_counts().head(30).rename_axis("키워드").reset_index(name="빈도")
            if altair_available():
                import altair as alt
                chart = alt.Chart(freq).mark_bar().encode(
                    y=alt.Y("키워드:N", sort="-x"),
                    x=alt.X("빈도:Q"),
                    tooltip=["키워드","빈도"]
                ).properties(height=480)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.bar_chart(freq.set_index("키워드"))
            with st.expander("표로 보기"):
                st.dataframe(freq, use_container_width=True, height=420)

st.divider()
csv = fdf.drop(columns=["dt"]).to_csv(index=False).encode("utf-8-sig")
st.download_button("CSV 다운로드(필터 적용)", csv, file_name="submissions_filtered.csv", mime="text/csv")














