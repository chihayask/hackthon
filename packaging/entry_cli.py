# -*- coding: utf-8 -*-
"""PyInstaller 入口：把 formula_agh 命令行封成单文件 exe。

打包命令见 packaging/build_exe.cmd。运行方式与源码一致：

    formula_agh.exe verify --task tasks/phys-ohm --formula "I*R"

exe 预期放在**项目根目录**下运行（需要 tasks/ reference/ sealed/ physics/ 等数据）；
config/agent.yaml 会优先读 exe 同目录的那一份，保证阈值仍只有一处。
"""
import os
import sys

# 源码运行时把 src/ 加入搜索路径；打包后公式引擎已被静态收集，这一句无副作用。
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from formula_agh.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
