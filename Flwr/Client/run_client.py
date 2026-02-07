#!/usr/bin/env python3
"""
==============================================================================
🚀 联邦学习客户端入口脚本
==============================================================================
"""
import sys

def _is_worker_process() -> bool:
    """
    检测当前进程是否为 loky/multiprocessing 的工作进程
    
    loky spawn 的子进程会收到特殊的命令行参数，用于标识它是工作进程。
    常见的标识包括:
    - --multiprocessing-fork
    - 包含 "loky" 的参数
    - 包含 "worker" 的参数
    - 包含 "semaphore_tracker" 的参数
    - 使用 -c 参数执行内联代码
    """
    # 方法1: 检查是否通过 python -c 执行（loky 常用方式）
    if len(sys.argv) >= 1 and sys.argv[0] == '-c':
        return True
    
    # 方法2: 检查命令行参数中是否包含 multiprocessing/loky 相关标识
    for arg in sys.argv:
        arg_lower = arg.lower()
        if any(keyword in arg_lower for keyword in [
            'multiprocessing', 'loky', 'semaphore', 'forkserver', 
            'spawn', 'resource_tracker'
        ]):
            return True
    
    # 方法3: 检查 __spec__ 属性（被 spawn 导入的模块有特殊的 __spec__）
    # 如果不是通过命令行直接运行，__spec__ 会是 None 或特殊值
    import importlib.util
    if hasattr(sys.modules.get('__main__'), '__spec__'):
        spec = sys.modules['__main__'].__spec__
        if spec is not None:
            # 如果有 __spec__，说明是作为模块被导入的
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
