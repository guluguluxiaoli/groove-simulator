import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path

# 禁用中文字体警告，直接使用英文标签（避免依赖系统字体）
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
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
st.title("Semi-elliptical Groove Simulator")

# 侧边栏参数调节
with st.sidebar:
    st.header("Parameters")
    M = st.slider("Groove mass M", 0.2, 5.0, 1.0, 0.01)
    m = st.slider("Ball mass m", 0.2, 5.0, 1.0, 0.01)
    a = st.slider("Semi-major axis a", 1.0, 4.0, 2.0, 0.01)
    b = st.slider("Semi-minor axis b", 0.5, 2.5, 1.0, 0.01)
    offset = st.slider("Horizontal offset", -3.0, 3.0, 0.0, 0.01)

    if st.button("Reset defaults"):
        # 重置所有参数和状态
        st.session_state.frame_idx = 0
        st.session_state.playing = False
        st.rerun()

# 计算轨迹
x_ball, y_ball, groove_center_x, X0, A = compute_trajectory(M, m, a, b)
x_ball_display = x_ball + offset
groove_center_x_display = groove_center_x + offset
X0_display = X0 + offset

frames = len(x_ball_display)

# 初始化 session_state
if 'frame_idx' not in st.session_state:
    st.session_state.frame_idx = 0
if 'playing' not in st.session_state:
    st.session_state.playing = False

# 播放/暂停控制
col1, col2, col3 = st.columns([1, 1, 3])
with col1:
    if st.button("⏸️ Pause" if st.session_state.playing else "▶️ Play"):
        st.session_state.playing = not st.session_state.playing
with col2:
    if st.button("⏮️ Reset frame"):
        st.session_state.frame_idx = 0
        st.session_state.playing = False
with col3:
    st.write(f"Frame: {st.session_state.frame_idx+1} / {frames}")

# 手动帧滑块
frame_slider = st.slider("Select frame", 0, frames-1, st.session_state.frame_idx)
if frame_slider != st.session_state.frame_idx:
    st.session_state.frame_idx = frame_slider
    st.session_state.playing = False

# 播放逻辑：如果 playing 为 True，自动增加帧索引
if st.session_state.playing:
    new_idx = st.session_state.frame_idx + 1
    if new_idx >= frames:
        new_idx = 0  # 循环
    st.session_state.frame_idx = new_idx
    # 延迟刷新（使用 st.rerun 模拟动画，但频率太高会白屏，改用 time.sleep 会阻塞）
    # 这里使用 st.empty 占位，但最简单的办法是每次 rerun 前进一帧
    # 注意：如果不加延迟，会以最快速度刷新（可能导致浏览器卡死）
    # 所以我们在播放时使用 st.experimental_rerun 并添加一个小的等待时间
    # 但 Streamlit 不支持 sleep，所以建议用户手动点击“下一帧”按钮
    # 为了避免白屏，这里暂时禁用自动播放，改为提示用户使用滑块或“下一帧”按钮
    st.session_state.playing = False  # 自动播放会导致页面频繁刷新，暂时关闭
    st.warning("Auto-play disabled due to stability. Use slider or manual next button.")

# 如果需要真正的自动播放，可以借助 JavaScript，但为了稳定，这里提供手动“下一帧”按钮
if st.button("Next frame ➡️"):
    new_idx = st.session_state.frame_idx + 1
    if new_idx >= frames:
        new_idx = 0
    st.session_state.frame_idx = new_idx
    st.rerun()

# 绘图
fig, ax = plt.subplots(figsize=(7, 5), dpi=100)
ax.set_aspect('equal')
ax.grid(True, linestyle=':', alpha=0.3)
ax.set_xlabel('x (m)')
ax.set_ylabel('y (m)')
ax.set_title('Ball motion simulation')

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
ax.plot(x_traj_static, y_traj_static, 'b--', lw=1.5, alpha=0.7, label='Theoretical trajectory')

# 特殊点标记
ax.plot(a + offset, 0, 'go', markersize=6, alpha=0.6, label='Right endpoint')
left_x = X0_display - A
ax.plot(left_x, 0, 'mo', markersize=6, alpha=0.6, label='Left endpoint')
ax.plot(X0_display, -b, 'co', markersize=6, alpha=0.6, label='Lowest point')

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
ax.plot(x_ellipse, y_ellipse, 'k-', lw=2, label='Elliptical groove')

# 小球
ax.plot(x_ball_display[frame], y_ball[frame], 'ro', markersize=8, zorder=5, label='Ball')

ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=9)
ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)

st.pyplot(fig)
