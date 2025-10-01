import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import requests
from bs4 import BeautifulSoup
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

class StockMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Monitor")
        self.root.geometry("900x700")
        
        self.config_file = "config.json"
        self.monitoring_threads = {}
        self.last_status = {}
        self.last_email_sent = {}
        
        self.load_config()
        self.create_ui()
        
    def load_config(self):
        """Load configuration from JSON file"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                'email_to': '',
                'email_from': '',
                'email_password': '',
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'email_interval': 300,
                'tabs': [
                    {'url': '', 'interval': 60} for _ in range(5)
                ]
            }
            
    def save_config(self):
        """Save configuration to JSON file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
            
    def create_ui(self):
        """Create the user interface"""
        # Email Settings Frame
        email_frame = ttk.LabelFrame(self.root, text="Email Settings", padding=10)
        email_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(email_frame, text="Your Email (From):").grid(row=0, column=0, sticky="w", padx=5)
        self.email_from_entry = ttk.Entry(email_frame, width=30)
        self.email_from_entry.grid(row=0, column=1, padx=5)
        self.email_from_entry.insert(0, self.config.get('email_from', ''))
        
        ttk.Label(email_frame, text="App Password:").grid(row=0, column=2, sticky="w", padx=5)
        self.email_password_entry = ttk.Entry(email_frame, width=20, show="*")
        self.email_password_entry.grid(row=0, column=3, padx=5)
        self.email_password_entry.insert(0, self.config.get('email_password', ''))
        
        ttk.Label(email_frame, text="Alert Email (To):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.email_to_entry = ttk.Entry(email_frame, width=30)
        self.email_to_entry.grid(row=1, column=1, padx=5, pady=5)
        self.email_to_entry.insert(0, self.config.get('email_to', ''))
        
        ttk.Label(email_frame, text="Email Interval (sec):").grid(row=1, column=2, sticky="w", padx=5)
        self.email_interval_entry = ttk.Entry(email_frame, width=20)
        self.email_interval_entry.grid(row=1, column=3, padx=5)
        self.email_interval_entry.insert(0, str(self.config.get('email_interval', 300)))
        
        ttk.Button(email_frame, text="Save Settings", command=self.save_settings).grid(row=2, column=3, pady=5)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.tab_frames = []
        self.url_entries = []
        self.interval_entries = []
        self.status_labels = []
        self.start_buttons = []
        self.stop_buttons = []
        
        for i in range(5):
            self.create_monitor_tab(i)
            
    def create_monitor_tab(self, index):
        """Create a monitor tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=f"Monitor {index + 1}")
        self.tab_frames.append(frame)
        
        # URL Input
        ttk.Label(frame, text="Product URL:").pack(anchor="w", padx=10, pady=(10, 0))
        url_entry = ttk.Entry(frame, width=80)
        url_entry.pack(fill="x", padx=10, pady=5)
        url_entry.insert(0, self.config['tabs'][index]['url'])
        self.url_entries.append(url_entry)
        
        # Interval Input
        interval_frame = ttk.Frame(frame)
        interval_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(interval_frame, text="Check Interval (seconds):").pack(side="left")
        interval_entry = ttk.Entry(interval_frame, width=10)
        interval_entry.pack(side="left", padx=5)
        interval_entry.insert(0, str(self.config['tabs'][index]['interval']))
        self.interval_entries.append(interval_entry)
        
        # Control Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        start_btn = ttk.Button(button_frame, text="Start Monitoring", 
                               command=lambda i=index: self.start_monitoring(i))
        start_btn.pack(side="left", padx=5)
        self.start_buttons.append(start_btn)
        
        stop_btn = ttk.Button(button_frame, text="Stop Monitoring", 
                              command=lambda i=index: self.stop_monitoring(i), state="disabled")
        stop_btn.pack(side="left", padx=5)
        self.stop_buttons.append(stop_btn)
        
        # Status Display
        status_frame = ttk.LabelFrame(frame, text="Status", padding=10)
        status_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        status_label = tk.Label(status_frame, text="Not monitoring", 
                               font=("Arial", 12), bg="gray", fg="white", pady=20)
        status_label.pack(fill="both", expand=True)
        self.status_labels.append(status_label)
        
    def save_settings(self):
        """Save all settings to config"""
        try:
            self.config['email_from'] = self.email_from_entry.get()
            self.config['email_password'] = self.email_password_entry.get()
            self.config['email_to'] = self.email_to_entry.get()
            self.config['email_interval'] = int(self.email_interval_entry.get())
            
            for i in range(5):
                self.config['tabs'][i]['url'] = self.url_entries[i].get()
                self.config['tabs'][i]['interval'] = int(self.interval_entries[i].get())
                
            self.save_config()
            messagebox.showinfo("Success", "Settings saved successfully!")
        except ValueError:
            messagebox.showerror("Error", "Invalid interval value. Please enter numbers only.")
            
    def check_stock(self, url):
        """Check if product is in stock"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text().lower()
            
            # Check for stock status
            if 'add to cart' in page_text:
                return 'in_stock'
            elif 'add to wishlist' in page_text:
                return 'out_of_stock'
            else:
                return 'unknown'
                
        except Exception as e:
            return f'error: {str(e)}'
            
    def send_email_alert(self, tab_index, url):
        """Send email alert when product comes in stock"""
        try:
            # Check if we should send email based on interval
            current_time = time.time()
            email_interval = self.config.get('email_interval', 300)
            
            if tab_index in self.last_email_sent:
                if current_time - self.last_email_sent[tab_index] < email_interval:
                    return  # Don't send email yet
                    
            msg = MIMEMultipart()
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['email_to']
            msg['Subject'] = f'Stock Alert - Monitor {tab_index + 1}'
            
            body = f"""
            Product is now IN STOCK!
            
            Monitor: {tab_index + 1}
            URL: {url}
            Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            Check it out now!
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.config.get('smtp_server', 'smtp.gmail.com'), 
                                 self.config.get('smtp_port', 587))
            server.starttls()
            server.login(self.config['email_from'], self.config['email_password'])
            server.send_message(msg)
            server.quit()
            
            self.last_email_sent[tab_index] = current_time
            
        except Exception as e:
            print(f"Email error: {str(e)}")
            
    def monitor_loop(self, tab_index):
        """Main monitoring loop for a tab"""
        url = self.url_entries[tab_index].get()
        interval = int(self.interval_entries[tab_index].get())
        
        while self.monitoring_threads.get(tab_index, {}).get('running', False):
            status = self.check_stock(url)
            
            # Update UI
            if status == 'in_stock':
                self.status_labels[tab_index].config(text="IN STOCK - Add to Cart Available!", 
                                                     bg="green", fg="white")
                self.notebook.tab(tab_index, text=f"✓ Monitor {tab_index + 1}")
                
                # Send email if status changed
                if self.last_status.get(tab_index) != 'in_stock':
                    threading.Thread(target=self.send_email_alert, args=(tab_index, url), daemon=True).start()
                    
            elif status == 'out_of_stock':
                self.status_labels[tab_index].config(text="OUT OF STOCK - Add to Wishlist Only", 
                                                     bg="red", fg="white")
                self.notebook.tab(tab_index, text=f"✗ Monitor {tab_index + 1}")
            else:
                self.status_labels[tab_index].config(text=f"Status: {status}", 
                                                     bg="orange", fg="white")
                                                     
            self.last_status[tab_index] = status
            
            time.sleep(interval)
            
    def start_monitoring(self, tab_index):
        """Start monitoring a tab"""
        url = self.url_entries[tab_index].get()
        
        if not url:
            messagebox.showerror("Error", "Please enter a URL first!")
            return
            
        if not self.config.get('email_from') or not self.config.get('email_password'):
            messagebox.showwarning("Warning", "Email settings not configured. Monitoring will work but no alerts will be sent.")
            
        self.monitoring_threads[tab_index] = {'running': True}
        thread = threading.Thread(target=self.monitor_loop, args=(tab_index,), daemon=True)
        thread.start()
        
        self.start_buttons[tab_index].config(state="disabled")
        self.stop_buttons[tab_index].config(state="normal")
        self.status_labels[tab_index].config(text="Starting monitoring...", bg="blue", fg="white")
        
    def stop_monitoring(self, tab_index):
        """Stop monitoring a tab"""
        if tab_index in self.monitoring_threads:
            self.monitoring_threads[tab_index]['running'] = False
            
        self.start_buttons[tab_index].config(state="normal")
        self.stop_buttons[tab_index].config(state="disabled")
        self.status_labels[tab_index].config(text="Monitoring stopped", bg="gray", fg="white")
        self.notebook.tab(tab_index, text=f"Monitor {tab_index + 1}")

if __name__ == "__main__":
    root = tk.Tk()
    app = StockMonitor(root)
    root.mainloop()