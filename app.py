import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle

st.set_page_config(page_title="渋滞シミュレーション", layout="wide")
st.title("🚗 渋滞シミュレーション")

# =========================
# 1. 曜日・時間帯の設定
# =========================

st.subheader("曜日・時間帯の設定")

day_type = st.selectbox("曜日", ["平日", "土日"])

time_zone = st.selectbox(
    "時間帯",
    ["朝(6:00〜11:59)", "昼(12:00〜17:59)", "夜(18:00〜23:59)", "深夜・早朝(24:00〜5:59)"]
)

traffic_table = {
    "平日": {
        "朝(6:00〜11:59)": 12,
        "昼(12:00〜17:59)": 8,
        "夜(18:00〜23:59)": 10,
        "深夜・早朝(24:00〜5:59)": 2,
    },
    "土日": {
        "朝(6:00〜11:59)": 8,
        "昼(12:00〜17:59)": 15,
        "夜(18:00〜23:59)": 12,
        "深夜・早朝(24:00〜5:59)": 3,
    },
}

traffic_volume = traffic_table[day_type][time_zone]

# =========================
# 2. 信号サイクルの設定
# =========================

YELLOW = 5
RED = 40
L_clearance = YELLOW + RED

MAX_CAPACITY = 30
demand_rate = traffic_volume / MAX_CAPACITY

if demand_rate >= 1:
    demand_rate = 0.95

C_sec = (1.5 * L_clearance + 5) / (1 - demand_rate)
C_min = C_sec / 60

GREEN_sec = C_sec - L_clearance
GREEN_min = GREEN_sec / 60

st.subheader("交通量と信号設定")

c1, c2, c3, c4 = st.columns(4)
c1.metric("交通量", f"{traffic_volume} 台/分")
c2.metric("需要率 λ", f"{demand_rate:.2f}")
c3.metric("サイクル長 C", f"{C_min:.2f} 分")
c4.metric("青信号時間", f"{GREEN_min:.2f} 分")

# =========================
# 3. 車両数の設定
# =========================

st.subheader("前方車両数の設定")

Nb = st.number_input("前にいる二輪車の台数", min_value=0, value=5)
Nc = st.number_input("前にいる普通車の台数", min_value=0, value=25)
Nl = st.number_input("前にいる大型車の台数", min_value=0, value=10)

N = Nb + Nc + Nl

last_vehicle_jp = st.selectbox("最後尾車両の種類", ["普通車", "二輪車", "大型車"])

vehicle_map = {
    "普通車": "car",
    "二輪車": "bike",
    "大型車": "large"
}

last_vehicle = vehicle_map[last_vehicle_jp]

# =========================
# 4. 車両の特性
# =========================

L = {
    "bike": 2.0,
    "car": 4.5,
    "large": 12.0
}

G = {
    "bike": 1.5,
    "car": 2.0,
    "large": 3.0
}

A = {
    "bike": 2.5,
    "car": 2.0,
    "large": 1.0
}

H = {
    "bike": 1.0,
    "car": 2.0,
    "large": 3.0
}

TURN_SPEED = {
    "bike": 5.0,
    "car": 5.0,
    "large": 3.0
}

D = 10.0
t0 = 2.0

# =========================
# 5. 直進・右折・左折の固定割合
# =========================

st.subheader("直進・右折・左折の割合")

STRAIGHT_RATIO = 0.7
RIGHT_RATIO = 0.1
LEFT_RATIO = 0.2

N_straight = round(N * STRAIGHT_RATIO)
N_right = round(N * RIGHT_RATIO)
N_left = N - N_straight - N_right

ratio_cols = st.columns(3)
ratio_cols[0].metric("直進車", f"{N_straight} 台")
ratio_cols[1].metric("右折車", f"{N_right} 台")
ratio_cols[2].metric("左折車", f"{N_left} 台")

st.write("直進：右折：左折 ＝ 7：1：2 で固定")

# =========================
# 6. 右折・左折条件
# =========================

st.subheader("右折・左折条件")

DECELERATION_DISTANCE = 20.0
RIGHT_TURN_SAFE_DISTANCE = 50.0

st.write("左折車・右折車は、交差点の20m手前から減速するものとする。")
st.write("右折車は、対向車が信号から50m以上離れている場合に右折可能とする。")

opposite_distance = st.slider(
    "対向車が信号から離れている距離（m）",
    0,
    100,
    40
)

opposite_speed = st.slider(
    "対向車が離れていく速度（m/s）",
    1.0,
    20.0,
    10.0
)

if opposite_distance >= RIGHT_TURN_SAFE_DISTANCE:
    right_turn_wait = 0.0
    can_turn_right = True
else:
    right_turn_wait = (RIGHT_TURN_SAFE_DISTANCE - opposite_distance) / opposite_speed
    can_turn_right = False

if can_turn_right:
    st.success("右折可能：対向車が50m以上離れています。")
else:
    st.warning(f"右折待ち：対向車が50m以上離れるまで約 {right_turn_wait:.1f} 秒待ちます。")

# =========================
# 7. 通過時間の計算
# =========================

trials = st.slider("試行回数", 100, 5000, 1000)


def calculate_move_time(Nb, Nc, Nl, last_vehicle):
    x = (
        Nb * (L["bike"] + G["bike"])
        + Nc * (L["car"] + G["car"])
        + Nl * (L["large"] + G["large"])
        + D
        + L[last_vehicle]
    )

    move_time = np.sqrt(2 * x / A[last_vehicle])
    return move_time


def calculate_turn_time(N_left, N_right, last_vehicle, right_turn_wait):
    turn_speed = TURN_SPEED[last_vehicle]

    left_turn_time = 0.0
    right_turn_time = 0.0

    if N_left > 0:
        left_turn_time = DECELERATION_DISTANCE / turn_speed

    if N_right > 0:
        right_turn_time = DECELERATION_DISTANCE / turn_speed + right_turn_wait

    return left_turn_time + right_turn_time


def calculate_T_sec(Nb, Nc, Nl, last_vehicle, N_left, N_right, right_turn_wait, epsilon=0):
    queue_time = (
        Nb * H["bike"]
        + Nc * H["car"]
        + Nl * H["large"]
    )

    move_time = calculate_move_time(Nb, Nc, Nl, last_vehicle)

    turn_time = calculate_turn_time(
        N_left,
        N_right,
        last_vehicle,
        right_turn_wait
    )

    T_sec = (
        t0
        + queue_time
        + move_time
        + turn_time
        + epsilon
    )

    return T_sec


T_list_min = []
jam_list = []

for _ in range(trials):
    epsilon = np.random.uniform(-3, 3)

    T_min = calculate_T_sec(
        Nb,
        Nc,
        Nl,
        last_vehicle,
        N_left,
        N_right,
        right_turn_wait,
        epsilon
    ) / 60

    T_list_min.append(T_min)
    jam_list.append(T_min > C_min)

avg_T_min = np.mean(T_list_min)
jam_rate = np.mean(jam_list)

# =========================
# 8. 結果表示
# =========================

st.subheader("シミュレーション結果")

r1, r2, r3, r4 = st.columns(4)

r1.metric("前方車両数 N", N)
r2.metric("平均通過時間 T", f"{avg_T_min:.2f} 分")
r3.metric("サイクル長 C", f"{C_min:.2f} 分")
r4.metric("渋滞率", f"{jam_rate * 100:.1f}%")

if avg_T_min > C_min:
    st.error("判定：渋滞が発生しやすい状態です。")
else:
    st.success("判定：1回の信号サイクル内で処理できる状態です。")

# =========================
# 9. 状態図
# =========================

st.subheader("右折時の状態図")

st.write(
    "アニメーションではなく、右折判断の流れを3つの状態図で表示します。"
)


def draw_road(ax):
    ax.set_xlim(-6, 6)
    ax.set_ylim(-6, 6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor("#f7f7f7")

    road_color = "#d9d9d9"
    line_color = "#6b3f1d"

    # 道路
    ax.add_patch(Rectangle((-1.2, -6), 2.4, 12, facecolor=road_color, edgecolor="none"))
    ax.add_patch(Rectangle((-6, -1.2), 12, 2.4, facecolor=road_color, edgecolor="none"))

    # 外枠
    ax.plot([-1.2, -1.2], [-6, -1.2], color=line_color, linewidth=1.5)
    ax.plot([1.2, 1.2], [-6, -1.2], color=line_color, linewidth=1.5)
    ax.plot([-1.2, -1.2], [1.2, 6], color=line_color, linewidth=1.5)
    ax.plot([1.2, 1.2], [1.2, 6], color=line_color, linewidth=1.5)

    ax.plot([-6, -1.2], [1.2, 1.2], color=line_color, linewidth=1.5)
    ax.plot([-6, -1.2], [-1.2, -1.2], color=line_color, linewidth=1.5)
    ax.plot([1.2, 6], [1.2, 1.2], color=line_color, linewidth=1.5)
    ax.plot([1.2, 6], [-1.2, -1.2], color=line_color, linewidth=1.5)

    # 中央線
    ax.plot([0, 0], [-6, -1.5], color=line_color, linestyle=(0, (5, 5)), linewidth=1.3)
    ax.plot([0, 0], [1.5, 6], color=line_color, linestyle=(0, (5, 5)), linewidth=1.3)
    ax.plot([-6, -1.5], [0, 0], color=line_color, linestyle=(0, (5, 5)), linewidth=1.3)
    ax.plot([1.5, 6], [0, 0], color=line_color, linestyle=(0, (5, 5)), linewidth=1.3)

    # 横断歩道
    for x in [-0.75, -0.35, 0.05, 0.45, 0.85]:
        ax.add_patch(Rectangle((x, -2.0), 0.18, 1.0, facecolor="white", edgecolor="none"))
        ax.add_patch(Rectangle((x, 1.0), 0.18, 1.0, facecolor="white", edgecolor="none"))

    for y in [-0.85, -0.45, -0.05, 0.35, 0.75]:
        ax.add_patch(Rectangle((-2.0, y), 1.0, 0.18, facecolor="white", edgecolor="none"))
        ax.add_patch(Rectangle((1.0, y), 1.0, 0.18, facecolor="white", edgecolor="none"))


def draw_signal(ax, x, y, active="green"):
    signal = FancyBboxPatch(
        (x, y),
        0.45,
        1.1,
        boxstyle="round,pad=0.03,rounding_size=0.08",
        facecolor="#222222",
        edgecolor="none"
    )
    ax.add_patch(signal)

    colors = {
        "red": "#e74c3c" if active == "red" else "#555555",
        "yellow": "#f1c40f" if active == "yellow" else "#555555",
        "green": "#2ecc71" if active == "green" else "#555555",
    }

    ax.add_patch(Circle((x + 0.225, y + 0.85), 0.12, color=colors["red"]))
    ax.add_patch(Circle((x + 0.225, y + 0.55), 0.12, color=colors["yellow"]))
    ax.add_patch(Circle((x + 0.225, y + 0.25), 0.12, color=colors["green"]))


def draw_car(ax, x, y, color, label="", direction="up"):
    if direction in ["up", "down"]:
        w, h = 0.42, 0.75
    else:
        w, h = 0.75, 0.42

    car = FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        facecolor=color,
        edgecolor="#333333",
        linewidth=1.0
    )
    ax.add_patch(car)

    if label:
        ax.text(
            x,
            y,
            label,
            color="white",
            ha="center",
            va="center",
            fontsize=9,
            fontweight="bold"
        )


def draw_arrow(ax, start, end, color="#333333"):
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(
            arrowstyle="->",
            lw=2,
            color=color
        )
    )


def draw_state_1():
    fig, ax = plt.subplots(figsize=(5, 5))
    draw_road(ax)

    draw_signal(ax, 1.45, -2.4, "green")
    draw_signal(ax, -1.9, 1.3, "red")

    # 自車線
    draw_car(ax, -0.45, -2.8, "#d62728", "R")
    draw_car(ax, -0.45, -3.7, "#1f77b4")
    draw_car(ax, -0.45, -4.6, "#2ca02c", "L")

    # 対向車
    draw_car(ax, 0.45, 3.3, "#9467bd", "O", "down")

    # 判断距離
    ax.plot([0.8, 0.8], [1.2, 4.2], color="#9467bd", linestyle="--", linewidth=1.5)
    ax.text(1.0, 3.8, "Check distance", fontsize=8)

    ax.set_title("State 1", fontsize=12)

    return fig


def draw_state_2():
    fig, ax = plt.subplots(figsize=(5, 5))
    draw_road(ax)

    draw_signal(ax, 1.45, -2.4, "green")
    draw_signal(ax, -1.9, 1.3, "red")

    # 右折車停止
    draw_car(ax, -0.45, -1.7, "#d62728", "R")
    draw_car(ax, -0.45, -2.6, "#1f77b4")
    draw_car(ax, -0.45, -3.5, "#2ca02c", "L")
    draw_car(ax, -0.45, -4.4, "#1f77b4")

    # 対向車が近い
    draw_car(ax, 0.45, 1.7, "#9467bd", "O", "down")

    ax.text(-5.5, 5.1, "Opponent < 50m", fontsize=9, color="#9467bd")
    ax.text(-5.5, 4.6, "Right car stops", fontsize=9, color="#d62728")
    ax.text(-5.5, 4.1, "Following cars wait", fontsize=9)

    ax.set_title("State 2", fontsize=12)

    return fig


def draw_state_3():
    fig, ax = plt.subplots(figsize=(5, 5))
    draw_road(ax)

    draw_signal(ax, 1.45, -2.4, "green")
    draw_signal(ax, -1.9, 1.3, "red")

    # 右折車が右折開始
    draw_car(ax, 1.8, 0.45, "#d62728", "R", "right")
    draw_arrow(ax, (-0.45, -1.2), (2.2, 0.45), "#d62728")

    # 後続車
    draw_car(ax, -0.45, -2.4, "#1f77b4")
    draw_car(ax, -0.45, -3.3, "#2ca02c", "L")
    draw_car(ax, -0.45, -4.2, "#1f77b4")

    # 対向車が遠い
    draw_car(ax, 0.45, 5.0, "#9467bd", "O", "down")

    ax.text(-5.5, 5.1, "Opponent >= 50m", fontsize=9, color="#9467bd")
    ax.text(-5.5, 4.6, "Right car turns", fontsize=9, color="#d62728")
    ax.text(-5.5, 4.1, "Following cars move", fontsize=9)

    ax.set_title("State 3", fontsize=12)

    return fig


fig1 = draw_state_1()
fig2 = draw_state_2()
fig3 = draw_state_3()

col1, col2, col3 = st.columns(3)

with col1:
    st.pyplot(fig1)
    st.caption("状態①：右折車が減速し、対向車との距離を確認する。")

with col2:
    st.pyplot(fig2)
    st.caption("状態②：対向車が50m未満の場合、右折車は停止し、後続車も待機する。")

with col3:
    st.pyplot(fig3)
    st.caption("状態③：対向車が50m以上離れたら、右折車が右折し、後続車が進む。")

plt.close(fig1)
plt.close(fig2)
plt.close(fig3)
