#!/usr/bin/env python3
"""
==============================================================================
🚀 联邦学习客户端入口脚本
==============================================================================
这是客户端的入口点脚本。

为什么需要这个脚本？
    joblib/loky 使用 spawn 方式创建子进程时，会重新导入 __main__ 模块。
    如果 client.py 直接作为 __main__ 运行，loky 子进程会重新执行 client.py，
    导致 main() 函数被意外执行。
    
    通过将入口逻辑分离到这个独立脚本中，当 loky 子进程导入 client.py 时，
    client.py 的 __name__ 是 "client"（不是 "__main__"），
    所以 main() 不会被执行。

用法:
    python run_client.py
    
    环境变量:
        CLIENT_ID: 客户端 ID (默认 0)
        TOTAL_CLIENTS: 总客户端数 (默认 2)
        ATTACK_TYPE: 攻击类型 (none, label_flip, backdoor, etc.)
        POISON_RATE: 投毒比例
        TARGET_LABEL: 目标标签

作者: Flwr 联邦学习项目
==============================================================================
"""

if __name__ == "__main__":
    # 只有当这个脚本直接运行时才执行 main()
    # loky 子进程导入 client.py 时不会执行这里
    from client import main
    main()
