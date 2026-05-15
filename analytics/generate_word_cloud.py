import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import bootstrap_windows_runtime  # noqa: F401

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_ERROR = None
except Exception as exc:
    plt = None
    MATPLOTLIB_ERROR = exc

def plot_vocab_analysis():
    if plt is None:
        print(f">>> Matplotlib unavailable in the current Windows runtime bridge: {MATPLOTLIB_ERROR}")
        print(">>> Vocabulary chart export is skipped in this runtime.")
        return

    # 路径适配：根据 run.py 调用逻辑，使用相对路径
    input_file = "../data/my_vocabulary.csv"
    output_dir = "../exports"
    
    if not os.path.exists(input_file): 
        print(">>> ❌ 未发现生词库数据，请先抓取单词！")
        return
    
    try:
        df = pd.read_csv(input_file)
        if df.empty:
            print(">>> ❌ 生词库目前是空的。")
            return

        # 只取查询次数最多的前 15 个词进行可视化，避免图表拥挤
        df = df.sort_values('Count', ascending=False).head(15)

        # 设置绘图风格
        plt.style.use('dark_background') # 匹配 AR HUD 的暗色系
        plt.figure(figsize=(12, 6))
        
        # 生成渐变色条形图
        colors = plt.cm.viridis(df['Count'] / df['Count'].max())
        bars = plt.bar(df['Word'], df['Count'], color=colors, edgecolor='#00ff9d', linewidth=1)
        
        # 添加数值标签
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2, yval + 0.5, yval, ha='center', color='#00ff9d')

        plt.title('Vocab Mastery & Difficulty Analysis', fontsize=15, color='#00ff9d', pad=20)
        plt.ylabel('Inquiry Frequency (Difficulty)', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', linestyle='--', alpha=0.3)
        
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "vocab_intensity.png")
        plt.tight_layout()
        plt.savefig(output_path)
        print(f"\n✅ 生词可视化完毕！图表已保存至: {output_path}")
        
    except Exception as e:
        print(f">>> ❌ 可视化失败: {e}")

if __name__ == "__main__":
    plot_vocab_analysis()
