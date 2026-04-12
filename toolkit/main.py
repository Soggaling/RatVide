import os
import sys
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def banner():
    print(f"""
    \033[92m
    🔱 SOGGABOARD TOOLKIT v1.0
    --------------------------
    [ SYSTEM: {sys.platform.upper()} ]
    [ STATUS: READY ]
    \033[0m
    """)

def main_menu():
    while True:
        clear()
        banner()
        print(" [1] IP Grabber")
        print(" [2] MAC Spoofer")
        print(" [3] Recon Kit")
        print(" [Q] Exit Toolkit")
        
        choice = input("\n>> ").lower()

        if choice == '1':
            from modules import ip_grabber
            ip_grabber.run()
        elif choice == '2':
            from modules import mac_spoofer
            mac_spoofer.run()
        elif choice == 'q':
            print("Shutting down...")
            break
        else:
            print("Invalid Sector.")
            import time
            time.sleep(1)

if __name__ == "__main__":
    main_menu()
