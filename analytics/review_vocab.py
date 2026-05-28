import os

import pandas as pd


def show_progress():
    file = "../data/my_vocabulary.csv"
    if not os.path.exists(file):
        print(">>> The vocabulary list is empty. Capture some words first.")
        return

    try:
        df = pd.read_csv(file)
        if df.empty:
            print(">>> The vocabulary list exists, but it is still empty.")
            return

        print("\n" + "=" * 35)
        print(f"My Rokid Vocabulary Log (total: {len(df)} words)")
        print("=" * 35)
        print("\nRecently captured:")
        print(df.sort_values("Last_Seen", ascending=False).head(5)[["Word", "Translation"]].to_string(index=False))

        hard_words = df[df["Count"] > 1]
        if not hard_words.empty:
            print("\nHigh-frequency review targets:")
            for _, row in hard_words.head(3).iterrows():
                print(f" - {row['Word']} (looked up {row['Count']} times)")
    except Exception:
        print("Could not read the vocabulary list.")


if __name__ == "__main__":
    show_progress()
