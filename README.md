import time
from typing import Tuple
import matplotlib
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import streamlit as st

# ── 폰트(한글 안전) ──
matplotlib.rcParams["font.family"] = [
    "Noto Sans CJK KR", "NanumGothic", "Apple SD Gothic Neo",
    "Malgun Gothic", "DejaVu Sans"
]
matplotlib.rcParams["font.size"] = 13

# ───────────────── 페이지/스타일 ─────────────────
st.set_page_config(
    page_title="Decimal Blocks 3D - 소수 셋째 자리까지의 덧셈·뺄셈",
    page_icon="🔢",
    layout="wide"
)
st.markdown("<h1 style='margin:0'>Decimal Blocks 3D - 소수 셋째 자리까지의 덧셈·뺄셈</h1>", unsafe_allow_html=True)
st.markdown("<div style='font-size:16px;color:#334155;margin:6px 0 14px 0'>원하는 두 수를 입력하고 각 탭의 <b>애니메이션 시작</b> 버튼을 눌러보세요.</div>", unsafe_allow_html=True)

# ── 색/타이밍 ──
COLOR_ONES   = (0.20, 0.48, 0.78, 1.0)   # 1 (큐브)
COLOR_TENTHS = (0.46, 0.68, 0.22, 1.0)   # 0.1 (판)
COLOR_HUNDS  = (0.98, 0.52, 0.18, 1.0)   # 0.01 (막대)
COLOR_THOUS  = (0.60, 0.40, 0.80, 1.0)   # 0.001 (작은 큐브)
COLOR_FLASH  = (1.00, 1.00, 0.10, 1.0)   # 깜빡임

STEP_DELAY = 0.5
BLINK_CYCLES, BLINK_INTERVAL = 2, 0.25

# ───────────────── 자릿수 파싱(셋째 자리) ─────────────────
def split_digits(x: float) -> Tuple[int,int,int,int]:
    x = round(float(x), 3)
    ones = int(x)
    frac = round(x - ones, 3)
    t = int(frac * 10)                 # 0.1
    h = int(round(frac * 100))  % 10   # 0.01
    k = int(round(frac * 1000)) % 10   # 0.001
    return ones % 10, t, h, k

# ───────────────── 3D 유틸 ─────────────────
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
    fig = plt.figure(figsize=(2.8, 2.8), dpi=210)
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

# ───────────────── 간격/크기 연동 ─────────────────
GAP_MICRO_X = 0.08     # 0.001 간격
GAP_ROD_X   = 0.08     # 0.01 간격
GAP_PLATE_Z = 0.08     # 0.1  간격

S = 1.0 + 9*GAP_ROD_X
PLATE_THICK = max((S - 9*GAP_PLATE_Z)/10.0, 0.001)

SIZE_MICRO = (0.1, 0.1, 0.1)     # 0.001
SIZE_ROD   = (0.1, S, 0.1)       # 0.01
SIZE_PLATE = (S, S, PLATE_THICK) # 0.1
SIZE_CUBE  = (S, S, S)           # 1

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

# ───────────────── 깜빡임(2회) ─────────────────
def flash_micros_as_rod(ph):
    for _ in range(BLINK_CYCLES):
        fig, ax = scene_axes(); draw_micros(ax, 10, COLOR_FLASH); ph.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)
        fig, ax = scene_axes(); draw_micros(ax, 10, COLOR_THOUS); ph.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)

def flash_rods_as_plate(ph):
    for _ in range(BLINK_CYCLES):
        fig, ax = scene_axes(); draw_rods(ax, 10, COLOR_FLASH); ph.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)
        fig, ax = scene_axes(); draw_rods(ax, 10, COLOR_HUNDS ); ph.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)

def flash_plates_as_cube(ph_T, ph_O, o_now):
    for _ in range(BLINK_CYCLES):
        fig, ax = scene_axes(); draw_plates(ax, 10, COLOR_FLASH); ph_T.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)
        fig, ax = scene_axes(); draw_plates(ax, 10, COLOR_TENTHS); ph_T.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)
    for _ in range(BLINK_CYCLES):
        fig, ax = scene_axes(); draw_cubes(ax, o_now+1, COLOR_FLASH); ph_O.pyplot(fig, True); plt.close(fig); time.sleep(0.15)
        fig, ax = scene_axes(); draw_cubes(ax, o_now,   COLOR_ONES ); ph_O.pyplot(fig, True); plt.close(fig); time.sleep(0.15)

# (뺄셈 전용) 받아내림 깜빡임
def flash_one_rod_to_ten_micros(ph_source_H, ph_dest_K):
    for _ in range(BLINK_CYCLES):
        fig, ax = scene_axes(); draw_rods(ax, 1, COLOR_FLASH); ph_source_H.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)
        fig, ax = scene_axes(); draw_rods(ax, 1, COLOR_HUNDS ); ph_source_H.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)
    for _ in range(BLINK_CYCLES):
        fig, ax = scene_axes(); draw_micros(ax, 10, COLOR_FLASH); ph_dest_K.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)
        fig, ax = scene_axes(); draw_micros(ax, 10, COLOR_THOUS); ph_dest_K.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)

def flash_one_plate_to_ten_rods(ph_source_T, ph_dest_H):
    for _ in range(BLINK_CYCLES):
        fig, ax = scene_axes(); draw_plates(ax, 1, COLOR_FLASH); ph_source_T.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)
        fig, ax = scene_axes(); draw_plates(ax, 1, COLOR_TENTHS); ph_source_T.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)
    for _ in range(BLINK_CYCLES):
        fig, ax = scene_axes(); draw_rods(ax, 10, COLOR_FLASH); ph_dest_H.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)
        fig, ax = scene_axes(); draw_rods(ax, 10, COLOR_HUNDS ); ph_dest_H.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)

def flash_one_cube_to_ten_plates(ph_source_O, ph_dest_T, t_now):
    for _ in range(BLINK_CYCLES):
        fig, ax = scene_axes(); draw_cubes(ax, 1, COLOR_FLASH); ph_source_O.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)
        fig, ax = scene_axes(); draw_cubes(ax, 1, COLOR_ONES ); ph_source_O.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)
    for _ in range(BLINK_CYCLES):
        fig, ax = scene_axes(); draw_plates(ax, 10, COLOR_FLASH); ph_dest_T.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)
        fig, ax = scene_axes(); draw_plates(ax, 10, COLOR_TENTHS); ph_dest_T.pyplot(fig, True); plt.close(fig); time.sleep(BLINK_INTERVAL)

# ───────── 공통 입력(사이드바 상단) ─────────
with st.sidebar:
    st.markdown("### 문제 설정")
    if "A" not in st.session_state: st.session_state["A"] = 1.257
    if "B" not in st.session_state: st.session_state["B"] = 0.078

    st.number_input(
        "첫번째 수 (0.000~9.999)",
        min_value=0.000, max_value=9.999,
        value=float(st.session_state["A"]),
        step=0.001, format="%.3f", key="A"
    )
    st.number_input(
        "두번째 수 (0.000~9.999)",
        min_value=0.000, max_value=9.999,
        value=float(st.session_state["B"]),
        step=0.001, format="%.3f", key="B"
    )

# ───────────────── 공용 UI 빌딩 블록 ─────────────────
def number_row(parent_col, o, t, h, k, title):
    parent_col.markdown(
        f"<div style='text-align:center;font-size:20px;font-weight:900;margin-bottom:4px;'>{title}</div>",
        unsafe_allow_html=True
    )
    c1, cdot, c2, c3, c4 = parent_col.columns([1, 0.10, 1, 1, 1], gap="small")
    o_ph = c1.empty(); dot_ph = cdot; t_ph = c2.empty(); h_ph = c3.empty(); k_ph = c4.empty()
    dot_ph.markdown("<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>·</div>", unsafe_allow_html=True)
    o_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{o}</div>", unsafe_allow_html=True)
    t_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{t}</div>", unsafe_allow_html=True)
    h_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{h}</div>", unsafe_allow_html=True)
    k_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{k}</div>", unsafe_allow_html=True)
    p1, _, p2, p3, p4 = parent_col.columns([1, 0.10, 1, 1, 1], gap="small")
    return (o_ph, t_ph, h_ph, k_ph), (p1.empty(), p2.empty(), p3.empty(), p4.empty())

def set_numbers(ph_tuple, o, t, h, k):
    o_ph, t_ph, h_ph, k_ph = ph_tuple
    o_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{o}</div>", unsafe_allow_html=True)
    t_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{t}</div>", unsafe_allow_html=True)
    h_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{h}</div>", unsafe_allow_html=True)
    k_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{k}</div>", unsafe_allow_html=True)

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

# ───────────────── 탭 구성 ─────────────────
tab_add, tab_sub = st.tabs(["➕ 덧셈", "➖ 뺄셈"])

# ───────────────── 덧셈 탭 ─────────────────
with tab_add:
    # 덧셈 전용 사이드바(채점 + 말풍선)
    with st.sidebar:
        st.markdown("### 덧셈 채점")
        add_guess = st.number_input("두 수의 합은 얼마일까요?", value=0.000, step=0.001, format="%.3f", key="add_guess_input")
        add_check = st.button("덧셈 채점", use_container_width=True, key="add_check_btn")
        st.markdown("<hr>", unsafe_allow_html=True)
        BUBBLE_ADD = st.empty()

    def bubble_add(text: str):
        BUBBLE_ADD.markdown(
            f"""
            <div style="background:#e5e7eb;padding:8px;border-radius:10px;">
              <div style="background:#ffffff;border-radius:12px;padding:16px;
                          font-size:22px;font-weight:1000;color:#0F766E;text-align:center;
                          box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                {text}
              </div>
            </div>
            """, unsafe_allow_html=True
        )
    def clear_bubble_add(): BUBBLE_ADD.empty()

    # 레이아웃
    row_top = st.columns(2, gap="large")
    row_bot = st.columns(1)

    # 입력값 → 자리수 분해
    A_o0, A_t0, A_h0, A_k0 = split_digits(st.session_state["A"])
    B_o0, B_t0, B_h0, B_k0 = split_digits(st.session_state["B"])

    A_nums, (F_O, F_T, F_H, F_K) = number_row(row_top[0], A_o0, A_t0, A_h0, A_k0, "첫번째 수")
    B_nums, (S_O, S_T, S_H, S_K) = number_row(row_top[1], B_o0, B_t0, B_h0, B_k0, "두번째 수")

    result_area = row_bot[0].container()
    result_area.markdown("<div style='text-align:center;font-size:20px;font-weight:900;margin-bottom:4px;'>결과</div>", unsafe_allow_html=True)
    r_num_cols = result_area.columns([1, 0.10, 1, 1, 1], gap="small")
    R_o_num, R_dot, R_t_num, R_h_num, R_k_num = r_num_cols[0].empty(), r_num_cols[1], r_num_cols[2].empty(), r_num_cols[3].empty(), r_num_cols[4].empty()
    R_dot.markdown("<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>·</div>", unsafe_allow_html=True)
    r_pan_cols = result_area.columns([1, 0.10, 1, 1, 1], gap="small")
    R_O, R_T, R_H, R_K = r_pan_cols[0].empty(), r_pan_cols[2].empty(), r_pan_cols[3].empty(), r_pan_cols[4].empty()

    def update_result_numbers_add(o, t, h, k):
        R_o_num.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{o}</div>", unsafe_allow_html=True)
        R_t_num.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{t}</div>", unsafe_allow_html=True)
        R_h_num.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{h}</div>", unsafe_allow_html=True)
        R_k_num.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{k}</div>", unsafe_allow_html=True)

    # 상태
    A_o, A_t, A_h, A_k = A_o0, A_t0, A_h0, A_k0
    B_o, B_t, B_h, B_k = B_o0, B_t0, B_h0, B_k0
    o = t = h = k = 0

    def render_all_add(label=None):
        set_numbers(A_nums, A_o, A_t, A_h, A_k)
        set_numbers(B_nums, B_o, B_t, B_h, B_k)
        update_result_numbers_add(o, t, h, k)
        render_panel(F_O, A_o, "O")
        render_panel(F_T, A_t, "T")
        render_panel(F_H, A_h, "H")
        render_panel(F_K, A_k, "K")
        render_panel(S_O, B_o, "O")
        render_panel(S_T, B_t, "T")
        render_panel(S_H, B_h, "H")
        render_panel(S_K, B_k, "K")
        render_panel(R_O, o, "O", label="O" if label=="O" else None)
        render_panel(R_T, t, "T", label="T" if label=="T" else None)
        render_panel(R_H, h, "H", label="H" if label=="H" else None)
        render_panel(R_K, k, "K")

    render_all_add()

    if st.button("▶ (덧셈) 애니메이션 시작", use_container_width=True, key="run_add"):
        clear_bubble_add()
        # 0.001 — A, B
        for _ in range(A_k0):
            A_k -= 1; k += 1; render_all_add(); time.sleep(STEP_DELAY)
            if k == 10:
                flash_micros_as_rod(R_K)
                bubble_add("0.001이 10개 모여 0.01이 됐어요.")
                k = 0; h += 1; render_all_add(label="H"); time.sleep(STEP_DELAY); clear_bubble_add()
        for _ in range(B_k0):
            B_k -= 1; k += 1; render_all_add(); time.sleep(STEP_DELAY)
            if k == 10:
                flash_micros_as_rod(R_K)
                bubble_add("0.001이 10개 모여 0.01이 됐어요.")
                k = 0; h += 1; render_all_add(label="H"); time.sleep(STEP_DELAY); clear_bubble_add()

        # 0.01
        for _ in range(A_h0):
            A_h -= 1; h += 1; render_all_add(); time.sleep(STEP_DELAY)
            if h == 10:
                flash_rods_as_plate(R_H)
                bubble_add("0.01이 10개 모여 0.1이 됐어요.")
                h = 0; t += 1; render_all_add(label="T"); time.sleep(STEP_DELAY); clear_bubble_add()
        for _ in range(B_h0):
            B_h -= 1; h += 1; render_all_add(); time.sleep(STEP_DELAY)
            if h == 10:
                flash_rods_as_plate(R_H)
                bubble_add("0.01이 10개 모여 0.1이 됐어요.")
                h = 0; t += 1; render_all_add(label="T"); time.sleep(STEP_DELAY); clear_bubble_add()

        # 0.1
        for _ in range(A_t0):
            A_t -= 1; t += 1; render_all_add(); time.sleep(STEP_DELAY)
            if t == 10:
                flash_plates_as_cube(R_T, R_O, o)
                bubble_add("0.1이 10개 모여 1이 됐어요.")
                t = 0; o += 1; render_all_add(label="O"); time.sleep(STEP_DELAY); clear_bubble_add()
        for _ in range(B_t0):
            B_t -= 1; t += 1; render_all_add(); time.sleep(STEP_DELAY)
            if t == 10:
                flash_plates_as_cube(R_T, R_O, o)
                bubble_add("0.1이 10개 모여 1이 됐어요.")
                t = 0; o += 1; render_all_add(label="O"); time.sleep(STEP_DELAY); clear_bubble_add()

        # 1
        for _ in range(A_o0):
            A_o -= 1; o += 1; render_all_add(); time.sleep(STEP_DELAY)
        for _ in range(B_o0):
            B_o -= 1; o += 1; render_all_add(); time.sleep(STEP_DELAY)

        # 복구
        A_o, A_t, A_h, A_k = A_o0, A_t0, A_h0, A_k0
        B_o, B_t, B_h, B_k = B_o0, B_t0, B_h0, B_k0
        render_all_add()

    # 채점(덧셈)
    true_sum_add = round(st.session_state["A"] + st.session_state["B"], 3)
    if add_check:
        st.write("### 덧셈 채점")
        st.metric("정답", f"{true_sum_add:.3f}")
        if abs(true_sum_add - add_guess) < 1e-12:
            st.success("정답이에요! ✅")
            st.balloons()
        else:
            st.error("아쉽! 다시 시도해봐요.")

# ───────────────── 뺄셈 탭 ─────────────────
with tab_sub:
    # 뺄셈 전용 사이드바(채점 + 말풍선)
    with st.sidebar:
        st.markdown("### 뺄셈 채점")
        sub_guess = st.number_input("두 수의 차는 얼마일까요?", value=0.000, step=0.001, format="%.3f", key="sub_guess_input")
        sub_check = st.button("뺄셈 채점", use_container_width=True, key="sub_check_btn")
        st.markdown("<hr>", unsafe_allow_html=True)
        BUBBLE_SUB = st.empty()

    def bubble_sub(text: str):
        BUBBLE_SUB.markdown(
            f"""
            <div style="background:#e5e7eb;padding:8px;border-radius:10px;">
              <div style="background:#ffffff;border-radius:12px;padding:16px;
                          font-size:22px;font-weight:1000;color:#0F766E;text-align:center;
                          box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                {text}
              </div>
            </div>
            """, unsafe_allow_html=True
        )
    def clear_bubble_sub(): BUBBLE_SUB.empty()

    # 레이아웃
    row_top = st.columns(2, gap="large")
    row_bot = st.columns(1)

    # 입력값 → 자리수 분해 (A-B)
    A0_o, A0_t, A0_h, A0_k = split_digits(st.session_state["A"])
    B0_o, B0_t, B0_h, B0_k = split_digits(st.session_state["B"])

    A_nums, (F_O, F_T, F_H, F_K) = number_row(row_top[0], A0_o, A0_t, A0_h, A0_k, "첫번째 수(피감수)")
    B_nums, (S_O, S_T, S_H, S_K) = number_row(row_top[1], B0_o, B0_t, B0_h, B0_k, "두번째 수(감수)")

    result_area = row_bot[0].container()
    result_area.markdown("<div style='text-align:center;font-size:20px;font-weight:900;margin-bottom:4px;'>결과</div>", unsafe_allow_html=True)
    r_num_cols = result_area.columns([1, 0.10, 1, 1, 1], gap="small")
    R_o_num, R_dot, R_t_num, R_h_num, R_k_num = r_num_cols[0].empty(), r_num_cols[1], r_num_cols[2].empty(), r_num_cols[3].empty(), r_num_cols[4].empty()
    R_dot.markdown("<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>·</div>", unsafe_allow_html=True)
    r_pan_cols = result_area.columns([1, 0.10, 1, 1, 1], gap="small")
    R_O, R_T, R_H, R_K = r_pan_cols[0].empty(), r_pan_cols[2].empty(), r_pan_cols[3].empty(), r_pan_cols[4].empty()

    def update_result_numbers_sub(o, t, h, k):
        R_o_num.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{o}</div>", unsafe_allow_html=True)
        R_t_num.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{t}</div>", unsafe_allow_html=True)
        R_h_num.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{h}</div>", unsafe_allow_html=True)
        R_k_num.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{k}</div>", unsafe_allow_html=True)

    # 상태(A/B 감소, 결과는 state dict)
    A_o, A_t, A_h, A_k = A0_o, A0_t, A0_h, A0_k
    B_o, B_t, B_h, B_k = B0_o, B0_t, B0_h, B0_k
    state = {"o": 0, "t": 0, "h": 0, "k": 0}

    def render_all_sub(label=None):
        set_numbers(A_nums, A_o, A_t, A_h, A_k)
        set_numbers(B_nums, B_o, B_t, B_h, B_k)
        update_result_numbers_sub(state["o"], state["t"], state["h"], state["k"])
        render_panel(F_O, A_o, "O")
        render_panel(F_T, A_t, "T")
        render_panel(F_H, A_h, "H")
        render_panel(F_K, A_k, "K")
        render_panel(S_O, B_o, "O")
        render_panel(S_T, B_t, "T")
        render_panel(S_H, B_h, "H")
        render_panel(S_K, B_k, "K")
        render_panel(R_O, state["o"], "O", label="O" if label=="O" else None)
        render_panel(R_T, state["t"], "T", label="T" if label=="T" else None)
        render_panel(R_H, state["h"], "H", label="H" if label=="H" else None)
        render_panel(R_K, state["k"], "K")

    render_all_sub()

    # 받아내림 헬퍼
    def ensure_k_available():
        if state["k"] > 0: return
        if state["h"] > 0:
            bubble_sub("0.01 하나를 0.001 열 개로 바꾸어 내려왔어요.")
            flash_one_rod_to_ten_micros(R_H, R_K)
            state["h"] -= 1
            state["k"] += 10
            render_all_sub(label="H"); time.sleep(STEP_DELAY); clear_bubble_sub()
            return
        if state["t"] > 0:
            bubble_sub("0.1 하나를 0.01 열 개로 바꾸어 내려왔어요.")
            flash_one_plate_to_ten_rods(R_T, R_H)
            state["t"] -= 1
            state["h"] += 10
            render_all_sub(label="T"); time.sleep(STEP_DELAY); clear_bubble_sub()
            ensure_k_available();  # 연쇄
            return
        if state["o"] > 0:
            bubble_sub("1 하나를 0.1 열 개로 바꾸어 내려왔어요.")
            flash_one_cube_to_ten_plates(R_O, R_T, state["t"])
            state["o"] -= 1
            state["t"] += 10
            render_all_sub(label="O"); time.sleep(STEP_DELAY); clear_bubble_sub()
            ensure_k_available()
            return

    def ensure_h_available():
        if state["h"] > 0: return
        if state["t"] > 0:
            bubble_sub("0.1 하나를 0.01 열 개로 바꾸어 내려왔어요.")
            flash_one_plate_to_ten_rods(R_T, R_H)
            state["t"] -= 1
            state["h"] += 10
            render_all_sub(label="T"); time.sleep(STEP_DELAY); clear_bubble_sub()
            return
        if state["o"] > 0:
            bubble_sub("1 하나를 0.1 열 개로 바꾸어 내려왔어요.")
            flash_one_cube_to_ten_plates(R_O, R_T, state["t"])
            state["o"] -= 1
            state["t"] += 10
            render_all_sub(label="O"); time.sleep(STEP_DELAY); clear_bubble_sub()
            ensure_h_available()
            return

    def ensure_t_available():
        if state["t"] > 0: return
        if state["o"] > 0:
            bubble_sub("1 하나를 0.1 열 개로 바꾸어 내려왔어요.")
            flash_one_cube_to_ten_plates(R_O, R_T, state["t"])
            state["o"] -= 1
            state["t"] += 10
            render_all_sub(label="O"); time.sleep(STEP_DELAY); clear_bubble_sub()
            return

    if st.button("▶ (뺄셈) 애니메이션 시작", use_container_width=True, key="run_sub"):
        clear_bubble_sub()
        # ① A를 결과에 쌓기
        for _ in range(A_k):
            A_k -= 1; state["k"] += 1; render_all_sub(); time.sleep(STEP_DELAY)
        for _ in range(A_h):
            A_h -= 1; state["h"] += 1; render_all_sub(); time.sleep(STEP_DELAY)
        for _ in range(A_t):
            A_t -= 1; state["t"] += 1; render_all_sub(); time.sleep(STEP_DELAY)
        for _ in range(A_o):
            A_o -= 1; state["o"] += 1; render_all_sub(); time.sleep(STEP_DELAY)

        # ② B를 빼기 (작은 자리부터)
        for _ in range(B_k):
            if state["k"] == 0: ensure_k_available()
            state["k"] -= 1; B_k -= 1
            render_all_sub(); time.sleep(STEP_DELAY)

        for _ in range(B_h):
            if state["h"] == 0: ensure_h_available()
            state["h"] -= 1; B_h -= 1
            render_all_sub(); time.sleep(STEP_DELAY)

        for _ in range(B_t):
            if state["t"] == 0: ensure_t_available()
            state["t"] -= 1; B_t -= 1
            render_all_sub(); time.sleep(STEP_DELAY)

        for _ in range(B_o):
            if state["o"] > 0:
                state["o"] -= 1; B_o -= 1
            render_all_sub(); time.sleep(STEP_DELAY)

        # 복구
        A_o, A_t, A_h, A_k = A0_o, A0_t, A0_h, A0_k
        B_o, B_t, B_h, B_k = B0_o, B0_t, B0_h, B0_k
        render_all_sub()

    # 채점(뺄셈)
    true_diff = round(st.session_state["A"] - st.session_state["B"], 3)
    if sub_check:
        st.write("### 뺄셈 채점")
        st.metric("정답", f"{true_diff:.3f}")
        if abs(true_diff - sub_guess) < 1e-12:
            st.success("정답이에요! ✅")
            st.balloons()
        else:
            st.error("아쉽! 다시 시도해봐요. (받아내림 과정을 잘 살펴보세요)")

