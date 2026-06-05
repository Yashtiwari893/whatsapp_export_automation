import os
import json
import time
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Drive permissions
SCOPES = ['https://www.googleapis.com/auth/drive']

# Local paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "data", "drive_token.json")

# Drive folder structure
DRIVE_ROOT_FOLDER = "WhatsApp Exports"  # Drive me yeh folder banega


class DriveUploader:
    """
    Google Drive automatic uploader.
    Ek baar login karo — phir sab automatic.
    """

    def __init__(self):
        self.service = self._authenticate()
        self.folder_cache = {}  # folder name → folder id cache
        print("[Drive] ✅ Google Drive connected")

    def _authenticate(self):
        """OAuth authentication — pehli baar browser khulega, phir automatic"""
        creds = None

        # Saved token check karo
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        # Token invalid ya expired hai
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Pehli baar — browser mein login
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Token save karo future use ke liye
            os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
            with open(TOKEN_FILE, 'w') as f:
                f.write(creds.to_json())

        return build('drive', 'v3', credentials=creds)

    # ==================== Folder Management ====================

    def get_or_create_folder(self, folder_name: str,
                              parent_id: str = None) -> str:
        """
        Folder ID return karo — exist nahi karta toh create karo.
        Cache se fast lookup.
        """
        cache_key = f"{parent_id}_{folder_name}"
        if cache_key in self.folder_cache:
            return self.folder_cache[cache_key]

        # Search karo existing folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = self.service.files().list(
            q=query,
            fields="files(id, name)"
        ).execute()

        files = results.get('files', [])

        if files:
            folder_id = files[0]['id']
        else:
            # Naya folder banao
            metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                metadata['parents'] = [parent_id]

            folder = self.service.files().create(
                body=metadata,
                fields='id'
            ).execute()
            folder_id = folder['id']
            print(f"[Drive] 📁 Folder created: {folder_name}")

        self.folder_cache[cache_key] = folder_id
        return folder_id

    def get_folder_structure(self, chat_type: str) -> str:
        """
        Drive folder structure:
        WhatsApp Exports/
        ├── Personal Chats/
        └── Group Chats/
        """
        # Root folder
        root_id = self.get_or_create_folder(DRIVE_ROOT_FOLDER)

        # Type folder
        if chat_type == "group":
            type_folder = "Group Chats"
        else:
            type_folder = "Personal Chats"

        type_id = self.get_or_create_folder(type_folder, root_id)
        return type_id

    # ==================== Upload ====================

    def upload_file(self, local_path: str, chat_name: str,
                    chat_type: str) -> str:
        """
        File ko Drive pe upload karo.
        Returns: Drive file ID
        """
        if not os.path.exists(local_path):
            print(f"[Drive] ❌ File not found: {local_path}")
            return None

        file_size = os.path.getsize(local_path)
        file_name = os.path.basename(local_path)

        print(f"[Drive] ⬆️  Uploading: {file_name} "
              f"({self._human_size(file_size)})")

        # Folder structure banao
        root_id = self.get_or_create_folder(DRIVE_ROOT_FOLDER)

        type_folder = "Personal Chats" if chat_type == "personal" else "Group Chats"
        type_id = self.get_or_create_folder(type_folder, root_id)

        chat_folder_id = self.get_or_create_folder(chat_name, type_id)

        # Duplicate check
        if self.file_exists_on_drive(file_name, chat_folder_id):
            print(f"[Drive] ⏭️  Already on Drive — skipping")
            return "already_exists"

        # File metadata
        file_metadata = {
            'name': file_name,
            'parents': [chat_folder_id]
        }

        # MIME type detect karo
        mime_type = self._get_mime_type(local_path)

        # Upload
        media = MediaFileUpload(
            local_path,
            mimetype=mime_type,
            resumable=True
        )

        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name'
            ).execute()

            drive_id = file.get('id')
            print(f"[Drive] ✅ Uploaded to: WhatsApp Exports/{type_folder}/{chat_name}/{file_name}")
            return drive_id

        except Exception as e:
            print(f"[Drive] ❌ Upload failed: {e}")
            return None

    def find_and_move_latest_export(self, chat_name: str,
                                    chat_type: str) -> str:
        """
        Drive root mein latest uploaded WhatsApp export dhundho,
        phir sahi folder mein move karo.
        Returns file_id or None.
        """
        import time as t

        # Thoda wait — upload complete hone do
        t.sleep(3)

        query = (
            "trashed=false and ("
            "name contains 'WhatsApp Chat' or "
            "name contains '_chat' or "
            "mimeType='application/zip' or "
            "mimeType='text/plain'"
            ")"
        )

        results = self.service.files().list(
            q=query,
            orderBy="createdTime desc",
            fields="files(id, name, parents, createdTime, mimeType)",
            pageSize=5
        ).execute()

        files = results.get('files', [])
        print(f"[Drive] Found {len(files)} recent files:")
        for f in files:
            print(f"       → {f['name']} ({f['id']})")

        if not files:
            print("[Drive] ❌ Koi recent file nahi mili")
            return None

        latest = files[0]
        file_id = latest['id']
        file_name = latest['name']

        print(f"[Drive] 📄 Latest file: {file_name}")

        # Target folder banao
        root_id = self.get_or_create_folder(DRIVE_ROOT_FOLDER)
        type_folder = "Personal Chats" if chat_type == "personal" else "Group Chats"
        type_id = self.get_or_create_folder(type_folder, root_id)
        chat_folder_id = self.get_or_create_folder(chat_name, type_id)

        try:
            file_info = self.service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            current_parents = ",".join(file_info.get('parents', []))

            self.service.files().update(
                fileId=file_id,
                addParents=chat_folder_id,
                removeParents=current_parents,
                fields='id, parents'
            ).execute()

            print(f"[Drive] ✅ Moved to: WhatsApp Exports/{type_folder}/{chat_name}/{file_name}")
            return file_id

        except Exception as e:
            print(f"[Drive] ❌ Move failed: {e}")
            return None

    def file_exists_on_drive(self, file_name: str,
                              parent_id: str) -> bool:
        """Check karo file already Drive pe hai"""
        query = (f"name='{file_name}' and "
                 f"'{parent_id}' in parents and trashed=false")
        results = self.service.files().list(
            q=query, fields="files(id)"
        ).execute()
        return len(results.get('files', [])) > 0

    # ==================== Helpers ====================

    def _get_mime_type(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        mime_map = {
            '.zip': 'application/zip',
            '.txt': 'text/plain',
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.png': 'image/png',
            '.mp4': 'video/mp4',
            '.opus': 'audio/opus',
            '.mp3': 'audio/mpeg',
        }
        return mime_map.get(ext, 'application/octet-stream')

    def _human_size(self, size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} GB"