# Zerowriter Modular E-Ink Typewriter

A clean, modular writing application for Raspberry Pi Zero and the Waveshare 4.2" (V2) E-Ink display. It captures direct hardware keyboard events, features automatic scroll rendering, includes a document manager, autosaves drafts, and syncs automatically to Google Drive in the background.

---

## Folder Structure

```
├── main.py                     # Entry point orchestrating the app loop
├── README.md                   # Installation & configuration guide
└── zerowriter/
    ├── __init__.py
    ├── config.py               # Constants, paths, font sizes, and thresholds
    ├── display.py              # E-ink drivers and layout render functions
    ├── editor.py               # Business logic tracking active document text
    ├── file_manager.py         # File load/save/autosave recovery mechanics
    ├── keyboard.py             # Event hook mapping hardware keys to actions
    └── sync.py                 # Asynchronous background thread executing Rclone syncs
```

---

## Installation on the Raspberry Pi

### 1. Position the Files
Copy the files from this directory to the examples folder of your Waveshare library on the Pi:
* **Package directory:** `~/waveshare-python/e-Paper/RaspberryPi_JetsonNano/python/examples/zerowriter/`
* **Entry point:** `~/waveshare-python/e-Paper/RaspberryPi_JetsonNano/python/examples/main.py`

### 2. Install Dependencies
Run these commands to install the event-handling library:
```bash
sudo apt update
sudo apt install -y python3-evdev rclone
```

---

## Configuring Google Drive Cloud Sync

We use **Rclone** to sync your documents silently in the background.

1. Start the interactive setup wizard:
   ```bash
   rclone config
   ```
2. Type **`n`** for a new remote and name it exactly **`gdrive`**.
3. Choose **`drive`** (Google Drive) from the list of storage types.
4. When asked for `client_id` and `client_secret`, leave them blank (press Enter).
5. When asked to edit advanced config, select **`n`** (No).
6. When asked `Use auto config?`, select **`n`** (No, because the Pi is headless).
7. Rclone will generate a link. **Copy and paste the link into your laptop's browser**, authorize your Google account, and copy the authentication code printed on your screen back into the terminal.
8. Confirm the setup and exit.

Test the sync by running:
```bash
rclone mkdir gdrive:Zerowriter
rclone sync ~/writings gdrive:Zerowriter
```

---

## Running the Application

Run the application as administrator (required for hardware keyboard monitoring):
```bash
sudo python3 main.py
```

### Key Controls
* **Menu Browsing:** Use the `Up/Down Arrow` keys, press `Enter` to open/create a file.
* **Typing Mode:** Regular typing updates the screen automatically when you pause typing for more than `0.15` seconds.
* **Ctrl + S:** Manually save the document and trigger an asynchronous background sync to Google Drive.
* **Ctrl + Q:** Save your progress, clean up temporary drafts, trigger a final background sync, and return to the main File Manager Menu.
* **Ctrl + R:** Force a full screen refresh to clear any e-ink ghosting artifacts.

---

## Standalone Auto-Start (Boot to Typewriter)

To configure your Pi to boot directly into the typewriter:

1. Create a systemd service file:
   ```bash
   sudo nano /etc/systemd/system/zerowriter.service
   ```

2. Paste the following configuration:
   ```ini
   [Unit]
   Description=Zerowriter E-Ink Typewriter Service
   After=multi-user.target

   [Service]
   Type=idle
   WorkingDirectory=/home/user/waveshare-python/e-Paper/RaspberryPi_JetsonNano/python/examples
   ExecStart=/usr/bin/python3 main.py
   StandardInput=tty
   StandardOutput=tty
   TTYPath=/dev/tty1
   TTYReset=yes
   TTYVHangup=yes
   User=root

   [Install]
   WantedBy=multi-user.target
   ```
   *(Ensure the `WorkingDirectory` matches where your files are located).*

3. Disable the system login prompt on the display so it doesn't conflict:
   ```bash
   sudo systemctl disable getty@tty1.service
   ```

4. Enable and start your service:
   ```bash
   sudo systemctl daemon-reload
   ```

5. Restart the Pi:
   ```bash
   sudo reboot
   ```

The typewriter will take over the display and keyboard automatically when the Pi boots up!
