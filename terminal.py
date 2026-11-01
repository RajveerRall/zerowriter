import os
import sys
import time
import select
import struct
import threading

# Platform check for PTY (Unix / Linux on Raspberry Pi)
try:
    import pty
    import termios
    import fcntl
    HAS_PTY = True
except ImportError:
    HAS_PTY = False

# Try pyte (in-memory VT100 / ANSI terminal screen emulator)
try:
    import pyte
    HAS_PYTE = True
except ImportError:
    HAS_PYTE = False


class FallbackScreen:
    """Simple line-buffered fallback screen when pyte is not installed."""
    def __init__(self, cols, rows):
        self.columns = cols
        self.lines = rows
        self.buffer = [""] * rows
        self.cursor_x = 0
        self.cursor_y = 0

    @property
    def display(self):
        return self.buffer

    class Cursor:
        def __init__(self, x=0, y=0):
            self.x = x
            self.y = y

    @property
    def cursor(self):
        return self.Cursor(self.cursor_x, self.cursor_y)

    def feed(self, data):
        text = data.decode("utf-8", errors="ignore")
        for char in text:
            if char == "\r":
                self.cursor_x = 0
            elif char == "\n":
                self.cursor_y = min(self.lines - 1, self.cursor_y + 1)
                if self.cursor_y == self.lines - 1:
                    self.buffer.pop(0)
                    self.buffer.append("")
                self.cursor_x = 0
            elif char == "\b":
                self.cursor_x = max(0, self.cursor_x - 1)
            elif ord(char) >= 32:
                line = list(self.buffer[self.cursor_y].ljust(self.columns))
                if self.cursor_x < self.columns:
                    line[self.cursor_x] = char
                    self.buffer[self.cursor_y] = "".join(line)[:self.columns]
                    self.cursor_x += 1


class TerminalSession:
    """Manages an active PTY bash shell session rendered to the E-Ink display."""
    def __init__(self, display, keyboard):
        self.display = display
        self.keyboard = keyboard
        self.running = False
        self.master_fd = None
        self.child_pid = None
        self.cols = getattr(self.display, "term_cols", 48)
        self.rows = getattr(self.display, "term_rows", 16)

        if HAS_PYTE:
            self.screen = pyte.Screen(self.cols, self.rows)
            self.stream = pyte.ByteStream(self.screen)
        else:
            self.screen = FallbackScreen(self.cols, self.rows)
            self.stream = None

        self.dirty = True
        self.last_output_time = time.time()
        self.full_refresh_needed = True

    def start_shell(self):
        if not HAS_PTY:
            print("[Terminal] Error: PTY is only available on Linux (Raspberry Pi).")
            return False

        try:
            self.child_pid, self.master_fd = pty.fork()
        except Exception as e:
            print(f"[Terminal] Failed to fork PTY: {e}")
            return False

        if self.child_pid == 0:
            # Child process: configure terminal dimensions and spawn bash
            winsize = struct.pack("HHHH", self.rows, self.cols, 400, 275)
            try:
                fcntl.ioctl(sys.stdin.fileno(), termios.TIOCSWINSZ, winsize)
            except Exception:
                pass

            env = os.environ.copy()
            env["TERM"] = "linux"
            env["COLUMNS"] = str(self.cols)
            env["LINES"] = str(self.rows)

            try:
                os.execvpe("bash", ["bash", "--login"], env)
            except Exception:
                os.execlp("sh", "sh")
            sys.exit(0)

        # Parent process: set non-blocking on master_fd
        try:
            flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            winsize = struct.pack("HHHH", self.rows, self.cols, 400, 275)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        except Exception as e:
            print(f"[Terminal] Error setting terminal attributes: {e}")

        self.running = True
        self.dirty = True
        self.full_refresh_needed = True

        threading.Thread(target=self._read_pty_loop, daemon=True).start()
        print(f"[Terminal] Started shell session (PID: {self.child_pid}, {self.cols}x{self.rows})")
        return True

    def _read_pty_loop(self):
        while self.running and self.master_fd is not None:
            try:
                r, _, _ = select.select([self.master_fd], [], [], 0.05)
                if self.master_fd in r:
                    data = os.read(self.master_fd, 1024)
                    if not data:
                        # EOF: child process exited
                        self.close()
                        break
                    if self.stream:
                        self.stream.feed(data)
                    else:
                        self.screen.feed(data)
                    self.dirty = True
                    self.last_output_time = time.time()
            except OSError:
                self.close()
                break

    def handle_key(self, event_type, value):
        if not self.running or self.master_fd is None:
            return

        data_to_send = None

        if event_type == "key":
            if value == "\n":
                data_to_send = b"\r"
            elif value == "\t":
                data_to_send = b"\t"
            elif value == "esc":
                data_to_send = b"\x1b"
            elif value == "backspace":
                data_to_send = b"\x7f"
            elif value == "delete":
                data_to_send = b"\x1b[3~"
            elif value == "up":
                data_to_send = b"\x1b[A"
            elif value == "down":
                data_to_send = b"\x1b[B"
            elif value == "right":
                data_to_send = b"\x1b[C"
            elif value == "left":
                data_to_send = b"\x1b[D"
            elif value == "home":
                data_to_send = b"\x1b[H"
            elif value == "end":
                data_to_send = b"\x1b[F"
            elif len(value) == 1:
                data_to_send = value.encode("utf-8")

        elif event_type == "shortcut":
            val = value.lower()
            if val == "r":
                # Ctrl+R triggers e-ink full refresh to clear ghosting, and sends Ctrl+L to redraw bash
                self.full_refresh_needed = True
                self.dirty = True
                data_to_send = b"\x0c"
            elif val == "q":
                # Quick exit to menu
                data_to_send = b"exit\r"
            elif "a" <= val <= "z":
                # Standard ASCII control chars (Ctrl+C = 3, Ctrl+D = 4, etc.)
                data_to_send = bytes([ord(val) - ord("a") + 1])

        if data_to_send and self.master_fd is not None:
            try:
                os.write(self.master_fd, data_to_send)
            except OSError:
                self.close()

    def render(self, full_refresh=False):
        if not self.running:
            return
        self.dirty = False
        cur_pos = (self.screen.cursor.x, self.screen.cursor.y)
        lines = list(self.screen.display)
        self.display.render_terminal(
            screen_lines=lines,
            cursor_pos=cur_pos,
            status_text="[Linux Terminal] Type 'exit' to return | Ctrl+R: Refresh",
            full_refresh=full_refresh or self.full_refresh_needed,
        )
        self.full_refresh_needed = False

    def close(self):
        if not self.running:
            return
        self.running = False
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except Exception:
                pass
            self.master_fd = None
        if self.child_pid is not None:
            try:
                os.waitpid(self.child_pid, os.WNOHANG)
            except Exception:
                pass
            self.child_pid = None
        print("[Terminal] Shell session closed.")


class StandaloneTerminalApp:
    """Allows running the terminal directly without the Zerowriter GUI."""
    def __init__(self):
        picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
        libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
        if os.path.exists(libdir):
            sys.path.append(libdir)

        try:
            from zerowriter import config
            from zerowriter.keyboard import KeyboardHandler
            from zerowriter.display import DisplayHandler
        except ImportError:
            import config
            from keyboard import KeyboardHandler
            from display import DisplayHandler

        self.keyboard = KeyboardHandler(
            device_name_part=config.KEYBOARD_DONGLE_NAME_PART,
            fallback_path=config.KEYBOARD_FALLBACK_DEVICE
        )
        self.display = DisplayHandler(picdir=picdir)
        self.session = TerminalSession(self.display, self.keyboard)

    def start(self):
        if not self.keyboard.device:
            print("Error: No keyboard device found. Please connect your USB keyboard.")
            sys.exit(1)

        self.keyboard.grab()
        print("[StandaloneTerminalApp] Launching E-Ink terminal...")
        if not self.session.start_shell():
            print("Failed to initialize shell.")
            return

        def render_loop():
            last_render = 0
            while self.session.running:
                now = time.time()
                if self.session.dirty and (now - last_render >= 0.1):
                    last_render = now
                    self.session.render()
                time.sleep(0.02)

        threading.Thread(target=render_loop, daemon=True).start()

        try:
            for event_type, value in self.keyboard.read_events():
                if not self.session.running:
                    break
                self.session.handle_key(event_type, value)
        except KeyboardInterrupt:
            pass
        finally:
            self.session.close()
            self.keyboard.ungrab()
            self.display.shutdown()
            print("[StandaloneTerminalApp] Exited cleanly.")


if __name__ == "__main__":
    app = StandaloneTerminalApp()
    app.start()
