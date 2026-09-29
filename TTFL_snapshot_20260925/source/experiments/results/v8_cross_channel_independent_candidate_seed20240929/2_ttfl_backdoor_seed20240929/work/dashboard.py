import os
import re
import sys
import time

# ==================== 解决 Windows 中文乱码问题 ====================
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
# ================================================================

# ==================== 数据库连接 ====================
# 注意：在 watch 模式下，每次运行脚本都会重新连接一次数据库
from Client.poison.db_manager import DBManager
db_manager = None
try:
    db_manager = DBManager()
    # 注释掉连接成功的提示，保持界面整洁
    # print("✅ [Dashboard] Connected to DB.")
except Exception as e:
    # 仅在出错时显示，避免 watch 界面乱码
    print(f"⚠️ [Dashboard] DB Connection failed: {e}")

def parse_server_log():
    """从 server.log 解析当前轮次"""
    log_path = "log/server.log"
    if not os.path.exists(log_path):
        return "Init"
    
    current_round = 0
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            matches = re.findall(r"\[ROUND (\d+)\]", content)
            if matches:
                current_round = matches[-1]
    except:
        pass
    return current_round

def get_all_status_from_db():
    """从数据库批量获取所有客户端状态"""
    if db_manager:
        return db_manager.get_all_client_status()
    return {}

# 这里的 cache 仅用于当前单次执行的数据传递
_db_cache = {}

def parse_client_log(client_id):
    """只读取数据库状态"""
    global _db_cache
    cid = int(client_id)
    
    # 基础状态
    state = {
        "status": "Waiting...",
        "round": "-",
        "loss": "-",
        "asr": "-",
        "attack": "-"
    }

    if cid in _db_cache:
        data = _db_cache[cid]
        state.update({
            "round": data.get("round", "-"),
            "loss": data.get("loss", "-"),
            "asr": data.get("asr", "-"),
            "attack": data.get("attack", "HONEST"), 
            "status": data.get("status", "Unknown")
        })

    return state

def main():
    global _db_cache
    total_clients = 20
    
    print("🚀 启动监控面板 (按 Ctrl+C 退出)...")
    time.sleep(1)

    while True:
        try:
            # 1. 获取数据 (单次)
            try:
                _db_cache = get_all_status_from_db()
            except:
                _db_cache = {}
            
            server_round = parse_server_log()
            
            # 构建顶部状态栏
            db_status = f"✅ Conn ({len(_db_cache)})" if db_manager else "❌ Disconn"
            
            print(f"┌{'─'*82}┐")
            print(f"│  🌍 服务器状态: Round {str(server_round).ljust(20)} | DB: {db_status.ljust(33)}│")
            print(f"├{'─'*8}┬{'─'*12}┬{'─'*12}┬{'─'*12}┬{'─'*10}┬{'─'*12}┬{'─'*12}┬{'─'*12}┤")
            print(f"│ {'ID'.center(6)} │ {'类型'.center(8)} │ {'攻击'.center(8)} │ {'轮次'.center(8)} │ {'Loss'.center(8)} │ {'Loc ASR'.center(10)} │ {'Glo ASR'.center(10)} │ {'状态'.center(8)} │")
            print(f"├{'─'*8}┼{'─'*12}┼{'─'*12}┼{'─'*12}┼{'─'*10}┼{'─'*12}┼{'─'*12}┼{'─'*12}┤")
            
            # 构建客户端列表
            stats = {} # 用于下方的统计聚合

            for i in range(total_clients):
                data = parse_client_log(i)
                
                # 收集统计信息
                attack_type = data['attack']
                if attack_type != '-':
                    if attack_type not in stats:
                        stats[attack_type] = {'loss': 0.0, 'loc_b': 0.0, 'loc_c': 0.0, 'glo_b': 0.0, 'glo_c': 0.0, 'count': 0}
                    
                    try: stats[attack_type]['loss'] += float(data['loss'])
                    except: pass
                    
                    # ASR 解析逻辑
                    def parse_bc(s):
                        b_val, c_val = 0.0, 0.0
                        try:
                            parts = s.split(' ')
                            for p in parts:
                                if p.startswith('B'): b_val = float(p.replace('B','').replace('%',''))
                                elif p.startswith('C'): c_val = float(p.replace('C','').replace('%',''))
                        except: pass
                        return b_val, c_val

                    if '|' in data['asr']:
                        for p in data['asr'].split('|'):
                            if p.startswith('L:'):
                                lb, lc = parse_bc(p.replace('L:', ''))
                                stats[attack_type]['loc_b'] += lb
                                stats[attack_type]['loc_c'] += lc
                            elif p.startswith('G:'):
                                gb, gc = parse_bc(p.replace('G:', ''))
                                stats[attack_type]['glo_b'] += gb
                                stats[attack_type]['glo_c'] += gc
                    stats[attack_type]['count'] += 1

                # 打印行逻辑
                c_type = "😈 恶意" if i < 4 else "✅ 诚实"
                c_type_cell = "  " + c_type + "   "
                
                # 解析显示用的 ASR 也就是 Local vs Global 显示
                asr_raw = data['asr']
                loc_val_str = "-"
                glo_val_str = "-"
                if '|' in asr_raw:
                    for p in asr_raw.split('|'):
                        if p.startswith('L:'): loc_val_str = p.replace('L:', '')
                        elif p.startswith('G:'): glo_val_str = p.replace('G:', '')
                else:
                    glo_val_str = asr_raw

                row = f"│ {str(i).center(6)} │{c_type_cell}│{data['attack'][:10].center(12)}│{str(data['round']).center(12)}│{str(data['loss']).center(10)}│{loc_val_str.center(12)}│{glo_val_str.center(12)}│{data['status'].center(12)}│"
                print(row)
                
            print(f"└{'─'*8}┴{'─'*12}┴{'─'*12}┴{'─'*12}┴{'─'*10}┴{'─'*12}┴{'─'*12}┴{'─'*12}┘")

            # ==================== 统计聚合 ====================
            if stats:
                print("\n📊 攻击效果统计 (Average):")
                print(f"┌{'─'*71}┐")
                print(f"│ {'攻击'.ljust(8)} │ {'Loss'.center(8)} │ {'L-BD'.center(6)} │ {'L-CL'.center(6)} │ {'G-BD'.center(6)} │ {'G-CL'.center(6)} │")
                print(f"├{'─'*14}┼{'─'*10}┼{'─'*8}┼{'─'*8}┼{'─'*8}┼{'─'*8}┤")
                
                for atype, s in stats.items():
                    if s['count'] > 0:
                        c = s['count']
                        
                        #先把数值算出来，避免在 f-string 里嵌套字典和计算
                        avg_loss = s['loss'] / c
                        avg_lb = s['loc_b'] / c
                        avg_lc = s['loc_c'] / c
                        avg_gb = s['glo_b'] / c
                        avg_gc = s['glo_c'] / c
                        
                        # 格式化字符串
                        loss_str = f"{avg_loss:.4f}"
                        lb_str = f"{avg_lb:.0f}%"
                        lc_str = f"{avg_lc:.0f}%"
                        gb_str = f"{avg_gb:.0f}%"
                        gc_str = f"{avg_gc:.0f}%"

                        # 拼接行
                        row = f"│ {atype.ljust(12)} │ {loss_str.center(8)} │ {lb_str.center(6)} │ {lc_str.center(6)} │ {gb_str.center(6)} │ {gc_str.center(6)} │"
                        print(row)
                print(f"└{'─'*71}┘")
            
            print("\n每 2 秒刷新一次...")
            # print("提示: 建议将此窗口与日志窗口并排显示。")
            
            time.sleep(2)
        except KeyboardInterrupt:
            print("\n正在退出...")
            break
        except Exception as e:
            # print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()