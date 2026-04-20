import streamlit as st
from streamlit_autorefresh import st_autorefresh
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path

# 禁用中文字体警告（使用英文标签）
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
    ax.arrow(xmin, 0, xmax - xmin - 0.2, 0, head_width=0.08, head_length=0.12,
             fc='black', ec='black', length_includes_head=True, lw=1, zorder=10)
    ax.arrow(0, ymin, 0, ymax - ymin - 0.2, head_width=0.08, head_length=0.12,
             fc='black', ec='black', length_includes_head=True, lw=1, zorder=10)
    xticks = np.arange(np.ceil(xmin / tick_step) * tick_step, xmax, tick_step)
    for x in xticks:
        if abs(x) < 1e-6:
            continue
        ax.plot([x, x], [0, 0.08], 'k-', lw=0.5, zorder=10)
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

# 播放/暂停按钮
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    play_label = "⏸️ Pause" if st.session_state.playing else "▶️ Play"
    if st.button(play_label):
        st.session_state.playing = not st.session_state.playing
        if st.session_state.playing:
            # 播放时强制刷新一次，启动 autorefresh
            st.rerun()
with col2:
    if st.button("⏮️ Reset frame"):
        st.session_state.frame_idx = 0
        st.session_state.playing = False
with col3:
    st.write(f"Frame: {st.session_state.frame_idx+1} / {frames}")

# 手动帧滑块（当播放时禁用滑块自动跳转，避免冲突）
slider_key = "frame_slider_disabled" if st.session_state.playing else "frame_slider"
frame_slider = st.slider("Select frame", 0, frames-1, st.session_state.frame_idx, key=slider_key, disabled=st.session_state.playing)
if not st.session_state.playing and frame_slider != st.session_state.frame_idx:
    st.session_state.frame_idx = frame_slider

# 自动刷新核心：仅在 playing = True 时启用 autorefresh
if st.session_state.playing:
    # 每 50 毫秒刷新一次页面（20 fps）
    st_autorefresh(interval=50, key="auto_play", debounce=False)
    # 每次刷新自动增加帧索引
    new_idx = st.session_state.frame_idx + 1
    if new_idx >= frames:
        new_idx = 0
    st.session_state.frame_idx = new_idx

# 绘图
fig, ax = plt.subplots(figsize=(7, 5), dpi=100)
ax.set_aspect('equal')
ax.grid(True, linestyle=':', alpha=0.3)
ax.set_xlabel('x (m)')
ax.set_ylabel('y (m)')
ax.set_title('Ball motion simulation')

xmin = min(-a-1.5, X0_display - A - 0.5) + offset
xmax = max(a+X0_display+1.5, a+offset+0.5) + 0.5
ymin = -b-0.8
ymax = b+0.8
draw_fixed_coordinate_system(ax, (xmin, xmax), (ymin, ymax), tick_step=0.5)

phi_traj = np.linspace(np.pi, 2*np.pi, 300)
x_traj_static = X0_display + A * np.cos(phi_traj)
y_traj_static = b * np.sin(phi_traj)
ax.plot(x_traj_static, y_traj_static, 'b--', lw=1.5, alpha=0.7, label='Theoretical trajectory')

ax.plot(a + offset, 0, 'go', markersize=6, alpha=0.6, label='Right endpoint')
left_x = X0_display - A
ax.plot(left_x, 0, 'mo', markersize=6, alpha=0.6, label='Left endpoint')
ax.plot(X0_display, -b, 'co', markersize=6, alpha=0.6, label='Lowest point')

frame = st.session_state.frame_idx
cx = groove_center_x_display[frame]
path = create_groove_path(cx, a, b, base_height=0.3)
groove_patch = PathPatch(path, facecolor='lightskyblue', edgecolor='deepskyblue',
                         linewidth=1.5, alpha=0.8, zorder=0)
ax.add_patch(groove_patch)

phi_ellipse_lower = np.linspace(np.pi, 2*np.pi, 200)
x_ellipse = cx + a * np.cos(phi_ellipse_lower)
y_ellipse = b * np.sin(phi_ellipse_lower)
ax.plot(x_ellipse, y_ellipse, 'k-', lw=2, label='Elliptical groove')

ax.plot(x_ball_display[frame], y_ball[frame], 'ro', markersize=8, zorder=5, label='Ball')

ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=9)
ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)

st.pyplot(fig)
