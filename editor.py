class EditorState:
    def __init__(self):
        self.text = ""
        self.filename = ""
        self.cursor_idx = 0
        
    def set_document(self, filename, text):
        self.filename = filename
        self.text = text
        self.cursor_idx = len(text)
        
    def append_char(self, char):
        # Insert char at cursor position
        self.text = self.text[:self.cursor_idx] + char + self.text[self.cursor_idx:]
        self.cursor_idx += len(char)
        
    def backspace(self):
        if self.cursor_idx > 0:
            self.text = self.text[:self.cursor_idx - 1] + self.text[self.cursor_idx:]
            self.cursor_idx -= 1
            return True
        return False
        
    def delete(self):
        # Delete character after the cursor
        if self.cursor_idx < len(self.text):
            self.text = self.text[:self.cursor_idx] + self.text[self.cursor_idx + 1:]
            return True
        return False

    def move_cursor_left(self):
        if self.cursor_idx > 0:
            self.cursor_idx -= 1
            return True
        return False

    def move_cursor_right(self):
        if self.cursor_idx < len(self.text):
            self.cursor_idx += 1
            return True
        return False

    def clear(self):
        self.text = ""
        self.filename = ""
        self.cursor_idx = 0
