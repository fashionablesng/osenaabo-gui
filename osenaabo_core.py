# osenaabo_core.py
"""
Core wrapper module for OSENAABO! GUI to interface with the bot logic.
"""

import json
import os
import sys
import platform
from datetime import datetime, time
import subprocess
import threading
from typing import Optional, Dict, Any

# Platform detection
IS_MAC = platform.system() == 'Darwin'
IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'

class OsenaaboCore:
    """Core interface between GUI and bot logic"""
    
    def __init__(self):
        self.bot_process = None
        self.bot_running = False
        self.current_session_data = {}
    
    def get_platform_tesseract_path(self):
        """Get Tesseract path based on platform"""
        if IS_MAC:
            mac_paths = [
                '/usr/local/bin/tesseract',
                '/opt/homebrew/bin/tesseract',
                '/usr/bin/tesseract'
            ]
            for path in mac_paths:
                if os.path.exists(path):
                    return path
            return 'tesseract'
        elif IS_WINDOWS:
            return r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        else:  # Linux
            return '/usr/bin/tesseract'
    
    def get_betting_hours(self) -> str:
        """Get formatted betting hours for today"""
        try:
            # Fallback betting hours - you can customize these
            betting_hours = {
                0: "09:00-12:00 | 14:00-17:00 | 19:00-22:00",  # Monday
                1: "09:00-12:00 | 14:00-17:00 | 19:00-22:00",  # Tuesday
                2: "09:00-12:00 | 14:00-17:00 | 19:00-22:00",  # Wednesday
                3: "09:00-12:00 | 14:00-17:00 | 19:00-22:00",  # Thursday
                4: "09:00-12:00 | 14:00-17:00 | 19:00-22:00",  # Friday
                5: "09:00-12:00 | 14:00-17:00 | 19:00-22:00",  # Saturday
                6: "09:00-12:00 | 14:00-17:00 | 19:00-22:00",  # Sunday
            }
            
            today = datetime.now().weekday()
            return betting_hours.get(today, "09:00-12:00 | 14:00-17:00 | 19:00-22:00")
            
        except Exception as e:
            return "09:00-12:00 | 14:00-17:00 | 19:00-22:00"
    
    def is_within_betting_hours(self) -> bool:
        """Check if current time is within betting hours"""
        try:
            now = datetime.now().time()
            # Simple check for demo - adjust as needed
            current_hour = now.hour
            return (9 <= current_hour < 12) or (14 <= current_hour < 17) or (19 <= current_hour < 22)
        except:
            return True
    
    def get_bot_status(self) -> Dict[str, Any]:
        """Get current bot status"""
        return {
            "available": True,
            "capital": 1000000,
            "profit": 0,
            "target_percent": 5,
            "running": self.bot_running
        }
    
    def start_bot(self, config: Dict[str, Any]) -> bool:
        """Start the bot with given configuration"""
        if self.bot_running:
            return False
        
        try:
            # Save configuration
            config_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Osenaabo')
            os.makedirs(config_dir, exist_ok=True)
            
            config_path = os.path.join(config_dir, 'gui_config.json')
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.bot_running = True
            print("✅ Bot started successfully (simulation mode)")
            return True
            
        except Exception as e:
            print(f"Error starting bot: {e}")
            self.bot_running = False
            return False
    
    def stop_bot(self) -> bool:
        """Stop the bot"""
        if not self.bot_running:
            return False
        
        self.bot_running = False
        print("✅ Bot stopped successfully")
        return True
    
    def validate_environment(self) -> Dict[str, bool]:
        """Validate that all required components are available"""
        checks = {
            'bot_module': True,
            'tesseract': self._check_tesseract(),
            'coordinates': os.path.exists('aviator_coordinates.json'),
            'dependencies': self._check_dependencies()
        }
        return checks
    
    def _check_tesseract(self) -> bool:
        """Check if Tesseract OCR is available"""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except:
            return False
    
    def _check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        try:
            import pyautogui
            import cv2
            import numpy as np
            import requests
            return True
        except ImportError:
            return False

# Create global instance
core = OsenaaboCore()

# Export functions for GUI
def get_betting_hours():
    return core.get_betting_hours()

def is_within_betting_hours():
    return core.is_within_betting_hours()

def get_bot_status():
    return core.get_bot_status()

def start_bot(config):
    return core.start_bot(config)

def stop_bot():
    return core.stop_bot()

def validate_environment():
    return core.validate_environment()

def get_platform_tesseract_path():
    return core.get_platform_tesseract_path()