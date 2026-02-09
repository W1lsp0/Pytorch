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
    total_clients = 10
    
    print("🚀 启动监控面板 (按 Ctrl+C 退出)...")
    time.sleep(1)

    while True:
        try:
            # 1. 刷新数据库缓存 (一次查询获取所有)
            _db_cache = get_all_status_from_db()
            
            # Debug: Write DB Cache to file
            with open("dashboard_debug.log", "w", encoding="utf-8") as f:
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
            print(f"├{'─'*8}┬{'─'*12}┬{'─'*12}┬{'─'*12}┬{'─'*10}┬{'─'*10}┬{'─'*12}┤")
            # 中文字符视觉宽度为2，所以 center 宽度要减去 (汉字数 (2) * 1) = 实际上 center(w) 产生的总视觉宽度是 w + 汉字数
            # 目标视觉宽度: 10. string="类型" len=2. center(8) -> 3sp + 2ch(4px) + 3sp = 10px.
            print(f"│ {'ID'.center(6)} │ {'类型'.center(8)} │ {'攻击'.center(8)} │ {'轮次'.center(8)} │ {'Loss'.center(8)} │ {'ASR'.center(8)} │ {'状态'.center(8)} │")
            print(f"├{'─'*8}┼{'─'*12}┼{'─'*12}┼{'─'*12}┼{'─'*10}┼{'─'*10}┼{'─'*12}┤")
            
            for i in range(total_clients):
                data = parse_client_log(i)
                
                # 简单的类型判断
                c_type = "😈 恶意" if i < 4 else "✅ 诚实"
                # c_type 包含2个汉字(恶意/诚实) + 1个emoji(😈/✅) + 1个空格.
                # emoji 宽度通常为2. 汉字为2.
                # 😈 (2) + ' ' (1) + 恶 (2) + 意 (2) = 7 visual width.
                # "😈 恶意".center(10) -> len=4. 3sp + 4len + 3sp.
                # Visual: 3 + 7 + 3 = 13. Too wide for 12 slot?
                # Slot is 12 (from header line 173).
                # To get visual 12: 12 - 7 = 5 spaces. center(4+5) -> center(9).
                # "😈 恶意".center(5) is too small.
                # Let's manual pad.
                c_type_str = f"{c_type}" # visual 7
                # target 12. left 2, right 3.
                c_type_cell = "  " + c_type_str + "   "
                
                # Attack is usually English (LABEL_FLIP etc)
                # target 12.
                attack_cell = data['attack'][:10].center(12)

                # Round target 12.
                round_cell = str(data['round']).center(12)
                
                # Loss target 10.
                loss_cell = str(data['loss']).center(10)
                
                # ASR target 10.
                asr_cell = data['asr'].center(10)
                
                # Status target 12.
                # If status is Chinese? It is "Training"/"Waiting" (English in code).
                status_cell = data['status'].center(12)

                row = f"│ {str(i).center(6)} │{c_type_cell}│{attack_cell}│{round_cell}│{loss_cell}│{asr_cell}│{status_cell}│"
                print(row)
                
            print(f"└{'─'*8}┴{'─'*12}┴{'─'*12}┴{'─'*12}┴{'─'*10}┴{'─'*10}┴{'─'*12}┘")
            
            # ==================== 统计聚合 (New Feature) ====================
            # 统计各类攻击的平均 ASR 和 Loss
            stats = {} # key: attack_type, value: {loss_sum, asr_sum, count}
            
            for i in range(total_clients):
                data = parse_client_log(i)
                attack_type = data['attack']
                if attack_type == '-': continue
                
                # Parse Loss
                try:
                    loss_val = float(data['loss'])
                except:
                    loss_val = 0.0
                    
                # Parse ASR (remove %)
                try:
                    asr_val = float(data['asr'].replace('%', ''))
                except:
                    asr_val = 0.0
                    
                if attack_type not in stats:
                    stats[attack_type] = {'loss': 0.0, 'asr': 0.0, 'count': 0}
                
                stats[attack_type]['loss'] += loss_val
                stats[attack_type]['asr'] += asr_val
                stats[attack_type]['count'] += 1
            
            print("\n📊 攻击效果统计 (Average):")
            print(f"┌{'─'*40}┐")
            print(f"│ {'Attack Type'.ljust(15)} │ {'Avg Loss'.center(8)} │ {'Avg ASR'.center(9)} │")
            print(f"├{'─'*17}┼{'─'*10}┼{'─'*11}┤")
            
            for atype, s in stats.items():
                if s['count'] > 0:
                    avg_loss = s['loss'] / s['count']
                    avg_asr = s['asr'] / s['count']
                    print(f"│ {atype.ljust(15)} │ {f'{avg_loss:.4f}'.center(8)} │ {f'{avg_asr:.1f}%'.center(9)} │")
            print(f"└{'─'*40}┘")
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
