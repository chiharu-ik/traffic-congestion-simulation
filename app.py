import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.title("🚗 渋滞シミュレーション")

st.write(
    "需要率 λ によって信号サイクル長 C が変化するモデルです。"
)

# ------------------
# 入力パラメータ
# ------------------
st.subheader("条件設定")

traffic_volume = st.slider("交通量（台/分）", 1, 40, 25)

demand_rate = st.slider(
    "需要率 λ",
    0.10,
    0.95,
    0.60,
    0.05
)

YELLOW = 5
RED = 40
CLEARANCE = YELLOW + RED

trials = st.slider("試行回数", 100, 5000, 1000)

# ------------------
# Webster の近似式
# C = (0.025L + 5) / (1 - λ)
# ------------------
C_min = (0.025 * CLEARANCE + 5) / (1 - demand_rate)
C_sec = C_min * 60

GREEN = C_sec - CLEARANCE

st.subheader("信号設定")

col_a, col_b, col_c = st.columns(3)

col_a.metric("サイクル長 C（秒）", round(C_sec, 1))
col_b.metric("青信号時間（秒）", round(GREEN, 1))
col_c.metric("黄＋赤時間（秒）", CLEARANCE)

# ------------------
# 車両設定
# ------------------
vehicle_types = ["car", "bike", "large"]
vehicle_probs = [0.7, 0.1, 0.2]

L = {
    "car": 4.5,
    "bike": 2.0,
    "large": 12.0
}

G = {
    "car": 2.0,
    "bike": 1.5,
    "large": 3.0
}

A = {
    "car": 2.0,
    "bike": 2.5,
    "large": 1.0
}

H = {
    "car": 1.0,
    "bike": 0.7,
    "large": 1.5
}

D = 10.0
t0 = 2.0


def simulate_once():
    # サイクル長 C に応じて、1サイクル中の到着台数 N を決める
    lam_cycle = traffic_volume * C_sec / 60

    N = np.random.poisson(lam_cycle)

    if N == 0:
        return 0, 0, False

    vehicles = np.random.choice(
        vehicle_types,
        size=N,
        p=vehicle_probs
    )

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

    move_time = np.sqrt(
        2 * distance / A[last_vehicle]
    )

    epsilon = np.random.uniform(-1, 1)

    T = t0 + queue_time + move_time + epsilon

    # C < T ではなく、実際には「青時間内に通過できるか」で判定
    jam = T > GREEN

    return N, T, jam


results = [simulate_once() for _ in range(trials)]

df = pd.DataFrame(
    results,
    columns=["N", "T", "jam"]
)

# ------------------
# 結果表示
# ------------------
st.subheader("シミュレーション結果")

col1, col2, col3 = st.columns(3)

col1.metric("平均車両数 N", round(df["N"].mean(), 2))
col2.metric("平均通過時間 T（秒）", round(df["T"].mean(), 2))
col3.metric("渋滞率", f"{df['jam'].mean() * 100:.1f}%")

# ------------------
# グラフ1
# ------------------
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

# ------------------
# グラフ2
# ------------------
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
    "本シミュレーションでは、需要率 λ によって Webster の近似式からサイクル長 C を求め、"
    "そのサイクル中に発生する車両数 N をポアソン分布で生成しています。"
)

st.write(
    "最後尾車両の通過時間 T が青信号時間を超えた場合、1回の青信号で処理しきれないため渋滞と判定しています。"
)
