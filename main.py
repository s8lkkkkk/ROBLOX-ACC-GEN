import tkinter as tk
from tkinter import scrolledtext
import threading
import random
import string
import sys
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor

OUTPUT_FILE = "generated_accounts.txt"
MAX_WORKERS = 2  # parallel browsers

ASCII_BANNER = r"""
 /$$      /$$  /$$$$$$  /$$   /$$ /$$    /$$    /$$
| $$$    /$$$ /$$__  $$| $$  / $$| $$   | $$   | $$ 
| $$$$  /$$$$| $$  \__/|  $$/ $$/| $$   | $$   | $$ 
| $$ $$/$$ $$|  $$$$$$  \  $$$$/ | $$   |  $$ / $$/ 
| $$  $$$| $$ \____  $$  >$$  $$ | $$    \  $$ $$/  
| $$\  $ | $$ /$$  \ $$ /$$/\  $$| $$     \  $$$/  
| $$ \/  | $$|  $$$$$$/| $$  \ $$| $$$$$$$$\  $/   
|__/     |__/ \______/ |__/  |__/|________/ \_/    
"""

def print_banner(log_func):
    log_func(ASCII_BANNER)
    text = "Roblox Account Generator"
    border_len = len(text) + 4
    log_func("_" * border_len)
    log_func(f"| {text} |")
    log_func("-" * border_len)

def generate_username():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=7))

def generate_password():
    return ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=10))

def save_account_with_cookie(username, password, driver, webhook_url=None):
    cookies = driver.get_cookies()
    roblosec = next((c['value'] for c in cookies if c['name'] == ".ROBLOSECURITY"), None)
    if roblosec:
        line = f"{username}:{password}:{roblosec}"
        with open(OUTPUT_FILE, "a") as f:
            f.write(line + "\n")
        if webhook_url:
            try:
                requests.post(webhook_url, json={"content": line})
            except Exception:
                pass
        return True
    return False

def signup_roblox(username, password, webhook_url=None):
    options = Options()
    options.add_argument("--window-size=1024,768")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    service = Service(log_path='nul' if sys.platform == 'win32' else '/dev/null')
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get("https://www.roblox.com/signup")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "signup-username"))
        )
        driver.find_element(By.ID, "signup-username").send_keys(username)
        driver.find_element(By.ID, "signup-password").send_keys(password)

        from selenium.webdriver.support.ui import Select
        Select(driver.find_element(By.ID, "MonthDropdown")).select_by_index(random.randint(1, 12))
        Select(driver.find_element(By.ID, "DayDropdown")).select_by_index(random.randint(1, 28))
        Select(driver.find_element(By.ID, "YearDropdown")).select_by_index(random.randint(10, 30))

        if random.choice([True, False]):
            driver.find_element(By.ID, "MaleButton").click()
        else:
            driver.find_element(By.ID, "FemaleButton").click()

        signup_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "signup-button"))
        )
        signup_button.click()

        # Wait for roblox.com/home to confirm login
        WebDriverWait(driver, 300).until(lambda d: "roblox.com/home" in d.current_url)

        if save_account_with_cookie(username, password, driver, webhook_url):
            return True, f"{username}:{password} created with .ROBLOSECURITY!"
        else:
            return False, f"{username}: could not get .ROBLOSECURITY."

    except Exception as e:
        return False, f"Error: {username} -> {e}"

    finally:
        driver.quit()

class GeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Roblox Account Generator")
        self.root.configure(bg="#121212")
        fg_color = "#00FF00"
        bg_color = "#121212"

        self.banner = tk.Label(root, text=ASCII_BANNER, fg=fg_color, bg=bg_color,
                               font=("Courier", 10), justify=tk.LEFT)
        self.banner.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=5)

        self.webhook_label = tk.Label(root, text="Webhook URL (optional):", fg=fg_color, bg=bg_color)
        self.webhook_label.grid(row=1, column=0, sticky="w", padx=10)
        self.webhook_entry = tk.Entry(root, width=60)
        self.webhook_entry.grid(row=1, column=1, columnspan=2, pady=5, sticky="w")

        self.start_button = tk.Button(root, text="Start Generating", command=self.start_generating)
        self.start_button.grid(row=2, column=1, pady=10)

        self.log_area = scrolledtext.ScrolledText(root, width=85, height=25, bg="#222", fg=fg_color, insertbackground=fg_color)
        self.log_area.grid(row=3, column=0, columnspan=3, padx=10, pady=10)
        self.log_area.config(state=tk.DISABLED)
        self.log_area.tag_config("success", foreground="#00FF00")
        self.log_area.tag_config("fail", foreground="#FF4444")

        self.running = False

    def log(self, message, tag=None):
        self.log_area.config(state=tk.NORMAL)
        if tag:
            self.log_area.insert(tk.END, message + "\n", tag)
        else:
            self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def start_generating(self):
        self.start_button.config(state=tk.DISABLED)
        self.running = True
        threading.Thread(target=self.generate_thread, daemon=True).start()

    def generate_thread(self):
        print_banner(self.log)

        def worker(index):
            while self.running:
                username = generate_username()
                password = generate_password()
                webhook_url = self.webhook_entry.get().strip() or None
                success, message = signup_roblox(username, password, webhook_url)
                if success:
                    self.log(message, "success")
                else:
                    self.log(message, "fail")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for i in range(MAX_WORKERS):
                executor.submit(worker, i)

if __name__ == "__main__":
    root = tk.Tk()
    gui = GeneratorGUI(root)
    root.mainloop()
