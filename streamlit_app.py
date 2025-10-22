import time
from typing import Tuple
import matplotlib

# ── 폰트(한글 안전) ──
matplotlib.rcParams["font.family"] = [
    "Noto Sans CJK KR", "NanumGothic", "Apple SD Gothic Neo",
    "Malgun Gothic", "DejaVu Sans"
]
matplotlib.rcParams["font.size"] = 13

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import streamlit as st

# ───────────────── 페이지/스타일 ─────────────────
st.set_page_config(page_title="Decimal Blocks 3D - 소수 셋째 자리까지의 덧셈", page_icon="🔢", layout="wide")
st.markdown("<h1 style='margin:0'>Decimal Blocks 3D - 소수 셋째 자리까지의 덧셈</h1>", unsafe_allow_html=True)
st.markdown("<div style='font-size:16px;color:#334155;margin:6px 0 14px 0'>원하는 두 수를 입력하고 <b>애니메이션 시작</b> 버튼을 눌러보세요.</div>", unsafe_allow_html=True)

COLOR_ONES   = (0.20, 0.48, 0.78, 1.0)   # 1 (큐브)
COLOR_TENTHS = (0.46, 0.68, 0.22, 1.0)   # 0.1 (판)
COLOR_HUNDS  = (0.98, 0.52, 0.18, 1.0)   # 0.01 (막대)
COLOR_THOUS  = (0.60, 0.40, 0.80, 1.0)   # 0.001 (작은 큐브)
COLOR_FLASH  = (1.00, 1.00, 0.10, 1.0)   # 깜빡임

# 타이밍: 동일 간격, 깜빡임 2회
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
    ax.add_collection3d(Poly3DCollection(cuboid_vertices(*pos, *size),
                                         facecolors=[color]*6,
                                         edgecolors=(0,0,0,0.35)))

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

# ───────────────── 사이드바(말풍선) ─────────────────
with st.sidebar:
    st.markdown("<div style='font-size:18px;font-weight:800;margin-bottom:8px;'>입력</div>", unsafe_allow_html=True)
    A = st.number_input("첫번째 수 (0.000~9.999)", 0.000, 9.999, 1.257, step=0.001, format="%.3f")
    B = st.number_input("두번째 수 (0.000~9.999)", 0.000, 9.999, 0.078, step=0.001, format="%.3f")
    run = st.button("▶ 애니메이션 시작", use_container_width=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:16px;font-weight:800;margin:6px 0 4px 0;'>내가 추측하기</div>", unsafe_allow_html=True)
    guess = st.number_input("A+B는 얼마일까요?", value=round(A+B,3), step=0.001, format="%.3f")
    check = st.button("채점", use_container_width=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    BUBBLE = st.empty()  # ← 말풍선 자리

def bubble(text: str):
    BUBBLE.markdown(
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
def clear_bubble():
    BUBBLE.empty()

# ───────────────── 숫자줄 + 패널 구성 ─────────────────
def number_row(parent_col, o, t, h, k, title):
    parent_col.markdown(
        f"<div style='text-align:center;font-size:20px;font-weight:900;margin-bottom:4px;'>{title}</div>",
        unsafe_allow_html=True
    )
    c1, cdot, c2, c3, c4 = parent_col.columns([1, 0.10, 1, 1, 1], gap="small")
    o_ph = c1.empty(); dot_ph = cdot; t_ph = c2.empty(); h_ph = c3.empty(); k_ph = c4.empty()
    dot_ph.markdown("<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>·</div>", unsafe_allow_html=True)
    # 숫자 placeholder 초기 채움
    o_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{o}</div>", unsafe_allow_html=True)
    t_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{t}</div>", unsafe_allow_html=True)
    h_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{h}</div>", unsafe_allow_html=True)
    k_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{k}</div>", unsafe_allow_html=True)
    # 아래 3D 영역
    p1, _, p2, p3, p4 = parent_col.columns([1, 0.10, 1, 1, 1], gap="small")
    return (o_ph, t_ph, h_ph, k_ph), (p1.empty(), p2.empty(), p3.empty(), p4.empty())

def set_numbers(ph_tuple, o, t, h, k):
    o_ph, t_ph, h_ph, k_ph = ph_tuple
    o_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{o}</div>", unsafe_allow_html=True)
    t_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{t}</div>", unsafe_allow_html=True)
    h_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{h}</div>", unsafe_allow_html=True)
    k_ph.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{k}</div>", unsafe_allow_html=True)

row_top = st.columns(2, gap="large")
row_bot = st.columns(1)

# A/B 숫자/패널(반환값 2묶음 받기 중요!)
A_o0, A_t0, A_h0, A_k0 = split_digits(A)
B_o0, B_t0, B_h0, B_k0 = split_digits(B)
A_nums, (F_O, F_T, F_H, F_K) = number_row(row_top[0], A_o0, A_t0, A_h0, A_k0, "첫번째 수")
B_nums, (S_O, S_T, S_H, S_K) = number_row(row_top[1], B_o0, B_t0, B_h0, B_k0, "두번째 수")

# 결과 숫자/패널(한 번만 만들고 업데이트)
result_area = row_bot[0].container()
result_area.markdown("<div style='text-align:center;font-size:20px;font-weight:900;margin-bottom:4px;'>결과</div>", unsafe_allow_html=True)
r_num_cols = result_area.columns([1, 0.10, 1, 1, 1], gap="small")
R_o_num, R_dot, R_t_num, R_h_num, R_k_num = r_num_cols[0].empty(), r_num_cols[1], r_num_cols[2].empty(), r_num_cols[3].empty(), r_num_cols[4].empty()
R_dot.markdown("<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>·</div>", unsafe_allow_html=True)
r_pan_cols = result_area.columns([1, 0.10, 1, 1, 1], gap="small")
R_O, R_T, R_H, R_K = r_pan_cols[0].empty(), r_pan_cols[2].empty(), r_pan_cols[3].empty(), r_pan_cols[4].empty()

def update_result_numbers(o, t, h, k):
    R_o_num.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{o}</div>", unsafe_allow_html=True)
    R_t_num.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{t}</div>", unsafe_allow_html=True)
    R_h_num.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{h}</div>", unsafe_allow_html=True)
    R_k_num.markdown(f"<div style='text-align:center;font-size:44px;font-weight:1000;line-height:1;'>{k}</div>", unsafe_allow_html=True)

# 3D 패널 렌더
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

# 상태(숫자도 애니메이션 동안 감소 표시)
A_o, A_t, A_h, A_k = A_o0, A_t0, A_h0, A_k0
B_o, B_t, B_h, B_k = B_o0, B_t0, B_h0, B_k0
o = t = h = k = 0

def render_all(label=None):
    # 숫자줄 갱신
    set_numbers(A_nums, A_o, A_t, A_h, A_k)
    set_numbers(B_nums, B_o, B_t, B_h, B_k)
    update_result_numbers(o, t, h, k)
    # 3D 패널 갱신
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

# 초기 렌더
render_all()

# ───────────────── 애니메이션 ─────────────────
if run:
    clear_bubble()
    # 0.001 — A
    for _ in range(A_k0):
        A_k -= 1; k += 1; render_all(); time.sleep(STEP_DELAY)
        if k == 10:
            flash_micros_as_rod(R_K)
            bubble("0.001이 10개 모여 0.01이 됐어요.")
            k = 0; h += 1; render_all(label="H"); time.sleep(STEP_DELAY); clear_bubble()
    # 0.001 — B
    for _ in range(B_k0):
        B_k -= 1; k += 1; render_all(); time.sleep(STEP_DELAY)
        if k == 10:
            flash_micros_as_rod(R_K)
            bubble("0.001이 10개 모여 0.01이 됐어요.")
            k = 0; h += 1; render_all(label="H"); time.sleep(STEP_DELAY); clear_bubble()

    # 0.01 — A
    for _ in range(A_h0):
        A_h -= 1; h += 1; render_all(); time.sleep(STEP_DELAY)
        if h == 10:
            flash_rods_as_plate(R_H)
            bubble("0.01이 10개 모여 0.1이 됐어요.")
            h = 0; t += 1; render_all(label="T"); time.sleep(STEP_DELAY); clear_bubble()
    # 0.01 — B
    for _ in range(B_h0):
        B_h -= 1; h += 1; render_all(); time.sleep(STEP_DELAY)
        if h == 10:
            flash_rods_as_plate(R_H)
            bubble("0.01이 10개 모여 0.1이 됐어요.")
            h = 0; t += 1; render_all(label="T"); time.sleep(STEP_DELAY); clear_bubble()

    # 0.1 — A
    for _ in range(A_t0):
        A_t -= 1; t += 1; render_all(); time.sleep(STEP_DELAY)
        if t == 10:
            flash_plates_as_cube(R_T, R_O, o)
            bubble("0.1이 10개 모여 1이 됐어요.")
            t = 0; o += 1; render_all(label="O"); time.sleep(STEP_DELAY); clear_bubble()
    # 0.1 — B
    for _ in range(B_t0):
        B_t -= 1; t += 1; render_all(); time.sleep(STEP_DELAY)
        if t == 10:
            flash_plates_as_cube(R_T, R_O, o)
            bubble("0.1이 10개 모여 1이 됐어요.")
            t = 0; o += 1; render_all(label="O"); time.sleep(STEP_DELAY); clear_bubble()

    # 1 — A, B
    for _ in range(A_o0):
        A_o -= 1; o += 1; render_all(); time.sleep(STEP_DELAY)
    for _ in range(B_o0):
        B_o -= 1; o += 1; render_all(); time.sleep(STEP_DELAY)

    # 계산 완료 후 A/B 숫자 복구
    A_o, A_t, A_h, A_k = A_o0, A_t0, A_h0, A_k0
    B_o, B_t, B_h, B_k = B_o0, B_t0, B_h0, B_k0
    render_all()

# ───────────────── 채점/레벨/힌트 ─────────────────
if "level" not in st.session_state:
    st.session_state.level = 0

true_sum = round(A + B, 3)

def hint_box(A_vals, B_vals):
    (Ao, At, Ah, Ak), (Bo, Bt, Bh, Bk) = A_vals, B_vals
    k_sum = Ak + Bk
    h_carry = 1 if k_sum >= 10 else 0
    h_sum = Ah + Bh + h_carry
    t_carry = 1 if h_sum >= 10 else 0
    t_sum = At + Bt + t_carry
    o_carry = 1 if t_sum >= 10 else 0

    lines = []
    lines.append(f"소수 셋째 자리: {Ak} + {Bk} = {k_sum} → {'받아올림 1' if h_carry else '받아올림 없음'}")
    lines.append(f"소수 둘째 자리: {Ah} + {Bh} {'+ 1(받아올림)' if h_carry else ''} = {h_sum} → {'받아올림 1' if t_carry else '받아올림 없음'}")
    lines.append(f"소수 첫째 자리: {At} + {Bt} {'+ 1(받아올림)' if t_carry else ''} = {t_sum} → {'받아올림 1' if o_carry else '받아올림 없음'}")
    lines.append(f"일의 자리: {Ao} + {Bo} {'+ 1(받아올림)' if o_carry else ''}")

    st.markdown(
        f"""
        <div style="padding:16px; background:#FFFFFF; border:3px solid #DC2626;
                    border-radius:12px; margin-top:8px;">
            <div style="font-size:22px; font-weight:1000; color:#DC2626; margin-bottom:6px;">
                ❌ 틀렸어요! 힌트를 볼까요?
            </div>
            <div style="font-size:16px; color:#111827; line-height:1.6;">
                {'<br>'.join(lines)}
            </div>
            <div style="font-size:16px; color:#111827; margin-top:6px;">
                <b>소수 셋째 → 둘째 → 첫째 → 일의</b> 순서로 다시 더해보세요.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

if check:
    st.write("### 채점")
    st.metric("정답", f"{true_sum:.3f}")
    if abs(true_sum - guess) < 1e-12:
        st.session_state.level += 1
        st.success(f"정답이에요! ✅  레벨 {st.session_state.level}")
        st.balloons()
    else:
        st.error("아쉽! 다시 시도해봐요.")
        hint_box(split_digits(A), split_digits(B))





























