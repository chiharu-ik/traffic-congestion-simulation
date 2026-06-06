import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.title("🚗 渋滞シミュレーション")

st.write("曜日・時間帯ごとの交通量と、前方車両数をもとに渋滞を判定します。")

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
    }
}

traffic_volume = traffic_table[day_type][time_zone]

max_capacity = 40
demand_rate = traffic_volume / max_capacity

if demand_rate >= 1:
    demand_rate = 0.99

YELLOW = 5
RED = 40
CLEARANCE = YELLOW + RED

C_min = (0.025 * CLEARANCE + 5) / (1 - demand_rate)
C_sec = C_min * 60
GREEN = C_sec - CLEARANCE

st.subheader("信号設定")

col1, col2, col3, col4 = st.columns(4)

col1.metric("交通量", f"{traffic_volume} 台/分")
col2.metric("需要率", round(demand_rate, 2))
col3.metric("サイクル長 C", f"{round(C_sec, 1)} 秒")
col4.metric("青信号時間", f"{round(GREEN, 1)} 秒")

st.subheader("前方車両数の設定")

Nb = st.number_input("前にいる二輪車の台数", min_value=0, value=5)
Nc = st.number_input("前にいる普通車の台数", min_value=0, value=25)
Nl = st.number_input("前にいる大型車の台数", min_value=0, value=10)

N = Nb + Nc + Nl

last_vehicle = st.selectbox("最後尾車両の種類", ["普通車", "二輪車", "大型車"])

vehicle_map = {
    "普通車": "car",
    "二輪車": "bike",
    "大型車": "large"
}

last_vehicle = vehicle_map[last_vehicle]

trials = st.slider("試行回数", 100, 5000, 1000)

L = {"car": 4.5, "bike": 2.0, "large": 12.0}
G = {"car": 2.0, "bike": 1.5, "large": 3.0}
A = {"car": 2.0, "bike": 2.5, "large": 1.0}
H = {"car": 1.0, "bike": 0.7, "large": 1.5}

D = 10.0
t0 = 2.0

def simulate_once():
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

    epsilon = np.random.uniform(-1, 1)

    T = t0 + queue_time + move_time + epsilon

    jam = T > GREEN

    return T, jam

results = [simulate_once() for _ in range(trials)]

df = pd.DataFrame(results, columns=["T", "jam"])
df["N"] = N

st.subheader("シミュレーション結果")

col_a, col_b, col_c = st.columns(3)

col_a.metric("前方車両数 N", N)
col_b.metric("平均通過時間 T", f"{round(df['T'].mean(), 2)} 秒")
col_c.metric("渋滞率", f"{df['jam'].mean() * 100:.1f}%")

st.subheader("通過時間の分布")

fig, ax = plt.subplots(figsize=(8, 5))

ax.hist(df["T"], bins=30, alpha=0.7)
ax.axvline(GREEN, linestyle="--", label="Green time threshold")

ax.set_xlabel("Passing time T (sec)")
ax.set_ylabel("Frequency")
ax.set_title("Distribution of Passing Time T")
ax.legend()
ax.grid(True)

st.pyplot(fig)

