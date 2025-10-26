# -*- coding: utf-8 -*-
# Decimal Blocks 3D — 학생 모드(덧셈/뺄셈 애니메이션 + 정답 맞혀보기 + 제출) + 교사 인증 시 자동 전환(안전)
import os, base64, time, sqlite3
from contextlib import closing
from typing import Optional, Tuple
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import matplotlib
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import pandas as pd
import streamlit as st

# ────────── 공통/DB ──────────
st.set_page_config(page_title="Decimal Blocks 3D", page_icon="🔢", layout="wide")
ROOT = Path(__file__).resolve().parent
DB_PATH = str(ROOT / "submissions.db")

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

def add_submission(row: dict):
    conn = get_conn()
    with conn:
        conn.execute("""
            INSERT INTO submissions
            (timestamp,class,nickname,quest,rubric_1,rubric_2,rubric_3,rubric_total,
             guess_mode,guess_value,guess_correct,correct_answer)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            row.get("timestamp"), row.get("class"), row.get("nickname"), row.get("quest"),
            row.get("rubric_1"), row.get("rubric_2"), row.get("rubric_3"), row.get("rubric_total"),
            row.get("guess_mode"), row.get("guess_value"), row.get("guess_correct"), row.get("correct_answer"),
        ))

def kst_now_str():
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")

# ────────── 세션 기본값 ──────────
def ensure_defaults():
    ss = st.session_state
    ss.setdefault("teacher_ok", False)
    ss.setdefault("A", 1.257)               # 첫번째 수
    ss.setdefault("B", 0.078)               # 두번째 수
    ss.setdefault("level", 0)               # 정답 레벨
    ss.setdefault("wrong_streak_add", 0)
    ss.setdefault("wrong_streak_sub", 0)
    ss.setdefault("last_guess_mode", None)
    ss.setdefault("last_guess_value", None)
    ss.setdefault("last_guess_correct", None)
    ss.setdefault("last_correct_answer", None)
ensure_defaults()

# ────────── 사이드바: 역할 선택(교사 인증 시 전환) + 문제 입력 ──────────
with st.sidebar:
    st.markdown("### 역할 선택")
    role = st.radio("역할", ["학생", "교사"], horizontal=True, key="role_sel")

    if role == "교사":
        pw = st.text_input("교사 비밀번호", type="password", help="관리자가 정한 비밀번호")
        teacher_pw = os.environ.get("TEACHER_PW", "teacher")  # 없으면 'teacher'
        if pw:
            if pw == teacher_pw:
                st.session_state.teacher_ok = True
                st.success("교사 인증 완료!")

                # ✅ 인증 즉시 교사 대시보드로 전환(스위치 실패 시 링크 제공)
                switched = False
                try:
                    st.switch_page("pages/1_teacher_dashboard.py")
                    switched = True
                except Exception:
                    pass
                if not switched:
                    st.page_link("pages/1_teacher_dashboard.py", label="📊 교사 대시보드 열기", icon="📊")
            else:
                st.session_state.teacher_ok = False
                st.error("비밀번호가 올바르지 않습니다.")
    else:
        st.session_state.teacher_ok = False

# 본문 보호 가드(이미 인증되어 있으면 즉시 전환, 실패 시 링크 제공)
if st.session_state.get("teacher_ok", False):
    try:
        st.switch_page("pages/1_teacher_dashboard.py")
    except Exception:
        st.info("교사 대시보드로 이동하려면 아래를 클릭하세요.")
        st.page_link("pages/1_teacher_dashboard.py", label="📊 교사 대시보드 열기", icon="📊")
    # 이후 학생용 렌더링은 자동으로 건너뜀
    st.stop()

# ────────── 학생 모드 헤더/입력 ──────────
st.markdown("<h1 style='margin:0'>Decimal Blocks 3D - 소수 셋째 자리까지의 덧셈·뺄셈</h1>", unsafe_allow_html=True)
st.markdown("<div style='font-size:16px;color:#334155;margin:6px 0 14px 0'>원하는 두 수를 입력하고 각 탭의 <b>정답 맞혀보기</b> 또는 <b>애니메이션 시작</b> 버튼을 눌러보세요.</div>", unsafe_allow_html=True)

with st.sidebar:
    st.divider()
    st.markdown("#### 문제 수 입력")
    st.number_input("첫번째 수 (0.000~9.999)", min_value=0.000, max_value=9.999,
                    value=float(st.session_state.get("A", 1.257)),
                    step=0.001, format="%.3f", key="A")
    st.number_input("두번째 수 (0.000~9.999)", min_value=0.000, max_value=9.999,
                    value=float(st.session_state.get("B", 0.078)),
                    step=0.001, format="%.3f", key="B")
    st.caption("팁: 애니메이션 전 ‘정답 맞혀보기’를 눌러보세요. 맞으면 풍선+효과음!")

# ────────── 스타일/타이밍/색 ──────────
matplotlib.rcParams["font.family"] = ["Noto Sans CJK KR","NanumGothic","Apple SD Gothic Neo","Malgun Gothic","DejaVu Sans"]
matplotlib.rcParams["font.size"] = 13

COLOR_ONES   = (0.20, 0.48, 0.78, 1.0)   # 1 (큐브)
COLOR_TENTHS = (0.46, 0.68, 0.22, 1.0)   # 0.1 (판)
COLOR_HUNDS  = (0.98, 0.52, 0.18, 1.0)   # 0.01 (막대)
COLOR_THOUS  = (0.60, 0.40, 0.80, 1.0)   # 0.001 (작은 큐브)
COLOR_FLASH  = (1.00, 1.00, 0.10, 1.0)   # 형광노랑

STEP_DELAY_MOVE     = 0.25
BLINK_CYCLES        = 2
BLINK_INTERVAL      = 0.60
CARRY_PAUSE_BEFORE  = 0.60
CARRY_PAUSE_AFTER   = 0.60
ALERT_SECONDS       = 4.0

# ────────── 숫자 분해 ──────────
def split_digits(x: float):
    s = f"{float(x):.3f}"
    left, right = s.split(".")
    o = int(left[-1]) if left else 0
    t = int(right[0]); h = int(right[1]); k = int(right[2])
    return o, t, h, k

# ────────── 3D 유틸 ──────────
def cuboid_vertices(x, y, z, dx, dy, dz):
    X=[x, x+dx, x+dx, x, x, x+dx, x+dx, x]
    Y=[y, y, y+dy, y+dy, y, y, y+dy, y+dy]
    Z=[z, z, z, z, z+dz, z+dz, z+dz, z+dz]
    return [
        [(X[0],Y[0],Z[0]),(X[1],Y[1],Z[1]),(X[2],Y[2],Z[2]),(X[3],Y[3],Z[3])],
        [(X[4],Y[4],Z[4]),(X[5],Y[5],Z[5]),(X[6],Y[6],Z[6]),(X[7],Y[7],Z[7])],
        [(X[0],Y[0],Z[0]),(X[1],Y[1],Z[1]),(X[5],Y[5],Z[5]),(X[4],Y[4],Z[4])],
        [(X[2],Y[2],Z[2]),(X[3],Y[3],Z[3]),(X[7],Y[7],Z[7]),(X[6],Y[6],Z[6])],
        [(X[1],Y[1],Z[1]),(X[2],Y[2],Z[2]),(X[6],Y[6],Z[6]),(X[5],Y[5],Z[5])],
        [(X[0],Y[0],Z[0]),(X[3],Y[3],Z[3]),(X[7],Y[7],Z[7]),(X[4],Y[4],Z[4])],
    ]

def add_block(ax, pos, size, color):
    ax.add_collection3d(Poly3DCollection(
        cuboid_vertices(*pos, *size),
        facecolors=[color]*6,
        edgecolors=(0,0,0,0.35)
    ))

def scene_axes():
    fig = plt.figure(figsize=(2.6, 2.6), dpi=160)
    ax = fig.add_subplot(111, projection='3d')
    ax.set_facecolor((1,1,1,0)); ax.grid(False)
    try: ax.set_proj_type('ortho')
    except: pass
    try: ax.set_box_aspect((5,3,3))
    except: pass
    ax.view_init(elev=18, azim=-45)
    ax.set_xlim(0,5.2); ax.set_ylim(0,3.2); ax.set_zlim(0,3.2)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])
    try: ax.set_position([0,0,1,1])
    except: pass
    return fig, ax

# ────────── 크기/간격(막대10=판1, 판10=큐브1 비율 일치) ──────────
GAP_MICRO_X = 0.10
GAP_ROD_X   = 0.10
GAP_PLATE_Z = 0.10

S = 1.0 + 9*GAP_ROD_X
PLATE_THICK = max((S - 9*GAP_PLATE_Z)/10.0, 0.001)

SIZE_MICRO = (0.1, 0.1, 0.1)      # 0.001
SIZE_ROD   = (0.1, S, 0.1)        # 0.01
SIZE_PLATE = (S, S, PLATE_THICK)  # 0.1
SIZE_CUBE  = (S, S, S)            # 1

def draw_micros(ax, n, color, gap_x=GAP_MICRO_X):
    dx, dy, dz = SIZE_MICRO
    for k in range(n):
        add_block(ax, (k*(dx + gap_x), 0.0, 0.0), SIZE_MICRO, color)

def draw_rods(ax, n, color, gap_x=GAP_ROD_X):
    dx, dy, dz = SIZE_ROD
    for k in range(n):
        add_block(ax, (k*(dx + gap_x), 0.0, 0.0), SIZE_ROD, color)

def draw_plates(ax, n, color, gap_z=GAP_PLATE_Z):
    for k in range(n):
        add_block(ax, (0.0, 0.0, k*(PLATE_THICK + gap_z)), SIZE_PLATE, color)

def draw_cubes(ax, n, color, cols=2, gap=None):
    if gap is None: gap = 0.35 * S
    for i in range(n):
        r, c = divmod(i, cols)
        add_block(ax, (c*(SIZE_CUBE[0]+gap), r*(SIZE_CUBE[1]+gap), 0), SIZE_CUBE, color)

# ────────── 사운드(선택) ──────────
def load_bytes(path: str) -> Optional[bytes]:
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None

def to_tuple(data: Optional[bytes], filename: str) -> Optional[Tuple[bytes,str]]:
    if not data: return None
    ext = os.path.splitext(filename)[1].lower()
    mime = "audio/mpeg" if ext == ".mp3" else "audio/wav"
    return (data, mime)

SND_POP   = to_tuple(load_bytes("이동2.mp3"),        "이동2.mp3")             # 이동
SND_TRANS = to_tuple(load_bytes("변환.mp3"),          "변환.mp3")              # 변환/받아올림/내림
SND_OK    = to_tuple(load_bytes("정답 레벨업.mp3"),   "정답 레벨업.mp3")       # 완료/정답
SND_WRONG = to_tuple(load_bytes("다시 생각해보세요.mp3"), "다시 생각해보세요.mp3") # 오답

def play_sound(t: Optional[Tuple[bytes,str]]):
    if not t: return
    data, mime = t
    b64 = base64.b64encode(data).decode()
    uid = str(time.time()).replace('.','')
    st.markdown(
        f"""<audio id="aud{uid}" autoplay style="display:none">
               <source src="data:{mime};base64,{b64}">
           </audio>""",
        unsafe_allow_html=True
    )

# ────────── 큰 말풍선(메인) ──────────
ALERT = st.empty()
def show_alert(text: str, seconds: float = 4.0):
    ALERT.markdown(
        f"""
        <div style="display:flex;align-items:center;justify-content:center;margin:8px 0 14px 0;">
          <div style="max-width:1100px;width:100%;
                      background:#ffffff;border:3px solid #0ea5a6;border-radius:16px;
                      padding:20px 24px;box-shadow:0 8px 28px rgba(0,0,0,0.15);
                      font-size:28px;font-weight:900;color:#0f172a;text-align:center;">
            {text}
          </div>
        </div>
        """, unsafe_allow_html=True
    )
    time.sleep(seconds)
    ALERT.empty()

# ────────── 깜빡임(받아올림/받아내림) ──────────
def flash_micros_as_rod(ph):
    time.sleep(0.60)
    for _ in range(2):
        fig, ax = scene_axes(); draw_micros(ax, 10, COLOR_FLASH); ph.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
        fig, ax = scene_axes(); draw_micros(ax, 10, COLOR_THOUS); ph.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
    time.sleep(0.60); play_sound(SND_TRANS)

def flash_rods_as_plate(ph):
    time.sleep(0.60)
    for _ in range(2):
        fig, ax = scene_axes(); draw_rods(ax, 10, COLOR_FLASH); ph.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
        fig, ax = scene_axes(); draw_rods(ax, 10, COLOR_HUNDS ); ph.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
    time.sleep(0.60); play_sound(SND_TRANS)

def flash_plates_as_cube(ph_T, ph_O, o_now):
    time.sleep(0.60)
    for _ in range(2):
        fig, ax = scene_axes(); draw_plates(ax, 10, COLOR_FLASH); ph_T.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
        fig, ax = scene_axes(); draw_plates(ax, 10, COLOR_TENTHS); ph_T.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
    for _ in range(2):
        fig, ax = scene_axes(); draw_cubes(ax, o_now+1, COLOR_FLASH); ph_O.pyplot(fig, True); plt.close(fig); time.sleep(0.25)
        fig, ax = scene_axes(); draw_cubes(ax, o_now,   COLOR_ONES ); ph_O.pyplot(fig, True); plt.close(fig); time.sleep(0.25)
    time.sleep(0.60); play_sound(SND_TRANS)

def flash_one_rod_to_ten_micros(ph_source_H, ph_dest_K):
    time.sleep(0.60)
    for _ in range(2):
        fig, ax = scene_axes(); draw_rods(ax, 1, COLOR_FLASH); ph_source_H.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
        fig, ax = scene_axes(); draw_rods(ax, 1, COLOR_HUNDS ); ph_source_H.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
    for _ in range(2):
        fig, ax = scene_axes(); draw_micros(ax, 10, COLOR_FLASH); ph_dest_K.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
        fig, ax = scene_axes(); draw_micros(ax, 10, COLOR_THOUS); ph_dest_K.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
    time.sleep(0.60); play_sound(SND_TRANS)

def flash_one_plate_to_ten_rods(ph_source_T, ph_dest_H):
    time.sleep(0.60)
    for _ in range(2):
        fig, ax = scene_axes(); draw_plates(ax, 1, COLOR_FLASH); ph_source_T.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
        fig, ax = scene_axes(); draw_plates(ax, 1, COLOR_TENTHS); ph_source_T.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
    for _ in range(2):
        fig, ax = scene_axes(); draw_rods(ax, 10, COLOR_FLASH); ph_dest_H.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
        fig, ax = scene_axes(); draw_rods(ax, 10, COLOR_HUNDS ); ph_dest_H.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
    time.sleep(0.60); play_sound(SND_TRANS)

def flash_one_cube_to_ten_plates(ph_source_O, ph_dest_T, t_now):
    time.sleep(0.60)
    for _ in range(2):
        fig, ax = scene_axes(); draw_cubes(ax, 1, COLOR_FLASH); ph_source_O.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
        fig, ax = scene_axes(); draw_cubes(ax, 1, COLOR_ONES ); ph_source_O.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
    for _ in range(2):
        fig, ax = scene_axes(); draw_plates(ax, 10, COLOR_FLASH); ph_dest_T.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
        fig, ax = scene_axes(); draw_plates(ax, 10, COLOR_TENTHS); ph_dest_T.pyplot(fig, True); plt.close(fig); time.sleep(0.60)
    time.sleep(0.60); play_sound(SND_TRANS)

# ────────── 공용 숫자/패널 렌더 ──────────
def number_row(parent_col, o, t, h, k, title):
    parent_col.markdown(f"<div style='text-align:center;font-size:20px;font-weight:900;margin-bottom:4px;'>{title}</div>", unsafe_allow_html=True)
    c1, cdot, c2, c3, c4 = parent_col.columns([1, 0.10, 1, 1, 1], gap="small")
    o_ph = c1.empty(); t_ph = c2.empty(); h_ph = c3.empty(); k_ph = c4.empty()
    cdot.markdown("<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>·</div>", unsafe_allow_html=True)
    for ph, val in [(o_ph,o),(t_ph,t),(h_ph,h),(k_ph,k)]:
        ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{val}</div>", unsafe_allow_html=True)
    p1, _, p2, p3, p4 = parent_col.columns([1, 0.10, 1, 1, 1], gap="small")
    return (o_ph, t_ph, h_ph, k_ph), (p1.empty(), p2.empty(), p3.empty(), p4.empty())

def set_numbers(ph_tuple, o, t, h, k):
    o_ph, t_ph, h_ph, k_ph = ph_tuple
    for ph, val in [(o_ph,o),(t_ph,t),(h_ph,h),(k_ph,k)]:
        ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{val}</div>", unsafe_allow_html=True)

def render_panel(ph, count, kind: str, label=None):
    fig, ax = scene_axes()
    if kind == "O":
        draw_cubes(ax, count, COLOR_ONES)
        if label == "O": ax.text(0.0, 0.0, 2.45, "0.1×10→1", color="#0F766E", fontsize=14, weight="bold")
    elif kind == "T":
        draw_plates(ax, count, COLOR_TENTHS)
        if label == "T": ax.text(0.0, 0.0, 2.45, "0.01×10→0.1", color="#0F766E", fontsize=14, weight="bold")
    elif kind == "H":
        draw_rods(ax, count, COLOR_HUNDS)
        if label == "H": ax.text(0.0, 0.0, 2.45, "0.001×10→0.01", color="#0F766E", fontsize=14, weight="bold")
    else:  # K
        draw_micros(ax, count, COLOR_THOUS)
    ph.pyplot(fig, True); plt.close(fig)

# ────────── 덧셈/뺄셈 탭 ──────────
tab_add, tab_sub = st.tabs(["➕ 덧셈", "➖ 뺄셈"])

# ===== 덧셈 =====
with tab_add:
    row_top = st.columns(2, gap="large")
    row_bot = st.columns(1)

    A_o0, A_t0, A_h0, A_k0 = split_digits(st.session_state["A"])
    B_o0, B_t0, B_h0, B_k0 = split_digits(st.session_state["B"])

    A_nums, (F_O, F_T, F_H, F_K) = number_row(row_top[0], A_o0, A_t0, A_h0, A_k0, "첫번째 수")
    B_nums, (S_O, S_T, S_H, S_K) = number_row(row_top[1], B_o0, B_t0, B_h0, B_k0, "두번째 수")

    result = row_bot[0].container()
    result.markdown("<div style='text-align:center;font-size:20px;font-weight:900;margin-bottom:4px;'>결과</div>", unsafe_allow_html=True)
    r_num = result.columns([1,0.10,1,1,1], gap="small")
    R_o_num, R_dot, R_t_num, R_h_num, R_k_num = r_num[0].empty(), r_num[1], r_num[2].empty(), r_num[3].empty(), r_num[4].empty()
    R_dot.markdown("<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>·</div>", unsafe_allow_html=True)
    r_pan = result.columns([1,0.10,1,1,1], gap="small")
    R_O, R_T, R_H, R_K = r_pan[0].empty(), r_pan[2].empty(), r_pan[3].empty(), r_pan[4].empty()

    def update_result_numbers_add(o, t, h, k):
        for ph, val in [(R_o_num,o),(R_t_num,t),(R_h_num,h),(R_k_num,k)]:
            ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{val}</div>", unsafe_allow_html=True)

    add_A = {"o":A_o0, "t":A_t0, "h":A_h0, "k":A_k0}
    add_B = {"o":B_o0, "t":B_t0, "h":B_h0, "k":B_k0}
    add_R = {"o":0,    "t":0,    "h":0,    "k":0}

    def render_all_add(label=None):
        set_numbers(A_nums, add_A["o"], add_A["t"], add_A["h"], add_A["k"])
        set_numbers(B_nums, add_B["o"], add_B["t"], add_B["h"], add_B["k"])
        update_result_numbers_add(add_R["o"], add_R["t"], add_R["h"], add_R["k"])
        render_panel(F_O, add_A["o"], "O"); render_panel(F_T, add_A["t"], "T")
        render_panel(F_H, add_A["h"], "H"); render_panel(F_K, add_A["k"], "K")
        render_panel(S_O, add_B["o"], "O"); render_panel(S_T, add_B["t"], "T")
        render_panel(S_H, add_B["h"], "H"); render_panel(S_K, add_B["k"], "K")
        render_panel(R_O, add_R["o"], "O", label="O" if label=="O" else None)
        render_panel(R_T, add_R["t"], "T", label="T" if label=="T" else None)
        render_panel(R_H, add_R["h"], "H", label="H" if label=="H" else None)
        render_panel(R_K, add_R["k"], "K")

    render_all_add()

    # --- 정답 맞혀보기 (덧셈) ---
    st.markdown("#### 🧠 정답 맞혀보기 (덧셈)")
    colg1, colg2 = st.columns([2,1])
    with colg1:
        user_guess_add = st.text_input("두 수의 합을 예상해 입력해 보세요(예: 2.035)", key="guess_add")
    with colg2:
        if st.button("정답 확인(덧셈)", key="check_add"):
            try:
                correct_add = round(float(st.session_state["A"]) + float(st.session_state["B"]), 3)
                guess_val = round(float(user_guess_add), 3)
                if guess_val == correct_add:
                    st.success("정답이에요! 🎉")
                    st.balloons(); play_sound(SND_OK)
                    st.session_state["level"] = st.session_state.get("level", 0) + 1
                    st.toast(f"레벨 {st.session_state['level']} 달성!", icon="🎈")
                    st.session_state["wrong_streak_add"] = 0
                    st.session_state["last_guess_mode"] = "add"
                    st.session_state["last_guess_value"] = f"{guess_val:.3f}"
                    st.session_state["last_guess_correct"] = 1
                    st.session_state["last_correct_answer"] = f"{correct_add:.3f}"
                else:
                    play_sound(SND_WRONG)
                    st.error("아쉬워요! ❌")
                    ws = st.session_state.get("wrong_streak_add", 0) + 1
                    st.session_state["wrong_streak_add"] = ws
                    A_o,A_t,A_h,A_k = split_digits(st.session_state["A"])
                    B_o,B_t,B_h,B_k = split_digits(st.session_state["B"])
                    hints = []
                    carry_k = 1 if (A_k+B_k)>=10 else 0
                    carry_h = 1 if (A_h+B_h+carry_k)>=10 else 0
                    carry_t = 1 if (A_t+B_t+carry_h)>=10 else 0
                    if ws >= 1:
                        step1 = []
                        if carry_k: step1.append("소수 셋째 자리에서 받아올림이 생겨요.")
                        if carry_h: step1.append("소수 둘째 자리에서도 받아올림이 생겨요.")
                        if carry_t: step1.append("소수 첫째 자리에서도 받아올림이 생겨요.")
                        if step1: hints.append("<br>".join(step1))
                    if ws >= 2:
                        k_sum = A_k + B_k
                        h_sum = A_h + B_h + (1 if k_sum>=10 else 0)
                        t_sum = A_t + B_t + (1 if h_sum>=10 else 0)
                        hints.append(f"부분합 힌트: 0.001자리={k_sum}, 0.01자리={h_sum}, 0.1자리={t_sum}")
                    if ws >= 3:
                        hints.append("정답 형식 힌트: 합은 소수 셋째 자리까지 표기(예: a.bcd).")
                    show_alert("<br>".join(hints) if hints else "자릿값을 다시 생각해 보세요!", seconds=3.5)
                    st.session_state["last_guess_mode"] = "add"
                    st.session_state["last_guess_value"] = f"{guess_val:.3f}"
                    st.session_state["last_guess_correct"] = 0
                    st.session_state["last_correct_answer"] = f"{correct_add:.3f}"
            except Exception:
                st.warning("숫자 형식으로 입력해 주세요. 예: 2.035")

    # --- (덧셈) 애니메이션 시작 ---
    if st.button("▶ (덧셈) 애니메이션 시작", use_container_width=True, key="run_add"):
        # 0.001 이동
        for _ in range(add_A["k"]):
            add_A["k"] -= 1; add_R["k"] += 1; render_all_add(); play_sound(SND_POP); time.sleep(STEP_DELAY_MOVE)
            if add_R["k"] == 10:
                show_alert("0.001이 10개 모여 0.01이 됐어요.<br><b>소수 둘째 자리로 1 받아올림할게요.</b>")
                flash_micros_as_rod(R_K)
                add_R["k"] = 0; add_R["h"] += 1; render_all_add(label="H"); time.sleep(STEP_DELAY_MOVE)
        for _ in range(add_B["k"]):
            add_B["k"] -= 1; add_R["k"] += 1; render_all_add(); play_sound(SND_POP); time.sleep(STEP_DELAY_MOVE)
            if add_R["k"] == 10:
                show_alert("0.001이 10개 모여 0.01이 됐어요.<br><b>소수 둘째 자리로 1 받아올림할게요.</b>")
                flash_micros_as_rod(R_K)
                add_R["k"] = 0; add_R["h"] += 1; render_all_add(label="H"); time.sleep(STEP_DELAY_MOVE)
        # 0.01 이동
        for _ in range(add_A["h"]):
            add_A["h"] -= 1; add_R["h"] += 1; render_all_add(); play_sound(SND_POP); time.sleep(STEP_DELAY_MOVE)
            if add_R["h"] == 10:
                show_alert("0.01이 10개 모여 0.1이 됐어요.<br><b>소수 첫째 자리로 1 받아올림할게요.</b>")
                flash_rods_as_plate(R_H)
                add_R["h"] = 0; add_R["t"] += 1; render_all_add(label="T"); time.sleep(STEP_DELAY_MOVE)
        for _ in range(add_B["h"]):
            add_B["h"] -= 1; add_R["h"] += 1; render_all_add(); play_sound(SND_POP); time.sleep(STEP_DELAY_MOVE)
            if add_R["h"] == 10:
                show_alert("0.01이 10개 모여 0.1이 됐어요.<br><b>소수 첫째 자리로 1 받아올림할게요.</b>")
                flash_rods_as_plate(R_H)
                add_R["h"] = 0; add_R["t"] += 1; render_all_add(label="T"); time.sleep(STEP_DELAY_MOVE)
        # 0.1 이동
        for _ in range(add_A["t"]):
            add_A["t"] -= 1; add_R["t"] += 1; render_all_add(); play_sound(SND_POP); time.sleep(STEP_DELAY_MOVE)
            if add_R["t"] == 10:
                show_alert("0.1이 10개 모여 1이 됐어요.<br><b>일의 자리로 1 받아올림할게요.</b>")
                flash_plates_as_cube(R_T, R_O, add_R["o"])
                add_R["t"] = 0; add_R["o"] += 1; render_all_add(label="O"); time.sleep(STEP_DELAY_MOVE)
        for _ in range(add_B["t"]):
            add_B["t"] -= 1; add_R["t"] += 1; render_all_add(); play_sound(SND_POP); time.sleep(STEP_DELAY_MOVE)
            if add_R["t"] == 10:
                show_alert("0.1이 10개 모여 1이 됐어요.<br><b>일의 자리로 1 받아올림할게요.</b>")
                flash_plates_as_cube(R_T, R_O, add_R["o"])
                add_R["t"] = 0; add_R["o"] += 1; render_all_add(label="O"); time.sleep(STEP_DELAY_MOVE)
        # 1 이동
        for _ in range(add_A["o"]):
            add_A["o"] -= 1; add_R["o"] += 1; render_all_add(); play_sound(SND_POP); time.sleep(STEP_DELAY_MOVE)
        for _ in range(add_B["o"]):
            add_B["o"] -= 1; add_R["o"] += 1; render_all_add(); play_sound(SND_POP); time.sleep(STEP_DELAY_MOVE)
        render_all_add(); play_sound(SND_OK)

# ===== 뺄셈 =====
with tab_sub:
    row_top = st.columns(2, gap="large")
    row_bot = st.columns(1)

    A0_o, A0_t, A0_h, A0_k = split_digits(st.session_state["A"])
    B0_o, B0_t, B0_h, B0_k = split_digits(st.session_state["B"])

    sub_A = {"o":A0_o, "t":A0_t, "h":A0_h, "k":A0_k}  # 원래 수(표시)
    sub_B = {"o":B0_o, "t":B0_t, "h":B0_h, "k":B0_k}  # 덜어내는 수(표시)
    res   = {"o":0,     "t":0,     "h":0,     "k":0}  # 결과판

    A_nums, (F_O, F_T, F_H, F_K) = number_row(row_top[0], sub_A["o"], sub_A["t"], sub_A["h"], sub_A["k"], "첫번째 수(원래 수)")
    B_nums, (S_O, S_T, S_H, S_K) = number_row(row_top[1], sub_B["o"], sub_B["t"], sub_B["h"], sub_B["k"], "두번째 수(덜어내는 수)")

    result_area = row_bot[0].container()
    result_area.markdown("<div style='text-align:center;font-size:20px;font-weight:900;margin-bottom:4px;'>결과</div>", unsafe_allow_html=True)
    r_num_cols = result_area.columns([1,0.10,1,1,1], gap="small")
    R_o_num, R_dot, R_t_num, R_h_num, R_k_num = r_num_cols[0].empty(), r_num_cols[1], r_num_cols[2].empty(), r_num_cols[3].empty(), r_num_cols[4].empty()
    R_dot.markdown("<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>·</div>", unsafe_allow_html=True)
    r_pan_cols = result_area.columns([1,0.10,1,1,1], gap="small")
    R_O, R_T, R_H, R_K = r_pan_cols[0].empty(), r_pan_cols[2].empty(), r_pan_cols[3].empty(), r_pan_cols[4].empty()

    def update_result_numbers_sub(o, t, h, k):
        for ph, val in [(R_o_num,o),(R_t_num,t),(R_h_num,h),(R_k_num,k)]:
            ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{val}</div>", unsafe_allow_html=True)

    def render_all_sub(label=None):
        set_numbers(A_nums, sub_A["o"], sub_A["t"], sub_A["h"], sub_A["k"])
        set_numbers(B_nums, sub_B["o"], sub_B["t"], sub_B["h"], sub_B["k"])
        update_result_numbers_sub(res["o"], res["t"], res["h"], res["k"])
        render_panel(F_O, sub_A["o"], "O"); render_panel(F_T, sub_A["t"], "T")
        render_panel(F_H, sub_A["h"], "H"); render_panel(F_K, sub_A["k"], "K")
        render_panel(S_O, sub_B["o"], "O"); render_panel(S_T, sub_B["t"], "T")
        render_panel(S_H, sub_B["h"], "H"); render_panel(S_K, sub_B["k"], "K")
        render_panel(R_O, res["o"], "O", label="O" if label=="O" else None)
        render_panel(R_T, res["t"], "T", label="T" if label=="T" else None)
        render_panel(R_H, res["h"], "H", label="H" if label=="H" else None)
        render_panel(R_K, res["k"], "K")

    render_all_sub()

    # 받아내림 헬퍼
    def borrow_for_k(need):
        if res["k"] >= need: return
        show_alert(f"{res['k']}에서 {need}을 뺄 수 없어요!<br><b>0.01 하나를 0.001 10개로 받아내림할게요.</b>")
        if res["h"] > 0:
            flash_one_rod_to_ten_micros(R_H, R_K)
            res["h"] -= 1; res["k"] += 10
            render_all_sub(label="H"); time.sleep(0.25); return
        if res["t"] > 0:
            show_alert("0.1 하나를 0.01 10개로 바꿔 먼저 내려올게요.")
            flash_one_plate_to_ten_rods(R_T, R_H)
            res["t"] -= 1; res["h"] += 10
            render_all_sub(label="T"); time.sleep(0.25)
            borrow_for_k(need); return
        if res["o"] > 0:
            show_alert("1 하나를 0.1 10개로 바꿔 먼저 내려올게요.")
            flash_one_cube_to_ten_plates(R_O, R_T, res["t"])
            res["o"] -= 1; res["t"] += 10
            render_all_sub(label="O"); time.sleep(0.25)
            borrow_for_k(need); return

    def borrow_for_h(need):
        if res["h"] >= need: return
        show_alert(f"{res['h']}에서 {need}을 뺄 수 없어요!<br><b>0.1 하나를 0.01 10개로 받아내림할게요.</b>")
        if res["t"] > 0:
            flash_one_plate_to_ten_rods(R_T, R_H)
            res["t"] -= 1; res["h"] += 10
            render_all_sub(label="T"); time.sleep(0.25); return
        if res["o"] > 0:
            show_alert("1 하나를 0.1 10개로 바꿔 먼저 내려올게요.")
            flash_one_cube_to_ten_plates(R_O, R_T, res["t"])
            res["o"] -= 1; res["t"] += 10
            render_all_sub(label="O"); time.sleep(0.25)
            borrow_for_h(need); return

    def borrow_for_t(need):
        if res["t"] >= need: return
        show_alert(f"{res['t']}에서 {need}을 뺄 수 없어요!<br><b>1 하나를 0.1 10개로 받아내림할게요.</b>")
        if res["o"] > 0:
            flash_one_cube_to_ten_plates(R_O, R_T, res["t"])
            res["o"] -= 1; res["t"] += 10
            render_all_sub(label="O"); time.sleep(0.25); return

    # --- 정답 맞혀보기 (뺄셈) ---
    st.markdown("#### 🧠 정답 맞혀보기 (뺄셈)")
    colg1s, colg2s = st.columns([2,1])
    with colg1s:
        user_guess_sub = st.text_input("두 수의 차를 예상해 입력해 보세요(예: 0.479)", key="guess_sub")
    with colg2s:
        if st.button("정답 확인(뺄셈)", key="check_sub"):
            try:
                correct_sub = round(float(st.session_state["A"]) - float(st.session_state["B"]), 3)
                guess_val = round(float(user_guess_sub), 3)
                if guess_val == correct_sub:
                    st.success("정답이에요! 🎉")
                    st.balloons(); play_sound(SND_OK)
                    st.session_state["level"] = st.session_state.get("level", 0) + 1
                    st.toast(f"레벨 {st.session_state['level']} 달성!", icon="🎈")
                    st.session_state["wrong_streak_sub"] = 0
                    st.session_state["last_guess_mode"] = "sub"
                    st.session_state["last_guess_value"] = f"{guess_val:.3f}"
                    st.session_state["last_guess_correct"] = 1
                    st.session_state["last_correct_answer"] = f"{correct_sub:.3f}"
                else:
                    play_sound(SND_WRONG)
                    st.error("아쉬워요! ❌")
                    ws = st.session_state.get("wrong_streak_sub", 0) + 1
                    st.session_state["wrong_streak_sub"] = ws
                    A_o,A_t,A_h,A_k = split_digits(st.session_state["A"])
                    B_o,B_t,B_h,B_k = split_digits(st.session_state["B"])
                    hints = []
                    need_k = A_k < B_k
                    need_h = (A_h - (1 if need_k else 0)) < B_h
                    need_t = (A_t - (1 if (need_h or (A_h==B_h and need_k)) else 0)) < B_t
                    if ws >= 1:
                        step1 = []
                        if need_k: step1.append("소수 셋째 자리에서 받아내림이 필요해요.")
                        if need_h: step1.append("소수 둘째 자리에서도 받아내림이 필요해요.")
                        if need_t: step1.append("소수 첫째 자리에서도 받아내림이 필요해요.")
                        if step1: hints.append("<br>".join(step1))
                    if ws >= 2:
                        hints.append(f"자리 비교: 0.001자리 {A_k} vs {B_k}, 0.01자리 {A_h} vs {B_h}, 0.1자리 {A_t} vs {B_t}")
                    if ws >= 3:
                        hints.append("정답 형식 힌트: 차는 소수 셋째 자리까지 표기(예: 0.abc). 받아내림이 있으면 앞자리에서 1을 빌려와요.")
                    show_alert("<br>".join(hints) if hints else "자릿값을 다시 생각해 보세요!", seconds=3.5)
                    st.session_state["last_guess_mode"] = "sub"
                    st.session_state["last_guess_value"] = f"{guess_val:.3f}"
                    st.session_state["last_guess_correct"] = 0
                    st.session_state["last_correct_answer"] = f"{correct_sub:.3f}"
            except Exception:
                st.warning("숫자 형식으로 입력해 주세요. 예: 0.479")

    # --- (뺄셈) 애니메이션: A를 결과로 즉시 옮긴 후 차감 시작 ---
    if st.button("▶ (뺄셈) 애니메이션 시작", use_container_width=True, key="run_sub"):
        # A를 결과로 즉시 반영(애니메이션 없이)
        res["k"] += sub_A["k"]; sub_A["k"] = 0
        res["h"] += sub_A["h"]; sub_A["h"] = 0
        res["t"] += sub_A["t"]; sub_A["t"] = 0
        res["o"] += sub_A["o"]; sub_A["o"] = 0
        render_all_sub()

        # 각 자리에서 B만큼 차감(필요 시 받아내림)
        if sub_B["k"] > 0:
            need = sub_B["k"]
            if res["k"] < need: borrow_for_k(need)
            for _ in range(need):
                res["k"] -= 1; sub_B["k"] -= 1
                render_all_sub(); play_sound(SND_POP); time.sleep(STEP_DELAY_MOVE)
        if sub_B["h"] > 0:
            need = sub_B["h"]
            if res["h"] < need: borrow_for_h(need)
            for _ in range(need):
                res["h"] -= 1; sub_B["h"] -= 1
                render_all_sub(); play_sound(SND_POP); time.sleep(STEP_DELAY_MOVE)
        if sub_B["t"] > 0:
            need = sub_B["t"]
            if res["t"] < need: borrow_for_t(need)
            for _ in range(need):
                res["t"] -= 1; sub_B["t"] -= 1
                render_all_sub(); play_sound(SND_POP); time.sleep(STEP_DELAY_MOVE)
        if sub_B["o"] > 0:
            need = sub_B["o"]
            for _ in range(need):
                res["o"] -= 1; sub_B["o"] -= 1
                render_all_sub(); play_sound(SND_POP); time.sleep(STEP_DELAY_MOVE)

        render_all_sub(); play_sound(SND_OK)

# ────────── [학생] 학습 결과 제출하기 ──────────
with st.expander("📝 학습 결과 제출하기 (교사 대시보드로 전송)", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        klass = st.selectbox("학급", ["4-사랑","4-기쁨","4-보람","4-행복","기타"], index=0)
        nickname = st.text_input("닉네임(또는 이름 이니셜)")
    with col2:
        quest = st.text_area("오늘의 문제/과제(간단히)", height=80,
                             placeholder="예: 1.257 + 0.078에서 받아올림이 언제 일어났나요?")
    with col3:
        st.markdown("**자기평가(각 0–2점)**")
        r1 = st.slider("개념이해", 0, 2, 1)
        r2 = st.slider("참여도", 0, 2, 1)
        r3 = st.slider("설명하기", 0, 2, 1)
        rubric_total = r1 + r2 + r3

    submitted = st.button("제출하기", use_container_width=True)
    if submitted:
        if not nickname.strip():
            st.error("닉네임을 입력해 주세요.")
        else:
            row = {
                "timestamp": kst_now_str(),
                "class": klass,
                "nickname": nickname.strip(),
                "quest": quest.strip(),
                "rubric_1": r1, "rubric_2": r2, "rubric_3": r3,
                "rubric_total": rubric_total,
                "guess_mode":     st.session_state.get("last_guess_mode"),
                "guess_value":    st.session_state.get("last_guess_value"),
                "guess_correct":  st.session_state.get("last_guess_correct"),
                "correct_answer": st.session_state.get("last_correct_answer"),
            }
            add_submission(row)
            st.success("제출 완료! 교사 대시보드에서 확인할 수 있어요.")
            st.session_state["last_guess_mode"] = None
            st.session_state["last_guess_value"] = None
            st.session_state["last_guess_correct"] = None
            st.session_state["last_correct_answer"] = None
















































