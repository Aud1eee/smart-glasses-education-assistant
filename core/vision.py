import hashlib
import os
import random
import re
from datetime import datetime

import cv2
import pytesseract
import requests
from dotenv import load_dotenv
from PIL import Image

try:
    from pix2tex.cli import LatexOCR
except Exception:
    LatexOCR = None


class VisionEngine:
    def __init__(self):
        load_dotenv()
        self.app_id = str(os.getenv("BAIDU_APP_ID", "")).strip()
        self.secret_key = str(os.getenv("BAIDU_SECRET_KEY", "")).strip()
        self.notes_path = "data/study_notes.md"

        if LatexOCR:
            print("Loading LaTeX OCR model...")
            try:
                self.tex_model = LatexOCR()
                print("LaTeX OCR model ready")
            except Exception as e:
                print(f"LaTeX OCR unavailable, falling back to basic OCR: {e}")
                self.tex_model = None
        else:
            print("pix2tex is not installed, falling back to basic OCR.")
            self.tex_model = None

        os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.notes_path):
            with open(self.notes_path, "w", encoding="utf-8") as f:
                f.write("# Rokid Engineering & Research Notes\n")

    def process_engineering_buffer(self, image_path):
        if not os.path.exists(image_path):
            return None

        raw_text = self._basic_ocr(image_path)
        c_type = self._classify(raw_text)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        final_content = raw_text

        if c_type == "EQUATION" and self.tex_model:
            try:
                img = Image.open(image_path)
                final_content = self.tex_model(img)
                entry = f"\n### Math Formula ({ts})\n$$\n{final_content}\n$$\n"
            except Exception as e:
                print(f"LaTeX OCR error: {e}")
                entry = f"\n### Note ({ts})\n> {raw_text}\n"
        elif c_type == "CODE":
            entry = f"\n### Code ({ts})\n```cpp\n{raw_text}\n```\n"
        else:
            entry = f"\n### Note ({ts})\n> {raw_text}\n"

        with open(self.notes_path, "a", encoding="utf-8") as f:
            f.write(entry + "\n")

        return {"type": c_type, "content": final_content}

    def _basic_ocr(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            return ""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return pytesseract.image_to_string(gray, config="--psm 6").strip()

    def _classify(self, text):
        if re.search(r"(\\frac|\\sum|\\int|=|\^|_[a-zA-Z0-9]|\d+\s*[\+\-\*/]\s*\d+)", text):
            return "EQUATION"
        if re.search(r"(int |void |if\(|std::|def |import |using )", text):
            return "CODE"
        return "TEXT"

    def ocr_and_translate(self, image_path):
        text = self._basic_ocr(image_path)
        if not text:
            return None
        match = re.search(r"[a-zA-Z]{3,}", text)
        if not match:
            return None
        word = match.group().capitalize()
        return self._call_baidu(word)

    def _call_baidu(self, word):
        if not self.app_id:
            return {"word": word, "trans": "Key Missing"}

        url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
        salt = str(random.randint(1, 65536))
        sign = hashlib.md5((self.app_id + word + salt + self.secret_key).encode("utf-8")).hexdigest()
        params = {
            "q": word,
            "from": "en",
            "to": "zh",
            "appid": self.app_id,
            "salt": salt,
            "sign": sign,
        }

        try:
            r = requests.get(url, params=params, timeout=3)
            return {"word": word, "trans": r.json()["trans_result"][0]["dst"]}
        except Exception:
            return {"word": word, "trans": "Error"}
