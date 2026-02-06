
import time
import argparse
from db_manager import DBManager
from simulator import DeviceSimulator

def main():
    parser = argparse.ArgumentParser(description="TMAA Hardware Trace Generator")
    parser.add_argument("--devices", type=int, default=50, help="Number of devices to simulate")
    parser.add_argument("--duration", type=int, default=600, help="Duration in seconds per device")
    parser.add_argument("--malicious_rate", type=float, default=0.2, help="Proportion of malicious devices")
    parser.add_argument("--clean", action="store_true", help="Clean existing data in DB before generation")
    args = parser.parse_args()
    
    # 1. 初始化数据库
    print("🔌 Connecting to Database...")
    try:
        db = DBManager()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("💡 Hint: Ensure MySQL is running on 127.0.0.1:3306 with root/root123456")
        return
        
    # 🚨 **Clean DB if requested** 🚨
    if args.clean:
        print("\n⚠️  WARNING: Cleaning Database as requested...")
        db.clear_all_data()
    else:
        print("\nℹ️  Appending to existing data (Use --clean to reset).")
    
    # 2. 定义异构设备池分布 (Heterogeneous Distribution)
    # 模拟真实 FL 场景: 少量高端服务器，大量中端 PC，海量边缘设备
    device_pool = {
        # High-End (15%)
        "NVIDIA_A100_80GB": 0.05,
        "NVIDIA_V100_32GB": 0.05,
        "NVIDIA_RTX4090":   0.05,
        
        # Mid-Range (35%)
        "NVIDIA_RTX3090":   0.15,
        "NVIDIA_RTX3080":   0.20,
        
        # Edge/Low-End (50%)
        "NVIDIA_Jetson_AGX": 0.10,
        "NVIDIA_Jetson_NX":  0.10,
        "NVIDIA_Jetson_Nano": 0.10,
        "Raspberry_Pi_4":    0.10,
        "Intel_NUC":         0.10
    }
    
    all_types = list(device_pool.keys())
    probs = list(device_pool.values())
    
    print(f"\n🚀 Starting Massive Simulation for {args.devices} devices...")
    print(f"⏱️  Duration: {args.duration}s/device -> Est. DB Rows: {args.devices * args.duration}")
    print(f"🌍 Device Mix: Heterogeneous (Datacenter to IoT)")
    print("=" * 50)
    
    for i in range(args.devices):
        dev_id = f"worker_{i:04d}" # worker_0001
        
        # 3. 随机分配属性
        is_malicious = (i < args.devices * args.malicious_rate)
        
        # 按概率分布选择硬件类型
        import random
        # random.choices 返回列表，取第0个
        h_type = random.choices(all_types, weights=probs, k=1)[0]
        
        # 4. 创建模拟器实例
        sim = DeviceSimulator(dev_id, profile_type=h_type, is_malicious=is_malicious)
        profile = sim.get_profile()
        
        # 5. 注册设备 (写入 Static Profile)
        db.register_device(profile)
        
        # 6. 生成时序数据 (Dynamic Telemetry)
        start_ts = time.time()
        
        # 恶意节点行为模式
        pattern = "sawtooth"
        if is_malicious:
            pattern = random.choice(["lazy", "miner"])
            
        logs = sim.generate_trace(start_ts, args.duration, pattern=pattern)
        
        # 7. 批量写入日志
        db.insert_telemetry_batch(logs)
        
        status = "😈 MALICIOUS" if is_malicious else "✅ HONEST"
        # 只打印部分日志，避免刷屏
        if i < 10 or i % 10 == 0:
            print(f"[{i+1}/{args.devices}] {dev_id.ljust(15)} | Type: {h_type.ljust(18)} | Role: {status} | Pattern: {pattern}")

    print("\n✨ Simulation Complete!")
    print(f"📊 Total records generated: {args.devices * args.duration}")
    print("You can verify data in MySQL table 'telemetry_logs'")

if __name__ == "__main__":
    main()
