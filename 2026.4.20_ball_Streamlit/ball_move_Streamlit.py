import streamlit as st
import numpy as np
import json

st.set_page_config(layout="wide")
st.title("Semi-elliptical Groove Simulator (Variable Speed)")

with st.sidebar:
    st.header("Parameters")
    M = st.slider("Groove mass M (kg)", 0.2, 5.0, 1.0, 0.01)
    m = st.slider("Ball mass m (kg)", 0.2, 5.0, 1.0, 0.01)
    a = st.slider("Semi-major axis a (m)", 1.0, 4.0, 2.0, 0.01)
    b = st.slider("Semi-minor axis b (m)", 0.5, 2.5, 1.0, 0.01)
    offset = st.slider("Horizontal offset", -3.0, 3.0, 0.0, 0.01)

static_data = {
    "M": M, "m": m, "a": a, "b": b, "offset": offset, "g": 9.8
}

# 坐标范围（确保小球始终可见）
xmin = -a - 1.5 + offset
xmax = a + 1.5 + offset
ymin = -b - 0.8
ymax = b + 0.8

html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ margin: 0; padding: 0; font-family: sans-serif; }}
        .main-container {{ display: flex; flex-wrap: wrap; align-items: flex-start; }}
        .canvas-container {{ flex: 0 0 auto; }}
        .legend-container {{
            margin-left: 20px; background: #f9f9f9; border: 1px solid #ccc;
            padding: 12px; width: 200px; border-radius: 5px;
        }}
        .legend-container h4 {{ margin: 0 0 10px 0; }}
        .legend-item {{ display: flex; align-items: center; margin-bottom: 8px; }}
        .legend-color {{ width: 20px; height: 20px; margin-right: 10px; border: 1px solid #888; }}
        .controls {{ margin-top: 15px; clear: both; }}
        button {{ margin: 5px; padding: 5px 15px; font-size: 16px; cursor: pointer; }}
        .info {{ display: inline-block; margin-left: 20px; font-family: monospace; font-size: 14px; }}
        canvas {{ border: 1px solid #ddd; background: white; }}
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
    const params = {json.dumps(static_data)};
    const M = params.M, m = params.m, a = params.a, b = params.b, offset = params.offset, g = params.g;
    
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const width = canvas.width, height = canvas.height;
    const xmin = {xmin}, xmax = {xmax};
    const ymin = {ymin}, ymax = {ymax};
    
    function toCanvasX(x) {{ return ((x - xmin) / (xmax - xmin)) * width; }}
    function toCanvasY(y) {{ return height - ((y - ymin) / (ymax - ymin)) * height; }}
    
    // 角度 θ ∈ [0, π]，0 对应右端点，π 对应左端点
    let theta = 1e-6;      // 微小初始偏移
    let direction = 1;     // 1: 向右运动? 实际上角度增加方向是从右端点到左端点，所以方向 = 1
    let currentTime = 0.0;
    let playing = false;
    let animationId = null;
    let lastTimestamp = null;
    
    // 等效转动惯量 I_eff(θ)
    function I_eff(th) {{
        const cosT = Math.cos(th);
        const sinT = Math.sin(th);
        return m * b * b * cosT * cosT + (m*m/(M+m)) * a * a * sinT * sinT;
    }}
    
    // 由能量守恒计算角速度大小（正值）
    function angularSpeed(th) {{
        const sinT = Math.sin(th);
        if (sinT <= 1e-9) return 0;
        const I = I_eff(th);
        return Math.sqrt(2 * m * g * b * sinT / I);
    }}
    
    // 更新角度：欧拉法，基于当前角速度
    function updateTheta(dt) {{
        let omega = angularSpeed(theta);
        let newTheta = theta + direction * omega * dt;
        // 边界反射
        if (newTheta < 0) {{
            newTheta = -newTheta;
            direction = 1;
        }}
        if (newTheta > Math.PI) {{
            newTheta = 2*Math.PI - newTheta;
            direction = -1;
        }}
        theta = newTheta;
    }}
    
    // 根据当前角度计算凹槽中心和小球地面坐标
    function getGrooveCenter(th) {{
        const x_rel0 = a;
        const x_rel = a * Math.cos(th);
        const X_groove = - (m/(M+m)) * (x_rel - x_rel0);
        return X_groove + offset;
    }}
    
    function getBallGroundPosition(th) {{
        const x_rel = a * Math.cos(th);
        const y_rel = -b * Math.sin(th);
        const x_rel0 = a;
        const X_groove = - (m/(M+m)) * (x_rel - x_rel0);
        const ball_x = x_rel + X_groove + offset;
        const ball_y = y_rel;
        return [ball_x, ball_y];
    }}
    
    // ========== 绘图函数 ==========
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
    
    // 凹字形凹槽（矩形底座 + 下半椭圆弧，两侧带小平整段）
    function drawGroove(cx) {{
        const baseHeight = 0.3;
        const flatWidth = 0.1;
        const left = cx - a - flatWidth;
        const right = cx + a + flatWidth;
        const bottomY = -b - baseHeight;
        const topY = 0;
        ctx.save();
        ctx.fillStyle = 'lightskyblue';
        ctx.globalAlpha = 0.7;
        ctx.strokeStyle = 'deepskyblue';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(toCanvasX(left), toCanvasY(bottomY));
        ctx.lineTo(toCanvasX(right), toCanvasY(bottomY));
        ctx.lineTo(toCanvasX(right), toCanvasY(topY));
        const arcRight = cx + a;
        ctx.lineTo(toCanvasX(arcRight), toCanvasY(topY));
        for (let t = 2*Math.PI; t >= Math.PI; t -= 0.05) {{
            let x = cx + a * Math.cos(t);
            let y = b * Math.sin(t);
            ctx.lineTo(toCanvasX(x), toCanvasY(y));
        }}
        const arcLeft = cx - a;
        ctx.lineTo(toCanvasX(arcLeft), toCanvasY(topY));
        ctx.lineTo(toCanvasX(left), toCanvasY(topY));
        ctx.lineTo(toCanvasX(left), toCanvasY(bottomY));
        ctx.fill();
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
        const X0 = (m*a)/(M+m) + offset;
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
    
    function renderFrame() {{
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
    }}
    
    // 动画循环
    function animationLoop(now) {{
        if (!playing) return;
        if (lastTimestamp === null) {{
            lastTimestamp = now;
            requestAnimationFrame(animationLoop);
            return;
        }}
        let dt = Math.min(0.02, (now - lastTimestamp) / 1000);
        if (dt > 0) {{
            updateTheta(dt);
            currentTime += dt;
        }}
        lastTimestamp = now;
        renderFrame();
        requestAnimationFrame(animationLoop);
    }}
    
    function startAnimation() {{
        if (animationId) cancelAnimationFrame(animationId);
        playing = true;
        lastTimestamp = null;
        animationId = requestAnimationFrame(animationLoop);
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
        theta = 1e-6;
        direction = 1;
        currentTime = 0.0;
        renderFrame();
    }}
    
    document.getElementById('playBtn').onclick = startAnimation;
    document.getElementById('pauseBtn').onclick = stopAnimation;
    document.getElementById('resetBtn').onclick = resetSimulation;
    
    resetSimulation();
</script>
</body>
</html>
"""
st.components.v1.html(html_code, height=700, width=1100)
