class EditorState:
    def __init__(self):
        self.text = ""
        self.filename = ""
        
    def set_document(self, filename, text):
        self.filename = filename
        self.text = text
        
    def append_char(self, char):
        self.text += char
        
    def backspace(self):
        if len(self.text) > 0:
            self.text = self.text[:-1]
            return True
        return False

    def clear(self):
        self.text = ""
        self.filename = ""
