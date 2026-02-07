#!/usr/bin/env python3
"""
==============================================================================
🚀 联邦学习客户端入口脚本
==============================================================================
这是客户端的入口点脚本。

为什么需要这个脚本？
    joblib/loky 使用 spawn 方式创建子进程时，会重新执行 __main__ 模块。
    通过在入口点检测是否为子进程，可以防止 main() 被意外执行。

用法:
    python run_client.py
    
    环境变量:
        CLIENT_ID: 客户端 ID (默认 0)
        TOTAL_CLIENTS: 总客户端数 (默认 2)
        ATTACK_TYPE: 攻击类型 (none, label_flip, backdoor, etc.)
        POISON_RATE: 投毒比例
        TARGET_LABEL: 目标标签

==============================================================================
"""
import multiprocessing

def _is_worker_process() -> bool:
    """
    检测当前进程是否为 loky/multiprocessing 的工作进程
    """
    # 检查进程名称：主进程名为 "MainProcess"，子进程名为其他
    current = multiprocessing.current_process()
    if current.name != "MainProcess":
        return True
    
    # 检查是否有父进程标记（loky 特有）
    import os
    if os.environ.get("LOKY_PICKLER"):
        return True
    
    return False

if __name__ == "__main__":
    # 支持 Windows 和 spawn 方式的 multiprocessing
    multiprocessing.freeze_support()
    
    # 检测是否为工作进程
    if _is_worker_process():
        # 子进程：静默退出，让 loky 正常处理
        pass
    else:
        # 主进程：执行客户端逻辑
        from client import main
        main()
