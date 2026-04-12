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
        idx_raw = subprocess.check_output(f'wmic nic where "NetConnectionID=\'{iface}\'" get Index', shell=True).decode()
        idx = re.findall(r'\d+', idx_raw)[0].zfill(4)
        reg_p = f'HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Class\\{{4d36e972-e325-11ce-bfc1-08002be10318}}\\{idx}'
        
        if revert:
            cmd = f'reg delete "{reg_p}" /v "NetworkAddress" /f'
        else:
            new_mac = get_random_mac('win')
            cmd = f'reg add "{reg_p}" /v "NetworkAddress" /t REG_SZ /d {new_mac} /f'

        subprocess.run(cmd, shell=True, check=True)
        subprocess.run(f'netsh interface set interface "{iface}" disable', shell=True)
        time.sleep(2)
        subprocess.run(f'netsh interface set interface "{iface}" enable', shell=True)
        print(f"\033[92m[+] Success: {iface} updated via Windows Registry.\033[0m")
    except Exception as e:
        print(f"\033[91m[-] Win Error: {e}\033[0m")

def linux_engine(iface, revert=False):
    has_mc = subprocess.call(["which", "macchanger"], stdout=subprocess.DEVNULL) == 0
    try:
        subprocess.run(["sudo", "ip", "link", "set", "dev", iface, "down"], check=True)
        if revert:
            if has_mc: 
                subprocess.run(["sudo", "macchanger", "-p", iface])
            else: 
                print("[!] Manual revert required without macchanger.")
        else:
            if has_mc: 
                subprocess.run(["sudo", "macchanger", "-r", iface])
            else:
                new_mac = get_random_mac()
                subprocess.run(["sudo", "ip", "link", "set", "dev", iface, "address", new_mac], check=True)
                print(f"[+] Manually assigned {new_mac}")
        subprocess.run(["sudo", "ip", "link", "set", "dev", iface, "up"], check=True)
        print(f"\033[92m[+] Success: {iface} link updated.\033[0m")
    except Exception as e:
        print(f"\033[91m[-] Linux Error: {e}\033[0m")

def macos_engine(iface):
    new_mac = get_random_mac()
    try:
        subprocess.run(["sudo", "ifconfig", iface, "ether", new_mac], check=True)
        print(f"\033[92m[+] macOS Success: {iface} set to {new_mac}\033[0m")
    except Exception as e:
        print(f"\033[91m[-] macOS Error: {e}\033[0m")

def run():
    print(f"\n\033[94m[*] SOGGABOARD UNIVERSAL SPOOFER\033[0m")
    
    is_win = sys.platform == "win32"
    is_mac = sys.platform == "darwin"
    is_linux = sys.platform.startswith("linux")
    
    os_label = "Windows" if is_win else "macOS" if is_mac else "Linux" if is_linux else "Unknown"
    print(f"[*] Detected Platform: \033[93m{os_label}\033[0m")

    if os_label == "Unknown":
        print("[-] OS Not Supported.")
        return

    ifaces = list(psutil.net_if_addrs().keys())
    for i, n in enumerate(ifaces): 
        print(f" [{i}] {n}")
    
    try:
        c = input("\nSelect Interface >> ")
        if not c.isdigit() or int(c) >= len(ifaces): 
            return
            
        target = ifaces[int(c)]
        mode = input("[S]poof or [R]evert? >> ").lower()
        rev = (mode == 'r')

        if is_win:
            windows_engine(target, rev)
        elif is_linux:
            linux_engine(target, rev)
        elif is_mac:
            if rev:
                print("[!] macOS revert requires a manual Wi-Fi toggle or reboot.")
            else:
                macos_engine(target)
                
    except KeyboardInterrupt: 
        pass
    except Exception as e:
        print(f"[-] Execution Error: {e}")
        
    input("\n[!] Process Finished. Press Enter...")
