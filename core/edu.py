import os
import time

import pandas as pd


class EduEngine:
    def __init__(self, vocab_path):
        self.vocab_path = vocab_path
        self.last_recall_time = time.time()
        self.recall_interval = 30

    def check_active_recall(self):
        if not os.path.exists(self.vocab_path):
            return None

        current_time = time.time()
        time_passed = current_time - self.last_recall_time

        # Print a lightweight debug update every 5 seconds.
        if int(time_passed) % 5 == 0 and int(time_passed) != 0:
            remaining = int(self.recall_interval - time_passed)
            if remaining > 0:
                print(f"[EDU] Time until the next vocabulary recall check: {remaining}s")

        if time_passed > self.recall_interval:
            self.last_recall_time = current_time
            return self._get_random_quiz()
        return None

    def _get_random_quiz(self):
        try:
            df = pd.read_csv(self.vocab_path)
            # Skip empty rows and malformed entries.
            df = df.dropna(subset=["Word"])
            if len(df) < 2:
                return None

            # Weighted sampling keeps frequently revisited words more likely to appear.
            word_row = df.sample(n=1, weights=df["Count"]).iloc[0]
            return {
                "type": "recall_quiz",
                "word": f"Recall check: {word_row['Word']}",
                "trans": f"Do you remember it? Translation: {word_row['Translation']}",
            }
        except Exception as exc:
            print(f"[EDU] Recall-check logic failed: {exc}")
            return None
