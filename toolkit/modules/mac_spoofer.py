import os
import sys
import random
import subprocess
import psutil
import re
import time

def get_random_mac(mode='unix'):
    if mode == 'win':
        char2 = random.choice("26AE")
        return f"0{char2}" + "".join(f"{random.randint(0, 255):02X}" for _ in range(5))
    else:
        mac = [0x00, 0x16, 0x3e, random.randint(0x00, 0x7f), 
               random.randint(0x00, 0xff), random.randint(0x00, 0xff)]
        return ':'.join(f"{x:02x}" for x in mac)

def windows_engine(iface, revert=False):
    try:
        # Use PowerShell to find the Interface Index (Index is used in Registry)
        ps_cmd = f'powershell -Command "(Get-NetAdapter -Name \'{iface}\').ifIndex"'
        idx_raw = subprocess.check_output(ps_cmd, shell=True).decode().strip()
        
        if not idx_raw:
            print(f"[-] Could not find index for {iface}")
            return

        idx = idx_raw.zfill(4)
        reg_p = f'HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Class\\{{4d36e972-e325-11ce-bfc1-08002be10318}}\\{idx}'
        
        if revert:
            cmd = f'reg delete "{reg_p}" /v "NetworkAddress" /f'
        else:
            new_mac = get_random_mac('win')
            cmd = f'reg add "{reg_p}" /v "NetworkAddress" /t REG_SZ /d {new_mac} /f'

        subprocess.run(cmd, shell=True, check=True)
        
        # Restart adapter using netsh (more reliable for some drivers)
        subprocess.run(f'netsh interface set interface "{iface}" disable', shell=True)
        time.sleep(2)
        subprocess.run(f'netsh interface set interface "{iface}" enable', shell=True)
        print(f"\033[92m[+] Success: {iface} updated.\033[0m")
    except Exception as e:
        print(f"\033[91m[-] Win Error: {e}\033[0m")

def linux_engine(iface, revert=False):
    try:
        subprocess.run(["sudo", "ip", "link", "set", "dev", iface, "down"], check=True)
        if revert:
            print("[!] Manual hardware reset triggered.")
            # Note: Linux reset often requires specific driver reloading or ethtool
        else:
            new_mac = get_random_mac()
            subprocess.run(["sudo", "ip", "link", "set", "dev", iface, "address", new_mac], check=True)
        subprocess.run(["sudo", "ip", "link", "set", "dev", iface, "up"], check=True)
        print(f"\033[92m[+] Success on {iface}\033[0m")
    except Exception as e:
        print(f"\033[91m[-] Linux Error: {e}\033[0m")

def macos_engine(iface):
    new_mac = get_random_mac()
    try:
        subprocess.run(["sudo", "ifconfig", iface, "ether", new_mac], check=True)
        print(f"\033[92m[+] macOS Success: {new_mac}\033[0m")
    except Exception as e:
        print(f"\033[91m[-] macOS Error: {e}\033[0m")

def run():
    print(f"\n\033[94m[*] SOGGABOARD UNIVERSAL SPOOFER\033[0m")
    
    # OS DETECTION
    if sys.platform == "win32":
        os_label = "Windows"
    elif sys.platform == "darwin":
        os_label = "macOS"
    elif sys.platform.startswith("linux"):
        os_label = "Linux"
    else:
        os_label = "Unknown"

    print(f"[*] Detected Platform: \033[93m{os_label}\033[0m")

    if os_label == "Unknown":
        print("[-] Error: OS not supported.")
        return

    ifaces = list(psutil.net_if_addrs().keys())
    for i, n in enumerate(ifaces): 
        print(f" [{i}] {n}")
    
    try:
        c = input("\nSelect Interface >> ")
        if not c.isdigit() or int(c) >= len(ifaces): return
        target = ifaces[int(c)]
        
        mode = input("[S]poof or [R]evert? >> ").lower()
        rev = (mode == 'r')

        # DISPATCH TO CORRECT ENGINE
        if os_label == "Windows":
            windows_engine(target, rev)
        elif os_label == "Linux":
            linux_engine(target, rev)
        elif os_label == "macOS":
            macos_engine(target)
            
    except KeyboardInterrupt: pass
    input("\n[!] Process Finished. Press Enter...")
