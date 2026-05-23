import subprocess
import threading

class SyncManager:
    def __init__(self, local_dir):
        self.local_dir = local_dir
        self.status = "local" # local, syncing, synced, failed
        
    def trigger_sync(self):
        if self.status == "syncing":
            return
            
        def run():
            self.status = "syncing"
            try:
                # Explicitly point to the user's rclone config since python runs as root (sudo)
                config_path = "/home/user/.config/rclone/rclone.conf"
                cmd = [
                    "rclone", 
                    "--config", config_path, 
                    "sync", 
                    self.local_dir, 
                    "gdrive:Zerowriter", 
                    "--exclude", ".*"
                ]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode == 0:
                    self.status = "synced"
                else:
                    self.status = "failed"
            except Exception as e:
                self.status = "failed"
                
        threading.Thread(target=run, daemon=True).start()
        
    def get_status_indicator(self):
        if self.status == "syncing":
            return "Syncing..."
        elif self.status == "synced":
            return "Synced"
        elif self.status == "failed":
            return "Sync Failed"
        return "Local"
