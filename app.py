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

# 左折・右折時の速度
TURN_SPEED = {
    "bike": 5.0,
    "car": 5.0,
    "large": 3.0
}

D = 10.0
t0 = 2.0

# =========================
# 5. 右折・左折条件
# =========================

st.subheader("右折・左折の設定")

straight_ratio = st.slider("直進車の割合（%）", 0, 100, 70)
left_ratio = st.slider("左折車の割合（%）", 0, 100, 20)

right_ratio = 100 - straight_ratio - left_ratio

if right_ratio < 0:
    st.warning("直進車と左折車の割合の合計が100%を超えています。")
    right_ratio = 0

N_straight = round(N * straight_ratio / 100)
N_left = round(N * left_ratio / 100)
N_right = N - N_straight - N_left

st.write(f"直進車：{N_straight}台")
st.write(f"左折車：{N_left}台")
st.write(f"右折車：{N_right}台")

DECELERATION_DISTANCE = 20.0
RIGHT_TURN_SAFE_DISTANCE = 50.0

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
# 6. 通過時間の計算
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
# 7. 結果表示
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
# 8. グラフ
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

    n_straight = round(n * straight_ratio / 100)
    n_left = round(n * left_ratio / 100)
    n_right = n - n_straight - n_left

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
# 9. 交差点アニメーション
# =========================

def draw_intersection_animation(N_straight, N_left, N_right, can_turn_right):
    st.subheader("交差点内の車両の動き")

    placeholder = st.empty()

    total_steps = 90

    for step in range(total_steps):
        fig, ax = plt.subplots(figsize=(6, 6))

        # 道路
        ax.axhline(0, color="gray", linewidth=35)
        ax.axvline(0, color="gray", linewidth=35)

        # 停止線
        ax.plot([-3, 3], [-4, -4], color="white", linewidth=2)

        # 20m手前の減速開始位置の目安
        ax.plot([-3, 3], [-7, -7], color="yellow", linewidth=2)

        # 右折判断距離 50m の目安
        ax.text(-9.5, 8.5, "Right turn condition: opposite car >= 50m", fontsize=9)

        ax.set_xlim(-10, 10)
        ax.set_ylim(-10, 10)
        ax.set_aspect("equal")
        ax.axis("off")

        progress = step / total_steps

        # 直進車：下から上
        for i in range(N_straight):
            delay = i * 0.06
            p = progress - delay

            if 0 <= p <= 1:
                x = -1.5
                y = -9 + 18 * p
                ax.scatter(x, y, s=120, marker="s", label="straight" if i == 0 else "")

        # 左折車：下から左
        for i in range(N_left):
            delay = i * 0.08
            p = progress - delay

            if 0 <= p <= 1:
                if p < 0.45:
                    x = 1.5
                    y = -9 + 9 * (p / 0.45)
                else:
                    x = 1.5 - 9 * ((p - 0.45) / 0.55)
                    y = 0.8

                ax.scatter(x, y, s=120, marker="s")

        # 右折車：下から右
        for i in range(N_right):
            delay = i * 0.12
            p = progress - delay

            # 右折できない場合は、一度停止してから右折するように見せる
            if not can_turn_right:
                stop_start = 0.35
                stop_end = 0.55

                if 0 <= p < stop_start:
                    x = 0.5
                    y = -9 + 7 * (p / stop_start)

                elif stop_start <= p < stop_end:
                    x = 0.5
                    y = -2.0

                elif stop_end <= p <= 1:
                    q = (p - stop_end) / (1 - stop_end)
                    if q < 0.45:
                        x = 0.5
                        y = -2.0 + 2.0 * (q / 0.45)
                    else:
                        x = 9 * ((q - 0.45) / 0.55)
                        y = -0.8
                else:
                    continue

            else:
                if 0 <= p <= 1:
                    if p < 0.45:
                        x = 0.5
                        y = -9 + 9 * (p / 0.45)
                    else:
                        x = 9 * ((p - 0.45) / 0.55)
                        y = -0.8
                else:
                    continue

            ax.scatter(x, y, s=120, marker="s")

        # 対向車の表示
        if not can_turn_right:
            ax.scatter(0.5, 8 - 8 * progress, s=140, marker="s")
            ax.text(1.2, 7.5 - 8 * progress, "opposite car", fontsize=8)

        ax.set_title(
            f"Straight: {N_straight}   Left: {N_left}   Right: {N_right}"
        )

        placeholder.pyplot(fig)
        plt.close(fig)

        time.sleep(0.05)

st.subheader("交差点アニメーション")

if st.button("交差点の動きを表示"):
    draw_intersection_animation(
        min(N_straight, 15),
        min(N_left, 15),
        min(N_right, 15),
        can_turn_right
    )
