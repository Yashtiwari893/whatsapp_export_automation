import uiautomator2 as u2
import time
import os
import subprocess
from config import *

class WhatsAppUIAutomator:

    def __init__(self):
        print(f"[UI] Connecting to device {DEVICE_SERIAL}...")
        self.d = u2.connect(DEVICE_SERIAL)
        print(f"[UI] ✅ Device connected: {self.d.device_info['model']}")

    # ==================== App Control ====================

    def launch_whatsapp(self):
        print("[UI] Launching WhatsApp...")
        
        self.d.app_stop(WHATSAPP_PACKAGE)
        time.sleep(1)

        subprocess.run([
            "adb", "-s", DEVICE_SERIAL,
            "shell", "am", "start",
            "-n", "com.whatsapp/com.whatsapp.home.ui.HomeActivity"
        ], capture_output=True)
        time.sleep(4)

        # Wait for chat list to appear
        found = self.d(resourceId="android:id/list").wait(timeout=15)
        if found:
            print("[UI] ✅ WhatsApp launched successfully")
        else:
            print("[UI] ⚠️  Chat list not found — 10 sec extra wait...")
            time.sleep(10)

    def go_to_chat_list(self):
        """Main chat list par jaayein"""
        for _ in range(4):
            self.d.press("back")
            time.sleep(0.4)
        
        # Chats tab click karein (bottom nav)
        chats_tab = self.d(description="Chats,1 new notification")
        if not chats_tab.exists:
            chats_tab = self.d(descriptionContains="Chats")
        if chats_tab.exists:
            chats_tab.click()
        time.sleep(1)

    # ==================== Chat Discovery ====================

    def get_visible_chats(self) -> list:
        chats = []

        # Sahi resourceId: contact_row_container ke andar conversations_row_contact_name
        items = self.d(resourceId="com.whatsapp:id/conversations_row_contact_name")
        count = items.count

        if count == 0:
            return []

        for i in range(count):
            try:
                name = items[i].get_text()
                if name and name.strip():
                    chat_type = self._detect_chat_type(name)
                    chats.append({"name": name.strip(), "type": chat_type})
            except Exception:
                continue

        return chats

    def _detect_chat_type(self, chat_name: str) -> str:
        group_indicators = [
            "group", "grp", "family", "team", "class", "batch",
            "society", "colony", "office", "school", "college",
            "friends", "gang", "club", "association", "committee"
        ]
        name_lower = chat_name.lower()
        for indicator in group_indicators:
            if indicator in name_lower:
                return "group"
        return "personal"

    def scroll_chat_list_down(self):
        """Chat list scroll karein — list ke andar swipe"""
        # android:id/list par directly swipe
        chat_list = self.d(resourceId="android:id/list")
        if chat_list.exists:
            chat_list.swipe("up", steps=30)
        else:
            # Fallback: screen swipe
            sw = self.d.window_size()
            self.d.swipe(sw[0]//2, int(sw[1]*0.75),
                         sw[0]//2, int(sw[1]*0.25), duration=0.4)
        time.sleep(SCROLL_DELAY)

    def is_at_end_of_list(self, prev_names: set, curr_names: set) -> bool:
        return len(prev_names) > 0 and prev_names == curr_names

    # ==================== Chat Export ====================

    def open_chat_by_name(self, chat_name: str) -> bool:
        """Chat search karke open karein"""
        try:
            # Search bar click karein
            search_bar = self.d(resourceId="com.whatsapp:id/search_bar_inner_layout")
            if not search_bar.exists:
                search_bar = self.d(resourceId="com.whatsapp:id/my_search_bar")
            
            if not search_bar.exists:
                print(f"[UI] Search bar nahi mila")
                return self._open_chat_direct(chat_name)

            search_bar.click()
            time.sleep(1)

            # Search input mein type karein
            search_input = self.d(resourceId="com.whatsapp:id/search_input")
            if not search_input.exists:
                search_input = self.d(focused=True)

            if search_input.exists:
                search_input.clear_text()
                search_input.set_text(chat_name[:40])
                time.sleep(2)

                # Result mein exact match dhundho
                result = self.d(resourceId="com.whatsapp:id/conversations_row_contact_name",
                                text=chat_name)
                if result.exists:
                    result.click()
                    time.sleep(1.5)
                    return True

                # Partial match try karein
                results = self.d(resourceId="com.whatsapp:id/conversations_row_contact_name")
                if results.count > 0:
                    results[0].click()
                    time.sleep(1.5)
                    return True

            # Search dismiss karein
            self.d.press("back")
            time.sleep(0.5)

        except Exception as e:
            print(f"[UI] Search error: {e}")
            try:
                self.d.press("back")
            except:
                pass

        return False

    def _open_chat_direct(self, chat_name: str) -> bool:
        """Direct chat list mein click karein"""
        item = self.d(resourceId="com.whatsapp:id/conversations_row_contact_name",
                      text=chat_name)
        if item.exists:
            item.click()
            time.sleep(1.5)
            return True
        return False

    def export_current_chat(self, include_media: bool = True) -> bool:
        try:
            # Step 1: Three-dot menu
            overflow = self.d(resourceId="com.whatsapp:id/menuitem_overflow")
            if not overflow.exists:
                overflow = self.d(description="More options")
            if not overflow.exists:
                print("[UI] Overflow menu nahi mila")
                return False
            overflow.click()
            time.sleep(0.8)

            # Step 2: "More" option
            more = self.d(text="More")
            if not more.exists:
                print("[UI] 'More' option nahi mila")
                self.d.press("back")
                return False
            more.click()
            time.sleep(0.8)

            # Step 3: "Export chat"
            export = self.d(text="Export chat")
            if not export.exists:
                print("[UI] 'Export chat' nahi mila")
                self.d.press("back")
                self.d.press("back")
                return False
            export.click()
            time.sleep(1.5)

            # Step 4: Media choice dialog
            if include_media:
                include_btn = self.d(text="Include Media")
                if not include_btn.exists:
                    include_btn = self.d(textContains="Include")
                if include_btn.exists:
                    include_btn.click()
                    time.sleep(MEDIA_EXPORT_WAIT)
                else:
                    # Without media fallback
                    without = self.d(text="Without Media")
                    if without.exists:
                        without.click()
                        time.sleep(EXPORT_WAIT_TIME)
            else:
                without = self.d(text="Without Media")
                if without.exists:
                    without.click()
                    time.sleep(EXPORT_WAIT_TIME)

            # Step 5: Share screen handle
            return self._handle_share_screen()

        except Exception as e:
            print(f"[UI] Export error: {e}")
            for _ in range(4):
                self.d.press("back")
                time.sleep(0.3)
            return False

    def _handle_share_screen(self) -> bool:
        time.sleep(2)

        # Drive button click karo
        drive_btn = self.d(resourceId="android:id/text1", text="Drive")
        if drive_btn.exists:
            print("[UI] ✅ Drive button mila — clicking...")
            drive_btn.click()
            time.sleep(2)
            return self._handle_drive_upload_dialog()

        # Coordinates fallback — dump se Drive bounds: [300,1080][528,1360]
        print("[UI] Coordinates se Drive click kar raha hai...")
        self.d.click(414, 1220)
        time.sleep(2)
        return self._handle_drive_upload_dialog()

    def _handle_drive_upload_dialog(self) -> bool:
        time.sleep(2)

        print("[UI] Drive dialog texts:")
        for el in self.d(className="android.widget.TextView"):
            try:
                t = el.get_text()
                if t and t.strip():
                    print(f"       → '{t}'")
            except:
                pass

        # Upload button dhundho
        for btn_text in ["Upload", "UPLOAD", "Save", "SAVE", "OK"]:
            btn = self.d(text=btn_text)
            if btn.exists:
                print(f"[UI] ✅ '{btn_text}' clicked")
                btn.click()
                time.sleep(5)  # Upload hone do
                return True

        self.d.press("back")
        return False

    # ==================== Helpers ====================

    def press_back(self):
        self.d.press("back")
        time.sleep(0.4)

    def is_whatsapp_active(self) -> bool:
        try:
            return self.d.current_app().get("package") == WHATSAPP_PACKAGE
        except:
            return False

    def get_screen_info(self) -> dict:
        try:
            return self.d.current_app()
        except:
            return {}

    def _wait_for_element(self, timeout=10, **kwargs) -> bool:
        if 'resource_id' in kwargs:
            kwargs['resourceId'] = kwargs.pop('resource_id')
        return self.d(**kwargs).wait(timeout=timeout)