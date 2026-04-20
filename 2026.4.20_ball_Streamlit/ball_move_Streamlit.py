import streamlit as st
import numpy as np
import json

def compute_trajectory(M, m, a, b):
    X0 = m * a / (M + m)
    A = M * a / (M + m)
    phi_forward = np.linspace(2*np.pi, np.pi, 100)
    phi_back = np.linspace(np.pi, 2*np.pi, 100)
    phi_frames = np.concatenate([phi_forward, phi_back])
    x_ball = X0 + A * np.cos(phi_frames)
    y_ball = b * np.sin(phi_frames)
    groove_center_x = m * (a - x_ball) / M
    return x_ball.tolist(), y_ball.tolist(), groove_center_x.tolist(), float(X0), float(A)

st.set_page_config(layout="wide")
st.title("Semi-elliptical Groove Simulator")

with st.sidebar:
    st.header("Parameters")
    M = st.slider("Groove mass M", 0.2, 5.0, 1.0, 0.01)
    m = st.slider("Ball mass m", 0.2, 5.0, 1.0, 0.01)
    a = st.slider("Semi-major axis a", 1.0, 4.0, 2.0, 0.01)
    b = st.slider("Semi-minor axis b", 0.5, 2.5, 1.0, 0.01)
    offset = st.slider("Horizontal offset", -3.0, 3.0, 0.0, 0.01)

x_ball, y_ball, groove_center_x, X0, A = compute_trajectory(M, m, a, b)
frames = len(x_ball)

xmin = min(-a-1.5, (X0 + offset) - A - 0.5) + offset
xmax = max(a + X0 + 1.5, a + offset + 0.5) + 0.5
ymin = -b - 0.8
ymax = b + 0.8

data = {
    "frames": frames,
    "x_ball": x_ball,
    "y_ball": y_ball,
    "groove_center_x": groove_center_x,
    "offset": offset,
    "a": a,
    "b": b,
    "xmin": xmin,
    "xmax": xmax,
    "ymin": ymin,
    "ymax": ymax,
    "X0": X0,
    "A": A
}

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
    <span class="info">Frame: <span id="frameInfo">0</span> / {frames}</span>
</div>
<script>
    const data = {json.dumps(data)};
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    
    const width = canvas.width, height = canvas.height;
    const xmin = data.xmin, xmax = data.xmax;
    const ymin = data.ymin, ymax = data.ymax;
    
    function toCanvasX(x) {{
        return ((x - xmin) / (xmax - xmin)) * width;
    }}
    function toCanvasY(y) {{
        return height - ((y - ymin) / (ymax - ymin)) * height;
    }}
    
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
        const a = data.a, b = data.b, baseHeight = 0.3;
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
    
    function drawBall(x, y) {{
        ctx.fillStyle = 'red';
        ctx.beginPath();
        ctx.arc(toCanvasX(x), toCanvasY(y), 6, 0, 2*Math.PI);
        ctx.fill();
    }}
    
    function drawTheoreticalTrajectory() {{
        const X0 = data.X0 + data.offset;
        const A = data.A;
        const b = data.b;
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
        ctx.fillStyle = 'green';
        const rightX = data.a + data.offset;
        ctx.beginPath();
        ctx.arc(toCanvasX(rightX), toCanvasY(0), 4, 0, 2*Math.PI);
        ctx.fill();
        ctx.fillStyle = 'magenta';
        const leftX = data.X0 + data.offset - data.A;
        ctx.beginPath();
        ctx.arc(toCanvasX(leftX), toCanvasY(0), 4, 0, 2*Math.PI);
        ctx.fill();
        ctx.fillStyle = 'cyan';
        const lowX = data.X0 + data.offset;
        ctx.beginPath();
        ctx.arc(toCanvasX(lowX), toCanvasY(-data.b), 4, 0, 2*Math.PI);
        ctx.fill();
    }}
    
    function drawEllipticalTrack(cx) {{
        ctx.save();
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 2;
        ctx.beginPath();
        for (let t = Math.PI; t <= 2*Math.PI; t+=0.02) {{
            let x = cx + data.a * Math.cos(t);
            let y = data.b * Math.sin(t);
            if (t === Math.PI) ctx.moveTo(toCanvasX(x), toCanvasY(y));
            else ctx.lineTo(toCanvasX(x), toCanvasY(y));
        }}
        ctx.stroke();
        ctx.restore();
    }}
    
    let currentFrame = 0;
    let playing = false;
    let intervalId = null;
    
    function render() {{
        ctx.clearRect(0, 0, width, height);
        drawAxes();
        drawTheoreticalTrajectory();
        drawSpecialPoints();
        const cx = data.groove_center_x[currentFrame] + data.offset;
        drawGroove(cx);
        drawEllipticalTrack(cx);
        drawBall(data.x_ball[currentFrame] + data.offset, data.y_ball[currentFrame]);
        document.getElementById('frameInfo').innerText = currentFrame+1;
    }}
    
    function play() {{
        if (intervalId) clearInterval(intervalId);
        playing = true;
        intervalId = setInterval(() => {{
            if (playing) {{
                currentFrame = (currentFrame + 1) % data.frames;
                render();
            }}
        }}, 50);
    }}
    
    function pause() {{
        playing = false;
        if (intervalId) {{
            clearInterval(intervalId);
            intervalId = null;
        }}
    }}
    
    function reset() {{
        pause();
        currentFrame = 0;
        render();
    }}
    
    document.getElementById('playBtn').onclick = play;
    document.getElementById('pauseBtn').onclick = pause;
    document.getElementById('resetBtn').onclick = reset;
    
    render();
</script>
</body>
</html>
"""
st.components.v1.html(html_code, height=700, width=1100)
