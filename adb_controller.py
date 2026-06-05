import subprocess
import time
import os
from config import DEVICE_SERIAL, ADB_HOST, ADB_PORT

class ADBController:
    """LDPlayer ke saath ADB communication handle karta hai"""
    
    def __init__(self):
        self.device = DEVICE_SERIAL
        self._connect()
    
    def _connect(self):
        """LDPlayer se ADB connect karein"""
        print(f"[ADB] Connecting to {self.device}...")
        
        result = subprocess.run(
            ["adb", "connect", self.device],
            capture_output=True, text=True
        )
        
        if "connected" in result.stdout.lower():
            print(f"[ADB] ✅ Connected successfully")
        else:
            print(f"[ADB] ❌ Connection failed: {result.stdout}")
            raise ConnectionError(f"ADB connection failed: {result.stdout}")
    
    def run_command(self, *args) -> str:
        """ADB command run karein"""
        cmd = ["adb", "-s", self.device] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip()
    
    def pull_file(self, android_path: str, local_path: str) -> bool:
        """Android se file pull karein"""
        try:
            result = subprocess.run(
                ["adb", "-s", self.device, "pull", android_path, local_path],
                capture_output=True, text=True, timeout=120
            )
            return result.returncode == 0
        except Exception as e:
            print(f"[ADB] Pull error: {e}")
            return False
    
    def pull_directory(self, android_dir: str, local_dir: str) -> bool:
        """Pura directory pull karein"""
        os.makedirs(local_dir, exist_ok=True)
        try:
            result = subprocess.run(
                ["adb", "-s", self.device, "pull", android_dir, local_dir],
                capture_output=True, text=True, timeout=300
            )
            return result.returncode == 0
        except Exception as e:
            print(f"[ADB] Directory pull error: {e}")
            return False
    
    def list_files(self, android_path: str) -> list:
        """Android directory ki files list karein"""
        output = self.run_command("shell", "ls", android_path)
        if "No such file" in output:
            return []
        return [f.strip() for f in output.split('\n') if f.strip()]
    
    def get_file_size(self, android_path: str) -> int:
        """File size bytes mein"""
        output = self.run_command("shell", "stat", "-c", "%s", android_path)
        try:
            return int(output.strip())
        except:
            return 0
    
    def take_screenshot(self, save_path: str = None) -> bytes:
        """Screenshot lein (debugging ke liye)"""
        self.run_command("shell", "screencap", "-p", "/sdcard/temp_screenshot.png")
        if save_path:
            self.pull_file("/sdcard/temp_screenshot.png", save_path)
        output = subprocess.run(
            ["adb", "-s", self.device, "exec-out", "screencap", "-p"],
            capture_output=True
        )
        return output.stdout
    
    def is_screen_on(self) -> bool:
        output = self.run_command("shell", "dumpsys", "power")
        return "mWakefulness=Awake" in output
    
    def wake_screen(self):
        if not self.is_screen_on():
            self.run_command("shell", "input", "keyevent", "KEYCODE_WAKEUP")
            time.sleep(1)