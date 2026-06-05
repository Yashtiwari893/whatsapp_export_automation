import os

# === ADB Configuration ===
ADB_HOST = "127.0.0.1"
ADB_PORT = 5555  # LDPlayer default port
DEVICE_SERIAL = f"{ADB_HOST}:{ADB_PORT}"

# === WhatsApp Package ===
WHATSAPP_PACKAGE = "com.whatsapp"
WHATSAPP_ACTIVITY = "com.whatsapp/.HomeActivity"

# === Paths ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORT_BASE_DIR = os.path.join(BASE_DIR, "exports")
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "progress.db")
CHAT_LIST_CACHE = os.path.join(DATA_DIR, "chat_list.json")

# Android Export Path (LDPlayer shared folder)
ANDROID_EXPORT_PATH = "/sdcard/WhatsApp/Media"
LDPLAYER_SHARED_PATH = r"C:\LDPlayer\vms\operaterecord\pictures"  # Apna path set karein

# === Timing Configuration ===
SCROLL_DELAY = 1.0          # Chat list scroll ke baad wait
EXPORT_WAIT_TIME = 15       # Export complete hone ka wait (seconds)
MEDIA_EXPORT_WAIT = 30      # Media include hone par extra wait
UI_RESPONSE_TIMEOUT = 10    # UI element appear hone ka timeout
RETRY_DELAY = 5             # Retry ke beech wait

# === Retry Configuration ===
MAX_RETRIES = 3
MAX_SCROLL_ATTEMPTS = 500   # 5000 chats ke liye

# === Export Options ===
INCLUDE_MEDIA = True         # Media include karein
BATCH_SIZE = 50              # Kitni chats baad save karein

# === File Organization ===
ORGANIZE_BY_TYPE = True      # Personal / Group alag folders
ORGANIZE_BY_DATE = False     # Date wise organize (optional)