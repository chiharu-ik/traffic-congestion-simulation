import streamlit as st
import numpy as np
import streamlit.components.v1 as components

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
# 2. 信号サイクル
# =========================

YELLOW = 5
RED = 40
L_clearance = YELLOW + RED
MAX_CAPACITY = 30

demand_rate = traffic_volume / MAX_CAPACITY
if demand_rate >= 1:
    demand_rate = 0.95

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

# =========================
# 3. 車両数
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
# 4. 車両特性
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

r1, r2, r3 = st.columns(3)
r1.metric("直進車", f"{N_straight} 台")
r2.metric("右折車", f"{N_right} 台")
r3.metric("左折車", f"{N_left} 台")

st.write("直進：右折：左折 ＝ 7：1：2 で固定")

# =========================
# 6. 右折条件
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

if opposite_distance >= RIGHT_TURN_SAFE_DISTANCE:
    right_turn_wait = 0.0
    can_turn_right = True
else:
    right_turn_wait = (RIGHT_TURN_SAFE_DISTANCE - opposite_distance) / opposite_speed
    can_turn_right = False

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
    return np.sqrt(2 * x / A[last_vehicle])

def calculate_turn_time(N_left, N_right, last_vehicle, right_turn_wait):
    turn_speed = TURN_SPEED[last_vehicle]

    left_turn_time = 0.0
    right_turn_time = 0.0

    if N_left > 0:
        left_turn_time = DECELERATION_DISTANCE / turn_speed

    if N_right > 0:
        right_turn_time = DECELERATION_DISTANCE / turn_speed + right_turn_wait

    return left_turn_time + right_turn_time

def calculate_T_sec(Nb, Nc, Nl, last_vehicle, N_left, N_right, right_turn_wait, epsilon=0):
    queue_time = (
        Nb * H["bike"]
        + Nc * H["car"]
        + Nl * H["large"]
    )

    move_time = calculate_move_time(Nb, Nc, Nl, last_vehicle)

    turn_time = calculate_turn_time(
        N_left,
        N_right,
        last_vehicle,
        right_turn_wait
    )

    return t0 + queue_time + move_time + turn_time + epsilon

T_list_min = []
jam_list = []

for _ in range(trials):
    epsilon = np.random.uniform(-3, 3)

    T_min = calculate_T_sec(
        Nb,
        Nc,
        Nl,
        last_vehicle,
        N_left,
        N_right,
        right_turn_wait,
        epsilon
    ) / 60

    T_list_min.append(T_min)
    jam_list.append(T_min > C_min)

avg_T_min = np.mean(T_list_min)
jam_rate = np.mean(jam_list)

# =========================
# 8. 結果表示
# =========================

st.subheader("シミュレーション結果")

m1, m2, m3, m4 = st.columns(4)

m1.metric("前方車両数 N", N)
m2.metric("平均通過時間 T", f"{avg_T_min:.2f} 分")
m3.metric("サイクル長 C", f"{C_min:.2f} 分")
m4.metric("渋滞率", f"{jam_rate * 100:.1f}%")

if avg_T_min > C_min:
    st.error("判定：渋滞が発生しやすい状態です。")
else:
    st.success("判定：1回の信号サイクル内で処理できる状態です。")

# =========================
# 9. HTML/CSS アニメーション
# =========================

st.subheader("交差点アニメーション")

if can_turn_right:
    animation_mode = "safe"
    st.write("対向車が50m以上離れているため、右折車は停止せずに右折します。")
else:
    animation_mode = "wait"
    st.write("対向車が50m以上離れていないため、右折車は一度停止し、後続車も追い越さずに待機します。")

right_car_class = "right-safe" if animation_mode == "safe" else "right-wait"

opposite_cars = ""
if animation_mode == "wait":
    opposite_cars = """
    <div class="car opposite opp1"></div>
    <div class="car opposite opp2"></div>
    <div class="car opposite opp3"></div>
    """
else:
    opposite_cars = """
    <div class="car opposite opp1"></div>
    """

html_code = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{
  margin: 0;
  padding: 0;
  background: white;
  font-family: sans-serif;
}}

.scene {{
  position: relative;
  width: 720px;
  height: 720px;
  margin: 0 auto;
  background: #f7f7f7;
  border-radius: 28px;
  overflow: hidden;
}}

.road-v {{
  position: absolute;
  left: 300px;
  top: 0;
  width: 120px;
  height: 720px;
  background: #d9d9d9;
}}

.road-h {{
  position: absolute;
  left: 0;
  top: 300px;
  width: 720px;
  height: 120px;
  background: #d9d9d9;
}}

.border-v-left {{
  position: absolute;
  left: 300px;
  top: 0;
  width: 3px;
  height: 720px;
  background: #6b3f1d;
}}

.border-v-right {{
  position: absolute;
  left: 420px;
  top: 0;
  width: 3px;
  height: 720px;
  background: #6b3f1d;
}}

.border-h-top {{
  position: absolute;
  left: 0;
  top: 300px;
  width: 720px;
  height: 3px;
  background: #6b3f1d;
}}

.border-h-bottom {{
  position: absolute;
  left: 0;
  top: 420px;
  width: 720px;
  height: 3px;
  background: #6b3f1d;
}}

.center-v {{
  position: absolute;
  left: 359px;
  top: 0;
  width: 4px;
  height: 720px;
  background: repeating-linear-gradient(
    to bottom,
    #6b3f1d 0px,
    #6b3f1d 28px,
    transparent 28px,
    transparent 58px
  );
}}

.center-h {{
  position: absolute;
  left: 0;
  top: 359px;
  width: 720px;
  height: 4px;
  background: repeating-linear-gradient(
    to right,
    #6b3f1d 0px,
    #6b3f1d 28px,
    transparent 28px,
    transparent 58px
  );
}}

.crosswalk-v-top,
.crosswalk-v-bottom,
.crosswalk-h-left,
.crosswalk-h-right {{
  position: absolute;
}}

.crosswalk-v-top {{
  left: 315px;
  top: 235px;
}}

.crosswalk-v-bottom {{
  left: 315px;
  top: 425px;
}}

.crosswalk-h-left {{
  left: 235px;
  top: 315px;
}}

.crosswalk-h-right {{
  left: 425px;
  top: 315px;
}}

.stripe-v {{
  position: absolute;
  width: 14px;
  height: 62px;
  background: white;
}}

.stripe-h {{
  position: absolute;
  width: 62px;
  height: 14px;
  background: white;
}}

.signal-own {{
  position: absolute;
  left: 435px;
  top: 435px;
  width: 32px;
  height: 78px;
  border-radius: 9px;
  background: #222;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-around;
  padding: 6px 0;
  box-sizing: border-box;
  z-index: 5;
}}

.signal-opp {{
  position: absolute;
  left: 250px;
  top: 205px;
  width: 32px;
  height: 78px;
  border-radius: 9px;
  background: #222;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-around;
  padding: 6px 0;
  box-sizing: border-box;
  z-index: 5;
}}

.light {{
  width: 17px;
  height: 17px;
  border-radius: 50%;
  background: #555;
}}

.light-red {{
  background: #e74c3c;
  box-shadow: 0 0 8px #e74c3c;
}}

.light-green {{
  background: #2ecc71;
  box-shadow: 0 0 8px #2ecc71;
}}

.car {{
  position: absolute;
  width: 32px;
  height: 56px;
  border-radius: 8px;
  border: 2px solid #333;
  box-sizing: border-box;
  color: white;
  font-weight: bold;
  text-align: center;
  line-height: 52px;
  font-size: 15px;
  z-index: 10;
  animation-duration: 16s;
  animation-timing-function: ease-in-out;
  animation-fill-mode: forwards;
}}

.blue {{
  background: #1f77b4;
}}

.red {{
  background: #d62728;
}}

.green {{
  background: #2ca02c;
}}

.opposite {{
  background: #9467bd;
}}

.note {{
  position: absolute;
  left: 24px;
  bottom: 20px;
  background: rgba(255,255,255,0.90);
  padding: 8px 12px;
  border-radius: 8px;
  color: #333;
  font-size: 14px;
  z-index: 20;
}}

/* 先頭の直進車3台 */
@keyframes straight1 {{
  0%   {{ left: 326px; top: 760px; transform: rotate(0deg); }}
  100% {{ left: 326px; top: -80px; transform: rotate(0deg); }}
}}

@keyframes straight2 {{
  0%   {{ left: 326px; top: 840px; transform: rotate(0deg); }}
  100% {{ left: 326px; top: -80px; transform: rotate(0deg); }}
}}

@keyframes straight3 {{
  0%   {{ left: 326px; top: 920px; transform: rotate(0deg); }}
  100% {{ left: 326px; top: -80px; transform: rotate(0deg); }}
}}

/* 右折車：安全時 */
@keyframes rightSafe {{
  0%   {{ left: 326px; top: 1000px; transform: rotate(0deg); }}
  45%  {{ left: 326px; top: 345px; transform: rotate(0deg); }}
  65%  {{ left: 420px; top: 330px; transform: rotate(90deg); }}
  100% {{ left: 760px; top: 330px; transform: rotate(90deg); }}
}}

/* 右折車：待機時 */
@keyframes rightWait {{
  0%   {{ left: 326px; top: 1000px; transform: rotate(0deg); }}
  32%  {{ left: 326px; top: 430px; transform: rotate(0deg); }}
  55%  {{ left: 326px; top: 430px; transform: rotate(0deg); }}
  75%  {{ left: 420px; top: 330px; transform: rotate(90deg); }}
  100% {{ left: 760px; top: 330px; transform: rotate(90deg); }}
}}

/* 後続車：右折車の後ろで待ってから進む */
@keyframes queueStraight {{
  0%   {{ left: 326px; top: 1080px; transform: rotate(0deg); }}
  34%  {{ left: 326px; top: 505px; transform: rotate(0deg); }}
  58%  {{ left: 326px; top: 505px; transform: rotate(0deg); }}
  100% {{ left: 326px; top: -80px; transform: rotate(0deg); }}
}}

@keyframes queueLeft1 {{
  0%   {{ left: 326px; top: 1160px; transform: rotate(0deg); }}
  36%  {{ left: 326px; top: 585px; transform: rotate(0deg); }}
  60%  {{ left: 326px; top: 585px; transform: rotate(0deg); }}
  78%  {{ left: 326px; top: 350px; transform: rotate(0deg); }}
  90%  {{ left: 250px; top: 350px; transform: rotate(-90deg); }}
  100% {{ left: -80px; top: 350px; transform: rotate(-90deg); }}
}}

@keyframes queueLeft2 {{
  0%   {{ left: 326px; top: 1240px; transform: rotate(0deg); }}
  38%  {{ left: 326px; top: 665px; transform: rotate(0deg); }}
  62%  {{ left: 326px; top: 665px; transform: rotate(0deg); }}
  80%  {{ left: 326px; top: 350px; transform: rotate(0deg); }}
  92%  {{ left: 250px; top: 350px; transform: rotate(-90deg); }}
  100% {{ left: -80px; top: 350px; transform: rotate(-90deg); }}
}}

/* 後ろの直進車 */
@keyframes afterStraight1 {{
  0%   {{ left: 326px; top: 1320px; transform: rotate(0deg); }}
  55%  {{ left: 326px; top: 760px; transform: rotate(0deg); }}
  100% {{ left: 326px; top: -80px; transform: rotate(0deg); }}
}}

@keyframes afterStraight2 {{
  0%   {{ left: 326px; top: 1400px; transform: rotate(0deg); }}
  60%  {{ left: 326px; top: 760px; transform: rotate(0deg); }}
  100% {{ left: 326px; top: -80px; transform: rotate(0deg); }}
}}

@keyframes afterStraight3 {{
  0%   {{ left: 326px; top: 1480px; transform: rotate(0deg); }}
  65%  {{ left: 326px; top: 760px; transform: rotate(0deg); }}
  100% {{ left: 326px; top: -80px; transform: rotate(0deg); }}
}}

/* 対向車：右折車が動く前に通過し終える */
@keyframes oppositeMove {{
  0%   {{ left: 365px; top: -80px; transform: rotate(180deg); }}
  100% {{ left: 365px; top: 760px; transform: rotate(180deg); }}
}}

.s1 {{ animation-name: straight1; animation-delay: 0s; }}
.s2 {{ animation-name: straight2; animation-delay: 0.7s; }}
.s3 {{ animation-name: straight3; animation-delay: 1.4s; }}

.right-safe {{ animation-name: rightSafe; animation-delay: 2.1s; }}
.right-wait {{ animation-name: rightWait; animation-delay: 2.1s; }}

.qs {{ animation-name: queueStraight; animation-delay: 2.1s; }}
.ql1 {{ animation-name: queueLeft1; animation-delay: 2.1s; }}
.ql2 {{ animation-name: queueLeft2; animation-delay: 2.1s; }}

.as1 {{ animation-name: afterStraight1; animation-delay: 2.1s; }}
.as2 {{ animation-name: afterStraight2; animation-delay: 2.1s; }}
.as3 {{ animation-name: afterStraight3; animation-delay: 2.1s; }}

.opp1 {{ animation-name: oppositeMove; animation-delay: 0s; animation-duration: 5s; }}
.opp2 {{ animation-name: oppositeMove; animation-delay: 1.4s; animation-duration: 5s; }}
.opp3 {{ animation-name: oppositeMove; animation-delay: 2.8s; animation-duration: 5s; }}

</style>
</head>

<body>
<div class="scene">

  <div class="road-v"></div>
  <div class="road-h"></div>

  <div class="border-v-left"></div>
  <div class="border-v-right"></div>
  <div class="border-h-top"></div>
  <div class="border-h-bottom"></div>

  <div class="center-v"></div>
  <div class="center-h"></div>

  <div class="crosswalk-v-top">
    <div class="stripe-v" style="left:0px;"></div>
    <div class="stripe-v" style="left:32px;"></div>
    <div class="stripe-v" style="left:64px;"></div>
    <div class="stripe-v" style="left:96px;"></div>
    <div class="stripe-v" style="left:128px;"></div>
  </div>

  <div class="crosswalk-v-bottom">
    <div class="stripe-v" style="left:0px;"></div>
    <div class="stripe-v" style="left:32px;"></div>
    <div class="stripe-v" style="left:64px;"></div>
    <div class="stripe-v" style="left:96px;"></div>
    <div class="stripe-v" style="left:128px;"></div>
  </div>

  <div class="crosswalk-h-left">
    <div class="stripe-h" style="top:0px;"></div>
    <div class="stripe-h" style="top:32px;"></div>
    <div class="stripe-h" style="top:64px;"></div>
    <div class="stripe-h" style="top:96px;"></div>
    <div class="stripe-h" style="top:128px;"></div>
  </div>

  <div class="crosswalk-h-right">
    <div class="stripe-h" style="top:0px;"></div>
    <div class="stripe-h" style="top:32px;"></div>
    <div class="stripe-h" style="top:64px;"></div>
    <div class="stripe-h" style="top:96px;"></div>
    <div class="stripe-h" style="top:128px;"></div>
  </div>

  <div class="signal-own">
    <div class="light"></div>
    <div class="light"></div>
    <div class="light light-green"></div>
  </div>

  <div class="signal-opp">
    <div class="light light-red"></div>
    <div class="light"></div>
    <div class="light"></div>
  </div>

  {opposite_cars}

  <div class="car blue s1"></div>
  <div class="car blue s2"></div>
  <div class="car blue s3"></div>

  <div class="car red {right_car_class}">R</div>

  <div class="car blue qs"></div>
  <div class="car green ql1">L</div>
  <div class="car green ql2">L</div>

  <div class="car blue as1"></div>
  <div class="car blue as2"></div>
  <div class="car blue as3"></div>

  <div class="note">
    片側1車線：右折車が停止すると後続車も停止する
  </div>

</div>
</body>
</html>
"""

components.html(html_code, height=760)
