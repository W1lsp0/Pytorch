"""
==============================================================================
🚀 Trace Generator 大规模数据生成器
==============================================================================
本脚本用于生成大规模的联邦学习设备仿真数据。

功能:
    1. 构建异构设备池 (按照真实世界比例分布)
    2. 随机注入恶意节点 (Lazy / Miner)
    3. 调用 Simulator 生成时序数据
    4. 批量写入 MySQL 数据库

使用方法:
    python generate_traces.py --devices 50 --duration 600 --clean

参数说明:
    --devices: 模拟设备总数 (默认 50)
    --duration: 每个设备模拟的时长(秒) (默认 600)
    --clean: 是否先清空数据库

作者: Flwr 联邦学习项目
==============================================================================
"""

import time
import argparse
import random
import sys
import os
try:
    from .db_manager import DBManager
    from .simulator import DeviceSimulator
except ImportError:
    from db_manager import DBManager
    from simulator import DeviceSimulator

# ==================== 解决 Windows 中文乱码问题 ====================
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="TMAA 硬件踪迹生成器")
    parser.add_argument("--devices", type=int, default=50, help="模拟设备数量")
    parser.add_argument("--duration", type=int, default=600, help="每台设备的模拟时长(秒)")
    parser.add_argument("--malicious_rate", type=float, default=0.2, help="恶意节点比例 (0.0~1.0)")
    parser.add_argument("--clean", action="store_true", help="生成前清空已有数据")
    args = parser.parse_args()
    
    # 1. 初始化数据库
    print("\n" + "="*60 + "\n" +
          "💾 正在初始化数据库连接...\n" +
          "="*60)
    
    try:
        db = DBManager()
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print("💡 提示: 请确保 MySQL 运行在 127.0.0.1:3306 且密码正确")
        return
        
    # 🚨 **Clean DB if requested** 🚨
    if args.clean:
        print("\n⚠️  警告: 已启用 --clean 参数，正在清空数据库...")
        db.clear_all_data()
    else:
        print("\nℹ️  追加模式: 数据将追加到现有表中 (使用 --clean 可重置)")
    
    # 2. 定义异构设备池分布 (Heterogeneous Distribution)
    # 模拟真实 FL 场景: 少量高端服务器，大量中端 PC，海量边缘设备
    device_pool = {
        # === 数据中心 (15%) ===
        "NVIDIA_A100_80GB": 0.05,
        "NVIDIA_V100_32GB": 0.05,
        "NVIDIA_RTX4090":   0.05,
        
        # === 消费级中高端 (35%) ===
        "NVIDIA_RTX3090":   0.15,
        "NVIDIA_RTX3080":   0.20,
        
        # === 边缘/低功耗 (50%) ===
        "NVIDIA_Jetson_AGX": 0.10,
        "NVIDIA_Jetson_NX":  0.10,
        "NVIDIA_Jetson_Nano": 0.10,
        "Raspberry_Pi_4":    0.10,
        "Intel_NUC":         0.10
    }
    
    all_types = list(device_pool.keys())
    probs = list(device_pool.values())
    
    total_records = args.devices * args.duration
    print("\n".join([
        f"\n🚀 开始大规模仿真任务:",
        f"   👥 模拟设备数: {args.devices}",
        f"   ⏱️  单机时长:   {args.duration} 秒",
        f"   📊 预计总记录: {total_records} 条",
        f"   🌍 设备分布:   异构混合 (DataCenter -> IoT)",
        f"   😈 恶意比例:   {args.malicious_rate * 100:.1f}%",
        "-" * 60
    ]))
    
    start_time_all = time.time()
    
    for i in range(args.devices):
        dev_id = f"worker_{i:04d}" # worker_0001
        
        
        # 3. 随机分配属性
        is_malicious = (i < args.devices * args.malicious_rate)
        
        # 按概率分布选择硬件类型
        # random.choices 返回列表，取第0个
        h_type = random.choices(all_types, weights=probs, k=1)[0]
        
        # 4. 创建模拟器实例
        sim = DeviceSimulator(dev_id, profile_type=h_type, is_malicious=is_malicious)
        profile = sim.get_profile()
        
        # [NEW] 分配具体攻击类型
        if is_malicious:
            # 随机选择一种攻击模式
            attack_pool = [
                "label_flip",           # 通用翻转
                "directed_label_flip",  # 定向翻转
                "backdoor",             # 经典后门
                "clean_label",          # 干净标签
                "semantic"              # 语义扰动
            ]
            profile["attack_type"] = random.choice(attack_pool)
        else:
            profile["attack_type"] = "none"

        # 恶意节点行为模式
        pattern = "normal"
        if is_malicious:
            pattern = random.choice(["lazy", "miner"])

        # 4. 创建模拟器实例 (Updated)
        sim = DeviceSimulator(dev_id, profile_type=h_type, is_malicious=is_malicious, pattern=pattern)
        
        # 5. 注册设备 (写入 Static Profile)
        db.register_device(profile)
        
        # 6. 生成离散数据池 (Discrete Phase Data Pools)
        # 每个 Phase 生成 200 个 Step 的数据供 Loop 使用
        phases = ["Idle", "Loading", "Forward", "Backward"]
        logs = []
        
        for phase in phases:
            # Lazy 节点也会生成这些 Phase 标签，但内容全是 Idle 特征 (由 Simulator 内部处理)
            # Miner 节点也会生成这些 Phase 标签，但内容全是 满载 特征
            phase_logs = sim.generate_phase_data(phase, count=200, start_step=0)
            logs.extend(phase_logs)
            
        # 7. 批量写入日志
        
        # 7. 批量写入日志
        db.insert_telemetry_batch(logs)
        
        # 进度输出美化
        status = "😈 MALICIOUS" if is_malicious else "✅ HONEST"
        p_icon = "📈" if pattern == "sawtooth" else ("💤" if pattern == "lazy" else "⛏️ ")
        
        # 只打印部分日志，避免刷屏
        if i < 10 or i % 10 == 0 or i == args.devices - 1:
            print(f"[{i+1:03d}/{args.devices}] {dev_id.ljust(12)} | {h_type.ljust(18)} | {status} | 模式: {pattern.ljust(8)} {p_icon}")
        elif i == 10:
            print("... (中间省略) ...")

    total_time = time.time() - start_time_all
    
    print("\n".join([
        "-" * 60,
        "",
        "✨ 仿真任务完成!",
        f"⏱️  总耗时:       {total_time:.2f} 秒",
        f"📊 生成总记录:   {total_records}",
        "🔍 验证提示:     请检查 MySQL 表 'telemetry_logs'",
        "=" * 60
    ]))

if __name__ == "__main__":
    main()
