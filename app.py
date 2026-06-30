import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
import time

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
# 9. 交差点アニメーション
# =========================

def smoothstep(t):
    t = max(0, min(1, t))
    return t * t * (3 - 2 * t)


def draw_road(ax):
    ax.set_xlim(-6, 6)
    ax.set_ylim(-6, 6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor("white")

    road_color = "#d9d9d9"
    line_color = "#6b3f1d"

    # 道路
    ax.add_patch(Rectangle((-1.2, -6), 2.4, 12, facecolor=road_color, edgecolor="none"))
    ax.add_patch(Rectangle((-6, -1.2), 12, 2.4, facecolor=road_color, edgecolor="none"))

    # 道路外枠
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

    # 横断歩道 下側・上側
    for x in [-0.75, -0.35, 0.05, 0.45, 0.85]:
        ax.add_patch(Rectangle((x, -2.0), 0.18, 1.0, facecolor="white", edgecolor="none"))
        ax.add_patch(Rectangle((x, 1.0), 0.18, 1.0, facecolor="white", edgecolor="none"))

    # 横断歩道 左側・右側
    for y in [-0.85, -0.45, -0.05, 0.35, 0.75]:
        ax.add_patch(Rectangle((-2.0, y), 1.0, 0.18, facecolor="white", edgecolor="none"))
        ax.add_patch(Rectangle((1.0, y), 1.0, 0.18, facecolor="white", edgecolor="none"))


def draw_car(ax, x, y, direction, color, label=None):
    if direction in ["up", "down"]:
        w, h = 0.34, 0.62
    else:
        w, h = 0.62, 0.34

    car = FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.06",
        facecolor=color,
        edgecolor="#333333",
        linewidth=0.8
    )
    ax.add_patch(car)

    if label:
        ax.text(x, y, label, color="white", ha="center", va="center", fontsize=7)


def route_position(route, p):
    p = smoothstep(p)

    # 直進
    if route == "S":
        x = -0.45
        y = -5.4 + 10.8 * p
        return x, y, "up"

    # 左折
    if route == "L":
        if p < 0.58:
            q = p / 0.58
            x = -0.45
            y = -5.4 + 5.2 * q
            return x, y, "up"
        else:
            q = (p - 0.58) / 0.42
            q = smoothstep(q)
            x = -0.45 - 4.8 * q
            y = -0.25
            return x, y, "left"

    # 右折
    if route == "R":
        if p < 0.58:
            q = p / 0.58
            x = -0.45
            y = -5.4 + 5.2 * q
            return x, y, "up"
        else:
            q = (p - 0.58) / 0.42
            q = smoothstep(q)
            x = -0.45 + 4.8 * q
            y = 0.25
            return x, y, "right"

    return -0.45, -5.4, "up"


def draw_animation(can_turn_right):
    st.subheader("交差点アニメーション")
    st.write("片側1車線のため、右折車が停止すると、後続車も追い越さずに待機します。")
    st.write("表示は、直進7台・右折1台・左折2台で固定しています。")

    placeholder = st.empty()

    # 直進7：右折1：左折2
    # 右折車を途中に配置して、右折待ちが後続車に影響する様子を表示
    routes = ["S", "S", "S", "R", "L", "L", "S", "S", "S", "S"]

    colors = {
        "S": "#1f77b4",
        "R": "#d62728",
        "L": "#2ca02c",
        "O": "#9467bd",
    }

    total_steps = 260
    frame_sleep = 0.025

    start_gap = 22
    move_duration = 120

    right_index = routes.index("R")
    wait_frames = 70 if not can_turn_right else 0

    for step in range(total_steps):
        fig, ax = plt.subplots(figsize=(6, 6))
        draw_road(ax)

        # 対向車線の車
        opp_count = 6 if not can_turn_right else 3

        for j in range(opp_count):
            p_opp = (step - j * 42) / 180
            if 0 <= p_opp <= 1:
                p_opp = smoothstep(p_opp)
                x_opp = 0.45
                y_opp = 5.4 - 10.8 * p_opp
                draw_car(ax, x_opp, y_opp, "down", colors["O"])

        for i, route in enumerate(routes):
            base_start = i * start_gap

            # 右折車より後ろの車は、右折待ち分だけ発進が遅れる
            if i > right_index:
                base_start += wait_frames

            # 右折車が右折できない場合
            if i == right_index and not can_turn_right:
                stop_start = base_start + 50
                stop_end = stop_start + wait_frames

                if step < base_start:
                    continue

                # 交差点手前まで進む
                elif base_start <= step < stop_start:
                    p = (step - base_start) / move_duration
                    p = min(p, 0.52)
                    x, y, d = route_position("R", p)
                    draw_car(ax, x, y, d, colors["R"], "R")

                # 一時停止
                elif stop_start <= step < stop_end:
                    x, y, d = -0.45, -1.25, "up"
                    draw_car(ax, x, y, d, colors["R"], "R")

                # 対向車が離れた後に右折
                else:
                    p = 0.52 + (step - stop_end) / 90 * 0.48
                    if p <= 1:
                        x, y, d = route_position("R", p)
                        draw_car(ax, x, y, d, colors["R"], "R")

            else:
                p = (step - base_start) / move_duration

                if 0 <= p <= 1:
                    x, y, d = route_position(route, p)

                    # 右折車が停止している間、後続車も同じ車線上で停止
                    if not can_turn_right and i > right_index:
                        stop_start = right_index * start_gap + 50
                        stop_end = stop_start + wait_frames

                        if stop_start <= step < stop_end:
                            queue_order = i - right_index
                            x = -0.45
                            y = -1.25 - queue_order * 0.78
                            d = "up"

                    label = route if route in ["R", "L"] else None
                    draw_car(ax, x, y, d, colors[route], label)

        ax.set_title("Straight : Right : Left = 7 : 1 : 2", fontsize=12)

        placeholder.pyplot(fig)
        plt.close(fig)

        time.sleep(frame_sleep)


if st.button("交差点の動きを表示"):
    draw_animation(can_turn_right)
