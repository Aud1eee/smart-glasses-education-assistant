import pandas as pd, os

def show_progress():
    file = "../data/my_vocabulary.csv"
    if not os.path.exists(file):
        print(">>> 生词库空空如也，快去抓取单词吧！")
        return

    try:
        df = pd.read_csv(file)
        if df.empty: return
        
        print("\n" + "★"*35)
        print(f"📖 我的 Rokid 引擎库 (累计: {len(df)} 词)")
        print("★" * 35)
        print("\n最近抓取:")
        print(df.sort_values('Last_Seen', ascending=False).head(5)[['Word', 'Translation']].to_string(index=False))
        
        hard_words = df[df['Count'] > 1]
        if not hard_words.empty:
            print("\n🔥 艾宾浩斯重难点 (高频查阅):")
            for _, row in hard_words.head(3).iterrows():
                print(f" ⚠️ {row['Word']} (查询了 {row['Count']} 次)")
    except:
        print("读取生词本失败。")

if __name__ == "__main__":
    show_progress()