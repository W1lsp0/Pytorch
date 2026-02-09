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
    log_path = "log/server.log"
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
except Exception as e:
    print(f"⚠️ [Dashboard] DB Connection failed: {e}")
    print(f"⚠️ [Dashboard] Falling back to log parsing.")

def get_all_status_from_db():
    """从数据库批量获取所有客户端状态"""
    if db_manager:
        return db_manager.get_all_client_status()
    return {}

# 缓存上一轮的 DB 状态，减少高频查询闪烁
_db_cache = {}

def parse_client_log(client_id):
    """
    只读取数据库状态 (No Fallback)
    """
    global _db_cache
    
    # 确保 ID 类型匹配 (DB key 是 int)
    cid = int(client_id)
    
    if cid in _db_cache:
        data = _db_cache[cid]
        return {
            "attack": data.get("attack", "-"),
            "round": str(data.get("round", "-")),
            "loss": str(data.get("loss", "-")),
            "asr": str(data.get("asr", "0%")),
            "status": data.get("status", "Unknown")
        }

    # 如果数据库里没有 (比如还没启动)
    return {
        "status": "Waiting...",
        "round": "-",
        "loss": "-",
        "asr": "-",
        "attack": "-"
    }

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    global _db_cache
    total_clients = 20
    
    print("🚀 启动监控面板 (按 Ctrl+C 退出)...")
    time.sleep(1)

    while True:
        try:
            # 1. 刷新数据库缓存 (一次查询获取所有)
            _db_cache = get_all_status_from_db()
            
            # Debug: Write DB Cache to file (in log dir)
            os.makedirs("log", exist_ok=True)
            with open("log/dashboard_debug.log", "w", encoding="utf-8") as f:
                f.write(f"Timestamp: {time.ctime()}\n")
                f.write(f"DB Cache Keys: {list(_db_cache.keys())}\n")
                if _db_cache:
                    f.write(f"Sample Client 0: {_db_cache.get(0)}\n")
                    f.write(f"Sample Client 2: {_db_cache.get(2)}\n")
            
            clear_screen()
            server_round = parse_server_log()
            
            print(f"┌{'─'*82}┐")
            
            # 调试信息: 显示 DB 连接状态和缓存大小
            db_status = f"✅ Connected ({len(_db_cache)} nodes)" if db_manager else "❌ Disconnected"
            print(f"│  🌍 服务器状态: Round {str(server_round).ljust(20)} | DB: {db_status.ljust(33)}│")
            print(f"├{'─'*8}┬{'─'*12}┬{'─'*12}┬{'─'*12}┬{'─'*10}┬{'─'*12}┬{'─'*12}┬{'─'*12}┤")
            # 目标视觉宽度: 12 Loc ASR (B99% C12%)
            # 目标视觉宽度: 12 Glo ASR (B99% C12%)
            print(f"│ {'ID'.center(6)} │ {'类型'.center(8)} │ {'攻击'.center(8)} │ {'轮次'.center(8)} │ {'Loss'.center(8)} │ {'Loc ASR'.center(10)} │ {'Glo ASR'.center(10)} │ {'状态'.center(8)} │")
            print(f"├{'─'*8}┼{'─'*12}┼{'─'*12}┼{'─'*12}┼{'─'*10}┼{'─'*12}┼{'─'*12}┼{'─'*12}┤")
            
            for i in range(total_clients):
                data = parse_client_log(i)
                
                # 简单的类型判断
                c_type = "😈 恶意" if i < 4 else "✅ 诚实"
                c_type_str = f"{c_type}" # visual 7
                c_type_cell = "  " + c_type_str + "   "
                
                # Attack
                attack_cell = data['attack'][:10].center(12)

                # Round
                round_cell = str(data['round']).center(12)
                
                # Loss
                loss_cell = str(data['loss']).center(10)
                
                # Parse ASR for separate Local/Global columns
                # Format: "L:B99% C12%|G:B45% C45%"
                asr_raw = data['asr']
                loc_val_str = "-"
                glo_val_str = "-"
                
                if '|' in asr_raw:
                    parts = asr_raw.split('|')
                    for p in parts:
                        if p.startswith('L:'):
                            loc_val_str = p.replace('L:', '') # "B99% C12%"
                        elif p.startswith('G:'):
                            glo_val_str = p.replace('G:', '') # "B45% C45%"
                else:
                    # Fallback
                    glo_val_str = asr_raw
                
                loc_cell = loc_val_str.center(12)
                glo_cell = glo_val_str.center(12)
                
                # Status
                status_cell = data['status'].center(12)

                row = f"│ {str(i).center(6)} │{c_type_cell}│{attack_cell}│{round_cell}│{loss_cell}│{loc_cell}│{glo_cell}│{status_cell}│"
                print(row)
                
            print(f"└{'─'*8}┴{'─'*12}┴{'─'*12}┴{'─'*12}┴{'─'*10}┴{'─'*12}┴{'─'*12}┴{'─'*12}┘")
            
            # ==================== 统计聚合 (New Feature) ====================
            # 统计各类攻击的平均 ASR 和 Loss
            # key: attack_type, value: {loss_sum, loc_b_sum, loc_c_sum, glo_b_sum, glo_c_sum, count}
            stats = {} 
            
            for i in range(total_clients):
                data = parse_client_log(i)
                attack_type = data['attack']
                if attack_type == '-': continue
                
                if attack_type not in stats:
                    stats[attack_type] = {
                        'loss': 0.0, 
                        'loc_b': 0.0, 'loc_c': 0.0, 
                        'glo_b': 0.0, 'glo_c': 0.0, 
                        'count': 0
                    }
                
                # Parse Loss
                try: stats[attack_type]['loss'] += float(data['loss'])
                except: pass
                    
                # Parse ASR (B/C splitting)
                asr_raw = data['asr']
                # Helper to extract B/C values from "B99% C12%"
                def parse_bc(s):
                    b_val, c_val = 0.0, 0.0
                    try:
                        # Simple parsing assuming "Bxx% Cyy%" format
                        parts = s.split(' ') # ["B99%", "C12%"]
                        for p in parts:
                            if p.startswith('B'):
                                b_val = float(p.replace('B','').replace('%',''))
                            elif p.startswith('C'):
                                c_val = float(p.replace('C','').replace('%',''))
                    except:
                        pass
                    return b_val, c_val

                if '|' in asr_raw:
                    parts = asr_raw.split('|')
                    for p in parts:
                        if p.startswith('L:'):
                            lb, lc = parse_bc(p.replace('L:', ''))
                            stats[attack_type]['loc_b'] += lb
                            stats[attack_type]['loc_c'] += lc
                        elif p.startswith('G:'):
                            gb, gc = parse_bc(p.replace('G:', ''))
                            stats[attack_type]['glo_b'] += gb
                            stats[attack_type]['glo_c'] += gc
                
                stats[attack_type]['count'] += 1
            
            print("\n📊 攻击效果统计 (Average): BD=Backdoor, CL=CleanLabel")
            print(f"┌{'─'*71}┐")
            print(f"│ {'攻击类型'.ljust(8)} │ {'损失(Loss)'.center(8)} │ {'本地 BD'.center(6)} │ {'本地 CL'.center(6)} │ {'全局 BD'.center(6)} │ {'全局 CL'.center(6)} │")
            print(f"├{'─'*14}┼{'─'*12}┼{'─'*10}┼{'─'*10}┼{'─'*10}┼{'─'*10}┤")
            
            for atype, s in stats.items():
                if s['count'] > 0:
                    cnt = s['count']
                    avg_loss = s['loss'] / cnt
                    avg_lb = s['loc_b'] / cnt
                    avg_lc = s['loc_c'] / cnt
                    avg_gb = s['glo_b'] / cnt
                    avg_gc = s['glo_c'] / cnt
                    
                    # 汉字对齐处理: ljust/center 对汉字支持不好，简单起见用 ljust+padding
                    # '攻击类型' 占 8 字符宽度 (4汉字) -> display width 8
                    # atype 可能是 'BACKDOOR' (8 chars) -> ljust(12) is fine
                    display_type = atype
                    
                    print(f"│ {display_type.ljust(12)} │ {f'{avg_loss:.4f}'.center(10)} │ {f'{avg_lb:.0f}%'.center(8)} │ {f'{avg_lc:.0f}%'.center(8)} │ {f'{avg_gb:.0f}%'.center(8)} │ {f'{avg_gc:.0f}%'.center(8)} │")
            print(f"└{'─'*71}┘")
            # ================================================================
            print("\n每 2 秒刷新一次...")
            print("提示: 建议将此窗口与日志窗口并排显示。")
            
            time.sleep(2)
        except KeyboardInterrupt:
            print("\n正在退出...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
