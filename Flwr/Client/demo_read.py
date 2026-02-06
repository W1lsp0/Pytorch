
from poison.db_manager import DBManager
import json

def main():
    db = DBManager()
    
    # 1. 获取一个设备ID (示例)
    # 这里我们假设生成时使用的是 worker_0000, worker_0001 ...
    target_device = "worker_0000"
    
    print(f"🔍 查询设备: {target_device}")
    
    # 2. 获取静态画像
    profile = db.get_device_info(target_device)
    if not profile:
        print("❌ 未找到该设备，请确认数据库中已有数据。")
        return
        
    print("\n[静态画像 (Static Profile)]")
    # 美化打印
    print(json.dumps(profile, indent=2, default=str)) # default=str 用于处理 datetime 对象
    
    # 3. 获取动态遥测数据 (前 5 条)
    logs = db.fetch_telemetry(target_device, limit=5)
    
    print(f"\n[动态遥测 (Telemetry Logs) - Top 5]")
    for log in logs:
        # 简单格式化输出
        print(f"Token: {log['timestamp']} | Phase: {log['phase']:<10} | "
              f"GPU: {log['gpu_util']}% | Temp: {log['temperature_c']}°C")

    # 4. 模拟 TMAA 如何使用数据
    # TMAA 通常会按时间片段读取数据来模拟"流式"监控
    print(f"\n[模拟 TMAA 监控流]")
    print("正在回放数据流...")
    for log in logs[:3]:
        # 假装在实时接收数据
        print(f"  -> 收到监控包: CPU={log['cpu_usage']}% / Mem={log['memory_usage_mb']:.1f}MB")
        
if __name__ == "__main__":
    main()
