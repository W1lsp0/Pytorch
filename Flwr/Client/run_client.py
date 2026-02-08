#!/usr/bin/env python3
"""
==============================================================================
🚀 联邦学习客户端入口脚本
==============================================================================
"""
import sys
import os

# ==================== 修复 stdout 缓冲问题 ====================
# 当 stdout 重定向到文件时，Python 默认使用块缓冲
# 这会导致 print() 输出被延迟，日志顺序混乱
# 解决方案：强制使用无缓冲模式
if not sys.stdout.isatty():
    import io
    sys.stdout = io.TextIOWrapper(
        open(sys.stdout.fileno(), 'wb', 0),  # 0 = unbuffered
        write_through=True
    )
    sys.stderr = io.TextIOWrapper(
        open(sys.stderr.fileno(), 'wb', 0),
        write_through=True
    )
# ================================================================

if __name__ == "__main__":
    from client import main
    main()

