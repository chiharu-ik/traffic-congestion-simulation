import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.title("🚗 渋滞シミュレーション")

st.write(
    "最後尾車両が1回の青信号で通過できるかを判定するシミュレーションです。"
)

# ------------------
# パラメータ
# ------------------
GREEN = st.slider("青信号時間（秒）", 10, 120, 60)
YELLOW = 5
RED = st.slider("赤信号時間（秒）", 10, 120, 55)
CYCLE = GREEN + YELLOW + RED

lam = st.slider("交通量 λ（台/分）", 1, 40, 25)
trials = st.slider("試行回数", 100, 5000, 1000)

vehicle_types = ["car", "bike", "large"]
vehicle_probs = [0.7, 0.1, 0.2]

L = {"car": 4.5, "bike": 2.0, "large": 12.0}
G = {"car": 2.0, "bike": 1.5, "large": 3.0}
A = {"car": 2.0, "bike": 2.5, "large": 1.0}
H = {"car": 1.0, "bike": 0.7, "large": 1.5}

D = 10.0
t0 = 2.0


def simulate_once():
    lam_cycle = lam * CYCLE / 60
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

col1.metric("平均車両数", round(df["N"].mean(), 2))
col2.metric("平均通過時間（秒）", round(df["T"].mean(), 2))
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
    "本シミュレーションでは、最後尾車両が青信号時間内に通過できない場合を渋滞と定義しています。"
)
