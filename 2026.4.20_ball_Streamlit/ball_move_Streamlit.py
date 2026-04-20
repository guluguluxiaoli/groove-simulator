import streamlit as st
import numpy as np
import json

def compute_static_data(M, m, a, b, offset):
    """计算静态参数和初始条件，用于前端物理积分"""
    g = 9.8
    # 初始位置：右端点（椭圆角度 theta = 0 对应右端点，但我们使用 theta 从 pi 到 2pi 表示下半部分）
    # 为了方便，定义 theta = 0 时在右端点（x_rel = a, y_rel = 0），theta = pi 时在左端点。
    # 但椭圆参数方程：x_rel = a * cos(theta), y_rel = b * sin(theta)
    # 当 theta = 0: 右端点；theta = pi: 左端点；theta = pi/2: 最低点（y = -b）
    # 小球从右端点（theta=0）静止释放。
    theta0 = 0.0
    # 计算等效转动惯量 I_eff = m * (a^2 * sin^2θ + b^2 * cos^2θ) + M * ( (m a sinθ / (M+m))^2? 复杂)
    # 简单起见，直接在前端用能量守恒数值积分。这里返回初始势能、参数等。
    # 为简化，前端将根据公式实时计算。
    return {
        "M": M, "m": m, "a": a, "b": b, "offset": offset,
        "g": g, "theta0": theta0
    }

st.set_page_config(layout="wide")
st.title("Semi-elliptical Groove Simulator (with speed variation)")

with st.sidebar:
    st.header("Parameters")
    M = st.slider("Groove mass M (kg)", 0.2, 5.0, 1.0, 0.01)
    m = st.slider("Ball mass m (kg)", 0.2, 5.0, 1.0, 0.01)
    a = st.slider("Semi-major axis a (m)", 1.0, 4.0, 2.0, 0.01)
    b = st.slider("Semi-minor axis b (m)", 0.5, 2.5, 1.0, 0.01)
    offset = st.slider("Horizontal offset", -3.0, 3.0, 0.0, 0.01)

# 计算静态数据
static = compute_static_data(M, m, a, b, offset)
# 坐标范围（稍作扩展）
xmin = -a - 1.5 + offset
xmax = a + 1.5 + offset
ymin = -b - 0.8
ymax = b + 0.8

# 生成HTML+JavaScript代码，使用requestAnimationFrame和物理积分
html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ margin: 0; padding: 0; font-family: sans-serif; }}
        .main-container {{
            display: flex;
            flex-wrap: wrap;
            align-items: flex-start;
        }}
        .canvas-container {{
            flex: 0 0 auto;
        }}
        .legend-container {{
            margin-left: 20px;
            background: #f9f9f9;
            border: 1px solid #ccc;
            padding: 12px;
            width: 200px;
            border-radius: 5px;
        }}
        .legend-container h4 {{ margin: 0 0 10px 0; }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            margin-right: 10px;
            border: 1px solid #888;
        }}
        .controls {{
            margin-top: 15px;
            clear: both;
        }}
        button {{
            margin: 5px;
            padding: 5px 15px;
            font-size: 16px;
            cursor: pointer;
        }}
        .info {{
            display: inline-block;
            margin-left: 20px;
            font-family: monospace;
            font-size: 14px;
        }}
        canvas {{
            border: 1px solid #ddd;
            background: white;
        }}
    </style>
</head>
<body>
<div class="main-container">
    <div class="canvas-container">
        <canvas id="canvas" width="800" height="600"></canvas>
    </div>
    <div class="legend-container">
        <h4>Legend</h4>
        <div class="legend-item"><div class="legend-color" style="background: blue;"></div> Theoretical trajectory (dashed)</div>
        <div class="legend-item"><div class="legend-color" style="background: black;"></div> Elliptical groove (solid)</div>
        <div class="legend-item"><div class="legend-color" style="background: red;"></div> Ball</div>
        <div class="legend-item"><div class="legend-color" style="background: lightskyblue;"></div> Groove body (translucent)</div>
        <div class="legend-item"><div class="legend-color" style="background: green;"></div> Right endpoint</div>
        <div class="legend-item"><div class="legend-color" style="background: magenta;"></div> Left endpoint</div>
        <div class="legend-item"><div class="legend-color" style="background: cyan;"></div> Lowest point</div>
    </div>
</div>
<div class="controls">
    <button id="playBtn">▶️ Play</button>
    <button id="pauseBtn">⏸️ Pause</button>
    <button id="resetBtn">⏮️ Reset</button>
    <span class="info">Time: <span id="timeInfo">0.00</span> s</span>
</div>
<script>
    const params = {json.dumps(static)};
    const M = params.M, m = params.m, a = params.a, b = params.b, offset = params.offset, g = params.g;
    const theta0 = params.theta0;
    
    // 坐标系转换
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const width = canvas.width, height = canvas.height;
    const xmin = {xmin}, xmax = {xmax};
    const ymin = {ymin}, ymax = {ymax};
    
    function toCanvasX(x) {{
        return ((x - xmin) / (xmax - xmin)) * width;
    }}
    function toCanvasY(y) {{
        return height - ((y - ymin) / (ymax - ymin)) * height;
    }}
    
    // 物理积分所需变量
    let theta = theta0;          // 当前角度 (0 = 右端点, π = 左端点, π/2 = 最低点)
    let omega = 0.0;            // 角速度
    let lastTimestamp = null;
    let animationId = null;
    let playing = false;
    
    // 辅助函数：计算当前系统的总机械能（初始能量）
    // 初始状态：theta=0, 小球在右端点，y_rel = 0，速度为零，凹槽速度为零。
    // 势能零点取 y_rel = 0 处。
    // 动能表达式：T = 0.5 * m * (v_ball^2) + 0.5 * M * V_groove^2
    // 由水平动量守恒：m * v_ball_x + M * V_groove = 0 => V_groove = - (m/M) * v_ball_x
    // 小球速度：v_ball = (dx_rel/dt, dy_rel/dt) + (V_groove, 0)
    // 可以推导出等效质量，但为简化，我们直接用数值积分计算角加速度。
    // 更准确：由拉格朗日方程推导出 theta 的二阶微分方程。
    // 这里提供解析的角加速度公式（从能量守恒和约束推导）：
    // 系统动能 T = 0.5 * (M + m) * V_groove^2 + 0.5 * m * ( (dx_rel/dt)^2 + (dy_rel/dt)^2 ) + m * V_groove * (dx_rel/dt)
    // 利用动量守恒消去 V_groove，最终得到 T = 0.5 * I_eff(theta) * omega^2，其中
    // I_eff = m * (a^2 sin^2θ + b^2 cos^2θ) - (m^2/(M+m)) * (a sinθ)^2
    // 势能 V = m * g * y_rel = m * g * b * sinθ (注意 y_rel = b sinθ, 当θ从0到π，sinθ≥0，但实际上y_rel在下方为负？需统一)
    // 我们的坐标系中y向上为正，椭圆参数方程 y_rel = b sinθ，当θ=π/2时y_rel = b（最高点），但轨道只有下半部分，我们实际使用的θ范围是π到2π，此时sinθ≤0。
    // 为简化，我们使用θ从0到π表示下半部分？重新定义：θ=0右端点，θ=π左端点，那么y_rel = -b * sinθ（因为sinθ≥0时y_rel≤0），这样最低点在θ=π/2处y_rel=-b。
    // 这样势能 V = m*g*(-b*sinθ) = -m g b sinθ，势能零点在y=0（θ=0和π时）。
    // 我们采用这个定义：θ∈[0,π]，右端点θ=0，左端点θ=π，最低点θ=π/2。
    // 那么参数方程：x_rel = a * cosθ, y_rel = -b * sinθ。
    // 重新计算等效转动惯量：
    // dx_rel/dθ = -a sinθ, dy_rel/dθ = -b cosθ
    // 速度分量：v_rel_x = -a sinθ * ω, v_rel_y = -b cosθ * ω
    // 动量守恒：V_groove = - (m/M) * (v_rel_x + V_groove)??? 实际上小球绝对水平速度 = v_rel_x + V_groove，凹槽速度 = V_groove
    // 水平动量守恒：m*(v_rel_x + V_groove) + M*V_groove = 0 => V_groove = - (m/(M+m)) * v_rel_x
    // 绝对水平速度 v_ball_x = v_rel_x + V_groove = v_rel_x * (M/(M+m))
    // 绝对竖直速度 v_ball_y = v_rel_y
    // 动能 T = 0.5*m*(v_ball_x^2+v_ball_y^2) + 0.5*M*V_groove^2
    // 代入化简得 T = 0.5 * [ m*( (M/(M+m))^2 * (a sinθ ω)^2 + (b cosθ ω)^2 ) + M*(m/(M+m))^2 * (a sinθ ω)^2 ]
    //     = 0.5 * ω^2 * [ m*(M/(M+m))^2 a^2 sin^2θ + m b^2 cos^2θ + M*(m/(M+m))^2 a^2 sin^2θ ]
    //     = 0.5 * ω^2 * [ m b^2 cos^2θ + (m^2/(M+m)) a^2 sin^2θ ]
    // 所以等效惯量 I_eff(θ) = m b^2 cos^2θ + (m^2/(M+m)) a^2 sin^2θ
    // 势能 V = m g y_ball = m g * (-b sinθ) = -m g b sinθ
    // 总能量守恒：E = 0.5 I_eff ω^2 + V = 常数 = 初始能量 V(θ=0)=0，初始ω=0，故E=0。
    // 因此 0.5 I_eff ω^2 - m g b sinθ = 0 => ω = sqrt( 2 m g b sinθ / I_eff )
    // 注意 sinθ≥0，开方有意义。这个微分方程可以用欧拉法积分。
    
    function I_eff(theta) {{
        const cosT = Math.cos(theta);
        const sinT = Math.sin(theta);
        return m * b * b * cosT * cosT + (m*m/(M+m)) * a * a * sinT * sinT;
    }}
    
    function omegaFromTheta(theta) {{
        // 从能量守恒直接计算当前角速度大小（方向由运动方向决定）
        const sinT = Math.sin(theta);
        if (sinT <= 1e-6) return 0;
        const I = I_eff(theta);
        return Math.sqrt(2 * m * g * b * sinT / I);
    }}
    
    // 积分函数：更新 theta 和 omega（使用能量守恒直接计算 omega，避免数值误差）
    // 实际上 omega 完全由 theta 决定，所以我们可以直接用 theta 的变化率。
    // 但是为了时间演化，我们需要 dθ/dt = omega(theta)，其中 omega(theta) = sqrt(2mgb sinθ / I_eff(θ))
    // 符号：从右端点释放，θ 从0增加，因此取正。
    function updateTheta(dt, currentTheta) {{
        let omegaVal = omegaFromTheta(currentTheta);
        // 当接近端点时，omega很小，避免过冲
        let newTheta = currentTheta + omegaVal * dt;
        // 边界处理：达到 π 时反向，但这里为了简单，允许越过 π 后反向？应该模拟来回摆动。
        // 因为能量守恒，小球会从右端滑到左端，再返回。所以 theta 范围 [0, π]，到达 π 时速度为零，然后反向。
        // 我们可以在每次积分后检查是否超出范围并反转速度。
        if (newTheta > Math.PI) {{
            newTheta = 2*Math.PI - newTheta;
            // 反转方向：实际上 omega 应该为负，但我们直接用绝对值，然后由边界处理符号
            // 这里简单重置速度方向，但更精确做法是保持能量，反弹。
        }}
        if (newTheta < 0) newTheta = -newTheta;
        return newTheta;
    }}
    
    // 更好的积分：使用欧拉法，并处理反射
    function integrate(dt) {{
        let omegaVal = omegaFromTheta(theta);
        let newTheta = theta + omegaVal * dt;
        // 边界反射
        if (newTheta > Math.PI) {{
            newTheta = Math.PI - (newTheta - Math.PI);
        }}
        if (newTheta < 0) {{
            newTheta = -newTheta;
        }}
        theta = newTheta;
    }}
    
    // 绘图相关函数
    function drawAxes() {{
        ctx.save();
        ctx.strokeStyle = 'black';
        ctx.fillStyle = 'black';
        ctx.lineWidth = 1;
        const y0 = toCanvasY(0);
        ctx.beginPath();
        ctx.moveTo(toCanvasX(xmin), y0);
        ctx.lineTo(toCanvasX(xmax), y0);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(toCanvasX(xmax)-8, y0-4);
        ctx.lineTo(toCanvasX(xmax), y0);
        ctx.lineTo(toCanvasX(xmax)-8, y0+4);
        ctx.fill();
        const x0 = toCanvasX(0);
        ctx.beginPath();
        ctx.moveTo(x0, toCanvasY(ymin));
        ctx.lineTo(x0, toCanvasY(ymax));
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x0-4, toCanvasY(ymax)+8);
        ctx.lineTo(x0, toCanvasY(ymax));
        ctx.lineTo(x0+4, toCanvasY(ymax)+8);
        ctx.fill();
        const tickStep = 0.5;
        for (let x = Math.ceil(xmin/tickStep)*tickStep; x <= xmax; x+=tickStep) {{
            if (Math.abs(x) < 1e-6) continue;
            const cx = toCanvasX(x);
            ctx.beginPath();
            ctx.moveTo(cx, y0);
            ctx.lineTo(cx, y0-5);
            ctx.stroke();
        }}
        for (let y = Math.ceil(ymin/tickStep)*tickStep; y <= ymax; y+=tickStep) {{
            if (Math.abs(y) < 1e-6) continue;
            const cy = toCanvasY(y);
            ctx.beginPath();
            ctx.moveTo(x0, cy);
            ctx.lineTo(x0+5, cy);
            ctx.stroke();
        }}
        ctx.restore();
    }}
    
    function drawGroove(cx) {{
        const baseHeight = 0.3;
        const left = cx - a, right = cx + a;
        const bottomY = -b - baseHeight;
        const topY = 0;
        ctx.save();
        ctx.fillStyle = 'lightskyblue';
        ctx.globalAlpha = 0.7;
        ctx.strokeStyle = 'deepskyblue';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.rect(toCanvasX(left), toCanvasY(bottomY), toCanvasX(right)-toCanvasX(left), toCanvasY(topY)-toCanvasY(bottomY));
        ctx.fill();
        ctx.stroke();
        // 下半椭圆弧
        ctx.beginPath();
        for (let t = Math.PI; t <= 2*Math.PI; t+=0.05) {{
            let x = cx + a * Math.cos(t);
            let y = b * Math.sin(t);
            if (t === Math.PI) ctx.moveTo(toCanvasX(x), toCanvasY(y));
            else ctx.lineTo(toCanvasX(x), toCanvasY(y));
        }}
        ctx.stroke();
        ctx.restore();
    }}
    
    function drawEllipticalTrack(cx) {{
        ctx.save();
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 2;
        ctx.beginPath();
        for (let t = Math.PI; t <= 2*Math.PI; t+=0.02) {{
            let x = cx + a * Math.cos(t);
            let y = b * Math.sin(t);
            if (t === Math.PI) ctx.moveTo(toCanvasX(x), toCanvasY(y));
            else ctx.lineTo(toCanvasX(x), toCanvasY(y));
        }}
        ctx.stroke();
        ctx.restore();
    }}
    
    function drawBall(x, y) {{
        ctx.fillStyle = 'red';
        ctx.beginPath();
        ctx.arc(toCanvasX(x), toCanvasY(y), 6, 0, 2*Math.PI);
        ctx.fill();
    }}
    
    function drawTheoreticalTrajectory() {{
        // 理论轨迹：小球相对于地面的轨迹（半椭圆）
        const X0 = (m*a)/(M+m) + offset;  // 椭圆中心最终x
        const A = (M*a)/(M+m);
        ctx.save();
        ctx.setLineDash([5, 5]);
        ctx.strokeStyle = 'blue';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        for (let t = Math.PI; t <= 2*Math.PI; t+=0.02) {{
            let x = X0 + A * Math.cos(t);
            let y = b * Math.sin(t);
            if (t === Math.PI) ctx.moveTo(toCanvasX(x), toCanvasY(y));
            else ctx.lineTo(toCanvasX(x), toCanvasY(y));
        }}
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.restore();
    }}
    
    function drawSpecialPoints() {{
        const X0 = (m*a)/(M+m) + offset;
        const A = (M*a)/(M+m);
        ctx.fillStyle = 'green';
        const rightX = a + offset;
        ctx.beginPath();
        ctx.arc(toCanvasX(rightX), toCanvasY(0), 4, 0, 2*Math.PI);
        ctx.fill();
        ctx.fillStyle = 'magenta';
        const leftX = X0 - A;
        ctx.beginPath();
        ctx.arc(toCanvasX(leftX), toCanvasY(0), 4, 0, 2*Math.PI);
        ctx.fill();
        ctx.fillStyle = 'cyan';
        const lowX = X0;
        ctx.beginPath();
        ctx.arc(toCanvasX(lowX), toCanvasY(-b), 4, 0, 2*Math.PI);
        ctx.fill();
    }}
    
    function getBallGroundPosition(theta) {{
        // 小球相对凹槽坐标（使用新定义 theta ∈ [0,π]）
        const x_rel = a * Math.cos(theta);
        const y_rel = -b * Math.sin(theta);
        // 凹槽速度 V_groove = - (m/(M+m)) * v_rel_x, 但我们需要凹槽位移，可通过动量守恒积分得到凹槽位置与theta的关系。
        // 实际上，凹槽位移 X_groove = - (m/(M+m)) * (x_rel - x_rel0) 因为初始 x_rel0 = a（θ=0时）。
        const x_rel0 = a;
        const X_groove = - (m/(M+m)) * (x_rel - x_rel0);
        const ball_ground_x = x_rel + X_groove + offset;
        const ball_ground_y = y_rel;
        return [ball_ground_x, ball_ground_y];
    }}
    
    function getGrooveCenter(theta) {{
        const x_rel0 = a;
        const x_rel = a * Math.cos(theta);
        const X_groove = - (m/(M+m)) * (x_rel - x_rel0);
        return X_groove + offset;
    }}
    
    let currentTime = 0;
    let lastFrameTime = null;
    
    function render(timestamp) {{
        if (!playing) return;
        if (lastFrameTime === null) {{
            lastFrameTime = timestamp;
            requestAnimationFrame(render);
            return;
        }}
        let dt = Math.min(0.02, (timestamp - lastFrameTime) / 1000);
        if (dt > 0) {{
            integrate(dt);
            currentTime += dt;
        }}
        lastFrameTime = timestamp;
        
        // 更新绘图
        ctx.clearRect(0, 0, width, height);
        drawAxes();
        drawTheoreticalTrajectory();
        drawSpecialPoints();
        const cx = getGrooveCenter(theta);
        drawGroove(cx);
        drawEllipticalTrack(cx);
        const [ballX, ballY] = getBallGroundPosition(theta);
        drawBall(ballX, ballY);
        
        document.getElementById('timeInfo').innerText = currentTime.toFixed(2);
        
        requestAnimationFrame(render);
    }}
    
    function startAnimation() {{
        if (animationId) cancelAnimationFrame(animationId);
        playing = true;
        lastFrameTime = null;
        animationId = requestAnimationFrame(render);
    }}
    
    function stopAnimation() {{
        playing = false;
        if (animationId) {{
            cancelAnimationFrame(animationId);
            animationId = null;
        }}
    }}
    
    function resetSimulation() {{
        stopAnimation();
        theta = theta0;
        currentTime = 0;
        // 重绘一次
        ctx.clearRect(0, 0, width, height);
        drawAxes();
        drawTheoreticalTrajectory();
        drawSpecialPoints();
        const cx = getGrooveCenter(theta);
        drawGroove(cx);
        drawEllipticalTrack(cx);
        const [ballX, ballY] = getBallGroundPosition(theta);
        drawBall(ballX, ballY);
        document.getElementById('timeInfo').innerText = "0.00";
    }}
    
    document.getElementById('playBtn').onclick = () => {{
        if (!playing) startAnimation();
    }};
    document.getElementById('pauseBtn').onclick = () => {{
        stopAnimation();
    }};
    document.getElementById('resetBtn').onclick = () => {{
        resetSimulation();
    }};
    
    // 初始绘制
    resetSimulation();
</script>
</body>
</html>
"""
st.components.v1.html(html_code, height=700, width=1100)
