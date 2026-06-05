import os, sys, time
from rich.console import Console

from config import *
from adb_controller import ADBController
from ui_automator import WhatsAppUIAutomator
from chat_discovery import ChatDiscovery
from export_manager import ExportManager
from progress_tracker import ProgressTracker
from report_generator import ReportGenerator

console = Console()

# ============ TESTING MODE ============
TEST_MODE = True    # Full run ke liye False kar dena
TEST_LIMIT = 10
# ======================================

def main():
    console.print("\n[bold green]🚀 WhatsApp Bulk Exporter v1.0[/bold green]")

    # Step 1: ADB
    console.print("\n[yellow]Step 1:[/yellow] ADB Connection...")
    try:
        adb = ADBController()
        console.print("[green]✅ ADB Connected[/green]")
    except Exception as e:
        console.print(f"[red]❌ Failed: {e}[/red]")
        sys.exit(1)

    # Step 2: UI Automator
    console.print("[yellow]Step 2:[/yellow] UI Automator...")
    try:
        ui = WhatsAppUIAutomator()
        console.print("[green]✅ Ready[/green]")
    except Exception as e:
        console.print(f"[red]❌ Failed: {e}[/red]")
        sys.exit(1)

    # Step 3: Launch WhatsApp
    console.print("[yellow]Step 3:[/yellow] WhatsApp Launch...")
    ui.launch_whatsapp()
    console.print("[green]✅ WhatsApp Launched[/green]")

    # Step 4: Chat Discovery
    console.print("[yellow]Step 4:[/yellow] Chat Discovery...")
    tracker = ProgressTracker()
    discovery = ChatDiscovery(ui, tracker)
    
    # Testing limit discovery mein bhi pass karein
    discover_limit = TEST_LIMIT if TEST_MODE else None
    chats = discovery.discover_all_chats(use_cache=False, limit=discover_limit)
    console.print(f"[green]✅ {len(chats)} chats found[/green]")

    if len(chats) == 0:
        console.print("[red]❌ Koi chat nahi mila! Check karein.[/red]")
        sys.exit(1)

    # Testing limit apply karein
    if TEST_MODE:
        chats = chats[:TEST_LIMIT]
        console.print(f"[yellow]🧪 TEST MODE: {TEST_LIMIT} chats export honge[/yellow]")
        console.print("[dim]Chats jo export honge:[/dim]")
        for i, c in enumerate(chats, 1):
            console.print(f"  {i}. {c['name']} ({c['type']})")

    # Step 5: Export
    console.print(f"\n[yellow]Step 5:[/yellow] Exporting {len(chats)} chats...")
    try:
        export_manager = ExportManager()
        export_manager.export_all_chats(chats)
    except KeyboardInterrupt:
        console.print("\n[yellow]⏸️  Paused — dobara run karo resume hoga[/yellow]")

    # Step 6: Report
    console.print("\n[yellow]Step 6:[/yellow] Report...")
    ReportGenerator().generate()
    console.print("\n[bold green]🎉 Done![/bold green]")

if __name__ == "__main__":
    main()