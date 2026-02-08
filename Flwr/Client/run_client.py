#!/usr/bin/env python3
"""
==============================================================================
🚀 联邦学习客户端入口脚本
==============================================================================
"""
import sys
import os

def _is_worker_process() -> bool:
    """
    检测当前进程是否为 loky/multiprocessing 的工作进程
    """
    # 调试输出
    debug = os.environ.get("DEBUG_WORKER_DETECTION", "0") == "1"
    if debug:
        print(f"[DEBUG] sys.argv = {sys.argv}")
        print(f"[DEBUG] __name__ = {__name__}")
        print(f"[DEBUG] PID = {os.getpid()}, PPID = {os.getppid()}")
    
    # 方法1: 检查是否通过 python -c 执行（loky 常用方式）
    if len(sys.argv) >= 1 and sys.argv[0] == '-c':
        if debug:
            print("[DEBUG] Detected as worker: sys.argv[0] == '-c'")
        return True
    
    # 方法2: 检查命令行参数中是否包含 multiprocessing/loky 相关标识
    for arg in sys.argv:
        arg_lower = arg.lower()
        # 注意: 只检查非常明确的标识
        if 'from multiprocessing' in arg_lower or 'loky.backend' in arg_lower:
            if debug:
                print(f"[DEBUG] Detected as worker: arg contains multiprocessing/loky: {arg}")
            return True
    
    return False

if __name__ == "__main__":
    # 检测是否为工作进程
    if _is_worker_process():
        # 子进程：静默退出，让 loky 正常处理
        pass
    else:
        # 主进程：执行客户端逻辑
        from client import main
        main()
