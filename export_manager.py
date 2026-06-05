import time
import os
from config import *
from ui_automator import WhatsAppUIAutomator
from progress_tracker import ProgressTracker
from adb_controller import ADBController
from file_manager import FileManager
from drive_uploader import DriveUploader  # ← NEW


class ExportManager:

    def __init__(self):
        self.ui = WhatsAppUIAutomator()
        self.tracker = ProgressTracker()
        self.adb = ADBController()
        self.file_manager = FileManager()

        # Drive uploader initialize karo
        print("[Export] 🔗 Google Drive se connect ho raha hai...")
        self.drive = DriveUploader()

    def export_all_chats(self, chats: list):
        total = len(chats)
        exported = 0
        failed = 0
        skipped = 0

        print(f"\n[Export] 🚀 Starting export of {total} chats...")
        print(f"[Export] {'='*50}")

        for index, chat in enumerate(chats, 1):
            chat_name = chat["name"]
            chat_type = chat["type"]

            print(f"\n[Export] [{index}/{total}] {chat_name}")

            if self.tracker.is_exported(chat_name):
                print(f"[Export] ⏭️  Already exported — SKIPPED")
                skipped += 1
                continue

            success = self._export_with_retry(chat_name, chat_type)

            if success:
                exported += 1
                print(f"[Export] ✅ Done ({exported} exported)")
            else:
                failed += 1
                print(f"[Export] ❌ Failed ({failed} failed)")

            if index % BATCH_SIZE == 0:
                stats = self.tracker.get_stats()
                print(f"\n[Progress] Exported: {stats['exported']} | "
                      f"Failed: {stats['failed']}")

        print(f"\n[Export] {'='*50}")
        print(f"[Export] 🏁 Complete!")
        self._print_final_stats(total, exported, failed, skipped)

    def _export_with_retry(self, chat_name: str,
                            chat_type: str) -> bool:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if attempt > 1:
                    print(f"[Export] 🔄 Retry {attempt}/{MAX_RETRIES}...")
                    time.sleep(RETRY_DELAY)

                self.tracker.mark_in_progress(chat_name)

                # Step 1: Chat open karo
                if not self.ui.open_chat_by_name(chat_name):
                    raise Exception("Chat open nahi hua")
                time.sleep(1)

                # Step 2: Export karo (Drive pe jaayega)
                if not self.ui.export_current_chat(INCLUDE_MEDIA):
                    raise Exception("Export process fail hua")

                # Step 3: Drive pe file dhundho aur move karo
                print("[Drive] 🔍 Drive pe uploaded file dhundh raha hai...")
                time.sleep(5)

                drive_id = self.drive.find_and_move_latest_export(
                    chat_name, chat_type
                )

                if drive_id:
                    print(f"[Drive] ✅ File sahi folder mein move ho gayi!")
                    self.tracker.mark_exported(chat_name, f"drive:{drive_id}")
                    self.ui.go_to_chat_list()
                    time.sleep(0.5)
                    return True
                else:
                    raise Exception("Drive pe file nahi mili")

            except Exception as e:
                print(f"[Export] ⚠️  Attempt {attempt} failed: {e}")
                self.tracker.mark_failed(chat_name, str(e))
                self._recover_app()

        return False

    def _collect_exported_file(self, chat_name: str,
                                chat_type: str) -> str:
        """
        Android se latest exported file pull karo.
        Multiple locations check karta hai.
        """
        import time as t

        # WhatsApp export possible locations
        android_dirs = [
            "/sdcard/WhatsApp/Exported/",
            "/sdcard/Android/media/com.whatsapp/WhatsApp/Exported/",
            "/sdcard/WhatsApp/Media/",
            "/sdcard/Downloads/",
        ]

        # Thoda wait karo — export complete hone do
        t.sleep(3)

        for android_dir in android_dirs:
            print(f"[ADB] Checking: {android_dir}")
            files = self.adb.list_files(android_dir)

            if files:
                print(f"[ADB] Files found in {android_dir}: {files}")

                export_files = [
                    f for f in files
                    if f.endswith('.zip') or
                       f.endswith('.txt') or
                       'WhatsApp Chat' in f
                ]

                if not export_files:
                    export_files = files

                latest_file = export_files[-1]
                android_path = f"{android_dir}{latest_file}"

                local_dir = self.file_manager.get_export_dir(
                    chat_name, chat_type
                )
                local_path = os.path.join(local_dir, latest_file)

                print(f"[ADB] Pulling: {android_path} → {local_path}")

                if self.adb.pull_file(android_path, local_path):
                    self.adb.run_command("shell", "rm", android_path)
                    print(f"[ADB] ✅ File pulled: {local_path}")
                    return local_path
                else:
                    print(f"[ADB] ❌ Pull failed")

        # Kuch nahi mila — debug ke liye saari files list karo
        print("[ADB] 🔍 /sdcard/ mein kya hai:")
        all_files = self.adb.run_command("shell", "ls", "/sdcard/")
        print(all_files)

        print("[ADB] 🔍 WhatsApp folder:")
        wa_files = self.adb.run_command("shell", "ls", "/sdcard/WhatsApp/")
        print(wa_files)

        return None

    def _recover_app(self):
        print("[Export] 🔧 Recovering...")
        try:
            for _ in range(5):
                self.ui.press_back()
                time.sleep(0.3)
            if not self.ui.is_whatsapp_active():
                self.ui.launch_whatsapp()
            else:
                self.ui.go_to_chat_list()
            time.sleep(2)
        except Exception:
            try:
                self.ui.launch_whatsapp()
                time.sleep(3)
            except:
                pass

    def _print_final_stats(self, total, exported, failed, skipped):
        print(f"  Total:      {total}")
        print(f"  ✅ Exported: {exported}")
        print(f"  ❌ Failed:   {failed}")
        print(f"  ⏭️  Skipped: {skipped}")