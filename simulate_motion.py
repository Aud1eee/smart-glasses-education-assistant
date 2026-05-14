import requests, time, math, random

def simulate():
    print("🚀 开始模拟头部转动数据 (发送至 app.py)...")
    step = 0
    try:
        while True:
            base_curve = 20 + 15 * math.sin(step * 0.15)
            noise = random.uniform(-2.0, 2.0) 
            pitch = base_curve + noise
            requests.post("http://127.0.0.1:5000/api/v1/posture", json={"pitch": pitch})
            print(f"\r发送原始值: {pitch:5.2f}° | 观察网页端平滑效果...", end="")
            step += 1
            time.sleep(0.1) 
    except KeyboardInterrupt:
        print("\n👋 停止模拟")

if __name__ == "__main__":
    simulate()