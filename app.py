import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="渋滞シミュレーション", layout="wide")

st.title("🚗 渋滞シミュレーション")

# =====================================================
# 曜日・時間帯
# =====================================================

st.subheader("曜日・時間帯の設定")

day_type = st.selectbox(
    "曜日",
    ["平日", "土日"]
)

time_zone = st.selectbox(
    "時間帯",
    [
        "朝(6:00〜11:59)",
        "昼(12:00〜17:59)",
        "夜(18:00〜23:59)",
        "深夜・早朝(24:00〜5:59)"
    ]
)

traffic_table = {
    "平日": {
        "朝(6:00〜11:59)": 25,
        "昼(12:00〜17:59)": 15,
        "夜(18:00〜23:59)": 20,
        "深夜・早朝(24:00〜5:59)": 3,
    },
    "土日": {
        "朝(6:00〜11:59)": 10,
        "昼(12:00〜17:59)": 30,
        "夜(18:00〜23:59)": 25,
        "深夜・早朝(24:00〜5:59)": 5,
    },
}

traffic_volume = traffic_table[day_type][time_zone]

# =====================================================
# Webster
# =====================================================

YELLOW = 5
RED = 40

L_clearance = YELLOW + RED

# 最大処理交通量
MAX_CAPACITY = 30

demand_rate = traffic_volume / MAX_CAPACITY

if demand_rate >= 1:
    demand_rate = 0.99

# Webster
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

# =====================================================
# 車両設定
# =====================================================

st.subheader("前方車両数の設定")

Nb = st.number_input(
    "前にいる二輪車の台数",
    min_value=0,
    value=5
)

Nc = st.number_input(
    "前にいる普通車の台数",
    min_value=0,
    value=25
)

Nl = st.number_input(
    "前にいる大型車の台数",
    min_value=0,
    value=10
)

N = Nb + Nc + Nl

last_vehicle_jp = st.selectbox(
    "最後尾車両の種類",
    [
        "普通車",
        "二輪車",
        "大型車"
    ]
)

vehicle_map = {
    "普通車": "car",
    "二輪車": "bike",
    "大型車": "large"
}

last_vehicle = vehicle_map[last_vehicle_jp]

# =====================================================
# 固定パラメータ
# =====================================================

# 車長(m)
L = {
    "bike": 2.0,
    "car": 4.5,
    "large": 12.0,
}

# 車間距離(m)
G = {
    "bike": 1.5,
    "car": 2.0,
    "large": 3.0,
}

# 加速度(m/s²)
A = {
    "bike": 2.5,
    "car": 2.0,
    "large": 1.0,
}

# 発車間隔(sec)
H = {
    "bike": 1.0,
    "car": 2.0,
    "large": 3.0,
}

# 横断歩道までの距離
D = 10.0

# 先頭車両反応時間
t0 = 2.0

trials = st.slider(
    "試行回数",
    100,
    5000,
    1000
)

# =====================================================
# T計算
# =====================================================

def calculate_T_sec(
    Nb,
    Nc,
    Nl,
    last_vehicle,
    epsilon=0
):

    queue_time = (
        Nb * H["bike"]
        + Nc * H["car"]
        + Nl * H["large"]
    )

    distance = (
        Nb * (L["bike"] + G["bike"])
        + Nc * (L["car"] + G["car"])
        + Nl * (L["large"] + G["large"])
        + D
        + L[last_vehicle]
    )

    move_time = np.sqrt(
        2 * distance / A[last_vehicle]
    )

    T_sec = (
        t0
        + queue_time
        + move_time
        + epsilon
    )

    return T_sec

# =====================================================
# シミュレーション
# =====================================================

T_list_min = []
jam_list = []

for _ in range(trials):

    epsilon = np.random.uniform(
        -3,
        3
    )

    T_sec = calculate_T_sec(
        Nb,
        Nc,
        Nl,
        last_vehicle,
        epsilon
    )

    T_min = T_sec / 60

    T_list_min.append(T_min)

    jam_list.append(
        T_min > C_min
    )

avg_T_min = np.mean(T_list_min)

jam_rate = np.mean(jam_list)

# =====================================================
# 結果
# =====================================================

st.subheader("シミュレーション結果")

r1, r2, r3, r4 = st.columns(4)

r1.metric(
    "前方車両数 N",
    N
)

r2.metric(
    "平均通過時間 T",
    f"{avg_T_min:.2f} 分"
)

r3.metric(
    "サイクル長 C",
    f"{C_min:.2f} 分"
)

r4.metric(
    "渋滞率",
    f"{jam_rate*100:.1f}%"
)

# =====================================================
# グラフ
# =====================================================

st.subheader("車両数 N と通過時間 T の関係")

max_N = max(
    120,
    N + 30
)

N_values = np.arange(
    1,
    max_N + 1
)

T_values = []

total = max(N, 1)

bike_ratio = Nb / total
car_ratio = Nc / total
large_ratio = Nl / total

for n in N_values:

    nb = round(n * bike_ratio)

    nc = round(n * car_ratio)

    nl = n - nb - nc

    T_sec = calculate_T_sec(
        nb,
        nc,
        nl,
        last_vehicle,
        0
    )

    T_values.append(
        T_sec / 60
    )

fig, ax = plt.subplots(
    figsize=(10, 6)
)

ax.plot(
    N_values,
    T_values,
    linewidth=2,
    label="Passing time T"
)

ax.axhline(
    C_min,
    linestyle="--",
    linewidth=2,
    label="Cycle length C"
)

ax.set_xlabel(
    "Number of vehicles N"
)

ax.set_ylabel(
    "Passing time T (min)"
)

ax.set_title(
    "Relationship between N and Passing Time T"
)

ax.grid(True)

ax.legend()

st.pyplot(fig)
