import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path

# ========== 设置中文字体 ==========
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Zen Hei']
plt.rcParams['axes.unicode_minus'] = False

# ================== 物理计算 ==================
def compute_trajectory(M, m, a, b):
    X0 = m * a / (M + m)
    A = M * a / (M + m)
    phi_forward = np.linspace(2*np.pi, np.pi, 100)
    phi_back = np.linspace(np.pi, 2*np.pi, 100)
    phi_frames = np.concatenate([phi_forward, phi_back])
    x_ball = X0 + A * np.cos(phi_frames)
    y_ball = b * np.sin(phi_frames)
    groove_center_x = m * (a - x_ball) / M
    return x_ball, y_ball, groove_center_x, X0, A

# ================== 凹槽形状 ==================
def create_groove_path(cx, a, b, base_height=0.3):
    x_left = cx - a
    x_right = cx + a
    y_bottom = -b - base_height
    verts = []
    codes = []
    verts.append((x_left, y_bottom))
    codes.append(Path.MOVETO)
    verts.append((x_right, y_bottom))
    codes.append(Path.LINETO)
    verts.append((x_right, 0))
    codes.append(Path.LINETO)
    theta = np.linspace(2*np.pi, np.pi, 50)
    x_arc = cx + a * np.cos(theta)
    y_arc = b * np.sin(theta)
    for i in range(1, len(theta)-1):
        verts.append((x_arc[i], y_arc[i]))
        codes.append(Path.LINETO)
    verts.append((x_left, 0))
    codes.append(Path.LINETO)
    verts.append((x_left, y_bottom))
    codes.append(Path.CLOSEPOLY)
    return Path(verts, codes)

# ================== 坐标系（刻度单侧） ==================
def draw_fixed_coordinate_system(ax, x_range, y_range, tick_step=0.5):
    xmin, xmax = x_range
    ymin, ymax = y_range
    # X轴（带箭头）
    ax.arrow(xmin, 0, xmax - xmin - 0.2, 0, head_width=0.08, head_length=0.12,
             fc='black', ec='black', length_includes_head=True, lw=1, zorder=10)
    # Y轴（带箭头）
    ax.arrow(0, ymin, 0, ymax - ymin - 0.2, head_width=0.08, head_length=0.12,
             fc='black', ec='black', length_includes_head=True, lw=1, zorder=10)
    # X轴刻度：只画在上方
    xticks = np.arange(np.ceil(xmin / tick_step) * tick_step, xmax, tick_step)
    for x in xticks:
        if abs(x) < 1e-6:
            continue
        ax.plot([x, x], [0, 0.08], 'k-', lw=0.5, zorder=10)
    # Y轴刻度：只画在右侧
    yticks = np.arange(np.ceil(ymin / tick_step) * tick_step, ymax, tick_step)
    for y in yticks:
        if abs(y) < 1e-6:
            continue
        ax.plot([0, 0.08], [y, y], 'k-', lw=0.5, zorder=10)

# ================== Streamlit 界面 ==================
st.set_page_config(layout="wide")
st.title("半椭圆轨道凹槽模拟器")

# 侧边栏参数调节
with st.sidebar:
    st.header("参数调节")
    M = st.slider("凹槽质量 M", 0.2, 5.0, 1.0, 0.01)
    m = st.slider("小球质量 m", 0.2, 5.0, 1.0, 0.01)
    a = st.slider("半长轴 a", 1.0, 4.0, 2.0, 0.01)
    b = st.slider("半短轴 b", 0.5, 2.5, 1.0, 0.01)
    offset = st.slider("手动水平偏移", -3.0, 3.0, 0.0, 0.01)

    if st.button("重置默认值"):
        st.session_state.M = 1.0
        st.session_state.m = 1.0
        st.session_state.a = 2.0
        st.session_state.b = 1.0
        st.session_state.offset = 0.0
        st.rerun()

# 计算轨迹
x_ball, y_ball, groove_center_x, X0, A = compute_trajectory(M, m, a, b)
x_ball_display = x_ball + offset
groove_center_x_display = groove_center_x + offset
X0_display = X0 + offset

# 帧数
frames = len(x_ball_display)

# 初始化 session state 控制播放
if 'frame_idx' not in st.session_state:
    st.session_state.frame_idx = 0
if 'playing' not in st.session_state:
    st.session_state.playing = False

# 播放/暂停逻辑
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if st.button("⏸️ 暂停" if st.session_state.playing else "▶️ 播放"):
        st.session_state.playing = not st.session_state.playing
with col2:
    if st.button("⏮️ 重置帧"):
        st.session_state.frame_idx = 0
        st.session_state.playing = False
with col3:
    st.write(f"帧: {st.session_state.frame_idx+1}/{frames}")

# 自动播放（每0.05秒增加一帧）
if st.session_state.playing:
    st.session_state.frame_idx = (st.session_state.frame_idx + 1) % frames
    # 通过 time.sleep 不行，使用 st.empty + 定时刷新，但 Streamlit 不支持真正的定时器
    # 这里使用 rerun 配合延迟（简单做法：每次 rerun 自动前进一帧，但需要保持播放状态）
    # 为了让动画连续，使用 st.empty 占位并不断刷新，但 Streamlit 没有内置定时器。
    # 替代方案：使用 st.progress 和手动步进，或者用 streamlit-autorefresh 组件。
    # 这里为了简洁，只做手动步进+播放按钮（每次点击播放会逐渐前进，但不够流畅）。
    # 更优雅：使用 st.experimental_rerun 和 time.sleep 不可取。
    # 因此，我们提供一个手动滑块控制帧。
    # 更好的做法：使用 st.slider 让用户拖动帧，配合自动播放按钮使用 JavaScript 计时器。
    # 为了演示简单，我们放弃自动连续播放，改用帧滑块手动控制。
    # 修改如下：

# 由于 Streamlit 无内置定时器，我们提供手动滑块控制帧，并用播放按钮步进（每次点击前进一帧）
# 或者使用 session_state + st.empty 递归刷新，但复杂。这里采用滑块方式，简单可靠。

# 替换上面的播放逻辑为：
st.session_state.frame_idx = st.slider("选择帧", 0, frames-1, st.session_state.frame_idx)

# 如果需要自动播放，可以使用 streamlit_autorefresh 组件，但需要额外安装。
# 为保持通用，我们只提供手动滑块。

# 绘图
fig, ax = plt.subplots(figsize=(7, 5), dpi=100)
ax.set_aspect('equal')
ax.grid(True, linestyle=':', alpha=0.3)
ax.set_xlabel('x (m)')
ax.set_ylabel('y (m)')
ax.set_title('小球运动模拟')

# 固定坐标系范围
xmin = min(-a-1.5, X0_display - A - 0.5) + offset
xmax = max(a+X0_display+1.5, a+offset+0.5) + 0.5
ymin = -b-0.8
ymax = b+0.8
draw_fixed_coordinate_system(ax, (xmin, xmax), (ymin, ymax), tick_step=0.5)

# 静态小球理论轨迹（半椭圆虚线）
phi_traj = np.linspace(np.pi, 2*np.pi, 300)
x_traj_static = X0_display + A * np.cos(phi_traj)
y_traj_static = b * np.sin(phi_traj)
ax.plot(x_traj_static, y_traj_static, 'b--', lw=1.5, alpha=0.7, label='小球理论轨迹')

# 特殊点标记
ax.plot(a + offset, 0, 'go', markersize=6, alpha=0.6, label='右端点')
left_x = X0_display - A
ax.plot(left_x, 0, 'mo', markersize=6, alpha=0.6, label='左端点')
ax.plot(X0_display, -b, 'co', markersize=6, alpha=0.6, label='最低点')

# 当前帧的凹槽和小球
frame = st.session_state.frame_idx
cx = groove_center_x_display[frame]
path = create_groove_path(cx, a, b, base_height=0.3)
groove_patch = PathPatch(path, facecolor='lightskyblue', edgecolor='deepskyblue',
                         linewidth=1.5, alpha=0.8, zorder=0)
ax.add_patch(groove_patch)

# 椭圆轨道线（只显示下半部分）
phi_ellipse_lower = np.linspace(np.pi, 2*np.pi, 200)
x_ellipse = cx + a * np.cos(phi_ellipse_lower)
y_ellipse = b * np.sin(phi_ellipse_lower)
ax.plot(x_ellipse, y_ellipse, 'k-', lw=2, label='椭圆轨道（凹槽内壁）')

# 小球
ax.plot(x_ball_display[frame], y_ball[frame], 'ro', markersize=8, zorder=5, label='小球')

ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=9)
ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)

st.pyplot(fig)