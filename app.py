import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

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

def calc_signal_cycle(q):
    demand_rate = q / MAX_CAPACITY

    if demand_rate >= 1:
        demand_rate = 0.95

    C_sec = (1.5 * L_clearance + 5) / (1 - demand_rate)
    C_min = C_sec / 60

    GREEN_sec = C_sec - L_clearance
    GREEN_min = GREEN_sec / 60

    return demand_rate, C_sec, C_min, GREEN_sec, GREEN_min

demand_rate, C_sec, C_min, GREEN_sec, GREEN_min = calc_signal_cycle(traffic_volume)

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
# 5. 直進・右折・左折
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
OPPOSITE_SPEED = 10.0

st.write("左折車・右折車は、交差点の20m手前から減速するものとする。")
st.write("右折車は、対向車が信号から50m以上離れている場合に右折可能とする。")
st.write("右折条件の基準値：50m、対向車が離れていく速度：10m/s")

opposite_distance = st.slider(
    "シミュレーション上の対向車距離（m）",
    0,
    100,
    40
)

def calc_right_turn_wait(distance):
    if distance >= RIGHT_TURN_SAFE_DISTANCE:
        return 0.0, True
    else:
        wait = (RIGHT_TURN_SAFE_DISTANCE - distance) / OPPOSITE_SPEED
        return wait, False

right_turn_wait, can_turn_right = calc_right_turn_wait(opposite_distance)

if can_turn_right:
    st.success("右折可能：対向車が50m以上離れています。")
else:
    st.warning(f"右折待ち：対向車が50m以上離れるまで約 {right_turn_wait:.1f} 秒待ちます。")

# =========================
# 7. 通過時間の計算
# =========================

trials = st.slider("試行回数", 100, 5000, 1000)

def calculate_move_time(nb, nc, nl, last_vehicle_type):
    x = (
        nb * (L["bike"] + G["bike"])
        + nc * (L["car"] + G["car"])
        + nl * (L["large"] + G["large"])
        + D
        + L[last_vehicle_type]
    )

    move_time = np.sqrt(2 * x / A[last_vehicle_type])
    return move_time

def calculate_phase_times(nb, nc, nl, last_vehicle_type, n_left, n_right, right_wait):
    reaction_time = t0

    queue_time = (
        nb * H["bike"]
        + nc * H["car"]
        + nl * H["large"]
    )

    move_time = calculate_move_time(nb, nc, nl, last_vehicle_type)

    turn_speed = TURN_SPEED[last_vehicle_type]

    left_turn_time = 0.0
    right_turn_time = 0.0

    if n_left > 0:
        left_turn_time = DECELERATION_DISTANCE / turn_speed

    if n_right > 0:
        right_turn_time = DECELERATION_DISTANCE / turn_speed + right_wait

    total_without_error = (
        reaction_time
        + queue_time
        + move_time
        + left_turn_time
        + right_turn_time
    )

    return {
        "reaction_time": reaction_time,
        "queue_time": queue_time,
        "move_time": move_time,
        "left_turn_time": left_turn_time,
        "right_turn_time": right_turn_time,
        "total": total_without_error
    }

def calculate_result(nb, nc, nl, last_vehicle_type, q, opposite_distance_case, trials=1000):
    n = nb + nc + nl

    n_straight = round(n * STRAIGHT_RATIO)
    n_right = round(n * RIGHT_RATIO)
    n_left = n - n_straight - n_right

    dr, C_s, C_m, G_s, G_m = calc_signal_cycle(q)

    wait, can_turn = calc_right_turn_wait(opposite_distance_case)

    phase = calculate_phase_times(
        nb,
        nc,
        nl,
        last_vehicle_type,
        n_left,
        n_right,
        wait
    )

    T_list = []
    jam_list = []

    for _ in range(trials):
        epsilon = np.random.uniform(-3, 3)
        T_sec = phase["total"] + epsilon
        T_min = T_sec / 60
        T_list.append(T_min)
        jam_list.append(T_min > C_m)

    avg_T_min = np.mean(T_list)
    jam_rate = np.mean(jam_list)

    return {
        "N": n,
        "N_straight": n_straight,
        "N_right": n_right,
        "N_left": n_left,
        "demand_rate": dr,
        "C_min": C_m,
        "T_min": avg_T_min,
        "jam_rate": jam_rate,
        "phase": phase,
        "right_wait": wait,
        "can_turn": can_turn
    }

result = calculate_result(
    Nb,
    Nc,
    Nl,
    last_vehicle,
    traffic_volume,
    opposite_distance,
    trials
)

# =========================
# 8. 結果表示
# =========================

st.subheader("シミュレーション結果")

r1, r2, r3, r4 = st.columns(4)

r1.metric("前方車両数 N", result["N"])
r2.metric("平均通過時間 T", f"{result['T_min']:.2f} 分")
r3.metric("サイクル長 C", f"{result['C_min']:.2f} 分")
r4.metric("渋滞率", f"{result['jam_rate'] * 100:.1f}%")

if result["T_min"] > result["C_min"]:
    st.error("判定：1回の信号サイクル内で処理しきれない状態です。")
else:
    st.success("判定：1回の信号サイクル内で処理できる状態です。")

# =========================
# 9. 通過時間の内訳
# =========================

st.subheader("通過時間の内訳")

phase = result["phase"]

phase_df = pd.DataFrame([
    {"項目": "反応時間", "時間（秒）": round(phase["reaction_time"], 2)},
    {"項目": "発進待ち時間", "時間（秒）": round(phase["queue_time"], 2)},
    {"項目": "移動時間", "時間（秒）": round(phase["move_time"], 2)},
    {"項目": "左折による減速時間", "時間（秒）": round(phase["left_turn_time"], 2)},
    {"項目": "右折による待ち・減速時間", "時間（秒）": round(phase["right_turn_time"], 2)},
    {"項目": "合計", "時間（秒）": round(phase["total"], 2)},
])

st.dataframe(phase_df, use_container_width=True)

# =========================
# 10. 渋滞グラフ：前方車両数 N と通過時間 T
# =========================

st.subheader("渋滞グラフ：前方車両数 N と通過時間 T")

st.write("現在の車種構成比を保ったまま、前方車両数 N を変化させた場合の通過時間 T を表示します。")

max_N = st.slider("グラフに表示する最大車両数 N", 20, 200, 120)

N_values = np.arange(1, max_N + 1)
T_values = []
jam_flags = []

total_now = max(N, 1)

bike_ratio = Nb / total_now
car_ratio = Nc / total_now
large_ratio = Nl / total_now

for n_case in N_values:
    nb_case = round(n_case * bike_ratio)
    nc_case = round(n_case * car_ratio)
    nl_case = n_case - nb_case - nc_case

    case_result = calculate_result(
        nb_case,
        nc_case,
        nl_case,
        last_vehicle,
        traffic_volume,
        opposite_distance,
        trials=300
    )

    T_values.append(case_result["T_min"])
    jam_flags.append(case_result["T_min"] > case_result["C_min"])

fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(N_values, T_values, linewidth=2, label="Passing time T")
ax.axhline(result["C_min"], linestyle="--", linewidth=2, label="Cycle length C")

ax.set_xlabel("Number of vehicles N")
ax.set_ylabel("Time min")
ax.set_title("Relationship between N and passing time")
ax.grid(True)
ax.legend()

st.pyplot(fig)
plt.close(fig)

# =========================
# 11. パラメータ変更による比較
# =========================

st.subheader("パラメータ変更による比較")

st.write("横軸にするパラメータを選び、その値を変えたときの渋滞率を確認します。")

parameter = st.selectbox(
    "変化させるパラメータ",
    ["前方車両数 N", "大型車台数", "対向車距離", "交通量"]
)

x_values = []
jam_rates = []
T_compare = []
C_compare = []

if parameter == "前方車両数 N":
    x_values = list(range(5, 121, 5))

    for n_case in x_values:
        nb_case = round(n_case * bike_ratio)
        nc_case = round(n_case * car_ratio)
        nl_case = n_case - nb_case - nc_case

        case = calculate_result(
            nb_case,
            nc_case,
            nl_case,
            last_vehicle,
            traffic_volume,
            opposite_distance,
            trials=500
        )

        jam_rates.append(case["jam_rate"] * 100)
        T_compare.append(case["T_min"])
        C_compare.append(case["C_min"])

elif parameter == "大型車台数":
    x_values = list(range(0, 41, 2))

    base_nb = Nb
    base_total = max(N, 1)

    for nl_case in x_values:
        nc_case = max(base_total - base_nb - nl_case, 0)
        nb_case = base_nb

        case = calculate_result(
            nb_case,
            nc_case,
            nl_case,
            last_vehicle,
            traffic_volume,
            opposite_distance,
            trials=500
        )

        jam_rates.append(case["jam_rate"] * 100)
        T_compare.append(case["T_min"])
        C_compare.append(case["C_min"])

elif parameter == "対向車距離":
    x_values = list(range(0, 101, 5))

    for dist_case in x_values:
        case = calculate_result(
            Nb,
            Nc,
            Nl,
            last_vehicle,
            traffic_volume,
            dist_case,
            trials=500
        )

        jam_rates.append(case["jam_rate"] * 100)
        T_compare.append(case["T_min"])
        C_compare.append(case["C_min"])

elif parameter == "交通量":
    x_values = list(range(1, 31, 1))

    for q_case in x_values:
        case = calculate_result(
            Nb,
            Nc,
            Nl,
            last_vehicle,
            q_case,
            opposite_distance,
            trials=500
        )

        jam_rates.append(case["jam_rate"] * 100)
        T_compare.append(case["T_min"])
        C_compare.append(case["C_min"])

fig2, ax2 = plt.subplots(figsize=(10, 5))

ax2.plot(x_values, jam_rates, linewidth=2, marker="o")
ax2.set_xlabel(parameter)
ax2.set_ylabel("Jam rate percent")
ax2.set_title("Parameter sensitivity")
ax2.grid(True)

st.pyplot(fig2)
plt.close(fig2)

compare_df = pd.DataFrame({
    parameter: x_values,
    "渋滞率（%）": [round(v, 1) for v in jam_rates],
    "通過時間 T（分）": [round(v, 2) for v in T_compare],
    "サイクル長 C（分）": [round(v, 2) for v in C_compare],
})

st.dataframe(compare_df, use_container_width=True)

# =========================
# 12. 曜日・時間帯別の比較
# =========================

st.subheader("曜日・時間帯別の比較")

scenario_rows = []

for d_type, time_dict in traffic_table.items():
    for t_zone, q_case in time_dict.items():
        case = calculate_result(
            Nb,
            Nc,
            Nl,
            last_vehicle,
            q_case,
            opposite_distance,
            trials=500
        )

        scenario_rows.append({
            "曜日": d_type,
            "時間帯": t_zone,
            "交通量（台/分）": q_case,
            "需要率 λ": round(case["demand_rate"], 2),
            "通過時間 T（分）": round(case["T_min"], 2),
            "サイクル長 C（分）": round(case["C_min"], 2),
            "渋滞率（%）": round(case["jam_rate"] * 100, 1)
        })

scenario_df = pd.DataFrame(scenario_rows)
st.dataframe(scenario_df, use_container_width=True)
