import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

class StockMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Monitor")
        self.root.geometry("900x700")
        
        self.config_file = "config.json"
        self.monitoring_threads = {}
        self.last_status = {}
        self.last_email_sent = {}
        self.refresh_labels = []
        
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
        
        # Refresh Indicator Label
        refresh_label = tk.Label(frame, text="", font=("Arial", 9, "italic"), 
                                fg="blue", bg="lightyellow", pady=2)
        refresh_label.pack(fill="x", padx=10, pady=(5, 0))
        refresh_label.pack_forget()  # Hide initially
        
        # Store refresh label for later access
        if not hasattr(self, 'refresh_labels'):
            self.refresh_labels = []
        self.refresh_labels.append(refresh_label)
        
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
        """Check if product is in stock using Selenium"""
        driver = None
        try:
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Get the directory where this script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            chromedriver_path = os.path.join(script_dir, 'chromedriver.exe')
            
            # Check if chromedriver exists in script directory
            if os.path.exists(chromedriver_path):
                print(f"Using ChromeDriver at: {chromedriver_path}")
                service = Service(chromedriver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # Try without explicit path (will search in PATH/system32)
                print("ChromeDriver not found in script directory, trying system PATH...")
                driver = webdriver.Chrome(options=chrome_options)
            
            driver.set_page_load_timeout(30)
            
            # Load the page
            driver.get(url)
            
            # Wait for page to load (wait for body element)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Give extra time for dynamic content to load
            time.sleep(3)
            
            # Get page source after JavaScript execution
            page_source = driver.page_source.lower()
            
            # Also try to find buttons/elements
            has_add_to_cart = False
            has_add_to_bag = False
            has_add_to_basket_enabled = False
            has_add_to_wishlist = False
            
            try:
                # Search for elements containing "add to cart"
                elements = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add to cart')]")
                if elements:
                    has_add_to_cart = True
            except:
                pass
            
            try:
                # Search for elements containing "add to bag"
                elements = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add to bag')]")
                if elements:
                    has_add_to_bag = True
            except:
                pass
            
            try:
                # Search for "add to basket" button and check if it has BLACK background
                basket_elements = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add to basket')]")
                print(f"DEBUG: Found {len(basket_elements)} 'add to basket' elements")
                
                if basket_elements:
                    # Check if the button is enabled (clickable) AND has black background
                    for idx, element in enumerate(basket_elements):
                        print(f"DEBUG: Checking element {idx + 1}")
                        print(f"  - is_enabled: {element.is_enabled()}")
                        print(f"  - is_displayed: {element.is_displayed()}")
                        
                        if element.is_enabled() and element.is_displayed():
                            # Additional check: verify it's not disabled via attribute
                            disabled_attr = element.get_attribute('disabled')
                            aria_disabled = element.get_attribute('aria-disabled')
                            
                            print(f"  - disabled attribute: {disabled_attr}")
                            print(f"  - aria-disabled: {aria_disabled}")
                            
                            if disabled_attr is None and aria_disabled != 'true':
                                # Check background color - must be black for in stock
                                try:
                                    bg_color = element.value_of_css_property('background-color')
                                    print(f"  - Background color: {bg_color}")
                                    
                                    # Convert to lowercase for comparison
                                    bg_color_lower = bg_color.lower()
                                    
                                    # Check if background is black or very dark
                                    # Black can be: rgb(0, 0, 0), rgba(0, 0, 0, 1), or very dark greys
                                    is_black = False
                                    
                                    if 'rgb' in bg_color_lower:
                                        # Extract RGB values
                                        rgb_values = re.findall(r'\d+', bg_color_lower)
                                        if len(rgb_values) >= 3:
                                            r, g, b = int(rgb_values[0]), int(rgb_values[1]), int(rgb_values[2])
                                            print(f"  - RGB values: R={r}, G={g}, B={b}")
                                            # Consider it black if all RGB values are below 50 (dark enough)
                                            if r < 50 and g < 50 and b < 50:
                                                is_black = True
                                                print(f"  - Is black: YES - Marking as IN STOCK")
                                            else:
                                                print(f"  - Is black: NO - Button is not black (likely grey/disabled)")
                                    
                                    if is_black:
                                        has_add_to_basket_enabled = True
                                        break
                                    else:
                                        print(f"  - Skipping this button - background is not black")
                                except Exception as color_error:
                                    print(f"  - Error getting color: {color_error}")
                                    # If we can't get color, DO NOT fall back - be strict
                                    print(f"  - Cannot verify color, skipping this element")
            except Exception as e:
                print(f"DEBUG: Error in basket check: {e}")
                pass
            
            try:
                # Search for elements containing "add to wishlist"
                elements = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add to wishlist')]")
                if elements:
                    has_add_to_wishlist = True
            except:
                pass
            
            # Fallback to page source search (only for cart and bag, not basket)
            if not has_add_to_cart and not has_add_to_bag and not has_add_to_basket_enabled and not has_add_to_wishlist:
                has_add_to_cart = 'add to cart' in page_source
                has_add_to_bag = 'add to bag' in page_source
                has_add_to_wishlist = 'add to wishlist' in page_source
            
            # Determine stock status (prioritize "add to cart", "add to bag", or enabled "add to basket")
            if has_add_to_cart or has_add_to_bag or has_add_to_basket_enabled:
                return 'in_stock'
            elif has_add_to_wishlist:
                return 'out_of_stock'
            else:
                return 'unknown'
                
        except TimeoutException:
            return 'error: Page load timeout'
        except WebDriverException as e:
            error_msg = str(e).lower()
            if 'chrome' in error_msg or 'chromedriver' in error_msg:
                return f'error: ChromeDriver issue - Check installation and version match Chrome browser'
            return f'error: Browser error - {str(e)[:60]}'
        except Exception as e:
            return f'error: {str(e)[:50]}'
        finally:
            # Always close the driver
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
    def update_tab_color(self, tab_index, color):
        """Update the tab background color"""
        try:
            # Create a custom style for this tab
            style = ttk.Style()
            style_name = f"Monitor{tab_index}.TLabel"
            
            if color == "green":
                style.configure(style_name, background="green", foreground="white")
            elif color == "red":
                style.configure(style_name, background="red", foreground="white")
            elif color == "orange":
                style.configure(style_name, background="orange", foreground="white")
            else:  # default/gray
                style.configure(style_name, background="SystemButtonFace", foreground="black")
            
            # Note: ttk.Notebook tabs don't support direct color changes easily
            # We'll use the text prefix with unicode characters instead for better visibility
        except:
            pass
    
    def show_refresh_indicator(self, tab_index, show=True):
        """Show or hide the refresh indicator - must be called from main thread"""
        def update():
            try:
                if show:
                    self.refresh_labels[tab_index].config(text="🔄 Refreshing...")
                    self.refresh_labels[tab_index].pack(fill="x", padx=10, pady=(5, 0))
                else:
                    self.refresh_labels[tab_index].config(text="")
                    self.refresh_labels[tab_index].pack_forget()
            except:
                pass
        
        # Schedule the update on the main thread
        self.root.after(0, update)
    
    def send_email_alert(self, tab_index, url):
        """Send email alert when product comes in stock"""
        try:
            # Check if we should send email based on interval
            current_time = time.time()
            email_interval = self.config.get('email_interval', 300)
            
            if tab_index in self.last_email_sent:
                if current_time - self.last_email_sent[tab_index] < email_interval:
                    return
                    
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
            # Show refresh indicator
            self.show_refresh_indicator(tab_index, True)
            
            status = self.check_stock(url)
            
            # Hide refresh indicator
            self.show_refresh_indicator(tab_index, False)
            
            # Update UI - use root.after to ensure main thread updates
            def update_ui():
                try:
                    if status == 'in_stock':
                        self.status_labels[tab_index].config(text="IN STOCK - Add to Cart/Bag/Basket Available!", 
                                                             bg="green", fg="white")
                        # Update tab with green indicator - using text symbols instead of emoji
                        self.notebook.tab(tab_index, text=f"✓ [IN STOCK] Monitor {tab_index + 1}")
                        
                        # Send email if status changed
                        if self.last_status.get(tab_index) != 'in_stock':
                            threading.Thread(target=self.send_email_alert, args=(tab_index, url), daemon=True).start()
                            
                    elif status == 'out_of_stock':
                        self.status_labels[tab_index].config(text="OUT OF STOCK - Add to Wishlist Only", 
                                                             bg="red", fg="white")
                        # Update tab with red indicator
                        self.notebook.tab(tab_index, text=f"✗ [OUT] Monitor {tab_index + 1}")
                    else:
                        self.status_labels[tab_index].config(text=f"Status: {status}", 
                                                             bg="orange", fg="white")
                        # Update tab with warning indicator for errors/unknown
                        self.notebook.tab(tab_index, text=f"⚠ [ERROR] Monitor {tab_index + 1}")
                except:
                    pass
                                                     
            self.root.after(0, update_ui)
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