import json, time, os
from config import *
from ui_automator import WhatsAppUIAutomator
from progress_tracker import ProgressTracker

class ChatDiscovery:

    def __init__(self, ui: WhatsAppUIAutomator, tracker: ProgressTracker):
        self.ui = ui
        self.tracker = tracker

    def discover_all_chats(self, use_cache: bool = True, limit: int = None) -> list:
        # Valid cache check
        if use_cache and os.path.exists(CHAT_LIST_CACHE):
            with open(CHAT_LIST_CACHE, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            if isinstance(cached, dict) and len(cached) > 0:
                chats = [{'name': k, 'type': v} for k, v in cached.items()]
                if limit:
                    chats = chats[:limit]
                print(f"[Discovery] 📂 Cache se {len(chats)} chats loaded")
                return chats

        print("[Discovery] 🔍 Starting fresh chat discovery...")
        self.tracker.log_event("discovery_started")

        all_chats = {}
        no_new_count = 0
        scroll_count = 0

        self.ui.go_to_chat_list()
        time.sleep(1.5)

        while scroll_count < MAX_SCROLL_ATTEMPTS:
            visible = self.ui.get_visible_chats()
            prev_names = set(all_chats.keys())

            new_found = 0
            for chat in visible:
                name = chat["name"]
                if name not in all_chats:
                    all_chats[name] = chat["type"]
                    self.tracker.add_chat(name, chat["type"])
                    new_found += 1

            curr_names = set(all_chats.keys())
            total = len(all_chats)

            if new_found > 0:
                no_new_count = 0
                print(f"[Discovery] Scroll {scroll_count:4d} | +{new_found:3d} new | Total: {total}")
            else:
                no_new_count += 1
                print(f"[Discovery] Scroll {scroll_count:4d} | No new ({no_new_count}/5) | Total: {total}")

            # Testing limit hit ho gayi — ruk jaao
            if limit and total >= limit:
                print(f"[Discovery] 🧪 Test limit {limit} reached — stopping!")
                break

            # End condition: 5 consecutive scrolls mein koi naya chat nahi
            if no_new_count >= 5:
                print("[Discovery] 🏁 List ka end aa gaya!")
                break

            self.ui.scroll_chat_list_down()
            scroll_count += 1

            # Har 50 scrolls par cache save
            if scroll_count % 50 == 0:
                self._save_cache(all_chats)

        chat_list = [{"name": k, "type": v} for k, v in all_chats.items()]
        if limit:
            chat_list = chat_list[:limit]

        self._save_cache(all_chats)
        self.tracker.log_event("discovery_complete", f"{len(chat_list)} chats found")
        print(f"\n[Discovery] ✅ Total: {len(chat_list)} chats discovered")
        return chat_list

    def _save_cache(self, chats: dict):
        os.makedirs(os.path.dirname(CHAT_LIST_CACHE), exist_ok=True)
        with open(CHAT_LIST_CACHE, 'w', encoding='utf-8') as f:
            json.dump(chats, f, ensure_ascii=False, indent=2)