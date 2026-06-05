import os
import re
import shutil
from datetime import datetime
from config import EXPORT_BASE_DIR

class FileManager:
    """Export files ko organize aur manage karta hai"""
    
    def __init__(self):
        self._create_directories()
    
    def _create_directories(self):
        """Base directories create karein"""
        dirs = [
            EXPORT_BASE_DIR,
            os.path.join(EXPORT_BASE_DIR, "personal"),
            os.path.join(EXPORT_BASE_DIR, "groups"),
            os.path.join(EXPORT_BASE_DIR, "media"),
            os.path.join(EXPORT_BASE_DIR, "_failed"),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)
    
    def get_export_dir(self, chat_name: str, chat_type: str) -> str:
        """Chat ke liye export directory get/create karein"""
        safe_name = self._sanitize_filename(chat_name)
        
        if chat_type == "group":
            folder = os.path.join(EXPORT_BASE_DIR, "groups", safe_name)
        else:
            folder = os.path.join(EXPORT_BASE_DIR, "personal", safe_name)
        
        os.makedirs(folder, exist_ok=True)
        return folder
    
    def _sanitize_filename(self, name: str) -> str:
        """Filename safe banaayen"""
        # Invalid characters remove karein
        safe = re.sub(r'[<>:"/\\|?*]', '_', name)
        safe = safe.strip('. ')
        safe = safe[:50]  # Max 50 chars
        return safe if safe else "unnamed_chat"
    
    def organize_media(self, export_dir: str):
        """
        Exported zip se media files extract karke organize karein.
        """
        import zipfile
        
        media_types = {
            "images": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
            "videos": [".mp4", ".mkv", ".avi", ".mov", ".3gp"],
            "audio": [".mp3", ".ogg", ".opus", ".m4a", ".wav"],
            "documents": [".pdf", ".doc", ".docx", ".xlsx", ".pptx", ".txt"]
        }
        
        # Zip files dhundho
        for filename in os.listdir(export_dir):
            if filename.endswith('.zip'):
                zip_path = os.path.join(export_dir, filename)
                
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        for member in zf.namelist():
                            ext = os.path.splitext(member)[1].lower()
                            
                            # Media type determine karein
                            media_folder = None
                            for folder, extensions in media_types.items():
                                if ext in extensions:
                                    media_folder = folder
                                    break
                            
                            if media_folder:
                                target_dir = os.path.join(export_dir, media_folder)
                                os.makedirs(target_dir, exist_ok=True)
                                zf.extract(member, target_dir)
                except Exception as e:
                    print(f"[FileManager] Organize error: {e}")