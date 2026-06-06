import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.title("🚗 渋滞シミュレーション")

st.write("曜日・時間帯ごとの交通量から需要率を求め、信号周期と渋滞を判定します。")

st.subheader("条件設定")

day_type = st.selectbox("曜日", ["平日", "土日"])
time_zone = st.selectbox("時間帯", ["朝(6:00〜11:59)", "昼(12:00〜17:59)", "夜(18:00〜23:59)", "深夜・早朝(24:00〜5:59)"])

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

max_capacity = st.slider("青信号中に処理できる最大交通量（台/分）", 20, 60, 40)

demand_rate = traffic_volume / max_capacity

if demand_rate >= 1:
    demand_rate = 0.99

YELLOW = 5
RED = 40
CLEARANCE = YELLOW + RED

trials = st.slider("試行回数", 100, 5000, 1000)

C_min = (0.025 * CLEARANCE + 5) / (1 - demand_rate)
C_sec = C_min * 60

GREEN = C_sec - CLEARANCE

st.subheader("交通量と信号設定")

col_a, col_b, col_c, col_d = st.columns(4)

col_a.metric("交通量", f"{traffic_volume} 台/分")
col_b.metric("需要率", round(demand_rate, 2))
col_c.metric("サイクル長 C", f"{round(C_sec, 1)} 秒")
col_d.metric("青信号時間", f"{round(GREEN, 1)} 秒")

vehicle_types = ["car", "bike", "large"]
vehicle_probs = [0.7, 0.1, 0.2]

L = {"car": 4.5, "bike": 2.0, "large": 12.0}
G = {"car": 2.0, "bike": 1.5, "large": 3.0}
A = {"car": 2.0, "bike": 2.5, "large": 1.0}
H = {"car": 1.0, "bike": 0.7, "large": 1.5}

D = 10.0
t0 = 2.0


def simulate_once():
    lam_cycle = traffic_volume * C_sec / 60
    N = np.random.poisson(lam_cycle)

    if N == 0:
        return 0, 0, False

    vehicles = np.random.choice(vehicle_types, size=N, p=vehicle_probs)

    last_vehicle = vehicles[-1]
    front = vehicles[:-1]

    Nb = np.sum(front == "bike")
    Nc = np.sum(front == "car")
    Nl = np.sum(front == "large")

    queue_time = sum(H[v] for v in front)

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

    return N, T, jam


results = [simulate_once() for _ in range(trials)]

df = pd.DataFrame(results, columns=["N", "T", "jam"])

st.subheader("シミュレーション結果")

col1, col2, col3 = st.columns(3)

col1.metric("平均車両数 N", round(df["N"].mean(), 2))
col2.metric("平均通過時間 T（秒）", round(df["T"].mean(), 2))
col3.metric("渋滞率", f"{df['jam'].mean() * 100:.1f}%")

st.subheader("車両数と通過時間の関係")

fig, ax = plt.subplots(figsize=(8, 5))

ax.scatter(df["N"], df["T"], alpha=0.4)
ax.axhline(GREEN, linestyle="--", label="Green time threshold")

ax.set_xlabel("Number of vehicles N")
ax.set_ylabel("Passing time T (sec)")
ax.set_title("Relationship between N and Passing Time T")
ax.legend()
ax.grid(True)

st.pyplot(fig)

st.subheader("車両数ごとの平均通過時間")

mean_by_N = df.groupby("N")["T"].mean()

fig2, ax2 = plt.subplots(figsize=(8, 5))

ax2.plot(mean_by_N.index, mean_by_N.values, marker="o")
ax2.axhline(GREEN, linestyle="--", label="Green time threshold")

ax2.set_xlabel("Number of vehicles N")
ax2.set_ylabel("Average passing time T (sec)")
ax2.set_title("Average Passing Time by Number of Vehicles")
ax2.legend()
ax2.grid(True)

st.pyplot(fig2)

st.write(
    "本シミュレーションでは、曜日と時間帯から交通量を決定し、その交通量から需要率を求めています。"
)

st.write(
    "需要率をWebsterの近似式に代入して信号サイクル長Cを求め、その1サイクル中に到着する車両数Nをポアソン分布で発生させています。"
)

st.write(
    "最後尾車両の通過時間Tが青信号時間を超えた場合、1回の青信号で処理しきれないため渋滞と判定しています。"
)
