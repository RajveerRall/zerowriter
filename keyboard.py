import os
import evdev
from evdev import InputDevice, categorize, ecodes

KEY_MAP = {
    'KEY_A': ('a', 'A'), 'KEY_B': ('b', 'B'), 'KEY_C': ('c', 'C'), 'KEY_D': ('d', 'D'),
    'KEY_E': ('e', 'E'), 'KEY_F': ('f', 'F'), 'KEY_G': ('g', 'G'), 'KEY_H': ('h', 'H'),
    'KEY_I': ('i', 'I'), 'KEY_J': ('j', 'J'), 'KEY_K': ('k', 'K'), 'KEY_L': ('l', 'L'),
    'KEY_M': ('m', 'M'), 'KEY_N': ('n', 'N'), 'KEY_O': ('o', 'O'), 'KEY_P': ('p', 'P'),
    'KEY_Q': ('q', 'Q'), 'KEY_R': ('r', 'R'), 'KEY_S': ('s', 'S'), 'KEY_T': ('t', 'T'),
    'KEY_U': ('u', 'U'), 'KEY_V': ('v', 'V'), 'KEY_W': ('w', 'W'), 'KEY_X': ('x', 'X'),
    'KEY_Y': ('y', 'Y'), 'KEY_Z': ('z', 'Z'),
    'KEY_1': ('1', '!'), 'KEY_2': ('2', '@'), 'KEY_3': ('3', '#'), 'KEY_4': ('4', '$'),
    'KEY_5': ('5', '%'), 'KEY_6': ('6', '^'), 'KEY_7': ('7', '&'), 'KEY_8': ('8', '*'),
    'KEY_9': ('9', '('), 'KEY_0': ('0', ')'),
    'KEY_SPACE': (' ', ' '),
    'KEY_MINUS': ('-', '_'), 'KEY_EQUAL': ('=', '+'),
    'KEY_LEFTBRACE': ('[', '{'), 'KEY_RIGHTBRACE': (']', '}'),
    'KEY_SEMICOLON': (';', ':'), 'KEY_APOSTROPHE': ("'", '"'),
    'KEY_GRAVE': ('`', '~'), 'KEY_BACKSLASH': ('\\', '|'),
    'KEY_COMMA': (',', '<'), 'KEY_DOT': ('.', '>'), 'KEY_SLASH': ('/', '?')
}

class KeyboardHandler:
    def __init__(self, device_name_part="yichip", fallback_path="/dev/input/event2"):
        self.device = self._find_keyboard(device_name_part, fallback_path)
        self.shift_pressed = False
        self.ctrl_pressed = False
        self.caps_lock = False
        
    def _find_keyboard(self, device_name_part, fallback_path):
        try:
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            
            # Helper to verify if device is a real typing keyboard by checking if it supports KEY_A (code 30)
            def is_real_keyboard(dev):
                try:
                    caps = dev.capabilities()
                    if evdev.ecodes.EV_KEY in caps:
                        return 30 in caps[evdev.ecodes.EV_KEY]
                except:
                    pass
                return False

            # First pass: Preferred device name part + is a real keyboard
            for device in devices:
                name = device.name.lower()
                if device_name_part in name and is_real_keyboard(device):
                    return device
            
            # Second pass: Any device with "keyboard" in its name + is a real keyboard
            for device in devices:
                name = device.name.lower()
                if "keyboard" in name and is_real_keyboard(device):
                    return device
                    
            # Third pass: Any device that is a real typing keyboard regardless of name
            for device in devices:
                if is_real_keyboard(device):
                    return device
                    
            if os.path.exists(fallback_path):
                return evdev.InputDevice(fallback_path)
        except Exception as e:
            print(f"[KeyboardHandler] Error listing/finding devices: {e}")
        return None

    def reconnect(self, device_name_part, fallback_path):
        print(f"[KeyboardHandler] Scanning for keyboards...")
        try:
            device = self._find_keyboard(device_name_part, fallback_path)
            if device:
                self.device = device
                # Reset states
                self.shift_pressed = False
                self.ctrl_pressed = False
                self.caps_lock = False
                print(f"[KeyboardHandler] Connected to keyboard: {device.path} ({device.name})")
                return True
        except Exception as e:
            print(f"[KeyboardHandler] Reconnection failed: {e}")
        return False

    def grab(self):
        if self.device:
            try:
                self.device.grab()
                print(f"[KeyboardHandler] Grabbed keyboard: {self.device.path}")
            except Exception as e:
                print(f"[KeyboardHandler] Could not grab keyboard: {e}")

    def ungrab(self):
        if self.device:
            try:
                self.device.ungrab()
                print(f"[KeyboardHandler] Ungrabbed keyboard: {self.device.path}")
            except Exception as e:
                print(f"[KeyboardHandler] Could not ungrab keyboard: {e}")

    def read_events(self):
        if not self.device:
            yield ("system", "disconnect")
            return
            
        try:
            for event in self.device.read_loop():
                if event.type == ecodes.EV_KEY:
                    key_event = categorize(event)
                    keycode = key_event.keycode
                    
                    if isinstance(keycode, list):
                        if len(keycode) > 0:
                            keycode = keycode[0]
                        else:
                            continue
                    
                    # Key press (1) or hold (2)
                    if key_event.keystate in (1, 2):
                        # Skip repeating modifier keystates
                        if key_event.keystate == 2 and keycode in ('KEY_LEFTSHIFT', 'KEY_RIGHTSHIFT', 'KEY_LEFTCTRL', 'KEY_RIGHTCTRL'):
                            continue
                            
                        if keycode in ('KEY_LEFTSHIFT', 'KEY_RIGHTSHIFT'):
                            self.shift_pressed = True
                        elif keycode in ('KEY_LEFTCTRL', 'KEY_RIGHTCTRL'):
                            self.ctrl_pressed = True
                        elif keycode == 'KEY_CAPSLOCK' and key_event.keystate == 1:
                            self.caps_lock = not self.caps_lock
                        elif keycode == 'KEY_ENTER':
                            yield ("key", "\n")
                        elif keycode == 'KEY_BACKSPACE':
                            yield ("key", "backspace")
                        elif keycode == 'KEY_UP':
                            yield ("key", "up")
                        elif keycode == 'KEY_DOWN':
                            yield ("key", "down")
                        elif keycode == 'KEY_Y' and not self.ctrl_pressed:
                            yield ("key", "y")
                        elif keycode == 'KEY_N' and not self.ctrl_pressed:
                            yield ("key", "n")
                        elif keycode in KEY_MAP:
                            char_normal, char_shift = KEY_MAP[keycode]
                            use_upper = self.shift_pressed
                            if keycode.startswith('KEY_') and keycode[4:].isalpha():
                                if self.caps_lock:
                                    use_upper = not use_upper
                            char = char_shift if use_upper else char_normal
                            
                            if self.ctrl_pressed:
                                yield ("shortcut", char.lower())
                            else:
                                yield ("key", char)
                                
                    # Key release (0)
                    elif key_event.keystate == 0:
                        if keycode in ('KEY_LEFTSHIFT', 'KEY_RIGHTSHIFT'):
                            self.shift_pressed = False
                        elif keycode in ('KEY_LEFTCTRL', 'KEY_RIGHTCTRL'):
                            self.ctrl_pressed = False
        except OSError as e:
            print(f"[KeyboardHandler] Connection lost: {e}")
            self.device = None
            yield ("system", "disconnect")
