import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
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

# =========================
# 9. グラフ
# =========================

st.subheader("車両数 N と通過時間 T の関係")

max_N = max(120, N + 30)
N_values = np.arange(1, max_N + 1)
T_values = []

total = max(N, 1)

bike_ratio = Nb / total
car_ratio = Nc / total
large_ratio = Nl / total

for n in N_values:
    nb = round(n * bike_ratio)
    nc = round(n * car_ratio)
    nl = n - nb - nc

    n_straight = round(n * STRAIGHT_RATIO)
    n_right = round(n * RIGHT_RATIO)
    n_left = n - n_straight - n_right

    T_values.append(
        calculate_T_sec(
            nb,
            nc,
            nl,
            last_vehicle,
            n_left,
            n_right,
            right_turn_wait,
            0
        ) / 60
    )

fig, ax = plt.subplots(figsize=(10, 6))

ax.plot(N_values, T_values, linewidth=2, label="Passing Time T")
ax.axhline(C_min, linestyle="--", linewidth=2, label="Cycle Length C")

ax.set_xlabel("Number of Vehicles N")
ax.set_ylabel("Passing Time T (min)")
ax.set_title("Relationship between N and Passing Time T")
ax.grid(True)
ax.legend()

st.pyplot(fig)

# =========================
# 10. 交差点アニメーション
# =========================

def draw_car(ax, x, y, color, label=None):
    car = plt.Rectangle(
        (x - 0.25, y - 0.45),
        0.5,
        0.9,
        facecolor=color,
        edgecolor="black",
        linewidth=0.8
    )
    ax.add_patch(car)

    if label is not None:
        ax.text(x, y + 0.65, label, ha="center", fontsize=8)


def draw_road_base(ax):
    ax.set_facecolor("#f5f5f5")

    # 道路
    ax.add_patch(plt.Rectangle((-2.2, -10), 4.4, 20, color="#777777"))
    ax.add_patch(plt.Rectangle((-10, -2.2), 20, 4.4, color="#777777"))

    # 車線の中心線
    ax.plot([0, 0], [-10, -2.4], color="white", linestyle="--", linewidth=1)
    ax.plot([0, 0], [2.4, 10], color="white", linestyle="--", linewidth=1)
    ax.plot([-10, -2.4], [0, 0], color="white", linestyle="--", linewidth=1)
    ax.plot([2.4, 10], [0, 0], color="white", linestyle="--", linewidth=1)

    # 停止線
    ax.plot([-2.0, 2.0], [-3.2, -3.2], color="white", linewidth=3)
    ax.plot([-2.0, 2.0], [3.2, 3.2], color="white", linewidth=3)

    # 20m手前の減速開始位置
    ax.plot([-2.0, 2.0], [-7.0, -7.0], color="orange", linewidth=3)
    ax.text(2.4, -7.1, "20m before", fontsize=8, va="center")

    ax.set_xlim(-10, 10)
    ax.set_ylim(-10, 10)
    ax.set_aspect("equal")
    ax.axis("off")


def draw_intersection_animation(N_straight, N_right, N_left, can_turn_right):
    st.subheader("交差点内の車両の動き")

    placeholder = st.empty()

    # 表示は直進7台・右折1台・左折2台に固定
    show_straight = 7
    show_right = 1
    show_left = 2

    total_steps = 120

    for step in range(total_steps):
        fig, ax = plt.subplots(figsize=(6, 6))
        draw_road_base(ax)

        p_all = step / (total_steps - 1)

        # 直進車：下から上へ
        for i in range(show_straight):
            p = p_all - i * 0.08

            if 0 <= p <= 1:
                x = -0.8
                y = -9 + 18 * p
                draw_car(ax, x, y, "#1f77b4")

        # 右折車：下から右へ
        for i in range(show_right):
            p = p_all - 0.20

            if 0 <= p <= 1:
                if not can_turn_right:
                    # 右折不可の場合：一度停止してから右折
                    if p < 0.35:
                        x = 0.2
                        y = -9 + 6.0 * (p / 0.35)
                    elif p < 0.60:
                        x = 0.2
                        y = -3.0
                    else:
                        q = (p - 0.60) / 0.40

                        if q < 0.45:
                            x = 0.2
                            y = -3.0 + 3.0 * (q / 0.45)
                        else:
                            r = (q - 0.45) / 0.55
                            x = 0.2 + 8.5 * r
                            y = 0.6
                else:
                    # 右折可能の場合：そのまま右折
                    if p < 0.55:
                        x = 0.2
                        y = -9 + 8.5 * (p / 0.55)
                    else:
                        q = (p - 0.55) / 0.45
                        x = 0.2 + 8.5 * q
                        y = 0.6

                draw_car(ax, x, y, "#d62728", "R")

        # 左折車：下から左へ
        for i in range(show_left):
            p = p_all - 0.35 - i * 0.10

            if 0 <= p <= 1:
                if p < 0.55:
                    x = 0.8
                    y = -9 + 8.5 * (p / 0.55)
                else:
                    q = (p - 0.55) / 0.45
                    x = 0.8 - 8.5 * q
                    y = -0.5

                draw_car(ax, x, y, "#2ca02c", "L" if i == 0 else None)

        # 対向車：右折不可の場合だけ表示
        if not can_turn_right:
            p = p_all
            x = 0.8
            y = 9 - 8 * p
            draw_car(ax, x, y, "#9467bd", "opposite")

        ax.set_title("Straight : Right : Left = 7 : 1 : 2", fontsize=12)

        placeholder.pyplot(fig)
        plt.close(fig)

        time.sleep(0.04)


st.subheader("交差点アニメーション")

if st.button("交差点の動きを表示"):
    draw_intersection_animation(
        N_straight,
        N_right,
        N_left,
        can_turn_right
    )
