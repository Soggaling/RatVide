import os
import sys
import random
import subprocess
import psutil
import re

# Platform-Specific Detection
IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

if IS_WINDOWS:
    import winreg

def get_random_mac(mode='unix'):
    """Generates a MAC compliant with the target OS requirements."""
    if mode == 'win':
        char2 = random.choice("26AE")
        mac = f"0{char2}" + "".join(f"{random.randint(0, 255):02X}" for _ in range(5))
        return mac
    else:
        mac = [0x00, 0x16, 0x3e, random.randint(0x00, 0x7f), 
               random.randint(0x00, 0xff), random.randint(0x00, 0xff)]
        return ':'.join(f"{x:02x}" for x in mac)

def windows_engine(iface, revert=False):
    reg_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as base_key:
            for i in range(winreg.QueryInfoKey(base_key)[0]):
                sub_name = winreg.EnumKey(base_key, i)
                with winreg.OpenKey(base_key, sub_name, 0, winreg.KEY_ALL_ACCESS) as sub_key:
                    try:
                        driver_desc, _ = winreg.QueryValueEx(sub_key, "DriverDesc")
                        if driver_desc == iface:
                            if revert:
                                winreg.DeleteValue(sub_key, "NetworkAddress")
                                print(f"[+] Reverted {iface} to original HWID.")
                            else:
                                new_mac = get_random_mac('win')
                                winreg.SetValueEx(sub_key, "NetworkAddress", 0, winreg.REG_SZ, new_mac)
                                print(f"[+] Spoofed {iface} to {new_mac}")
                            
                            subprocess.run(f'netsh interface set interface "{iface}" disable', shell=True)
                            subprocess.run(f'netsh interface set interface "{iface}" enable', shell=True)
                            return
                    except: continue
    except Exception as e: print(f"[-] Windows Reg Error: {e}")

def linux_engine(iface, revert=False):
    has_macchanger = subprocess.call(["which", "macchanger"], stdout=subprocess.DEVNULL) == 0
    
    try:
        subprocess.run(["sudo", "ip", "link", "set", "dev", iface, "down"], check=True)
        if revert:
            if has_macchanger:
                subprocess.run(["sudo", "macchanger", "-p", iface])
            else:
                print("[!] Linux requires reboot or manual entry to revert without macchanger.")
        else:
            if has_macchanger:
                subprocess.run(["sudo", "macchanger", "-r", iface])
            else:
                new_mac = get_random_mac()
                subprocess.run(["sudo", "ip", "link", "set", "dev", iface, "address", new_mac], check=True)
                print(f"[+] Manually assigned {new_mac} to {iface}")
        subprocess.run(["sudo", "ip", "link", "set", "dev", iface, "up"], check=True)
    except Exception as e: print(f"[-] Linux Link Error: {e}")

def macos_engine(iface):
    new_mac = get_random_mac()
    try:
        subprocess.run(["sudo", "ifconfig", iface, "ether", new_mac], check=True)
        print(f"[+] macOS ether address updated to {new_mac}")
    except Exception as e: print(f"[-] macOS Config Error: {e}")

def run():
    print(f"\n\033[94m[*] SOGGABOARD MULTI-OS SPOOFER\033[0m")
    
    os_name = "Windows" if IS_WINDOWS else "macOS" if IS_MAC else "Linux"
    print(f"[*] Platform Detected: \033[93m{os_name}\033[0m")

    interfaces = list(psutil.net_if_addrs().keys())
    for i, name in enumerate(interfaces):
        print(f" [{i}] {name}")
    
    choice = input("\nSelect Interface >> ")
    if not choice.isdigit() or int(choice) >= len(interfaces): return
    target = interfaces[int(choice)]

    mode = input("[S]poof or [R]evert? >> ").lower()
    do_revert = (mode == 'r')
  
    if IS_WINDOWS:
        windows_engine(target, revert=do_revert)
    elif IS_LINUX:
        linux_engine(target, revert=do_revert)
    elif IS_MAC:
        if do_revert:
            print("[!] On macOS, please toggle Wi-Fi Off/On to revert.")
        else:
            macos_engine(target)
    else:
        print("[-] Unsupported Operating System.")

    input("\n[!] Process Complete. Press Enter...")
