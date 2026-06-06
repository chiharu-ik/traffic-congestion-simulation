import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.title("Traffic Congestion Simulation")

st.write(
    "This app simulates whether the last vehicle can pass through a signalized crosswalk during one green light."
)

# ------------------
# Parameters
# ------------------
GREEN = st.slider("Green light time (sec)", 10, 120, 60)
YELLOW = 5
RED = st.slider("Red light time (sec)", 10, 120, 55)
CYCLE = GREEN + YELLOW + RED

lam = st.slider("Traffic volume λ (vehicles/min)", 1, 40, 25)
trials = st.slider("Number of trials", 100, 5000, 1000)

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

st.subheader("Simulation Results")

col1, col2, col3 = st.columns(3)

col1.metric("Average N", round(df["N"].mean(), 2))
col2.metric("Average T (sec)", round(df["T"].mean(), 2))
col3.metric("Jam Rate", f"{df['jam'].mean() * 100:.1f}%")

st.subheader("Relationship between N and T")

fig, ax = plt.subplots(figsize=(8, 5))

ax.scatter(df["N"], df["T"], alpha=0.4)
ax.axhline(GREEN, linestyle="--", label="Green time threshold")

ax.set_xlabel("Number of vehicles N")
ax.set_ylabel("Passing time T (sec)")
ax.set_title("Relationship between N and Passing Time T")
ax.legend()
ax.grid(True)

st.pyplot(fig)

st.subheader("Average T by N")

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

st.write("Jam is defined as the case where the last vehicle cannot pass during one green light.")
