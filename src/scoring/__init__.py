# -*- coding: utf-8 -*-
"""评分包（M2 交付 5/8）——与智能体进程完全隔离的一侧。

隔离规则（可机械核对，见 tests/test_isolation.py）
-------------------------------------------------
1. 本包是 src/ 下的独立顶层包 scoring，formula_agh 的任何模块都不得 import 它。
   智能体通过 CLI 调用 formula_agh；评分只在人工/流水线中单独启动。
2. 只有本包可以读取 reference/（标准答案）。证据：把 reference/ 改名后，
   formula_agh 的全部验证结论逐位不变。
3. 本包只读取两类输入：
     - runs/<run_id>/（智能体的运行输出）
     - reference/ + tasks/*/meta.json（标准答案与任务元数据）
   除此之外不读任何东西。
"""
__all__ = ["compare"]
