import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.title("🚗 渋滞シミュレーション")

# ------------------
# 曜日・時間帯
# ------------------
st.subheader("曜日・時間帯の設定")

day_type = st.selectbox("曜日", ["平日", "土日"])

time_zone = st.selectbox(
    "時間帯",
    ["朝(6:00〜11:59)", "昼(12:00〜17:59)", "夜(18:00〜23:59)", "深夜・早朝(24:00〜5:59)"]
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

# ------------------
# 信号設定
# ------------------
YELLOW = 5
RED = 40
L_clearance = YELLOW + RED

MAX_CAPACITY = 60
demand_rate = traffic_volume / MAX_CAPACITY

if demand_rate >= 1:
    demand_rate = 0.99

# Webster の近似式
# C = (1.5L + 5) / (1 - λ)
C = (1.5 * L_clearance + 5) / (1 - demand_rate)

GREEN = C - L_clearance

st.subheader("交通量と信号設定")

col1, col2, col3, col4 = st.columns(4)

col1.metric("交通量", f"{traffic_volume} 台/分")
col2.metric("需要率 λ", round(demand_rate, 2))
col3.metric("サイクル長 C", f"{round(C, 1)} 秒")
col4.metric("青信号時間", f"{round(GREEN, 1)} 秒")

# ------------------
# 車両台数設定
# ------------------
st.subheader("前方車両数の設定")

Nb = st.number_input("前にいる二輪車の台数", min_value=0, value=5)
Nc = st.number_input("前にいる普通車の台数", min_value=0, value=25)
Nl = st.number_input("前にいる大型車の台数", min_value=0, value=10)

N = Nb + Nc + Nl

last_vehicle_jp = st.selectbox(
    "最後尾車両の種類",
    ["普通車", "二輪車", "大型車"]
)

vehicle_map = {
    "普通車": "car",
    "二輪車": "bike",
    "大型車": "large",
}

last_vehicle = vehicle_map[last_vehicle_jp]

# ------------------
# 車両パラメータ
# ------------------
L = {
    "bike": 2.0,
    "car": 4.5,
    "large": 12.0,
}

G = {
    "bike": 1.5,
    "car": 2.0,
    "large": 3.0,
}

A = {
    "bike": 2.5,
    "car": 2.0,
    "large": 1.0,
}

H = {
    "bike": 0.7,
    "car": 1.0,
    "large": 1.5,
}

D = 10.0
t0 = 2.0

trials = st.slider("試行回数", 100, 5000, 1000)

# ------------------
# 通過時間を計算する関数
# ------------------
def calculate_T(Nb, Nc, Nl, last_vehicle, epsilon=0):
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

    move_time = np.sqrt(2 * distance / A[last_vehicle])

    T = t0 + queue_time + move_time + epsilon

    return T

# ------------------
# シミュレーション
# ------------------
results = []

for _ in range(trials):
    epsilon = np.random.uniform(-1, 1)
    T = calculate_T(Nb, Nc, Nl, last_vehicle, epsilon)
    jam = C < T
    results.append([T, jam])

df = pd.DataFrame(results, columns=["T", "jam"])

# ------------------
# 結果表示
# ------------------
st.subheader("シミュレーション結果")

col_a, col_b, col_c = st.columns(3)

col_a.metric("前方車両数 N", N)
col_b.metric("平均通過時間 T", f"{round(df['T'].mean(), 2)} 秒")
col_c.metric("渋滞率", f"{df['jam'].mean() * 100:.1f}%")

if df["T"].mean() > C:
    st.error("判定：C < T のため、渋滞が発生しています。")
else:
    st.success("判定：C ≥ T のため、渋滞は発生していません。")

# ------------------
# Nを変化させたグラフ
# ------------------
st.subheader("車両数 N と通過時間 T の関係")

max_N = max(80, N + 40)

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

    T_n = calculate_T(nb, nc, nl, last_vehicle, epsilon=0)
    T_values.append(T_n)

fig, ax = plt.subplots(figsize=(8, 5))

ax.plot(N_values, T_values, marker="o", markersize=3, label="Passing time T")
ax.axhline(C, linestyle="--", label="Cycle length C")

ax.set_xlabel("Number of vehicles N")
ax.set_ylabel("Passing time T (sec)")
ax.set_title("Relationship between N and Passing Time T")
ax.legend()
ax.grid(True)

st.pyplot(fig)
