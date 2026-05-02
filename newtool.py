import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import os
import sys
from urllib.parse import urlparse

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    print("Please install colorama: pip install colorama")
    sys.exit(1)

def print_banner():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')
        
    banner = f"""{Fore.RED}
    ██████╗ ██████╗ ██╗   ██╗████████╗███████╗
    ██╔══██╗██╔══██╗██║   ██║╚══██╔══╝██╔════╝
    ██████╔╝██████╔╝██║   ██║   ██║   █████╗  
    ██╔══██╗██╔══██╗██║   ██║   ██║   ██╔══╝  
    ██████╔╝██║  ██║╚██████╔╝   ██║   ███████╗
    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚══════╝
{Fore.YELLOW}        Advanced Web Fuzzer Framework v1.0
{Style.RESET_ALL}"""
    print(banner)

def load_state(state_file):
    if not os.path.exists(state_file):
        return 0
    try:
        return int(open(state_file).read().strip())
    except:
        return 0

def save_state(i, state_file, lock):
    with lock:
        with open(state_file, "w") as f:
            f.write(str(i))

def wait_for_slot(lock, delay, last_req):
    with lock:
        now = time.time()
        elapsed = now - last_req[0]
        if elapsed < delay:
            time.sleep(delay - elapsed)
        last_req[0] = time.time()

def load_payloads(input_file):
    if not os.path.exists(input_file):
        print(f"{Fore.RED}[!] Error: {input_file} not found.{Style.RESET_ALL}")
        sys.exit(1)
    with open(input_file, "r") as f:
        return [line.strip() for line in f if line.strip()]

def save_non200(value, status, length, good_file, lock):
    with lock:
        with open(good_file, "a") as f:
            f.write(f"{value} | {status} | {length}\n")

def save_processed(value, processed_file, lock):
    with lock:
        with open(processed_file, "a") as f:
            f.write(value + "\n")

def send_request(value, index, url, headers, field_name, lock, delay, last_req, good_file, processed_file, state_file):
    wait_for_slot(lock, delay, last_req)
    
    data = {field_name: value}
    
    try:
        r = requests.post(url, headers=headers, data=data, allow_redirects=False, timeout=10)
        status = r.status_code
        length = len(r.text)
        
        if status == 200:
            print(f"{Fore.GREEN}[+] [{status}] {value}{Style.RESET_ALL}")
        elif status == 429:
            print(f"{Fore.YELLOW}[!] [{status}] Rate limited -> {value}{Style.RESET_ALL}")
            time.sleep(5)
        else:
            print(f"{Fore.CYAN}[*] [{status}] {value} (Len: {length}){Style.RESET_ALL}")
            save_non200(value, status, length, good_file, lock)
            
        save_processed(value, processed_file, lock)
        save_state(index, state_file, lock)
        
    except Exception as e:
        print(f"{Fore.RED}[-] {value} -> Timeout / Error{Style.RESET_ALL}")

def run():
    print_banner()
    
    url = input(f"{Fore.BLUE}[?] Target URL (e.g. https://site.com/login): {Style.RESET_ALL}").strip()
    if not url:
        print(f"{Fore.RED}[!] URL is required.{Style.RESET_ALL}")
        sys.exit(1)
        
    parsed_url = urlparse(url)
    origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": origin,
        "Referer": url
    }
    
    field_name = input(f"{Fore.BLUE}[?] Target Field Name (Default: card_number): {Style.RESET_ALL}").strip() or "card_number"
    input_file = input(f"{Fore.BLUE}[?] Payloads List File (Default: payloads.txt): {Style.RESET_ALL}").strip() or "payloads.txt"
    good_file = input(f"{Fore.BLUE}[?] Output File for hits (Default: hits.txt): {Style.RESET_ALL}").strip() or "hits.txt"
    
    try:
        rpm = int(input(f"{Fore.BLUE}[?] Requests per minute (Default: 200): {Style.RESET_ALL}") or 200)
    except:
        rpm = 200
        
    try:
        threads = int(input(f"{Fore.BLUE}[?] Threads (Default: 5): {Style.RESET_ALL}") or 5)
    except:
        threads = 5

    processed_file = "processed.txt"
    state_file = "state.txt"
    
    delay = 60.0 / rpm if rpm > 0 else 0
    lock = threading.Lock()
    last_req = [0.0]
    
    payloads = load_payloads(input_file)
    start = load_state(state_file)
    
    print(f"\n{Fore.MAGENTA}==================================================")
    print(f"[*] Initialization Complete")
    print(f"[*] Total Payloads : {len(payloads)}")
    print(f"[*] Resuming From  : {start}")
    print(f"[*] Target URL     : {url}")
    print(f"[*] Threads / RPM  : {threads} / {rpm}")
    print(f"=================================================={Style.RESET_ALL}\n")
    
    def worker(i):
        send_request(payloads[i], i, url, headers, field_name, lock, delay, last_req, good_file, processed_file, state_file)

    try:
        with ThreadPoolExecutor(max_workers=threads) as ex:
            ex.map(worker, range(start, len(payloads)))
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}[!] Aborted by user.{Style.RESET_ALL}")
        sys.exit(0)

if __name__ == "__main__":
    run()
