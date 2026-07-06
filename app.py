import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform

# 🎨 OSごとの日本語フォント自動設定（PC環境でのエラー・文字化け対策）
os_name = platform.system()
if os_name == "Windows":
    plt.rcParams['font.family'] = 'MS Gothic'
elif os_name == "Darwin":  # Mac
    plt.rcParams['font.family'] = 'AppleGothic'
else:  # Linux (Colab等用バックアップ)
    try:
        font_path = '/usr/share/fonts/truetype/fonts-ipafont-gothic/ipag.ttf'
        font_prop = fm.FontProperties(fname=font_path)
        plt.rcParams['font.family'] = font_prop.get_name()
    except:
        pass

# 🌐 画面の基本設定
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

def calc_signal_cycle(traffic_volume):
    demand_rate = traffic_volume / MAX_CAPACITY

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
# 3. 前方車両数の設定
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
# 5. 直進・右折・左折の固定割合
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

st.write("左折車・右折車は、交差点の20m手前から減速するものとする。")
st.write("右折車は、対向車が信号から50m以上離れている場合に右折可能とする。")

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

def calc_right_turn_wait(opposite_distance, opposite_speed):
    if opposite_distance >= RIGHT_TURN_SAFE_DISTANCE:
        return 0.0, True
    else:
        wait = (RIGHT_TURN_SAFE_DISTANCE - opposite_distance) / opposite_speed
        return wait, False

right_turn_wait, can_turn_right = calc_right_turn_wait(opposite_distance, opposite_speed)

if can_turn_right:
    st.success("右折可能：対向車が50m以上離れています。")
else:
    st.warning(f"右折待ち：対向車が50m以上離れるまで約 {right_turn_wait:.1f} 秒待ちます。")

# =========================
# 7. 通過時間の計算
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


def calculate_phase_times(Nb, Nc, Nl, last_vehicle, N_left, N_right, right_turn_wait):
    reaction_time = t0

    queue_time = (
        Nb * H["bike"]
        + Nc * H["car"]
        + Nl * H["large"]
    )

    move_time = calculate_move_time(Nb, Nc, Nl, last_vehicle)

    turn_speed = TURN_SPEED[last_vehicle]

    left_turn_time = 0.0
    right_turn_time = 0.0

    if N_left > 0:
        left_turn_time = DECELERATION_DISTANCE / turn_speed

    if N_right > 0:
        right_turn_time = DECELERATION_DISTANCE / turn_speed + right_turn_wait

    total_without_error = (
        reaction_time
        + queue_time
        + move_time
        + left_turn_time
        + right_turn_time
    )

    return {
        "反応時間": reaction_time,
        "発進待ち時間": queue_time,
        "移動時間": move_time,
        "左折による減速時間": left_turn_time,
        "右折による待ち・減速時間": right_turn_time,
        "合計": total_without_error
    }


phase_times = calculate_phase_times(
    Nb,
    Nc,
    Nl,
    last_vehicle,
    N_left,
    N_right,
    right_turn_wait
)

T_list_min = []
jam_list = []

for _ in range(trials):
    epsilon = np.random.uniform(-3, 3)
    T_sec = phase_times["合計"] + epsilon
    T_min = T_sec / 60

    T_list_min.append(T_min)
    jam_list.append(T_min > C_min)

avg_T_min = np.mean(T_list_min)
jam_rate = np.mean(jam_list)
risk_ratio = avg_T_min / C_min

# =========================
# 8. 結果表示
# =========================
st.subheader("シミュレーション結果")

r1, r2, r3, r4 = st.columns(4)

r1.metric("前方車両数 N", f"{N} 台")
r2.metric("平均通過時間 T", f"{avg_T_min:.2f} 分")
r3.metric("サイクル長 C", f"{C_min:.2f} 分")
r4.metric("渋滞率", f"{jam_rate * 100:.1f}%")

if avg_T_min > C_min:
    st.error("判定：渋滞が発生しやすい状態です。")
else:
    st.success("判定：1回の信号サイクル内で処理できる状態です。")

# =========================
# 9. 渋滞につながりやすい要因
# =========================
st.subheader("渋滞につながりやすい要因")

factor_rows = []

large_ratio = Nl / N if N > 0 else 0
right_ratio_actual = N_right / N if N > 0 else 0

if demand_rate >= 0.45:
    factor_rows.append({
        "要因": "交通量が多い",
        "現在の状態": f" need λ = {demand_rate:.2f}",
        "渋滞につながる理由": "信号1サイクルで処理すべき車両が多くなり、余裕が小さくなるため"
    })

if N >= 40:
    factor_rows.append({
        "要因": "前方車両数が多い",
        "現在の状態": f"N = {N} 台",
        "渋滞につながる理由": "発進待ち時間が長くなり、最後尾車両の通過時間が大きくなるため"
    })

if large_ratio >= 0.25:
    factor_rows.append({
        "要因": "大型車の割合が高い",
        "現在の状態": f"{large_ratio * 100:.1f}%",
        "渋滞につながる理由": "大型車は車長・車間距離・発車間隔が大きく、車列全体の通過時間を伸ばすため"
    })

if right_turn_wait > 0:
    factor_rows.append({
        "要因": "右折待ちが発生している",
        "現在の状態": f"{right_turn_wait:.1f} 秒",
        "渋滞につながる理由": "片側1車線では右折車が停止すると、後続車も追い越せず待機するため"
    })

if N_right > 0:
    factor_rows.append({
        "要因": "右折車が含まれている",
        "現在の状態": f"{N_right} 台",
        "渋滞につながる理由": "右折車は対向車の影響を受けるため、直進車より通過時間が不安定になりやすいため"
    })

if phase_times["発進待ち時間"] >= 60:
    factor_rows.append({
        "要因": "発進待ち時間が長い",
        "現在の状態": f"{phase_times['発進待ち時間']:.1f} 秒",
        "渋滞につながる理由": "前の車が順番に発進するまで最後尾車両が動けないため"
    })

if not factor_rows:
    factor_rows.append({
        "要因": "大きな渋滞要因は小さい",
        "現在の状態": "現在の設定では余裕あり",
        "渋滞につながる理由": "通過時間が信号サイクル長を下回っているため"
    })

st.dataframe(pd.DataFrame(factor_rows), use_container_width=True)

# =========================
# 10. 時間の内訳
# =========================
st.subheader("通過時間の内訳")

phase_df = pd.DataFrame([
    {"項目": "反応時間", "時間（秒）": phase_times["反応時間"]},
    {"項目": "発進待ち時間", "時間（秒）": phase_times["発進待ち時間"]},
    {"項目": "移動時間", "時間（秒）": phase_times["移動時間"]},
    {"項目": "左折による減速時間", "時間（秒）": phase_times["左折による減速時間"]},
    {"項目": "右折による待ち・減速時間", "時間（秒）": phase_times["右折による待ち・減速時間"]},
    {"項目": "合計", "時間（秒）": phase_times["合計"]},
])

st.dataframe(phase_df, use_container_width=True)

# =========================
# 11. 曜日・時間帯別の渋滞リスク比較
# =========================
st.subheader("曜日・時間帯別の渋滞リスク比較")

scenario_rows = []

for d_type, times in traffic_table.items():
    for t_zone, q in times.items():
        dr, C_s, C_m, G_s, G_m = calc_signal_cycle(q)

        T_min_base = phase_times["合計"] / 60
        risk = T_min_base / C_m

        if risk >= 1:
            level = "高"
        elif risk >= 0.8:
            level = "中"
        else:
            level = "低"

        scenario_rows.append({
            "曜日": d_type,
            "時間帯": t_zone,
            "交通量（台/分）": q,
            "需要率 λ": round(dr, 2),
            "サイクル長 C（分）": round(C_m, 2),
            "通過時間 T（分）": round(T_min_base, 2),
            "T/C": round(risk, 2),
            "渋滞リスク": level
        })

scenario_df = pd.DataFrame(scenario_rows)
scenario_df = scenario_df.sort_values("T/C", ascending=False)

st.dataframe(scenario_df, use_container_width=True)

# =========================
# 12. 右折待ちの影響
# =========================
st.subheader("対向車距離による右折待ちリスク")

distance_rows = []

for dist in [0, 10, 20, 30, 40, 50, 60, 80, 100]:
    wait, can_turn = calc_right_turn_wait(dist, opposite_speed)

    phase = calculate_phase_times(
        Nb,
        Nc,
        Nl,
        last_vehicle,
        N_left,
        N_right,
        wait
    )

    T_min_case = phase["合計"] / 60
    risk = T_min_case / C_min

    if risk >= 1:
        level = "高"
    elif risk >= 0.8:
        level = "中"
    else:
        level = "低"

    distance_rows.append({
        "対向車距離（m）": dist,
        "右折可能か": "可能" if can_turn else "待機",
        "右折待ち時間（秒）": round(wait, 1),
        "通過時間 T（分）": round(T_min_case, 2),
        "T/C": round(risk, 2),
        "渋滞リスク": level
    })

distance_df = pd.DataFrame(distance_rows)

st.dataframe(distance_df, use_container_width=True)
