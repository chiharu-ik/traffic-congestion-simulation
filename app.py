# =========================
# 9. 交差点アニメーション
# =========================

def draw_road(ax):
    ax.set_xlim(-6, 6)
    ax.set_ylim(-6, 6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor("white")

    road_color = "#d9d9d9"
    line_color = "#6b3f1d"

    # 道路
    ax.add_patch(Rectangle((-1.2, -6), 2.4, 12, facecolor=road_color, edgecolor="none"))
    ax.add_patch(Rectangle((-6, -1.2), 12, 2.4, facecolor=road_color, edgecolor="none"))

    # 外枠
    ax.plot([-1.2, -1.2], [-6, -1.2], color=line_color, linewidth=1.5)
    ax.plot([1.2, 1.2], [-6, -1.2], color=line_color, linewidth=1.5)
    ax.plot([-1.2, -1.2], [1.2, 6], color=line_color, linewidth=1.5)
    ax.plot([1.2, 1.2], [1.2, 6], color=line_color, linewidth=1.5)

    ax.plot([-6, -1.2], [1.2, 1.2], color=line_color, linewidth=1.5)
    ax.plot([-6, -1.2], [-1.2, -1.2], color=line_color, linewidth=1.5)
    ax.plot([1.2, 6], [1.2, 1.2], color=line_color, linewidth=1.5)
    ax.plot([1.2, 6], [-1.2, -1.2], color=line_color, linewidth=1.5)

    # 中央線
    ax.plot([0, 0], [-6, -1.5], color=line_color, linestyle=(0, (5, 5)), linewidth=1.3)
    ax.plot([0, 0], [1.5, 6], color=line_color, linestyle=(0, (5, 5)), linewidth=1.3)
    ax.plot([-6, -1.5], [0, 0], color=line_color, linestyle=(0, (5, 5)), linewidth=1.3)
    ax.plot([1.5, 6], [0, 0], color=line_color, linestyle=(0, (5, 5)), linewidth=1.3)

    # 横断歩道
    for x in [-0.75, -0.35, 0.05, 0.45, 0.85]:
        ax.add_patch(Rectangle((x, -2.0), 0.18, 1.0, facecolor="white", edgecolor="none"))
        ax.add_patch(Rectangle((x, 1.0), 0.18, 1.0, facecolor="white", edgecolor="none"))

    for y in [-0.85, -0.45, -0.05, 0.35, 0.75]:
        ax.add_patch(Rectangle((-2.0, y), 1.0, 0.18, facecolor="white", edgecolor="none"))
        ax.add_patch(Rectangle((1.0, y), 1.0, 0.18, facecolor="white", edgecolor="none"))


def draw_car(ax, x, y, direction, color, label=None):
    if direction in ["up", "down"]:
        w, h = 0.34, 0.62
    else:
        w, h = 0.62, 0.34

    car = FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.06",
        facecolor=color,
        edgecolor="#333333",
        linewidth=0.8
    )
    ax.add_patch(car)

    if label:
        ax.text(x, y, label, color="white", ha="center", va="center", fontsize=7)


def car_position_by_route(route, p):
    """
    片側1車線なので、全車両は同じ車線 x=-0.45 を進む。
    交差点内に入ってから、直進・右折・左折に分かれる。
    """

    # 直進
    if route == "S":
        x = -0.45
        y = -5.4 + 10.8 * p
        direction = "up"
        return x, y, direction

    # 左折
    if route == "L":
        if p < 0.58:
            x = -0.45
            y = -5.4 + 5.4 * (p / 0.58)
            direction = "up"
        else:
            q = (p - 0.58) / 0.42
            x = -0.45 - 4.8 * q
            y = -0.45
            direction = "left"
        return x, y, direction

    # 右折
    if route == "R":
        if p < 0.58:
            x = -0.45
            y = -5.4 + 5.4 * (p / 0.58)
            direction = "up"
        else:
            q = (p - 0.58) / 0.42
            x = -0.45 + 4.8 * q
            y = 0.45
            direction = "right"
        return x, y, direction


def stopped_position(index):
    """
    右折車が止まったとき、後続車は同じ車線上で後ろに並ぶ。
    """
    x = -0.45
    y = -1.25 - index * 0.75
    return x, y, "up"


def draw_animation(can_turn_right):
    st.subheader("交差点アニメーション")
    st.write("片側1車線のため、右折車が停止すると後続車も追い越さずに待機します。")

    placeholder = st.empty()

    # 直進7：右折1：左折2
    # 右折車を途中に置くことで、右折待ちが後続車に影響する様子を出す
    routes = ["S", "S", "S", "R", "L", "L", "S", "S", "S", "S"]

    colors = {
        "S": "#1f77b4",
        "R": "#d62728",
        "L": "#2ca02c",
        "opposite": "#9467bd",
    }

    total_steps = 190
    start_interval = 16
    move_duration = 90

    right_index = routes.index("R")
    waiting_frames = 55 if not can_turn_right else 0

    for step in range(total_steps):
        fig, ax = plt.subplots(figsize=(6, 6))
        draw_road(ax)

        # 対向車線：上から下へ複数台走らせる
        for j in range(5):
            p_opp = ((step - j * 28) % total_steps) / total_steps
            x_opp = 0.45
            y_opp = 5.4 - 10.8 * p_opp
            draw_car(ax, x_opp, y_opp, "down", colors["opposite"])

        # 自車線：全車両が同じ車線を順番に進む
        for i, route in enumerate(routes):
            start = i * start_interval

            # 右折車より後ろの車は、右折待ちの分だけ遅れる
            if i > right_index:
                start += waiting_frames

            # 右折車が右折不可の場合、一度停止する
            if i == right_index and not can_turn_right:
                stop_start = start + 38
                stop_end = stop_start + waiting_frames

                if step < start:
                    continue

                elif start <= step < stop_start:
                    p = (step - start) / move_duration
                    x, y, d = car_position_by_route(route, p)
                    draw_car(ax, x, y, d, colors[route], route)

                elif stop_start <= step < stop_end:
                    x, y, d = -0.45, -1.25, "up"
                    draw_car(ax, x, y, d, colors[route], route)

                else:
                    p = (step - start - waiting_frames) / move_duration
                    if 0 <= p <= 1:
                        x, y, d = car_position_by_route(route, p)
                        draw_car(ax, x, y, d, colors[route], route)

            else:
                p = (step - start) / move_duration

                if 0 <= p <= 1:
                    x, y, d = car_position_by_route(route, p)

                    # 右折車が止まっている間、後続車は後ろに並ぶ
                    if not can_turn_right and i > right_index:
                        stop_start = right_index * start_interval + 38
                        stop_end = stop_start + waiting_frames

                        if stop_start <= step < stop_end:
                            queue_order = i - right_index
                            x, y, d = stopped_position(queue_order)

                    draw_car(ax, x, y, d, colors[route], route if route != "S" else None)

        ax.set_title("Straight : Right : Left = 7 : 1 : 2", fontsize=12)

        placeholder.pyplot(fig)
        plt.close(fig)
        time.sleep(0.04)


if st.button("交差点の動きを表示"):
    draw_animation(can_turn_right)
