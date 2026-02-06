import time
import argparse
from tmaa.db_manager import DBManager
from tmaa.simulator import DeviceSimulator

def main():
    parser = argparse.ArgumentParser(description="TMAA Hardware Trace Generator")
    parser.add_argument("--devices", type=int, default=10, help="Number of devices to simulate")
    parser.add_argument("--duration", type=int, default=600, help="Duration in seconds per device")
    parser.add_argument("--malicious_rate", type=float, default=0.2, help="Proportion of malicious devices")
    args = parser.parse_args()
    
    # 1. 初始化数据库
    print("🔌 Connecting to Database...")
    try:
        db = DBManager()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("💡 Hint: Ensure MySQL is running on 127.0.0.1:3306 with root/root123456")
        return

    # 2. 定义设备池分布
    device_types = ["NVIDIA_RTX3090", "Jetson_Nano", "Raspberry_Pi_4"]
    weights = [0.2, 0.5, 0.3] # 20% 高端, 50% 中端, 30% 低端
    
    print(f"\n🚀 Starting simulation for {args.devices} devices...")
    print(f"⏱️  Duration: {args.duration}s per device")
    print(f"😈 Malicious Rate: {args.malicious_rate:.1%}")
    print("=" * 50)
    
    for i in range(args.devices):
        dev_id = f"device_{i}"
        
        # 随机分配属性
        is_malicious = (i < args.devices * args.malicious_rate)
        h_type = device_types[0] # Default
        
        # 按照权重随机选择硬件类型
        import random
        r = random.random()
        if r < weights[0]: h_type = device_types[0]
        elif r < weights[0] + weights[1]: h_type = device_types[1]
        else: h_type = device_types[2]
        
        # 3. 创建模拟器实例
        sim = DeviceSimulator(dev_id, profile_type=h_type, is_malicious=is_malicious)
        profile = sim.get_profile()
        
        # 4. 注册设备 (写入 Static Profile)
        db.register_device(profile)
        
        # 5. 生成时序数据 (Dynamic Telemetry)
        start_ts = time.time()
        
        # 恶意节点行为模式
        pattern = "sawtooth"
        if is_malicious:
            pattern = random.choice(["lazy", "miner"])
            
        logs = sim.generate_trace(start_ts, args.duration, pattern=pattern)
        
        # 6. 批量写入日志
        db.insert_telemetry_batch(logs)
        
        status = "😈 MALICIOUS" if is_malicious else "✅ HONEST"
        print(f"[{i+1}/{args.devices}] {dev_id.ljust(10)} | Type: {h_type.ljust(15)} | Role: {status} | Pattern: {pattern}")

    print("\n✨ Simulation Complete!")
    print(f"📊 Total records generated: {args.devices * args.duration}")
    print("You can verify data in MySQL table 'telemetry_logs'")

if __name__ == "__main__":
    main()
