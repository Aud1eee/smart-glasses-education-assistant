import pandas as pd
import time, os

class EduEngine:
    def __init__(self, vocab_path):
        self.vocab_path = vocab_path
        self.last_recall_time = time.time()
        self.recall_interval = 30 

    def check_active_recall(self):
        if not os.path.exists(self.vocab_path): return None
        
        current_time = time.time()
        time_passed = current_time - self.last_recall_time
        
        # 调试信息：每 5 秒打印一次进度
        if int(time_passed) % 5 == 0 and int(time_passed) != 0:
            remaining = int(self.recall_interval - time_passed)
            if remaining > 0:
                print(f"⏳ [EDU] 距离下次生词抽查还剩: {remaining}s")

        if time_passed > self.recall_interval: 
            self.last_recall_time = current_time
            return self._get_random_quiz()
        return None

    def _get_random_quiz(self):
        try:
            df = pd.read_csv(self.vocab_path)
            # 过滤掉标题行或空数据
            df = df.dropna(subset=['Word'])
            if len(df) < 2: return None
            
            # 权重抽取
            word_row = df.sample(n=1, weights=df['Count']).iloc[0]
            return {
                "type": "recall_quiz",
                "word": f"🧠 盲盒测试: {word_row['Word']}",
                "trans": f"记得吗？翻译是: {word_row['Translation']}"
            }
        except Exception as e:
            print(f"❌ [EDU] 抽查逻辑出错: {e}")
            return None