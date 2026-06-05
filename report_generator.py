import json
from datetime import datetime
from config import EXPORT_BASE_DIR, DATA_DIR
from progress_tracker import ProgressTracker
import os

class ReportGenerator:
    """Final export summary report generate karta hai"""
    
    def __init__(self):
        self.tracker = ProgressTracker()
    
    def generate(self):
        """Complete report generate karein"""
        stats = self.tracker.get_stats()
        all_chats = self.tracker.get_all_chats()
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": stats,
            "exported_chats": [],
            "failed_chats": [],
        }
        
        for chat in all_chats:
            name, chat_type, status, export_path = chat
            entry = {"name": name, "type": chat_type, "path": export_path}
            
            if status == "exported":
                report["exported_chats"].append(entry)
            elif status == "failed":
                report["failed_chats"].append(entry)
        
        # JSON report save karein
        report_path = os.path.join(DATA_DIR, "export_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # Text summary print karein
        print("\n" + "="*60)
        print("📊 EXPORT SUMMARY REPORT")
        print("="*60)
        print(f"✅ Successfully Exported: {stats.get('exported', 0)}")
        print(f"❌ Failed:               {stats.get('failed', 0)}")
        print(f"⏭️  Skipped:             {stats.get('pending', 0)}")
        print(f"📁 Export Location:      {EXPORT_BASE_DIR}")
        print(f"📄 Report saved at:      {report_path}")
        print("="*60)
        
        return report