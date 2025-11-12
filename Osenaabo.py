import sys
import subprocess
import importlib
import os
from PIL import Image, ImageTk
import re
import shutil
import io
import json
import base64
from io import BytesIO
import threading
import time
import tempfile
import traceback
from tkinter import messagebox
from datetime import datetime, time as dt_time, timezone, date, timedelta
import tkinter as tk
from tkinter import messagebox, simpledialog
import customtkinter as ctk
import pyautogui
import keyboard
import requests
import gc
import pytz
import winsound
import pytesseract
import logging
import atexit
import webbrowser
import hashlib
import uuid
import platform

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("OpenCV not available - using fallback methods")

# OpenCV availability check
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
    print("✅ OpenCV loaded successfully")
except ImportError as e:
    OPENCV_AVAILABLE = False
    print(f"⚠️ OpenCV not available: {e}")
    # Create dummy classes for fallback
    class cv2:
        @staticmethod
        def imread(*args, **kwargs):
            return None
        @staticmethod
        def imwrite(*args, **kwargs):
            return False
        @staticmethod
        def cvtColor(*args, **kwargs):
            return None
        COLOR_BGR2GRAY = 6
        COLOR_RGB2BGR = 4
    class np:
        @staticmethod
        def array(*args, **kwargs):
            return list(args[0]) if args else []
        @staticmethod
        def zeros(*args, **kwargs):
            return [0] * (args[0] if args else 1)
        uint8 = int

# Platform detection
IS_MAC = platform.system() == 'Darwin'
IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'

# Platform-specific adjustments
if IS_MAC:
    MAC_FONT_SIZE_ADJUSTMENT = -1
    MAC_BUTTON_HEIGHT = 28
    MAC_ENTRY_HEIGHT = 30
else:
    MAC_FONT_SIZE_ADJUSTMENT = 0
    MAC_BUTTON_HEIGHT = 32
    MAC_ENTRY_HEIGHT = 32

def cleanup_tkinter():
    """Clean up Tkinter to prevent 'invalid command name' errors"""
    try:
        if hasattr(tk, '_default_root') and tk._default_root:
            tk._default_root.quit()
            tk._default_root.destroy()
    except:
        pass

atexit.register(cleanup_tkinter)

# ======== HARDWARE LOCKING FUNCTIONS ========
def get_hardware_id():
    """Generate unique hardware fingerprint (SAME as get_user_hwid.py)"""
    info = ""
    try:
        # Windows: Use MAC + CPUID fallback
        if IS_WINDOWS:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 48, 8)][::-1])
            info += mac
            info += platform.processor() or ""
        # Linux
        elif IS_LINUX:
            with open("/etc/machine-id", "r") as f:
                info += f.read().strip()
        # macOS
        elif IS_MAC:
            result = subprocess.run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                                  capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if "IOPlatformUUID" in line:
                    info += line.split('=')[-1].strip().strip('"')
                    break
        info += platform.node()  # Hostname
    except Exception as e:
        # Fallback
        info = str(uuid.getnode()) + platform.node()
    
    return hashlib.sha256(info.encode()).hexdigest()[:32]

def get_hardware_fingerprint():
    """Get readable hardware fingerprint for display"""
    hardware_id = get_hardware_id()
    return f"PC_{hardware_id.upper()}"

# ---------------------------
# Data Directory Management
# ---------------------------
def get_data_directory():
    """Get a writable data directory - ALWAYS use AppData for installed apps"""
    try:
        # Always use AppData for installed applications
        appdata_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'Osenaabo')
        os.makedirs(appdata_dir, exist_ok=True)
        print(f"Using AppData directory: {appdata_dir}")
        return appdata_dir
    except Exception as e:
        print(f"Error getting data directory: {e}")
        # Emergency fallback to temp directory
        temp_dir = os.path.join(tempfile.gettempdir(), 'Osenaabo')
        os.makedirs(temp_dir, exist_ok=True)
        print(f"Using temp directory as fallback: {temp_dir}")
        return temp_dir

# ---------------------------
# Resource Extraction
# ---------------------------
def get_resource_path(relative_path):
    """Get the absolute path to a resource, works for dev and PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)

# Import the core wrapper
try:
    import osenaabo_core 
except ImportError:
    print("osenaabo_core not found - core functionality disabled")
    osenaabo_core = None

# ======== FIXED LICENSE MANAGER IMPORT ========
import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

validate_license = None

# Try multiple import methods
try:
    from license_manager import validate_license
    print("✅ License manager imported from current directory")
except ImportError as e:
    print(f"❌ Current directory import failed: {e}")
    
    try:
        # Try license subdirectory
        license_dir = os.path.join(current_dir, 'license')
        if license_dir not in sys.path:
            sys.path.insert(0, license_dir)
        from license_manager import validate_license
        print("✅ License manager imported from license subdirectory")
    except ImportError as e:
        print(f"❌ License subdirectory import failed: {e}")

# Final fallback
if validate_license is None:
    print("⚠️  Using license validation fallback")
    def validate_license_fallback(validation_input):
        return {"valid": False, "message": "License validation not available"}
    validate_license = validate_license_fallback

# ======== FIXED PYGAME IMPORT ========
try:
    import pygame
    PYGAME_AVAILABLE = True
    print("✅ Pygame imported successfully")
except ImportError as e:
    print(f"❌ Pygame not available: {e}")
    pygame = None
    PYGAME_AVAILABLE = False

def extract_bundled_files():
    """Extract bundled text files to the writable data directory"""
    bundled_files = {
        'readme.txt': """=== Welcome to OSENAABO! (The 3rd 👁️) ===

Thank you for installing OSENAABO!, a high-frequency trading bot for virtual crash markets.""",
        'TESSERACT_GUIDE.txt': r"""Tesseract-OCR Installation Guide
================================

Tesseract-OCR is required for optical character recognition in OSENAABO!.

Installation Steps for Windows:
1. Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer and follow the prompts.
3. During installation, select 'Add Tesseract to PATH' or manually add the installation directory (e.g., C:\Program Files\Tesseract-OCR) to your system PATH.""",
        'INSTALLATION_GUIDE.txt': """OSENAABO! Installation Guide
============================

REQUIRED SOFTWARE:
1. Python 3.8 or newer (https://python.org)
2. Tesseract-OCR (https://github.com/UB-Mannheim/tesseract/wiki)
3. Required Python packages"""
    }
    
    # USE THE DATA DIRECTORY FUNCTION - NOT current file location
    current_dir = get_data_directory()
    print(f"Extracting files to: {current_dir}")
    
    for dir_name in ['assets', 'license', 'logs', 'sessions']:
        dir_path = os.path.join(current_dir, dir_name)
        try:
            os.makedirs(dir_path, exist_ok=True)
            print(f"Created directory: {dir_path}")
        except Exception as e:
            print(f"Warning: Could not create directory {dir_path}: {e}")
    
    for filename, content in bundled_files.items():
        file_path = os.path.join(current_dir, filename)
        if not os.path.exists(file_path):
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Created file: {file_path}")
            except Exception as e:
                print(f"Warning: Could not create file {file_path}: {e}")

def setup_environment():
    """Setup and verify the runtime environment"""
    extract_bundled_files()
    
    if sys.version_info < (3, 8):
        messagebox.showerror(
            "Python Version Error",
            "Python 3.8 or newer is required!\n\nPlease download from: https://python.org"
        )
        sys.exit(1)
    
    requirements = {
        'customtkinter': 'customtkinter',
        'PIL': 'pillow', 
        'pyautogui': 'pyautogui',
        'keyboard': 'keyboard',
        'pygame': 'pygame',
        'pygetwindow': 'pygetwindow',
        'pynput': 'pynput'
    }
    
    missing = []
    
    for import_name, pip_name in requirements.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(pip_name)
    
    if missing:
        install_missing_packages(missing)
    
    create_directories()

def install_missing_packages(missing_packages):
    """Install missing packages with user confirmation"""
    response = messagebox.askyesno(
        "Install Dependencies",
        f"Missing packages detected:\n\n{', '.join(missing_packages)}\n\nWould you like to install them automatically?"
    )
    
    if response:
        try:
            for package in missing_packages:
                print(f"Installing {package}...")
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", package,
                    "--user", "--upgrade"
                ])
            
            messagebox.showinfo("Success", "Dependencies installed successfully!\nRestarting application...")
            os.execl(sys.executable, sys.executable, *sys.argv)
            
        except Exception as e:
            messagebox.showerror("Installation Failed", f"Failed to install: {e}")
            sys.exit(1)
    else:
        show_manual_instructions(missing_packages)

def create_directories():
    """Create necessary application directories"""
    dirs = ['assets', 'license', 'logs', 'sessions']
    data_dir = get_data_directory()
    for dir_name in dirs:
        os.makedirs(os.path.join(data_dir, dir_name), exist_ok=True)

def show_manual_instructions(missing_packages):
    """Show manual installation instructions"""
    instructions = f"MANUAL INSTALLATION REQUIRED\n\nPlease install: pip install {' '.join(missing_packages)}"
    messagebox.showinfo("Manual Installation Required", instructions)
    sys.exit(1)

# Run environment setup
setup_environment()

# ---------------------------
# Constants / config
# ---------------------------
BASE64_LOGO = "AAABAAkAEBAAAAEAIABoBAAAlgAAABgYAAABACAAiAkAAP4EAAA="

APP_TITLE = "OSENAABO! - The 3rd 👁️"
APP_SUB1 = "A High-Frequency Trading Bot For Virtual Crash Markets"
APP_SUB2 = ""
WINDOW_W, WINDOW_H = 1000, 650
MIN_W, MIN_H = 350, 550

# Updated file paths to use data directory
def get_license_path():
    return os.path.join(get_data_directory(), "license.json")

def get_coords_path():
    return os.path.join(get_data_directory(), "aviator_coordinates.json")

def get_config_path():
    return os.path.join(get_data_directory(), "config.json")

def get_validation_state_path():
    return os.path.join(get_data_directory(), "validation_state.json")

LICENSE_FILE = get_license_path()
COORDS_FILE = get_coords_path()
CONFIG_FILE = get_config_path()
VALIDATION_STATE_FILE = get_validation_state_path()

DEFAULT_STOP_LOSS = 20.0
PUBLIC_KEY_FILE = os.path.join(get_data_directory(), "license", "public.pem")
ASSETS_DIR = os.path.join(get_data_directory(), "assets")
CLAP_SOUND = os.path.join(ASSETS_DIR, "clap.wav")
FOUND_SOUND = os.path.join(ASSETS_DIR, "found.wav")
SESSIONS_DIR = os.path.join(get_data_directory(), "sessions")

# Platform URL configuration
PLATFORM_URLS = {
    "SportyBetNg": "https://www.sportybet.com/ng/",
    "BetwayNg": "https://www.betway.com.ng/"
}

# ======== LICENSE FILE FUNCTIONS ========

def load_license_json():
    """Load license data - ALWAYS returns dict, never None"""
    if not os.path.exists(LICENSE_FILE):
        return {}  # Return empty dict
    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}  # Return empty dict on error

def save_license_json(data):
    """Save license data"""
    try:
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False

def save_config_json(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_config_json():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_coords_json(data):
    with open(COORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_coords_json():
    if not os.path.exists(COORDS_FILE):
        return {}
    try:
        with open(COORDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_validation_state(state):
    """Save validation state to persist across refreshes"""
    try:
        with open(VALIDATION_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass

def load_validation_state():
    """Load validation state after refresh"""
    if not os.path.exists(VALIDATION_STATE_FILE):
        return {
            "validation_counter": 0,
            "last_payout": None,
            "sequence_completed": False,
            "blocks_setup": False,
            "pending_block2_bet": False,
            "last_payout_timestamp": None
        }
    try:
        with open(VALIDATION_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "validation_counter": 0,
            "last_payout": None,
            "sequence_completed": False,
            "blocks_setup": False,
            "pending_block2_bet": False,
            "last_payout_timestamp": None
        }

def clear_validation_state():
    """Clear validation state when session properly ends"""
    try:
        if os.path.exists(VALIDATION_STATE_FILE):
            os.remove(VALIDATION_STATE_FILE)
    except Exception:
        pass

def format_betting_hours(hours_str):
    """Convert betting hours string to 12-hour format with AM/PM and | separators."""
    try:
        if not hours_str or hours_str in ["Not configured", "Not available", "Error reading betting hours", "No betting hours today"]:
            return "Not available"
        
        if hours_str.startswith("[") and hours_str.endswith("]") and "|" in hours_str:
            return hours_str[1:-1]
        
        if hours_str.startswith("Today: "):
            hours_str = hours_str[len("Today: "):]
        ranges = hours_str.split("; ")
        if not ranges or ranges == [""]:
            return "Not available"
        
        formatted_ranges = []
        for time_range in ranges:
            if not time_range or "-" not in time_range:
                continue
            start, end = time_range.split(" - ")
            def to_am_pm(time_str):
                try:
                    dt = datetime.strptime(time_str.strip(), "%H:%M")
                    hour = dt.hour
                    period = "AM" if hour < 12 else "PM"
                    if hour == 0:
                        hour = 12
                    elif hour > 12:
                        hour -= 12
                    return f"{hour}:{dt.strftime('%M')}{period}"
                except ValueError:
                    return time_str.strip()
            
            start_12hr = to_am_pm(start)
            end_12hr = to_am_pm(end)
            formatted_ranges.append(f"{start_12hr}-{end_12hr}")
        
        return " | ".join(formatted_ranges)
    except Exception:
        return "Not available"

def get_today_session_file():
    """Get today's session file path"""
    today = date.today().isoformat()
    sessions_dir = os.path.join(get_data_directory(), "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    return os.path.join(sessions_dir, f"session_{today}.json")

def load_today_session():
    """Load today's session data"""
    session_file = get_today_session_file()
    if not os.path.exists(session_file):
        return {"sessions": [], "target_reached": False}
    
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"sessions": [], "target_reached": False}

def save_today_session(session_data):
    """Save today's session data"""
    session_file = get_today_session_file()
    try:
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2)
    except Exception:
        pass

def add_session_record(profit, capital_after, target_reached=False):
    """Add a session record to today's sessions"""
    session_data = load_today_session()
    session_record = {
        "timestamp": datetime.now().isoformat(),
        "profit": profit,
        "capital_after": capital_after,
        "target_reached": target_reached
    }
    session_data["sessions"].append(session_record)
    
    if target_reached:
        session_data["target_reached"] = True
    
    save_today_session(session_data)
    return session_data

def check_session_continuation():
    """Check if we should continue from previous session or start fresh"""
    session_data = load_today_session()
    
    if not session_data.get("sessions"):
        return "fresh"
    
    if session_data.get("target_reached", False):
        response = messagebox.askyesno(
            "Target Reached Today",
            "You've already reached your target profit today!\n\nWould you like to reset and start a fresh session?"
        )
        return "reset" if response else "tomorrow"
    
    if session_data.get("sessions"):
        response = messagebox.askyesno(
            "Continue Session?",
            "You have previous sessions today.\n\nWould you like to continue from the last session?"
        )
        return "continue" if response else "fresh"
    
    return "fresh"

def is_within_betting_hours():
    """Check if current time is within betting hours"""
    try:
        if osenaabo_core:
            hours_str = osenaabo_core.get_betting_hours()
        else:
            hours_str = "09:00-12:00, 14:00-17:00, 19:00-22:00"
            
        if not hours_str or hours_str == "Not available":
            return True
            
        current_time = datetime.now().time()
        time_ranges = hours_str.split(', ')
        
        for time_range in time_ranges:
            start_str, end_str = time_range.split('-')
            start_hour, start_min = map(int, start_str.split(':'))
            end_hour, end_min = map(int, end_str.split(':'))
            
            start_time = dt_time(start_hour, start_min)
            end_time = dt_time(end_hour, end_min)
            
            if start_time <= current_time <= end_time:
                return True
        return False
    except Exception:
        return True

# ======== HARDWARE-LOCKED LICENSE VALIDATION ========
def validate_license_with_hardware(validation_input):
    """Validate license with hardware binding - FIXED VERSION"""
    try:
        print(f"🔐 Hardware validation for: {validation_input.split(':')[0] if ':' in validation_input else 'unknown'}")
        
        if validate_license is None:
            return {"valid": False, "message": "License validation not available"}
        
        # Step 1: Validate license
        result = validate_license(validation_input)
        
        if not result or not result.get("valid", False):
            return result
        
        # Step 2: Get hardware info
        current_hardware_id = get_hardware_id()
        print(f"Current hardware: {current_hardware_id}")
        
        # Step 3: Load license data - THIS NOW RETURNS {} INSTEAD OF None
        license_data = load_license_json()
        print(f"License data: {license_data}")
        
        # Step 4: Check hardware binding
        if license_data and 'hardware_id' in license_data:
            # License already bound
            if license_data['hardware_id'] == current_hardware_id:
                print("✅ Hardware match")
                return result
            else:
                return {
                    "valid": False, 
                    "message": f"❌ License bound to PC_{license_data['hardware_id'].upper()}",
                    "details": f"This license is permanently bound to another computer."
                }
        else:
            # First activation
            license_hardware_id = result.get('hardware_id')
            if license_hardware_id and license_hardware_id != current_hardware_id:
                return {
                    "valid": False, 
                    "message": f"❌ License not authorized for this computer",
                    "details": f"License pre-bound to: PC_{license_hardware_id.upper()}\nYour computer: PC_{current_hardware_id.upper()}"
                }
            
            # Bind license to this hardware
            license_data['hardware_id'] = current_hardware_id
            license_data['activation_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            license_data['hardware_locked'] = True
            license_data['valid'] = True
            license_data['telegram_id'] = result.get('telegram_id')
            license_data['plan'] = result.get('plan')
            license_data['expires'] = result.get('expires')
            
            save_license_json(license_data)
            print("✅ License bound to this computer")
            
            return result
        
    except Exception as e:
        return {"valid": False, "message": f"License validation error: {str(e)}"}

# ---------------------------
# License Update Dialog
# ---------------------------
class LicenseUpdateDialog(ctk.CTkToplevel):
    """Dialog for updating license information"""
    
    def __init__(self, parent, on_license_updated=None):
        super().__init__(parent)
        self.parent = parent
        self.on_license_updated = on_license_updated
        self.title("Update License")
        self.geometry("500x600")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self._build_ui()
        self._load_current_license()
        
    def _build_ui(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
        self.scrollable_frame = ctk.CTkScrollableFrame(main_frame, height=500)
        self.scrollable_frame.pack(fill="both", expand=True)
    
        title_label = ctk.CTkLabel(self.scrollable_frame, text="License Management", 
                     font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=(0, 20))
    
        tg_frame = ctk.CTkFrame(self.scrollable_frame)
        tg_frame.pack(fill="x", pady=(0, 15))
    
        ctk.CTkLabel(tg_frame, text="Telegram User ID:", 
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(12, 5))
    
        self.tg_entry = ctk.CTkEntry(tg_frame, placeholder_text="Enter your Telegram User ID")
        self.tg_entry.pack(fill="x", padx=12, pady=(0, 12))
    
        license_frame = ctk.CTkFrame(self.scrollable_frame)
        license_frame.pack(fill="x", pady=(0, 15))
    
        ctk.CTkLabel(license_frame, text="License Key:", 
                    font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(12, 5))
    
        ctk.CTkLabel(license_frame, 
                    text="Paste your license key below and click 'Validate & Update License'",
                    text_color="gray",
                    font=ctk.CTkFont(size=11)).pack(anchor="w", padx=12, pady=(0, 5))
    
        self.license_textbox = ctk.CTkTextbox(license_frame, height=100)
        self.license_textbox.pack(fill="x", padx=12, pady=(0, 12))
    
        support_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        support_frame.pack(fill="x", pady=(0, 15))
    
        support_label = ctk.CTkLabel(support_frame, 
                               text="Need a license? Contact:\nTelegram: @OsenaaboSupport",
                               text_color="lightblue",
                               font=ctk.CTkFont(size=12),
                               justify="center")
        support_label.pack(pady=10)
    
        current_license_frame = ctk.CTkFrame(self.scrollable_frame)
        current_license_frame.pack(fill="x", pady=(0, 15))
    
        ctk.CTkLabel(current_license_frame, text="Current License:", 
                    font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(12, 5))
    
        self.license_info_text = ctk.CTkTextbox(current_license_frame, height=80, state="disabled")
        self.license_info_text.pack(fill="x", padx=12, pady=(0, 12))
    
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 0))
    
        self.validate_btn = ctk.CTkButton(button_frame, text="Validate & Update License", 
                                        command=self._validate_license,
                                        fg_color="green", hover_color="darkgreen")
        self.validate_btn.pack(side="left", padx=(0, 10))
    
        self.clear_btn = ctk.CTkButton(button_frame, text="Clear License", 
                                    command=self._clear_license,
                                    fg_color="orange", hover_color="darkorange")
        self.clear_btn.pack(side="left", padx=(0, 10))
    
        self.close_btn = ctk.CTkButton(button_frame, text="Close", 
                                    command=self.destroy)
        self.close_btn.pack(side="right")
        
    def _load_current_license(self):
        """Load and display current license information with hardware details"""
        license_data = load_license_json()
        
        self.license_info_text.configure(state="normal")
        self.license_info_text.delete("1.0", "end")
        
        if license_data and license_data.get("valid"):
            telegram_id = license_data.get("telegram_id", "N/A")
            expires = license_data.get("expires", "N/A")
            issued = license_data.get("issued", "N/A")
            plan = license_data.get("plan", "N/A")
            hardware_id = license_data.get("hardware_id")
            activation_date = license_data.get("activation_date", "N/A")
            
            info_text = f"✅ VALID LICENSE - HARDWARE LOCKED\n\n"
            info_text += f"Telegram ID: {telegram_id}\n"
            info_text += f"Plan: {plan}\n"
            info_text += f"Issued: {issued}\n"
            info_text += f"Expires: {expires}\n"
            
            if hardware_id:
                info_text += f"🔒 Hardware Bound: YES\n"
                info_text += f"🖥️ Activation Date: {activation_date}\n"
                info_text += f"📍 Computer ID: PC_{hardware_id.upper()}\n"
                info_text += f"\nStatus: Active and locked to this computer"
            else:
                info_text += f"🔒 Hardware Bound: NOT YET ACTIVATED\n"
                info_text += f"\nStatus: Ready for first activation"
            
            self.tg_entry.delete(0, "end")
            self.tg_entry.insert(0, telegram_id)
            
        else:
            info_text = "❌ NO VALID LICENSE\n\n"
            info_text += "Please enter your Telegram User ID and license key above.\n"
            info_text += "On first activation, the license will be permanently bound to this computer.\n\n"
            info_text += "If you don't have a license, contact @OsenaaboSupport on Telegram."
            
        self.license_info_text.insert("1.0", info_text)
        self.license_info_text.configure(state="disabled")
        
    def _validate_license(self):
        """Validate the entered license with hardware binding"""
        tg_user = self.tg_entry.get().strip()
        license_key = self.license_textbox.get("1.0", "end-1c").strip()
        
        if not tg_user:
            messagebox.showerror("Error", "Please enter your Telegram User ID")
            return
            
        if not license_key:
            messagebox.showerror("Error", "Please enter your license key")
            return
            
        if not validate_license:
            messagebox.showerror("Error", "License validation not available")
            return
            
        try:
            self.validate_btn.configure(state="disabled", text="Validating...")
            self.update()
            
            validation_input = f"{tg_user}:{license_key}"
            
            # Use hardware-bound validation
            result = validate_license_with_hardware(validation_input)
            
            if result["valid"]:
                # Load the saved license data to get full details
                license_data = load_license_json()
                
                expires = license_data.get("expires", "N/A")
                plan = license_data.get("plan", "N/A")
                hardware_id = license_data.get("hardware_id", "Not yet bound")
                
                messagebox.showinfo("License Activated", 
                                  f"✅ License activated successfully!\n\n"
                                  f"📱 Telegram ID: {tg_user}\n"
                                  f"💎 Plan: {plan}\n"
                                  f"📅 Expires: {expires}\n"
                                  f"🔒 Hardware Locked: ✅\n"
                                  f"🖥️ Bound to this computer\n\n"
                                  f"This license is now permanently bound to your computer.")
                
                if self.on_license_updated:
                    self.on_license_updated()
                    
                self._load_current_license()
                    
            else:
                messagebox.showerror("Activation Failed", 
                                   f"❌ {result.get('message', 'License validation failed')}\n\n"
                                   f"Please check your Telegram ID and license key, "
                                   f"or contact @OsenaaboSupport for assistance.")
                
        except Exception as e:
            messagebox.showerror("Validation Error", 
                               f"Error during license validation:\n\n{str(e)}")
        finally:
            self.validate_btn.configure(state="normal", text="Validate & Update License")
            
    def _clear_license(self):
        """Clear the current license"""
        if messagebox.askyesno("Clear License", 
                             "Are you sure you want to clear the current license?\n\n"
                             "This will disable all protected features until a new valid license is entered."):
            try:
                if os.path.exists(LICENSE_FILE):
                    os.remove(LICENSE_FILE)
                self._load_current_license()
                if self.on_license_updated:
                    self.on_license_updated()
                messagebox.showinfo("License Cleared", "License has been cleared successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear license: {str(e)}")

# ---------------------------
# Calibration Wizard (GUI)
# ---------------------------
class CalibrationWizard(ctk.CTkToplevel):
    """GUI-driven calibration wizard."""

    REQUIRED_REGIONS = [
        "Block1_AutoToggle",
        "Block1_StakeInput",
        "Block1_AutoCashToggle",
        "Block1_AutoCashInput",
        "Block1_BetButton",
        "Block2_AutoToggle",
        "Block2_StakeInput",
        "Block2_AutoCashToggle",
        "Block2_AutoCashInput",
        "Block2_BetButton",
        "Block1_History"
    ]

    def __init__(self, parent, block2_enabled=True, on_complete=None):
        super().__init__(parent)
        self.parent = parent
        self.on_complete = on_complete
        self.title("Calibration Wizard")
        self.geometry("720x480")
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.coords = {}
        self.coords["calibrated_at"] = datetime.now(timezone.utc).isoformat()
        self.prestart_flow = []
        self.block2_enabled = block2_enabled
        self._build_ui()
        self.step = 0
        self.current_region = None
        self.recording_tl = None
        self.recording_br = None
        self._render_step()
        self.bind("<Return>", self._on_enter_key)

    def _build_ui(self):
        self.logbox = ctk.CTkTextbox(self, height=300)
        self.logbox.pack(fill="both", expand=True, padx=12, pady=12)
        
        self.coord_frame = ctk.CTkFrame(self)
        self.coord_frame.pack(fill="x", padx=12, pady=(0, 12))
        
        tl_frame = ctk.CTkFrame(self.coord_frame)
        tl_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(tl_frame, text="Top Left:", width=80).pack(side="left", padx=(5, 2))
        self.tl_x_entry = ctk.CTkEntry(tl_frame, width=60, placeholder_text="X")
        self.tl_x_entry.pack(side="left", padx=2)
        self.tl_y_entry = ctk.CTkEntry(tl_frame, width=60, placeholder_text="Y")
        self.tl_y_entry.pack(side="left", padx=2)
        self.tl_calibrate_btn = ctk.CTkButton(tl_frame, text="Calibrate", width=80, command=self._capture_tl)
        self.tl_calibrate_btn.pack(side="left", padx=(10, 5))
        
        br_frame = ctk.CTkFrame(self.coord_frame)
        br_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(br_frame, text="Bottom Right:", width=80).pack(side="left", padx=(5, 2))
        self.br_x_entry = ctk.CTkEntry(br_frame, width=60, placeholder_text="X")
        self.br_x_entry.pack(side="left", padx=2)
        self.br_y_entry = ctk.CTkEntry(br_frame, width=60, placeholder_text="Y")
        self.br_y_entry.pack(side="left", padx=2)
        self.br_calibrate_btn = ctk.CTkButton(br_frame, text="Calibrate", width=80, command=self._capture_br)
        self.br_calibrate_btn.pack(side="left", padx=(10, 5))

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=12, pady=(0, 12))
        self.skip_btn = ctk.CTkButton(btn_frame, text="Skip", command=self._on_skip)
        self.skip_btn.pack(side="left", padx=(0, 6))
        self.next_btn = ctk.CTkButton(btn_frame, text="Next", command=self._on_next)
        self.next_btn.pack(side="left", padx=(0, 6))
        self.finish_btn = ctk.CTkButton(btn_frame, text="Finish", command=self._on_finish, state="disabled")
        self.finish_btn.pack(side="right")

    def _capture_tl(self):
        self._append_log("Capturing Top-Left in 5 seconds...")
        self.tl_calibrate_btn.configure(state="disabled", text="5...")
        self._countdown_capture(5, "tl")

    def _capture_br(self):
        self._append_log("Capturing Bottom-Right in 5 seconds...")
        self.br_calibrate_btn.configure(state="disabled", text="5...")
        self._countdown_capture(5, "br")

    def _countdown_capture(self, count, capture_type):
        if count > 0:
            getattr(self, f"{capture_type}_calibrate_btn").configure(text=f"{count}...")
            self.after(1000, lambda: self._countdown_capture(count-1, capture_type))
        else:
            getattr(self, f"{capture_type}_calibrate_btn").configure(text="Calibrate", state="normal")
            pos = pyautogui.position()
            if capture_type == "tl":
                self.tl_x_entry.delete(0, "end")
                self.tl_x_entry.insert(0, str(pos.x))
                self.tl_y_entry.delete(0, "end")
                self.tl_y_entry.insert(0, str(pos.y))
                self.recording_tl = pos
                self._append_log(f"Top-Left captured at ({pos.x}, {pos.y})")
            else:
                self.br_x_entry.delete(0, "end")
                self.br_x_entry.insert(0, str(pos.x))
                self.br_y_entry.delete(0, "end")
                self.br_y_entry.insert(0, str(pos.y))
                self.recording_br = pos
                self._append_log(f"Bottom-Right captured at ({pos.x}, {pos.y})")
                self._calculate_region()

    def _calculate_region(self):
        if self.recording_tl and self.recording_br and self.current_region:
            x = min(self.recording_tl.x, self.recording_br.x)
            y = min(self.recording_tl.y, self.recording_br.y)
            w = abs(self.recording_br.x - self.recording_tl.x)
            h = abs(self.recording_br.y - self.recording_tl.y)
            
            if w > 0 and h > 0:
                self.coords[self.current_region] = {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}
                self._append_log(f"Captured {self.current_region} -> ({x},{y},{w},{h})")
                self.next_btn.configure(state="normal")
                self.tl_x_entry.delete(0, "end")
                self.tl_y_entry.delete(0, "end")
                self.br_x_entry.delete(0, "end")
                self.br_y_entry.delete(0, "end")
                self.recording_tl = None
                self.recording_br = None
                self.after(100, self._advance_region)

    def _append_log(self, msg):
        self.logbox.configure(state="normal")
        self.logbox.insert("end", f"{now_ts()} - {msg}\n")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def _render_step(self):
        self.logbox.configure(state="normal")
        self.logbox.delete("0.0", "end")
        self.logbox.configure(state="disabled")
        if self.step == 0:
            self._append_log("Step 1: Prestart Flow Configuration")
            self._append_log("Enter UP arrow presses (0 to skip):")
            up_entry = ctk.CTkEntry(self)
            up_entry.pack(pady=6)
            self._append_log("Enter DOWN arrow presses (0 to skip):")
            down_entry = ctk.CTkEntry(self)
            down_entry.pack(pady=6)
            
            def submit_prestart():
                try:
                    up = int(up_entry.get() or 0)
                    down = int(down_entry.get() or 0)
                    flow = []
                    if up > 0: flow.append({"direction": "up", "count": up})
                    if down > 0: flow.append({"direction": "down", "count": down})
                    self.coords["Prestart_Flow"] = flow
                    self._append_log(f"Prestart Flow: {flow}")
                    self.step = 1
                    self._render_step()
                except ValueError:
                    self._append_log("Invalid input. Try again.")
                    
            submit_btn = ctk.CTkButton(self, text="Submit", command=submit_prestart)
            submit_btn.pack(pady=12)
            
            def cleanup_and_submit():
                up_entry.destroy()
                down_entry.destroy()
                submit_btn.destroy()
                submit_prestart()
                
            submit_btn.configure(command=cleanup_and_submit)
            
        elif self.step == 1:
            self._append_log("Step 2: Game Activation (optional)")
            self._append_log("Capture Game Activation? (y/n)")
            
            def yes():
                self.current_region = "Game_Activation"
                self._append_log("Move mouse to TOP-LEFT and press ENTER.")
                for widget in self.winfo_children():
                    if isinstance(widget, ctk.CTkButton) and widget.winfo_y() > 300:
                        widget.destroy()
                        
            def no():
                self.step = 2
                self._render_step()
                for widget in self.winfo_children():
                    if isinstance(widget, ctk.CTkButton) and widget.winfo_y() > 300:
                        widget.destroy()
                        
            yes_btn = ctk.CTkButton(self, text="Yes", command=yes)
            yes_btn.pack(side="left", padx=6)
            no_btn = ctk.CTkButton(self, text="No", command=no)
            no_btn.pack(side="left", padx=6)
            
        elif self.step == 2:
            self._append_log("Step 3: Close Chat Window (optional)")
            self._append_log("Capture Close Chat Window button? (y/n)")
            
            def yes():
                self.current_region = "Close_Chat_Window"
                self._append_log("Move mouse to TOP-LEFT and press ENTER.")
                for widget in self.winfo_children():
                    if isinstance(widget, ctk.CTkButton) and widget.winfo_y() > 300:
                        widget.destroy()
                        
            def no():
                self.step = 3
                self._render_step()
                for widget in self.winfo_children():
                    if isinstance(widget, ctk.CTkButton) and widget.winfo_y() > 300:
                        widget.destroy()
                        
            yes_btn = ctk.CTkButton(self, text="Yes", command=yes)
            yes_btn.pack(side="left", padx=6)
            no_btn = ctk.CTkButton(self, text="No", command=no)
            no_btn.pack(side="left", padx=6)
            
        elif self.step == 3:
            self._append_log("Step 4: Block 1 Regions")
            self._append_log("We will now capture Block 1 regions.")
            self._append_log("Press Next to begin...")
            self.next_btn.configure(state="normal", command=self._start_block1)
            
        elif self.step == 4:
            self._append_log("Step 5: Block 2 Regions")
            self._append_log("We will now capture Block 2 regions.")
            self._append_log("Press Next to begin...")
            self.next_btn.configure(state="normal", command=self._start_block2)
            
        elif self.step == 5:
            self._append_log("Step 6: History Region")
            self._append_log("We will now capture the History region.")
            self._append_log("Press Next to begin...")
            self.next_btn.configure(state="normal", command=self._start_history)
            
        elif self.step == 6:
            self._append_log("Calibration Complete!")
            self._append_log("Press Finish to save.")
            self.finish_btn.configure(state="normal")
            self.next_btn.configure(state="disabled")

    def _start_block1(self):
        self.step = 4
        self.current_region = "Block1_AutoToggle"
        self._append_log("Capture Block1_AutoToggle region:")
        self._append_log("Move mouse to TOP-LEFT and press ENTER.")
        self.next_btn.configure(state="disabled")

    def _start_block2(self):
        self.step = 5
        self.current_region = "Block2_AutoToggle"
        self._append_log("Capture Block2_AutoToggle region:")
        self._append_log("Move mouse to TOP-LEFT and press ENTER.")
        self.next_btn.configure(state="disabled")

    def _start_history(self):
        self.step = 6
        self.current_region = "Block1_History"
        self._append_log("Capture Block1_History region:")
        self._append_log("Move mouse to TOP-LEFT and press ENTER.")
        self.next_btn.configure(state="disabled")

    def _advance_region(self):
        regions = self.REQUIRED_REGIONS.copy()
        if not self.block2_enabled:
            regions = [r for r in regions if not r.startswith("Block2")]
            
        if self.current_region in regions:
            idx = regions.index(self.current_region)
            if idx + 1 < len(regions):
                self.current_region = regions[idx + 1]
                self._append_log(f"Capture {self.current_region} region:")
                self._append_log("Move mouse to TOP-LEFT and press ENTER.")
            else:
                self.current_region = None
                self.step = 6
                self._render_step()
        else:
            self.current_region = None
            self.step = 6
            self._render_step()

    def _on_enter_key(self, event):
        if self.current_region:
            if not self.recording_tl:
                self._capture_tl()
            elif not self.recording_br:
                self._capture_br()

    def _on_skip(self):
        if self.current_region:
            self._append_log(f"Skipped {self.current_region}")
            self._advance_region()

    def _on_next(self):
        if self.step == 0:
            self.step = 1
            self._render_step()
        elif self.step == 1:
            self.step = 2
            self._render_step()
        elif self.step == 2:
            self.step = 3
            self._render_step()
        elif self.step == 3:
            self._start_block1()
        elif self.step == 4:
            self._start_block2()
        elif self.step == 5:
            self._start_history()
        elif self.step == 6:
            self._on_finish()

    def _on_finish(self):
        save_coords_json(self.coords)
        self._append_log("Calibration saved!")
        if self.on_complete:
            self.on_complete(self.coords)
        self.destroy()

    def _on_close(self):
        if messagebox.askokcancel("Quit", "Quit calibration? Progress will be lost."):
            self.destroy()

# ---------------------------
# Main Application
# ---------------------------
class OsenaaboApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Basic window configuration
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("OSENAABO! - The 3rd 👁️")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.minsize(MIN_W, MIN_H)
        
        # Center window
        self._center_window()
        
        # Initialize attributes
        self.corner_radius = 20
        self.logo_img = load_inline_logo_image()
        self.calib_data = load_coords_json()
        self.stop_event = threading.Event()
        self.bot_thread = None
        self.block2_enabled = True
        self.mute_sounds = tk.BooleanVar(value=False)
        self.mute_notifications = tk.BooleanVar(value=False)
        
        # Initialize license status variable
        self.license_status_var = ctk.StringVar(value="⚠️ No valid license")
        
        # Session management
        self.current_session_type = "fresh"
        self.session_start_capital = 0
        
        # Configuration panel visibility state
        self.config_panel_visible = True
        
        # Platform selection
        self.platform_var = ctk.StringVar(value="SportyBetNg")
        self.platform_enabled = False
        self.previous_platform = "SportyBetNg"
        
        # Daily target tracking
        self.daily_target_reached = 0.0
        self.daily_target_reset_btn_state = "disabled"
        
        # Trading state management
        self.trading_started = False
        self.capital_locked = False
        
        # Session cookies management
        self.session_cookies = {}
        
        # Telegram notification settings
        self.telegram_enabled = tk.BooleanVar(value=False)
        self.bot_token = tk.StringVar(value="")
        self.chat_id = tk.StringVar(value="")
        
        # Initialize pygame mixer if available
        if PYGAME_AVAILABLE and pygame:
            try:
                pygame.mixer.init()
            except:
                pass
                
        self._build_ui()
        self._refresh_license_ui()
        self._update_betting_hours()
        self._load_daily_target()
        self._load_platform_selection()

    def _center_window(self):
        """Center the window on the screen"""
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - WINDOW_W) // 2
        y = (screen_height - WINDOW_H) // 2
        self.geometry(f"{WINDOW_W}x{WINDOW_H}+{x}+{y}")

    def _load_daily_target(self):
        """Load daily target from file"""
        try:
            daily_target_file = os.path.join(get_data_directory(), 'bot_state.json')
            with open(daily_target_file, 'r') as f:
                state = json.load(f)
                self.daily_target_reached = state.get('DAILY_TARGET_REACHED', 0.0)
        except:
            self.daily_target_reached = 0.0

    def _save_daily_target(self):
        """Save daily target to file"""
        try:
            daily_target_file = os.path.join(get_data_directory(), 'bot_state.json')
            with open(daily_target_file, 'r') as f:
                state = json.load(f)
            state['DAILY_TARGET_REACHED'] = self.daily_target_reached
            with open(daily_target_file, 'w') as f:
                json.dump(state, f, indent=4)
        except:
            pass

    def _load_platform_selection(self):
        """Load platform selection from config"""
        config = load_config_json()
        platform = config.get("platform", "SportyBetNg")
        self.platform_var.set(platform)
        self.previous_platform = platform

    def _build_ui(self):
        # Header frame
        header_frame = ctk.CTkFrame(self, height=70, corner_radius=self.corner_radius)
        header_frame.pack(fill="x", padx=12, pady=12)
        header_frame.grid_propagate(False)
        
        # Logo and title
        logo_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        logo_frame.pack(side="left", padx=15, pady=10)
        
        if self.logo_img:
            ctk.CTkLabel(logo_frame, image=self.logo_img, text="").pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(logo_frame, text=APP_TITLE, font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(logo_frame, text=APP_SUB1, font=ctk.CTkFont(size=12)).pack(anchor="w")
        
        # Mute options on the right side of header
        mute_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        mute_frame.pack(side="right", padx=15, pady=10)
        
        ctk.CTkCheckBox(mute_frame, text="Mute Sounds", variable=self.mute_sounds).pack(side="left", padx=6)
        ctk.CTkCheckBox(mute_frame, text="Mute Notifications", variable=self.mute_notifications).pack(side="left", padx=6)

        # main content area
        self.main_frame = ctk.CTkFrame(self, corner_radius=self.corner_radius)
        self.main_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)

        # Configuration panel
        self.config_panel = ctk.CTkFrame(self.main_frame, width=400, corner_radius=self.corner_radius)
        self.config_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.config_panel.grid_propagate(False)
        
        # Scrollable frame for configuration content
        self.config_scrollable = ctk.CTkScrollableFrame(self.config_panel, fg_color="transparent", height=650)
        self.config_scrollable.pack(fill="both", expand=True, padx=12, pady=12)
        
        # Configuration widgets with better spacing
        capital_label = ctk.CTkLabel(self.config_scrollable, text="Starting Capital (₦):", anchor="w")
        capital_label.pack(fill="x", padx=12, pady=(12, 5))
        
        self.capital_entry = ctk.CTkEntry(self.config_scrollable, placeholder_text="1000000")
        self.capital_entry.pack(fill="x", padx=12, pady=(0, 8))
        self.capital_entry.bind("<KeyRelease>", self._update_base_bet_display)
        
        stoploss_label = ctk.CTkLabel(self.config_scrollable, text="Stop Loss (%):", anchor="w")
        stoploss_label.pack(fill="x", padx=12, pady=(8, 5))
        
        self.stoploss_entry = ctk.CTkEntry(self.config_scrollable)
        self.stoploss_entry.insert(0, str(DEFAULT_STOP_LOSS))
        self.stoploss_entry.pack(fill="x", padx=12, pady=(0, 8))
        
        # Stop Loss Warning
        self.stop_loss_warning = ctk.CTkLabel(self.config_scrollable, 
                                            text="⚠️ Changing Stop Loss may increase risk exposure!",
                                            text_color="orange", 
                                            font=ctk.CTkFont(size=12),
                                            anchor="w",
                                            wraplength=350)
        self.stop_loss_warning.pack(fill="x", padx=12, pady=(0, 12))
        
        self.block2_var = tk.BooleanVar(value=True)
        block2_cb = ctk.CTkCheckBox(self.config_scrollable, text="Enable Block 2 (higher risk)", 
                                   variable=self.block2_var, command=self._on_block2_toggle)
        block2_cb.pack(fill="x", padx=12, pady=(8, 5))
        
        # License status display
        license_status_label = ctk.CTkLabel(self.config_scrollable, text="License Status:", anchor="w")
        license_status_label.pack(fill="x", padx=12, pady=(12, 5))
        
        license_status_display = ctk.CTkLabel(self.config_scrollable, textvariable=self.license_status_var, 
                                            text_color="yellow", anchor="w")
        license_status_display.pack(fill="x", padx=12, pady=(0, 8))
        
        self.update_license_btn = ctk.CTkButton(self.config_scrollable, text="Update License", 
                                              command=self._show_license_dialog)
        self.update_license_btn.pack(fill="x", padx=12, pady=(0, 8))
        
        # Platform selector
        platform_label = ctk.CTkLabel(self.config_scrollable, text="Trading Platform:", anchor="w")
        platform_label.pack(fill="x", padx=12, pady=(12, 5))
        
        self.platform_selector = ctk.CTkOptionMenu(self.config_scrollable, 
                                                 values=["SportyBetNg", "BetwayNg"],
                                                 variable=self.platform_var,
                                                 state="disabled",
                                                 command=self._on_platform_select)
        self.platform_selector.pack(fill="x", padx=12, pady=(0, 8))
        
        self.calibrate_btn = ctk.CTkButton(self.config_scrollable, text="Calibrate", 
                                         command=self._launch_calibration,
                                         state="disabled")
        self.calibrate_btn.pack(fill="x", padx=12, pady=(8, 8))
        
        self.start_btn = ctk.CTkButton(self.config_scrollable, text="Start Bot", 
                                     command=self._toggle_bot, 
                                     fg_color="green", hover_color="dark green",
                                     state="disabled")
        self.start_btn.pack(fill="x", padx=12, pady=(0, 8))
        
        self.stop_btn = ctk.CTkButton(self.config_scrollable, text="Stop Bot", 
                                    command=self._toggle_bot, 
                                    fg_color="red", hover_color="dark red", 
                                    state="disabled")
        self.stop_btn.pack(fill="x", padx=12, pady=(0, 12))
        
        # Add Telegram Notification Section
        self._build_telegram_section()

        # Status & Info panel
        self.status_panel = ctk.CTkFrame(self.main_frame, corner_radius=self.corner_radius)
        self.status_panel.grid(row=0, column=1, sticky="nsew")
        self.status_panel.grid_rowconfigure(1, weight=1)
        self.status_panel.grid_columnconfigure(0, weight=1)
        
        # Status header with toggle button
        status_header = ctk.CTkFrame(self.status_panel, fg_color="transparent")
        status_header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 0))
        status_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(status_header, text="Status & Info", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w")
        
        # Add toggle button to status header
        self.toggle_config_btn = ctk.CTkButton(status_header, text="◀▶", width=30, command=self.toggle_config_view)
        self.toggle_config_btn.grid(row=0, column=1, sticky="e")
        
        # Content area for status panel
        self.status_content = ctk.CTkFrame(self.status_panel, corner_radius=self.corner_radius)
        self.status_content.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
        self.status_content.grid_rowconfigure(4, weight=1)
        self.status_content.grid_columnconfigure(0, weight=1)
        
        # Base Bet display in Status & Info
        base_bet_frame = ctk.CTkFrame(self.status_content, corner_radius=12)
        base_bet_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(0, 8))
        
        ctk.CTkLabel(base_bet_frame, text="Base Bet:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(8, 0))
        self.base_bet_label = ctk.CTkLabel(base_bet_frame, text="₦0", font=ctk.CTkFont(size=14))
        self.base_bet_label.pack(anchor="w", padx=12, pady=(0, 8))
        
        # Daily Target display with reset button
        daily_target_frame = ctk.CTkFrame(self.status_content, corner_radius=12)
        daily_target_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        
        daily_target_header = ctk.CTkFrame(daily_target_frame, fg_color="transparent")
        daily_target_header.pack(fill="x", padx=12, pady=(8, 0))
        
        ctk.CTkLabel(daily_target_header, text="Daily 5% Target:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.daily_target_reset_btn = ctk.CTkButton(daily_target_header, 
                                                  text="Reset", 
                                                  width=60,
                                                  state="disabled",
                                                  command=self._reset_daily_target)
        self.daily_target_reset_btn.pack(side="right")
        
        self.daily_target_label = ctk.CTkLabel(daily_target_frame, text="0.00%", font=ctk.CTkFont(size=14))
        self.daily_target_label.pack(anchor="w", padx=12, pady=(0, 8))
        
        # Trading hours display
        self.trading_hours_frame = ctk.CTkFrame(self.status_content, corner_radius=12)
        self.trading_hours_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        
        ctk.CTkLabel(self.trading_hours_frame, text="Trading Hours:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(8, 0))
        self.trading_hours_label = ctk.CTkLabel(self.trading_hours_frame, text="Loading...")
        self.trading_hours_label.pack(anchor="w", padx=12, pady=(0, 8))
        
        # Hardware ID display in Status & Info
        hardware_frame = ctk.CTkFrame(self.status_content, corner_radius=12)
        hardware_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))
        
        ctk.CTkLabel(hardware_frame, text="Computer ID:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(8, 0))
        
        hardware_id = get_hardware_fingerprint()
        self.hardware_label = ctk.CTkLabel(hardware_frame, text=hardware_id, 
                                  font=ctk.CTkFont(family="Courier", size=11),
                                  text_color="lightblue")
        self.hardware_label.pack(anchor="w", padx=12, pady=(0, 8))
        
        # Add copy hardware ID button
        def copy_hardware_id():
            self.clipboard_clear()
            self.clipboard_append(hardware_id)
            messagebox.showinfo("Copied", f"Computer ID copied to clipboard:\n{hardware_id}")
        
        copy_btn = ctk.CTkButton(hardware_frame, text="Copy ID", 
                                command=copy_hardware_id,
                                width=60, height=25)
        copy_btn.pack(anchor="e", padx=12, pady=(0, 8))
        
        # Log display
        log_frame = ctk.CTkFrame(self.status_content, corner_radius=12)
        log_frame.grid(row=4, column=0, sticky="nsew", padx=12, pady=(0, 12))
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(log_frame, text="Activity Log:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=12, pady=(8, 0))
        
        self.log_textbox = ctk.CTkTextbox(log_frame, wrap="word", state="disabled")
        self.log_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        # Update initial displays
        self._update_base_bet_display()
        self._update_daily_target_display()

    def _build_telegram_section(self):
        """Build Telegram notification configuration section"""
        separator = ctk.CTkFrame(self.config_scrollable, height=2, fg_color="gray")
        separator.pack(fill="x", padx=12, pady=(10, 15))
    
        telegram_frame = ctk.CTkFrame(self.config_scrollable)
        telegram_frame.pack(fill="x", padx=12, pady=(0, 12))
    
        telegram_header = ctk.CTkFrame(telegram_frame, fg_color="transparent")
        telegram_header.pack(fill="x", padx=0, pady=(8, 0))
    
        ctk.CTkLabel(telegram_header, text="Telegram Notifications", 
                    font=ctk.CTkFont(weight="bold", size=14)).pack(side="left")
    
        license_badge = ctk.CTkLabel(telegram_header, text="🔒 License Required",
                                    text_color="orange", font=ctk.CTkFont(size=10))
        license_badge.pack(side="left", padx=(10, 0))
    
        info_btn = ctk.CTkButton(telegram_header, text="ℹ", width=30, height=30,
                                command=self._show_telegram_info,
                                fg_color="blue", hover_color="darkblue")
        info_btn.pack(side="right", padx=(0, 5))
    
        self.telegram_cb = ctk.CTkCheckBox(telegram_frame, text="Enable Telegram Notifications",
                                         variable=self.telegram_enabled,
                                         command=self._on_telegram_toggle)
        self.telegram_cb.pack(anchor="w", padx=12, pady=(12, 8))
        
        bot_token_label = ctk.CTkLabel(telegram_frame, text="Bot Token:", anchor="w")
        bot_token_label.pack(fill="x", padx=12, pady=(5, 0))
        
        self.bot_token_entry = ctk.CTkEntry(telegram_frame, 
                                          placeholder_text="1234567890:ABCdefGHIjkLMNoPQRsTUVwxyZ",
                                          textvariable=self.bot_token,
                                          height=35)
        self.bot_token_entry.pack(fill="x", padx=12, pady=(0, 8))
        
        chat_id_label = ctk.CTkLabel(telegram_frame, text="Chat ID:", anchor="w")
        chat_id_label.pack(fill="x", padx=12, pady=(5, 0))
        
        self.chat_id_entry = ctk.CTkEntry(telegram_frame, 
                                        placeholder_text="123456789",
                                        textvariable=self.chat_id,
                                        height=35)
        self.chat_id_entry.pack(fill="x", padx=12, pady=(0, 12))
        
        test_btn = ctk.CTkButton(telegram_frame, 
                               text="Test Notification", 
                               command=self._test_telegram_notification,
                               fg_color="purple", 
                               hover_color="darkpurple")
        test_btn.pack(fill="x", padx=12, pady=(0, 8))
        
        self.bot_token_entry.configure(state="disabled")
        self.chat_id_entry.configure(state="disabled")
        
        self._load_telegram_settings()

    def _show_telegram_info(self):
        """Show Telegram setup information"""
        info_text = """📱 Telegram Notification Setup

1. Create a Telegram Bot:
   • Search for @BotFather in Telegram
   • Send /newbot command
   • Follow instructions to get your Bot Token

2. Get Your Chat ID:
   • Start a chat with your new bot
   • Send any message
   • Visit: https://api.telegram.org/bot<YourBOTToken>/getUpdates
   • Find your chat ID in the response

3. Format:
   • Bot Token: 1234567890:ABCdefGHIjkLMNoPQRsTUVwxyZ
   • Chat ID: 123456789

Example:
   Bot Token: 1234567890:AAHxR8v8v6V5v6V5v6V5v6V5v6V5v6V5v6
   Chat ID: 987654321"""

        messagebox.showinfo("Telegram Setup Guide", info_text)

    def _load_telegram_settings(self):
        """Load telegram settings from config"""
        config = load_config_json()
        telegram_config = config.get("telegram", {})
        
        if telegram_config:
            self.telegram_enabled.set(telegram_config.get("enabled", False))
            self.bot_token.set(telegram_config.get("bot_token", ""))
            self.chat_id.set(telegram_config.get("chat_id", ""))
            
            if self.telegram_enabled.get():
                self.bot_token_entry.configure(state="normal")
                self.chat_id_entry.configure(state="normal")

    def _save_telegram_settings(self):
        """Save telegram settings to config"""
        config = load_config_json()
        config["telegram"] = {
            "enabled": self.telegram_enabled.get(),
            "bot_token": self.bot_token.get(),
            "chat_id": self.chat_id.get()
        }
        save_config_json(config)

    def _on_telegram_toggle(self):
        """Handle telegram notification toggle"""
        if not self.platform_enabled:
            self._show_license_required_message("enable Telegram notifications")
            self.telegram_enabled.set(False)
            return
        
        if self.telegram_enabled.get():
            self.bot_token_entry.configure(state="normal")
            self.chat_id_entry.configure(state="normal")
        else:
            self.bot_token_entry.configure(state="disabled")
            self.chat_id_entry.configure(state="disabled")

    def _test_telegram_notification(self):
        """Test Telegram notification with current settings"""
        if not self.platform_enabled:
            self._show_license_required_message("test Telegram notifications")
            return
        
        if not self.telegram_enabled.get():
            messagebox.showwarning("Telegram Disabled", "Please enable Telegram notifications first.")
            return
        
        bot_token = self.bot_token.get().strip()
        chat_id = self.chat_id.get().strip()
        
        if not bot_token or not chat_id:
            messagebox.showwarning("Missing Information", "Please enter both Bot Token and Chat ID.")
            return
        
        self._save_telegram_settings()
        
        try:
            import requests
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': '🔔 OSENAABO! Test Notification\n\nThis is a test message from your trading bot. If you receive this, your Telegram notifications are working correctly! ✅',
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=payload, timeout=10)
            
            if response.status_code == 200:
                messagebox.showinfo("Test Successful", "✅ Telegram test notification sent successfully!")
                self._log("Telegram test notification sent successfully")
            else:
                error_msg = response.json().get('description', 'Unknown error')
                messagebox.showerror("Test Failed", f"❌ Failed to send test notification:\n{error_msg}")
                self._log(f"Telegram test failed: {error_msg}")
                
        except Exception as e:
            messagebox.showerror("Test Failed", f"❌ Error sending test notification:\n{str(e)}")
            self._log(f"Telegram test error: {str(e)}")

    # ======== FIXED SOUND HANDLING ========
    def play_sound(self, sound_type):
        """Play sound with platform compatibility - FIXED with PYGAME_AVAILABLE check"""
        if self.mute_sounds.get():
            return
            
        # ADD THIS CHECK:
        if not PYGAME_AVAILABLE:
            return  # Skip sound if pygame not available
            
        try:
            # First try: Use existing .wav files with pygame (works on all platforms)
            if pygame and pygame.mixer.get_init():
                if sound_type == "clap" and os.path.exists(CLAP_SOUND):
                    pygame.mixer.Sound(CLAP_SOUND).play()
                    return
                elif sound_type == "found" and os.path.exists(FOUND_SOUND):
                    pygame.mixer.Sound(FOUND_SOUND).play()
                    return
                
            # Second try: Platform-specific fallbacks ONLY if .wav files fail
            self._play_fallback_sound(sound_type)
            
        except Exception as e:
            print(f"Sound play failed: {e}")
            self._play_fallback_sound(sound_type)

    def _play_fallback_sound(self, sound_type):
        """Platform-specific fallback sounds - only used if .wav files fail"""
        try:
            if IS_WINDOWS:
                import winsound
                if sound_type == "clap":
                    winsound.Beep(800, 400)
                elif sound_type == "found":
                    winsound.Beep(1200, 300)
                elif sound_type == "win":
                    winsound.Beep(1000, 500)
                elif sound_type == "loss":
                    winsound.Beep(500, 300)
                    
            elif IS_MAC:
                if sound_type == "clap":
                    os.system('afplay /System/Library/Sounds/Submarine.aiff > /dev/null 2>&1')
                elif sound_type == "found":
                    os.system('afplay /System/Library/Sounds/Glass.aiff > /dev/null 2>&1')
                elif sound_type == "win":
                    os.system('afplay /System/Library/Sounds/Tink.aiff > /dev/null 2>&1')
                elif sound_type == "loss":
                    os.system('osascript -e "beep 1"')
                    
            elif IS_LINUX:
                if sound_type == "clap":
                    os.system('paplay /usr/share/sounds/ubuntu/stereo/button-pressed.ogg > /dev/null 2>&1')
                elif sound_type == "found":
                    os.system('paplay /usr/share/sounds/ubuntu/stereo/message.ogg > /dev/null 2>&1')
                elif sound_type == "win":
                    os.system('echo -e "\a\a"')
                elif sound_type == "loss":
                    os.system('echo -e "\a"')
                    
        except Exception as e:
            print(f"Fallback sound failed: {e}")

    def _show_license_dialog(self):
        """Open license update dialog"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Update License")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Telegram User ID:", font=ctk.CTkFont(weight="bold")).pack(pady=(20,5))
        tg_entry = ctk.CTkEntry(dialog, width=400)
        tg_entry.pack(pady=5)

        ctk.CTkLabel(dialog, text="License Key:", font=ctk.CTkFont(weight="bold")).pack(pady=(15,5))
        license_entry = ctk.CTkEntry(dialog, width=400, height=80)
        license_entry.pack(pady=5)

        def validate():
            tg = tg_entry.get().strip()
            key = license_entry.get().strip()
            if not tg or not key:
                messagebox.showerror("Error", "Both fields required")
                return
            result = validate_license_with_hardware(f"{tg}:{key}", get_license_path())
            if result["valid"]:
                messagebox.showinfo("Success", "License updated!")
                self._refresh_license_ui()
                dialog.destroy()
            else:
                messagebox.showerror("Failed", result.get("message", "Invalid"))

        ctk.CTkButton(dialog, text="Validate", command=validate).pack(pady=20)

    def _update_base_bet_display(self, event=None):
        """Update the base bet display based on capital entry"""
        try:
            capital = float(self.capital_entry.get().replace(",", ""))
            base_bet = capital * 0.001
            self.base_bet_label.configure(text=f"₦{base_bet:,.2f}")
        except (ValueError, AttributeError):
            self.base_bet_label.configure(text="₦0")

    def _update_daily_target_display(self):
        """Update the daily target display"""
        self.daily_target_label.configure(text=f"{self.daily_target_reached:.2f}%")
        
        if self.daily_target_reached >= 5.0:
            self.daily_target_reset_btn.configure(state="normal")
        else:
            self.daily_target_reset_btn.configure(state="disabled")

    def _reset_daily_target(self):
        """Reset daily target with capital unlock"""
        if self.daily_target_reached >= 5.0:
            response = messagebox.askyesno(
                "Reset Daily Target",
                "WARNING: Resetting daily target allows continued trading beyond the 5% target.\n\n"
                "Continuing beyond daily target increases risks of financial loss, "
                "emotional stress, and suboptimal performance.\n\n"
                "Are you sure you want to reset the daily target and continue trading?",
                icon="warning"
            )
            if response:
                self.daily_target_reached = 0.0
                self._update_daily_target_display()
                self._save_daily_target()
                
                self.capital_locked = False
                self.capital_entry.configure(state="normal")
                self._log("Daily target reset to 0% - capital unlocked for update")
                
                messagebox.showinfo("Target Reset", 
                                  "Daily target has been reset to 0%. You can now update your capital.")

    def _on_platform_select(self, choice):
        """Handle platform selection with restrictions"""
        if self.trading_started:
            messagebox.showwarning("Platform Change", 
                                 "Cannot change platform while bot is running. Stop the bot first.")
            self.platform_selector.set(self.previous_platform)
            return
        
        if not self.platform_enabled:
            self._show_license_required_message("select a trading platform")
            self.platform_selector.set("SportyBetNg")
            return
        
        self.previous_platform = choice
        self._log(f"Platform selected: {choice}")
        
        config = load_config_json()
        config["platform"] = choice
        save_config_json(config)

    def _show_license_required_message(self, action):
        """Show license required message for protected actions"""
        messagebox.showinfo(
            "License Required",
            f"Valid license required to {action}.\n\n"
            "Please update your license or contact support:\n"
            "Telegram: @OsenaaboSupport"
        )

    def toggle_config_view(self):
        """Toggle configuration panel visibility and adjust content area"""
        if self.config_panel_visible:
            self.config_panel.grid_remove()
            self.status_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.toggle_config_btn.configure(text="◀▶")
            self.config_panel_visible = False
        else:
            self.config_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
            self.status_panel.grid(row=0, column=1, sticky="nsew")
            self.toggle_config_btn.configure(text="◀▶")
            self.config_panel_visible = True

    def _on_block2_toggle(self):
        """Handle block2 toggle"""
        self.block2_enabled = self.block2_var.get()
        self._log(f"Block 2 {'enabled' if self.block2_enabled else 'disabled'}")

    def _log(self, msg, level="info"):
        """Add message to log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {msg}"
        
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", formatted_msg + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")
        
        print(formatted_msg)

    def _refresh_license_ui(self):
        """Update license status in main GUI"""
        license_data = load_license_json()
        if license_data and license_data.get("valid"):
            hwid = license_data.get("hardware_id", "Unknown")
            plan = license_data.get("plan", "Standard")
            expires = license_data.get("expires", "Never")
            self.license_status_var.set(f"Valid | {plan} | PC_{hwid.upper()[:8]}...")
            self.platform_selector.configure(state="normal")
            self.calibrate_btn.configure(state="normal")
            self.start_btn.configure(state="normal")
            self._log(f"License active: {plan} plan")
        else:
            self.license_status_var.set("No valid license")
            self.platform_selector.configure(state="disabled")
            self.calibrate_btn.configure(state="disabled")
            self.start_btn.configure(state="disabled")
            self._log("No valid license - features locked")

    def _update_betting_hours(self):
        """Update trading hours display"""
        try:
            if osenaabo_core:
                hours = osenaabo_core.get_betting_hours()
                formatted_hours = format_betting_hours(hours)
                
                if "Not available" in formatted_hours or "No betting hours" in formatted_hours:
                    self.trading_hours_label.configure(text="Available Today: No trading hours")
                else:
                    self.trading_hours_label.configure(text=f"Available Today: {formatted_hours}")
            else:
                self.trading_hours_label.configure(text="Core module not available")
        except Exception as e:
            self.trading_hours_label.configure(text="Error loading hours")
            self._log(f"Error updating trading hours: {e}")

    def _launch_calibration(self):
        """Launch calibration wizard with platform URL opening"""
        if not self.platform_enabled:
            self._show_license_required_message("calibrate")
            return
        
        platform = self.platform_var.get()
        platform_url = PLATFORM_URLS.get(platform)
        
        if platform_url:
            self._log(f"Opening {platform} URL: {platform_url}")
            try:
                webbrowser.open(platform_url)
                
                messagebox.showinfo("Platform Opened", 
                                  f"{platform} has been opened in your browser.\n\n"
                                  "Please log in and position the game window, then click OK to start calibration.")
                
            except Exception as e:
                self._log(f"Failed to open platform URL: {e}")
                messagebox.showerror("Error", f"Failed to open {platform} URL: {e}")
        
        wizard = CalibrationWizard(self, self.block2_enabled, self._on_calibration_complete)
        wizard.grab_set()

    def _on_calibration_complete(self, coords):
        """Handle calibration completion"""
        self.calib_data = coords
        self._log("Calibration completed successfully")
        save_coords_json(coords)
        self.play_sound("clap")

    def _update_capital_lock(self):
        """Update capital field lock state based on trading status"""
        if self.trading_started and not self.capital_locked:
            self.capital_entry.configure(state="disabled")
            self.capital_locked = True
            self._log("Capital locked - reset required to change")
        elif not self.trading_started and self.capital_locked:
            self.capital_entry.configure(state="normal")
            self.capital_locked = False

    def _toggle_bot(self):
        """Start or stop the bot"""
        if not self.platform_enabled:
            self._show_license_required_message("start the bot")
            return
            
        if self.bot_thread and self.bot_thread.is_alive():
            self._stop_bot()
        else:
            self._start_bot()

    def _start_bot(self):
        """Start the trading bot with session management"""
        try:
            capital = float(self.capital_entry.get().replace(",", ""))
            stop_loss = float(self.stoploss_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values for capital and stop loss")
            return
            
        license_data = load_license_json()
        if not license_data or not license_data.get("valid"):
            messagebox.showerror("Error", "Valid license required to start bot")
            return
            
        self._save_telegram_settings()
            
        if not is_within_betting_hours():
            response = messagebox.askyesno(
                "Outside Betting Hours", 
                "Current time is outside configured betting hours. Continue anyway?"
            )
            if not response:
                return
        
        self.current_session_type = check_session_continuation()
        if self.current_session_type == "tomorrow":
            self._log("Session start cancelled by user")
            return
            
        if self.current_session_type == "continue":
            session_data = load_today_session()
            if session_data.get("sessions"):
                last_session = session_data["sessions"][-1]
                self.session_start_capital = last_session["capital_after"]
                self._log(f"Continuing from previous session. Capital: ₦{self.session_start_capital:,.2f}")
                self._load_session_cookies()
        else:
            self.session_start_capital = capital
            if self.current_session_type == "reset":
                save_today_session({"sessions": [], "target_reached": False})
                self.session_cookies = {}
                self._save_session_cookies()
                self._log("Previous session data cleared. Starting fresh session.")
            else:
                self._log("Starting fresh session.")
        
        self.trading_started = True
        self._update_capital_lock()
        
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.platform_selector.configure(state="disabled")
        
        self.stop_event.clear()
        self.bot_thread = threading.Thread(target=self._run_bot, daemon=True)
        self.bot_thread.start()
        
        self._log("Bot started successfully")
        self.play_sound("found")

    def _stop_bot(self):
        """Stop the trading bot and unlock platform selection"""
        self.stop_event.set()
        self.trading_started = False
        self._update_capital_lock()
        
        self.platform_selector.configure(state="normal")
        
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self._log("Bot stopping...")

    def _load_session_cookies(self):
        """Load session cookies from file"""
        try:
            session_file = get_today_session_file().replace('.json', '_cookies.json')
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    self.session_cookies = json.load(f)
                self._log("Session cookies loaded")
        except Exception as e:
            self._log(f"Error loading session cookies: {e}")

    def _save_session_cookies(self):
        """Save session cookies to file"""
        try:
            session_file = get_today_session_file().replace('.json', '_cookies.json')
            with open(session_file, 'w') as f:
                json.dump(self.session_cookies, f, indent=2)
        except Exception as e:
            self._log(f"Error saving session cookies: {e}")

    def _run_bot(self):
        """Main bot execution loop with session management"""
        try:
            self._save_session_cookies()
            
            count = 0
            while not self.stop_event.is_set() and count < 10:
                self._log(f"Bot running... {count}")
                
                if count % 3 == 0:
                    self.session_cookies['last_activity'] = datetime.now().isoformat()
                    self._save_session_cookies()
                    self._log("Session cookies updated")
                
                time.sleep(2)
                count += 1
                
            if not self.stop_event.is_set():
                self._log("Bot completed normally")
            else:
                self._log("Bot stopped by user")
                
        except Exception as e:
            self._log(f"Bot error: {str(e)}")
        finally:
            self._save_session_cookies()
            
            self.after(0, lambda: self.start_btn.configure(state="normal"))
            self.after(0, lambda: self.stop_btn.configure(state="disabled"))
            self.after(0, lambda: self.platform_selector.configure(state="normal"))

    def on_closing(self):
        """Handle application closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if self.bot_thread and self.bot_thread.is_alive():
                self.stop_event.set()
                self.bot_thread.join(timeout=5)
            
            cleanup_tkinter()
            self.destroy()

# Helper function
def now_ts():
    return datetime.now().strftime("%H:%M:%S")

def load_inline_logo_image(size=(36, 36)):
    """Return a ctk-compatible image from inline base64 logo."""
    try:
        raw = base64.b64decode(BASE64_LOGO)
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        img = img.resize(size, Image.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception:
        return None

# First Run License Setup
def first_time_setup():
    """Check if this is first run and setup license"""
    license_data = load_license_json()
    
    if not license_data or not license_data.get("valid"):
        if IS_MAC:
            setup_width, setup_height = 480, 420
        else:
            setup_width, setup_height = 500, 450
            
        root = ctk.CTk()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        root.title("OSENAABO! License Activation")
        root.geometry(f"{setup_width}x{setup_height}")
        root.resizable(False, False)
        
        def center_window(window):
            window.update_idletasks()
            width = window.winfo_width()
            height = window.winfo_height()
            x = (window.winfo_screenwidth() // 2) - (width // 2)
            y = (window.winfo_screenheight() // 2) - (height // 2)
            window.geometry(f'{width}x{height}+{x}+{y}')
        
        center_window(root)
        
        title_font_size = 20 if IS_MAC else 22
        normal_font_size = 12 if IS_MAC else 14
        
        main_frame = ctk.CTkFrame(root, corner_radius=12)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15, 8))
        
        ctk.CTkLabel(header_frame, text="🎯 OSENAABO! Activation", 
                    font=ctk.CTkFont(size=title_font_size, weight="bold")).pack(pady=(0, 4))
        
        ctk.CTkLabel(header_frame, 
                    text="Welcome to OSENAABO! - The 3rd 👁️\nPlease activate your license to continue.",
                    font=ctk.CTkFont(size=normal_font_size-2),
                    text_color="lightblue",
                    justify="center").pack()
        
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=15, pady=8)
        
        ctk.CTkLabel(content_frame, text="Telegram User ID:", 
                    font=ctk.CTkFont(weight="bold", size=normal_font_size-1)).pack(anchor="w", pady=(8, 3))
        tg_entry = ctk.CTkEntry(content_frame, height=MAC_ENTRY_HEIGHT if IS_MAC else 35)
        tg_entry.pack(fill="x", pady=(0, 12))
        
        ctk.CTkLabel(content_frame, text="License Key:", 
                    font=ctk.CTkFont(weight="bold", size=normal_font_size-1)).pack(anchor="w", pady=(3, 3))
        license_entry = ctk.CTkEntry(content_frame, height=MAC_ENTRY_HEIGHT if IS_MAC else 35,
                                   placeholder_text="Enter your license key")
        license_entry.pack(fill="x", pady=(0, 15))
        
        support_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        support_frame.pack(fill="x", pady=8)
        
        ctk.CTkLabel(support_frame, 
                    text="Need a license? Contact: @OsenaaboSupport",
                    text_color="lightblue",
                    font=ctk.CTkFont(size=normal_font_size-2),
                    justify="center").pack()
        
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(8, 0))
        
        def activate_license():
            tg_id = tg_entry.get().strip()
            license_key = license_entry.get().strip()
            
            if not tg_id or not license_key:
                messagebox.showerror("Error", "Both Telegram ID and License Key are required")
                return
            
            activate_btn.configure(state="disabled", text="Validating...")
            root.update()
            
            try:
                validation_input = f"{tg_id}:{license_key}"
                license_path = get_license_path()
                
                result = validate_license_with_hardware(validation_input, license_path)
                
                if result["valid"]:
                    # Success - reload license
                    messagebox.showinfo(
                        "License Activated",
                        f"License activated successfully!\n\n"
                        f"Telegram ID: {result.get('telegram_id')}\n"
                        f"Plan: {result.get('plan')}\n"
                        f"Expires: {result.get('expires')}\n"
                        f"Hardware: PC_{result.get('hardware_id','?').upper()}\n"
                        f"Activation: {result.get('activation_date','Now')}\n\n"
                        f"This license is now permanently bound to this computer."
                    )
                    root.destroy()
                    start_main_app()
                else:
                    messagebox.showerror(
                        "Activation Failed",
                        f"{result.get('message','Invalid license')}\n\n"
                        f"{result.get('details','')}\n\n"
                        f"Contact @OsenaaboSupport for help."
                    )
            except Exception as e:
                messagebox.showerror("Error", f"Validation error: {e}")
            finally:
                activate_btn.configure(state="normal", text="Activate License")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Activation error: {str(e)}")
                activate_btn.configure(state="normal", text="Activate License")
        
        def skip_activation():
            if messagebox.askyesno("Skip Activation", 
                                 "Without a valid license, most features will be disabled.\n\n"
                                 "Are you sure you want to continue?"):
                root.destroy()
                start_main_app()
        
        activate_btn = ctk.CTkButton(button_frame, text="Activate License", 
                                   command=activate_license,
                                   fg_color="#1f6aa5", 
                                   hover_color="#144870",
                                   height=MAC_BUTTON_HEIGHT if IS_MAC else 40,
                                   font=ctk.CTkFont(weight="bold", size=normal_font_size-1))
        activate_btn.pack(fill="x", pady=(0, 8))
        
        skip_btn = ctk.CTkButton(button_frame, text="Skip for Now", 
                               command=skip_activation,
                               fg_color="gray", 
                               hover_color="darkgray",
                               height=MAC_BUTTON_HEIGHT-3 if IS_MAC else 35,
                               font=ctk.CTkFont(size=normal_font_size-1))
        skip_btn.pack(fill="x")
        
        tg_entry.focus()
        
        def on_enter_key(event):
            activate_license()
        
        root.bind('<Return>', on_enter_key)
        
        root.mainloop()
    else:
        start_main_app()

def start_main_app():
    """Start the main OSENAABO application"""
    try:
        app = OsenaaboApp()
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start application:\n{str(e)}")
        traceback.print_exc()

# ---------------------------
# Application Entry Point
# ---------------------------
if __name__ == "__main__":
    try:
        first_time_setup()
    except Exception as e:
        messagebox.showerror("Critical Error", f"Application failed to start:\n{str(e)}")
        traceback.print_exc()
    finally:
        cleanup_tkinter()