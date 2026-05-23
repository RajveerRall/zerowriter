import os
import time

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

class FileManager:
    def __init__(self, writings_dir, draft_path):
        self.writings_dir = writings_dir
        self.draft_path = draft_path
        os.makedirs(self.writings_dir, exist_ok=True)
        
    def has_docx_support(self):
        return HAS_DOCX

    def list_files(self):
        try:
            # List both docx and txt files
            files = [
                f for f in os.listdir(self.writings_dir) 
                if (f.endswith(".docx") or f.endswith(".txt")) and not f.startswith(".")
            ]
            files.sort(key=lambda x: os.path.getmtime(os.path.join(self.writings_dir, x)), reverse=True)
            return files
        except Exception as e:
            print(f"Error scanning directory: {e}")
            return []

    def has_crash_draft(self):
        return os.path.exists(self.draft_path) and os.path.getsize(self.draft_path) > 0

    def read_crash_draft(self):
        try:
            with open(self.draft_path, 'r') as f:
                return f.read()
        except:
            return ""

    def clear_crash_draft(self):
        if os.path.exists(self.draft_path):
            try:
                os.remove(self.draft_path)
            except:
                pass

    def save_crash_draft(self, text):
        try:
            with open(self.draft_path, 'w') as f:
                f.write(text)
        except:
            pass

    def load_file(self, filename):
        path = os.path.join(self.writings_dir, filename)
        try:
            if HAS_DOCX and filename.endswith(".docx"):
                doc = Document(path)
                return "\n".join([p.text for p in doc.paragraphs])
            else:
                with open(path, 'r') as f:
                    return f.read()
        except Exception as e:
            print(f"Error reading file {filename}: {e}")
            return ""

    def save_file(self, filename, text):
        path = os.path.join(self.writings_dir, filename)
        try:
            if HAS_DOCX and filename.endswith(".docx"):
                doc = Document()
                for line in text.split('\n'):
                    doc.add_paragraph(line)
                doc.save(path)
            else:
                with open(path, 'w') as f:
                    f.write(text)
            self.clear_crash_draft()
            return True
        except Exception as e:
            print(f"Error saving file {filename}: {e}")
            return False

    def generate_filename(self):
        ext = ".docx" if HAS_DOCX else ".txt"
        return f"draft_{time.strftime('%Y%m%d_%H%M%S')}{ext}"
