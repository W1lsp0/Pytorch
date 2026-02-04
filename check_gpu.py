import torch
import sys
import platform


def check_pytorch_pro():
    print("=" * 50)
    print("🚀 PyTorch + CUDA + cuDNN 深度环境报告")
    print("=" * 50)

    # 1. 软件环境
    print(f"【软件版本】")
    print(f"Python 版本:    {sys.version.split()[0]}")
    print(f"PyTorch 版本:   {torch.__version__}")

    # 2. CUDA 核心信息
    cuda_available = torch.cuda.is_available()
    print(f"\n【CUDA 信息】")
    print(f"CUDA 是否可用:  {'✅ 是' if cuda_available else '❌ 否'}")

    if cuda_available:
        print(f"CUDA 编译版本:  {torch.version.cuda}")

        # 3. cuDNN 核心信息 (重点)
        print(f"\n【cuDNN 加速库】")
        cudnn_enabled = torch.backends.cudnn.enabled
        print(f"cuDNN 启用状态: {'✅ 已启用' if cudnn_enabled else '❌ 未启用'}")
        if cudnn_enabled:
            # 获取 cuDNN 版本号
            version = torch.backends.cudnn.version()
            # 格式化版本号 (例如 8902 -> 8.9.2)
            v_str = str(version)
            if len(v_str) >= 4:
                major = v_str[0]
                minor = v_str[1]
                patch = v_str[2:]
                print(f"cuDNN 运行版本: {major}.{minor}.{patch}")
            else:
                print(f"cuDNN 运行版本: {version}")

            # cuDNN 确定性与基准设置 (Benchmark 模式能加速固定维度的输入)
            print(f"cuDNN Benchmark: {torch.backends.cudnn.benchmark}")
            print(f"cuDNN Deterministic: {torch.backends.cudnn.deterministic}")

        # 4. 显卡硬件细节
        prop = torch.cuda.get_device_properties(0)
        print(f"\n【显卡详情】")
        print(f"设备名称:       {prop.name}")
        print(f"算力级别:       {prop.major}.{prop.minor}")
        print(f"总显存:         {prop.total_memory / 1024 ** 2:.0f} MB")

        # 5. 简单性能实测
        print(f"\n【实时性能测试】")
        device = torch.device("cuda")
        a = torch.randn(size=(4000, 4000), device=device)
        b = torch.randn(size=(4000, 4000), device=device)

        # 预热 GPU
        torch.matmul(a, b)

        # 正式计时
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)

        start.record()
        torch.matmul(a, b)
        end.record()

        torch.cuda.synchronize()
        print(f"✅ 4000x4000 矩阵乘法耗时: {start.elapsed_time(end):.2f} ms")

    else:
        print("\n⚠️ 未检测到 CUDA，请检查驱动或安装包版本。")

    print("=" * 50)


if __name__ == "__main__":
    check_pytorch_pro()
