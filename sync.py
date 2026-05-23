import subprocess
import threading

class SyncManager:
    def __init__(self, local_dir):
        self.local_dir = local_dir
        self.status = "local" # local, syncing, synced, failed
        
    def trigger_sync(self, on_complete=None):
        if self.status == "syncing":
            print("[SyncManager] Sync already in progress, skipping trigger.")
            return
            
        print(f"[SyncManager] Triggering background sync. Source: {self.local_dir}")
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
                print(f"[SyncManager] Running command: {' '.join(cmd)}")
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                
                print(f"[SyncManager] Rclone process completed with returncode: {result.returncode}")
                if result.stdout:
                    print(f"[SyncManager] Rclone stdout:\n{result.stdout}")
                if result.stderr:
                    print(f"[SyncManager] Rclone stderr:\n{result.stderr}")
                    
                if result.returncode == 0:
                    self.status = "synced"
                    print("[SyncManager] Sync completed successfully.")
                else:
                    self.status = "failed"
                    print(f"[SyncManager] Sync failed with returncode {result.returncode}")
            except Exception as e:
                self.status = "failed"
                print(f"[SyncManager] Sync exception occurred: {e}")
                import traceback
                traceback.print_exc()
                
            if on_complete:
                try:
                    print("[SyncManager] Firing sync complete callback...")
                    on_complete()
                except Exception as cb_err:
                    print(f"[SyncManager] Error in completion callback: {cb_err}")
                
        threading.Thread(target=run, daemon=True).start()
        
    def get_status_indicator(self):
        if self.status == "syncing":
            return "Syncing..."
        elif self.status == "synced":
            return "Synced"
        elif self.status == "failed":
            return "Sync Failed"
        return "Local"
