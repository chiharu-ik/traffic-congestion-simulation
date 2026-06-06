import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

np.random.seed(0)

# =====================
# 1. 信号設定（文京区春日周辺の横断歩道を想定）
# =====================
GREEN = 60      # 青信号 秒
YELLOW = 5      # 黄信号 秒
RED = 55        # 赤信号 秒
CYCLE = GREEN + YELLOW + RED  # 1サイクル 秒

# 渋滞判定：1回の青信号で最後尾車両が通過できなければ渋滞
JAM_THRESHOLD = GREEN


# =====================
# 2. 車両設定
# 4輪：2輪：大型車 = 7:1:2
# =====================
vehicle_types = ["car", "bike", "large"]
vehicle_probs = [0.7, 0.1, 0.2]

# 車長 m
L = {
    "car": 4.5,
    "bike": 2.0,
    "large": 12.0
}

# 停車時の車間距離 m
G = {
    "car": 2.0,
    "bike": 1.5,
    "large": 3.0
}

# 加速度 m/s^2
A = {
    "car": 2.0,
    "bike": 2.5,
    "large": 1.0
}

# 発進間隔 秒
H = {
    "car": 1.0,
    "bike": 0.7,
    "large": 1.5
}

# 横断歩道・信号区間の長さ m
D = 10.0

# 青信号になって先頭車が動き出すまでの時間 秒
t0 = 2.0


# =====================
# 3. 交通量 λ
# 単位：台/分
# =====================
def get_lambda(day_type, hour):
    if day_type == "weekday":
        if 6 <= hour < 12:
            return 25
        elif 12 <= hour < 18:
            return 15
        elif 18 <= hour < 24:
            return 20
        else:
            return 3

    elif day_type == "weekend":
        if 6 <= hour < 12:
            return 10
        elif 12 <= hour < 18:
            return 30
        elif 18 <= hour < 24:
            return 25
        else:
            return 5

    else:
        raise ValueError("day_type は 'weekday' または 'weekend' にしてください")


# =====================
# 4. 1回分のシミュレーション
# =====================
def simulate_once(day_type="weekday", hour=8):
    # 1分あたりの平均到着台数
    lam_per_min = get_lambda(day_type, hour)

    # 信号1サイクル中の平均到着台数に変換
    lam_cycle = lam_per_min * CYCLE / 60

    # 信号1サイクル中に到着する台数 N
    N = np.random.poisson(lam_cycle)

    if N == 0:
        return {
            "N": 0,
            "T": 0,
            "jam": False,
            "last_vehicle": None
        }

    # N台分の車種を発生
    vehicles = np.random.choice(vehicle_types, size=N, p=vehicle_probs)

    # 最後尾車両
    last_vehicle = vehicles[-1]

    # 最後尾より前にいる車両
    front_vehicles = vehicles[:-1]

    # 前方車両数
    N_front = len(front_vehicles)

    # 車種ごとの台数
    Nb = np.sum(front_vehicles == "bike")
    Nc = np.sum(front_vehicles == "car")
    Nl = np.sum(front_vehicles == "large")

    # ① 青信号になって先頭車が動き出すまでの時間
    time_first_start = t0

    # ② 前の車が順番に発進し、最後尾車両が動き出すまでの時間
    time_queue = sum(H[v] for v in front_vehicles)

    # ③ 最後尾車両が進む距離
    # 前方車両の車長＋車間距離＋横断歩道長＋最後尾車両自身の車長
    distance = (
        Nb * (L["bike"] + G["bike"])
        + Nc * (L["car"] + G["car"])
        + Nl * (L["large"] + G["large"])
        + D
        + L[last_vehicle]
    )

    # ④ 加速度に基づく移動時間
    # s = 1/2 at^2 より t = sqrt(2s/a)
    time_move = np.sqrt(2 * distance / A[last_vehicle])

    # ⑤ 誤差 ε：-1秒〜1秒
    epsilon = np.random.uniform(-1, 1)

    # 最後尾車両が停止してから横断歩道を完全に通過するまでの時間
    T = time_first_start + time_queue + time_move + epsilon

    # 渋滞判定
    # T が青信号時間を超える場合、1回の青信号で捌ききれないので渋滞
    jam = T > JAM_THRESHOLD

    return {
        "N": N,
        "N_front": N_front,
        "Nb_bike": Nb,
        "Nc_car": Nc,
        "Nl_large": Nl,
        "last_vehicle": last_vehicle,
        "distance_m": distance,
        "T": T,
        "jam": jam
    }


# =====================
# 5. 複数回シミュレーション
# =====================
def run_simulation(day_type="weekday", hour=8, trials=1000):
    results = []

    for _ in range(trials):
        results.append(simulate_once(day_type, hour))

    return pd.DataFrame(results)


# =====================
# 6. 実行
# =====================
df = run_simulation(day_type="weekday", hour=8, trials=1000)

print(df.head())
print()
print("平均車両数 N:", df["N"].mean())
print("平均通過時間 T:", df["T"].mean())
print("渋滞発生率:", df["jam"].mean())


# =====================
# 7. グラフ1：NとTの関係
# =====================
plt.figure(figsize=(8, 5))
plt.scatter(df["N"], df["T"], alpha=0.5)
plt.axhline(JAM_THRESHOLD, linestyle="--", label="Jam threshold")
plt.xlabel("Number of vehicles N")
plt.ylabel("Passing time T (sec)")
plt.title("Relationship between N and congestion time")
plt.legend()
plt.grid(True)
plt.show()


# =====================
# 8. グラフ2：Nごとの平均T
# =====================
mean_by_N = df.groupby("N")["T"].mean()

plt.figure(figsize=(8, 5))
plt.plot(mean_by_N.index, mean_by_N.values, marker="o")
plt.axhline(JAM_THRESHOLD, linestyle="--", label="Jam threshold")
plt.xlabel("Number of vehicles N")
plt.ylabel("Average passing time T (sec)")
plt.title("Average passing time by number of vehicles")
plt.legend()
plt.grid(True)
plt.show()


# =====================
# 9. 時間帯別の渋滞率比較
# =====================
summary = []

for day_type in ["weekday", "weekend"]:
    for hour_label, hour in {
        "morning": 8,
        "daytime": 14,
        "night": 20,
        "midnight": 2
    }.items():
        temp = run_simulation(day_type=day_type, hour=hour, trials=1000)
        summary.append({
            "day_type": day_type,
            "time": hour_label,
            "avg_N": temp["N"].mean(),
            "avg_T": temp["T"].mean(),
            "jam_rate": temp["jam"].mean()
        })

summary_df = pd.DataFrame(summary)
print()
print(summary_df)
