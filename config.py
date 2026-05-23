import os

# Font configurations
FONT_SIZE = 18
STATUS_FONT_SIZE = 12
TITLE_FONT_SIZE = 24

# Directory and paths
WRITINGS_DIR = os.path.expanduser("~/writings")
DRAFT_PATH = os.path.join(WRITINGS_DIR, ".draft_tmp.txt")

# Keyboard input settings
KEYBOARD_DONGLE_NAME_PART = "yichip"
KEYBOARD_FALLBACK_DEVICE = "/dev/input/event2"

# Speed/refresh timings
AUTOSAVE_INTERVAL_SEC = 10
DEBOUNCE_DELAY_SEC = 0.15

# UI Layout settings
WRAP_WIDTH = 42  # Increased from 35 to use more of the screen width
CURSOR_CHAR = "|"  # Static cursor appended to show typing position

