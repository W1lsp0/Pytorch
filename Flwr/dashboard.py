import os
import time
import re
import glob
import sys

# ==================== 解决 Windows 中文乱码问题 ====================
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
# ================================================================

def get_last_line(filepath):
    """读取文件最后一行"""
    if not os.path.exists(filepath):
        return "Waiting..."
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            # 简单读取最后几行
            # 对于大文件，应该 seek 到末尾，但日志通常不大，直接 readlines 也可以
            # 优化: seek
            try:
                f.seek(0, 2)
                fsize = f.tell()
                f.seek(max(fsize - 1024, 0), 0) # 只读最后 1KB
                lines = f.readlines()
                if lines:
                    return lines[-1].strip()
            except:
                pass
            return "Reading..."
    except Exception:
        return "Error"

def parse_server_log():
    """从 server.log 解析当前轮次"""
    log_path = "server.log"
    if not os.path.exists(log_path):
        return "Init"
    
    current_round = 0
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        # 倒序查找 [ROUND X]
        # 由于文件可能增加，我们简单读取全部查找最后出现的 Round
        content = f.read()
        matches = re.findall(r"\[ROUND (\d+)\]", content)
        if matches:
            current_round = matches[-1]
    return current_round

# ==================== 数据库连接 ====================
from Client.poison.db_manager import DBManager
db_manager = None
try:
    # 尝试连接数据库，如果失败则回退到日志
    db_manager = DBManager()
    print("✅ [Dashboard] Connected to DB.")
except:
    print("⚠️ [Dashboard] DB Connection failed, using logs only.")

def get_all_status_from_db():
    """从数据库批量获取所有客户端状态"""
    if db_manager:
        return db_manager.get_all_client_status()
    return {}

# 缓存上一轮的 DB 状态，减少高频查询闪烁
_db_cache = {}

def parse_client_log(client_id):
    """
    优先读取数据库状态，回退到日志
    """
    global _db_cache
    
    # 1. 尝试从 DB 缓存读取 (主循环负责更新缓存)
    if client_id in _db_cache:
        data = _db_cache[client_id]
        return {
            "attack": data.get("attack", "-"),
            "round": str(data.get("round", "-")),
            "loss": str(data.get("loss", "-")),
            "asr": str(data.get("asr", "0%")),
            "status": data.get("status", "Unknown")
        }

    # 2. 回退到日志解析 (Legacy)
    log_path = f"client_{client_id}.log"
    
    info = {
        "status": "Waiting",
        "round": "-",
        "loss": "-",
        "asr": "0%",
        "attack": "-"
    }
    
    if not os.path.exists(log_path):
        return info

    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # 1. 攻击类型
            att_match = re.search(r"攻击模式:\s+(\w+)", content)
            if att_match:
                info["attack"] = att_match.group(1)
            else:
                 # 尝试从 Banner 找 Honest
                 if "正常训练 (Honest)" in content:
                     info["attack"] = "HONEST"
            
            # 2. 当前轮次
            # Match "Round X |" with optional logging prefixes
            round_match = re.findall(r"Round (\d+) \|", content)
            if round_match:
                info["round"] = round_match[-1]
                info["status"] = "Training"
            
            # 3. Loss
            # Match "Loss: 0.1234"
            loss_match = re.findall(r"Loss: ([\d\.]+)", content)
            if loss_match:
                info["loss"] = loss_match[-1]

            # 4. ASR (Attack Success Rate)
            # Match "ASR): 99.00%"
            asr_match = re.findall(r"ASR\): ([\d\.]+)", content)
            if asr_match:
                info["asr"] = asr_match[-1] + "%"
                
            # 5. TMAA 签名
            if "已生成可信报告" in content[-500:]: # 检查最后 500 字符
                info["status"] = "Reported"

    except Exception:
        pass
        
    return info

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    total_clients = 10
    
    print("🚀 启动监控面板 (按 Ctrl+C 退出)...")
    time.sleep(1)

    while True:
        try:
            # 1. 刷新数据库缓存 (一次查询获取所有)
            _db_cache = get_all_status_from_db()
            
            clear_screen()
            server_round = parse_server_log()
            
            print(f"┌{'─'*82}┐")
            print(f"│  🌍 Server Status: Round {str(server_round).ljust(60)}│")
            print(f"├{'─'*8}┬{'─'*12}┬{'─'*12}┬{'─'*12}┬{'─'*10}┬{'─'*10}┬{'─'*12}┤")
            print(f"│ {'ID'.center(6)} │ {'Type'.center(10)} │ {'Attack'.center(10)} │ {'Round'.center(10)} │ {'Loss'.center(8)} │ {'ASR'.center(8)} │ {'Status'.center(10)} │")
            print(f"├{'─'*8}┼{'─'*12}┼{'─'*12}┼{'─'*12}┼{'─'*10}┼{'─'*10}┼{'─'*12}┤")
            
            for i in range(total_clients):
                data = parse_client_log(i)
                
                # 简单的类型判断
                c_type = "😈 BAD" if i < 4 else "✅ GOOD"
                if i < 4 and data["attack"] == "-": data["attack"] = "Unknown" 
                
                # ASR 只有 Backdoor/CleanLabel 有意义，其他可以标灰 (这里简单全显示)
                asr_val = data['asr']
                if data['attack'] not in ['BACKDOOR', 'CLEAN_L']:
                     # Optional: make it less prominent
                     pass

                row = f"│ {str(i).center(6)} │ {c_type.center(10)} │ {data['attack'][:10].center(10)} │ {str(data['round']).center(10)} │ {str(data['loss']).center(8)} │ {asr_val.center(8)} │ {data['status'].center(10)} │"
                print(row)
                
            print(f"└{'─'*8}┴{'─'*12}┴{'─'*12}┴{'─'*12}┴{'─'*10}┴{'─'*10}┴{'─'*12}┘")
            print("\nUpdating every 2 seconds...")
            print("Tip: Run this in a separate window side-by-side with your logs.")
            
            time.sleep(2)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
