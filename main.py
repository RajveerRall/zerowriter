import sys
import os
import time
import threading

# Set up paths to load the waveshare library
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from zerowriter import config
from zerowriter.keyboard import KeyboardHandler
from zerowriter.display import DisplayHandler
from zerowriter.file_manager import FileManager
from zerowriter.sync import SyncManager
from zerowriter.editor import EditorState

# State constants
STATE_MENU = 0
STATE_RECOVER = 1
STATE_NEW_FILE = 2
STATE_EDITOR = 3

class TypewriterApp:
    def __init__(self):
        self.state = STATE_MENU
        self.running = True
        self.dirty = True
        self.last_type_time = time.time()
        self.full_refresh_needed = False
        
        # Sub-managers
        self.keyboard = KeyboardHandler(
            device_name_part=config.KEYBOARD_DONGLE_NAME_PART,
            fallback_path=config.KEYBOARD_FALLBACK_DEVICE
        )
        self.display = DisplayHandler(picdir=picdir)
        self.file_manager = FileManager(
            writings_dir=config.WRITINGS_DIR,
            draft_path=config.DRAFT_PATH
        )
        self.sync_manager = SyncManager(local_dir=config.WRITINGS_DIR)
        self.editor = EditorState()
        
        # UI/State data
        self.menu_items = []
        self.selected_idx = 0
        self.filename_buffer = ""
        
        # Check keyboard
        if not self.keyboard.device:
            print("Error: No keyboard device found. Please make sure the USB dongle is connected.")
            sys.exit(1)
            
    def update_menu(self):
        self.menu_items = ["[ New Document ]"]
        self.menu_items.extend(self.file_manager.list_files())
        self.selected_idx = 0

    def autosave_loop(self):
        last_saved_text = ""
        while self.running:
            time.sleep(config.AUTOSAVE_INTERVAL_SEC)
            if self.state == STATE_EDITOR and self.running:
                current_text = self.editor.text
                if current_text != last_saved_text:
                    self.file_manager.save_crash_draft(current_text)
                    last_saved_text = current_text

    def render_loop(self):
        while self.running:
            should_render = False
            
            # Debounce rendering when in editor state
            if self.state == STATE_EDITOR:
                if self.dirty and (time.time() - self.last_type_time > config.DEBOUNCE_DELAY_SEC):
                    should_render = True
            else:
                if self.dirty:
                    should_render = True
                    
            if should_render:
                if self.state == STATE_RECOVER:
                    self.display.render_recovery()
                elif self.state == STATE_MENU:
                    self.display.render_menu(self.menu_items, self.selected_idx)
                elif self.state == STATE_NEW_FILE:
                    self.display.render_new_file(self.filename_buffer)
                elif self.state == STATE_EDITOR:
                    sync_indicator = self.sync_manager.get_status_indicator()
                    self.display.render_editor(self.editor.text, sync_indicator)
                    
                self.dirty = False
            time.sleep(0.02)

    def on_sync_complete(self):
        # Force redraw to show completed sync status
        self.dirty = True
        self.last_type_time = 0

    def start(self):
        # Scan files and check crash files
        self.update_menu()
        if self.file_manager.has_crash_draft():
            self.state = STATE_RECOVER
        else:
            self.state = STATE_MENU
            
        # Start helper threads
        threading.Thread(target=self.render_loop, daemon=True).start()
        threading.Thread(target=self.autosave_loop, daemon=True).start()
        
        print(f"\n--- ZEROWRITER MODULAR SYSTEM ---")
        print(f"Reading hardware keyboard: {self.keyboard.device.name}")
        
        self.keyboard.grab()
        
        try:
            for event_type, value in self.keyboard.read_events():
                if not self.running:
                    break
                    
                self.handle_event(event_type, value)
        except KeyboardInterrupt:
            pass
        finally:
            self.keyboard.ungrab()
            self.display.shutdown()
            print("Shutdown complete.")

    def handle_event(self, event_type, value):
        if self.state == STATE_RECOVER:
            if event_type == "key":
                if value == "y":
                    recovered_text = self.file_manager.read_crash_draft()
                    new_filename = f"recovered_{int(time.time())}.txt"
                    self.editor.set_document(new_filename, recovered_text)
                    self.file_manager.save_file(new_filename, recovered_text)
                    self.state = STATE_EDITOR
                    self.dirty = True
                elif value == "n":
                    self.file_manager.clear_crash_draft()
                    self.state = STATE_MENU
                    self.update_menu()
                    self.dirty = True
                    
        elif self.state == STATE_MENU:
            if event_type == "key":
                if value == "up":
                    self.selected_idx = max(0, self.selected_idx - 1)
                    self.dirty = True
                elif value == "down":
                    self.selected_idx = min(len(self.menu_items) - 1, self.selected_idx + 1)
                    self.dirty = True
                elif value == "\n":
                    if self.selected_idx == 0:
                        self.state = STATE_NEW_FILE
                        self.filename_buffer = ""
                    else:
                        filename = self.menu_items[self.selected_idx]
                        loaded_text = self.file_manager.load_file(filename)
                        self.editor.set_document(filename, loaded_text)
                        self.state = STATE_EDITOR
                    self.dirty = True
            elif event_type == "shortcut":
                if value == "q":
                    self.running = False
                    
        elif self.state == STATE_NEW_FILE:
            if event_type == "key":
                if value == "\n":
                    if not self.filename_buffer:
                        self.filename_buffer = self.file_manager.generate_filename()
                    if not self.filename_buffer.endswith(".txt"):
                        self.filename_buffer += ".txt"
                    self.file_manager.save_file(self.filename_buffer, "")
                    self.editor.set_document(self.filename_buffer, "")
                    self.state = STATE_EDITOR
                    self.dirty = True
                elif value == "backspace":
                    if len(self.filename_buffer) > 0:
                        self.filename_buffer = self.filename_buffer[:-1]
                        self.dirty = True
                elif len(value) == 1:
                    # Safe filename verification
                    if value.isalnum() or value in ('-', '_', '.'):
                        self.filename_buffer += value
                        self.dirty = True
                        
        elif self.state == STATE_EDITOR:
            if event_type == "shortcut":
                if value == "q": # Ctrl+Q to exit to menu
                    if self.editor.filename:
                        self.file_manager.save_file(self.editor.filename, self.editor.text)
                        self.sync_manager.trigger_sync(self.on_sync_complete)
                    self.editor.clear()
                    self.state = STATE_MENU
                    self.update_menu()
                    self.dirty = True
                elif value == "s": # Ctrl+S to save and sync
                    if self.editor.filename:
                        self.file_manager.save_file(self.editor.filename, self.editor.text)
                        self.sync_manager.trigger_sync(self.on_sync_complete)
                    self.dirty = True
                    self.last_type_time = 0 # Force immediate render to show synced status
                elif value == "r": # Ctrl+R to full refresh
                    self.display.update(self.display.render_editor(self.editor.text, self.sync_manager.get_status_indicator()), full_refresh=True)
            elif event_type == "key":
                if value == "backspace":
                    if self.editor.backspace():
                        self.dirty = True
                        self.last_type_time = time.time()
                elif value == "\n":
                    self.editor.append_char("\n")
                    self.dirty = True
                    self.last_type_time = time.time()
                else:
                    self.editor.append_char(value)
                    self.dirty = True
                    self.last_type_time = time.time()

if __name__ == "__main__":
    app = TypewriterApp()
    app.start()
