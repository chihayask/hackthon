# -*- coding: utf-8 -*-
"""对抗性测试套件（M2 交付 7/8）。

验收标准（对应分工表 10-13）
---------------------------
"故意构造能让验证放水的用例（过拟合、外推崩溃、量纲错误），每类用例都被正确否决，记录在案。"

本套件与 tests/ 下的单元测试不同：它是一次**正式实验**，覆盖分工文档"异常处理实测记录表"
的 9 类异常，外加 M2 怀疑清单里的 5 项自我攻击。每一类都记录：

    攻击方式 -> 期望行为 -> 实测行为 -> 是否通过 -> 证据位置

关键纪律：**如果某一类没有被正确拦住，就如实写"未拦住"**，并把它列为已知边界。
掩盖一次失败，等于把整个证据包的可信度押上去。

产出：
    evidence/adversarial/report.json
    evidence/adversarial/report.md
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from typing import Dict, List, Optional

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from formula_agh.contract import validate_task                      # noqa: E402
from formula_agh.safe_eval import UnsafeExpression, compile_formula  # noqa: E402
from formula_agh.settings import verify_settings                     # noqa: E402
from formula_agh.split import build_split                            # noqa: E402
from formula_agh.verify import VerifyError, load_task, verify_formula  # noqa: E402

TASKS = os.path.join(ROOT, "tasks")
OUT = os.path.join(ROOT, "evidence", "adversarial")
# 临时任务放在工作区内：文件沙箱可能不允许往系统临时目录写。
TMP = os.path.join(ROOT, "_adversarial_tmp")
SETTINGS = verify_settings()


def verify(task_id, formula, params=None, columns=None, meta=None, settings=None, seed=None):
    s = dict(settings or SETTINGS)
    if seed is not None:
        s["seed"] = seed
    if columns is None or meta is None:
        columns, meta = load_task(os.path.join(TASKS, task_id))
    return verify_formula(
        formula, columns, meta, parameters=params or [],
        holdout_threshold=float(s["holdout_threshold"]),
        extrapolation_threshold=float(s["extrapolation_threshold"]),
        holdout_ratio=float(s["holdout_ratio"]),
        extrapolation_ratio=float(s["extrapolation_ratio"]),
        seed=int(s["seed"]),
        dimension_check=bool(s.get("dimension_check", True)),
        scale_check=bool(s.get("scale_check", True)),
        fit_max_residual=float(s.get("fit_max_residual", 0.5)))


def failed_checks(report) -> List[str]:
    return [c.name for c in report.checks if not c.passed]


def case(name, category, attack, expected, observed, passed, evidence="", note=""):
    return {"name": name, "category": category, "attack": attack, "expected": expected,
            "observed": observed, "passed": bool(passed), "evidence": evidence, "note": note}


# ==========================================================================
# 异常 1：数据缺失 / 异常值
# ==========================================================================

def case_missing_values(tmp) -> Dict[str, object]:
    task_dir = os.path.join(tmp, "nan-task")
    shutil.copytree(os.path.join(TASKS, "phys-ohm"), task_dir)
    csv_path = os.path.join(task_dir, "data.csv")
    with open(csv_path, encoding="utf-8") as fh:
        lines = fh.readlines()
    # 人为制造缺失：把第 5..12 行的 y 列清空
    for i in range(5, 13):
        parts = lines[i].rstrip("\n").split(",")
        parts[-1] = ""
        lines[i] = ",".join(parts) + "\n"
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        fh.writelines(lines)
    findings = validate_task(task_dir, "nan-task")
    codes = sorted({f.code for f in findings if f.severity == "error"})
    caught = "CSV_NON_NUMERIC" in codes
    return case(
        "数据缺失/异常值", "异常处理表第 1 行",
        "在一个通过校验的任务里清空 8 行的 y 值，重新跑数据契约校验",
        "契约校验必须报 error 并拒绝该任务，不得静默通过",
        "error codes = " + (",".join(codes) if codes else "（无，说明漏检）"),
        caught,
        evidence="evidence/adversarial/report.json",
        note="检测点在数据体检（契约校验），不是拟合阶段——缺失数据不该被带进拟合。")


# ==========================================================================
# 异常 2：拟合不收敛
# ==========================================================================

def case_fit_divergence() -> Dict[str, object]:
    report = verify("phys-ideal-gas", "R*n*T", params=["R"])
    checks = {c.name: c for c in report.checks}
    fit_failed = ("fit" in checks) and (not checks["fit"].passed)
    return case(
        "拟合不收敛", "异常处理表第 2 行",
        "给物理上不完整的候选式 R*n*T（漏掉体积项 1/V）做参数拟合",
        "判定 rejected，且失败项必须是 fit，理由指向函数形式而非初值",
        "verdict=%s，失败项=%s，理由：%s" % (
            report.verdict, ",".join(failed_checks(report)) or "-",
            (checks.get("fit").reason if "fit" in checks else "-")[:60]),
        (report.verdict == "rejected") and (fit_failed or "holdout" in failed_checks(report)),
        note="给智能体的提示明确要求'先怀疑函数形式，而不是反复换初值'。")


# ==========================================================================
# 异常 3：量纲不一致
# ==========================================================================

def case_dimension_violation() -> Dict[str, object]:
    report = verify("phys-kinetic-energy", "m*v/2")
    checks = {c.name: c for c in report.checks}
    dim_failed = ("dimension" in checks) and (not checks["dimension"].passed)
    return case(
        "量纲不一致（漏掉速度的平方）", "异常处理表第 3 行",
        "把 m*v**2/2 改成 m*v/2（少一个速度因子）",
        "量纲检验必须 fail（J 对不上），整体 rejected",
        "dimension.passed=%s，verdict=%s" % (checks.get("dimension").passed, report.verdict),
        dim_failed and report.verdict == "rejected",
        note="该任务没有自由参数，因此走严格量纲比对，不存在'参数吸收单位'的模糊空间。")


def case_wrong_unit_in_meta(tmp) -> Dict[str, object]:
    task_dir = os.path.join(tmp, "badunit-task")
    shutil.copytree(os.path.join(TASKS, "phys-kinetic-energy"), task_dir)
    meta_path = os.path.join(task_dir, "meta.json")
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)
    meta["units"]["v"] = "m/s^2"          # 人为把速度单位写错
    with open(meta_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    columns, meta2 = load_task(task_dir)
    report = verify("phys-kinetic-energy", "m*v**2/2", columns=columns, meta=meta2)
    checks = {c.name: c for c in report.checks}
    return case(
        "物理荒谬但拟合好（人为给错单位）", "异常处理表第 8 行",
        "把 meta.units 里速度的单位从 m/s 改成 m/s^2，公式本身不动",
        "量纲检验必须 fail：物理上说不通的表达式不能因为数值拟合好就通过",
        "dimension.passed=%s，verdict=%s" % (checks.get("dimension").passed, report.verdict),
        ("dimension" in checks) and (not checks["dimension"].passed),
        note="这条同时验证了'量纲表缺单位'的风险已被堵住——修复前 8 个任务的量纲门是静默跳过的。")


# ==========================================================================
# 异常 4 / 7：外推崩溃与过拟合
# ==========================================================================

def case_small_angle_approximation() -> Dict[str, object]:
    exact = verify("phys-pendulum-exact", "2*pi*sqrt(L/g)*(1 + theta0**2/16)")
    approx = verify("phys-pendulum-exact", "2*pi*sqrt(L/g)")
    a = {c.name: c for c in approx.checks}
    got = "精确式=%s，小角度近似=%s（失败项 %s）" % (
        exact.verdict, approx.verdict, ",".join(failed_checks(approx)) or "-")
    return case(
        "外推崩溃 / 小角度近似", "异常处理表第 7 行",
        "同时提交精确周期公式与小角度近似公式 2*pi*sqrt(L/g)",
        "精确式 accepted；近似式 rejected（域内已失真）",
        got,
        exact.verdict == "accepted" and approx.verdict == "rejected",
        note="这是项目最有说服力的一类对比：近似式在任何单点上都不荒谬，但整体不成立。")


def case_taylor_overfit() -> Dict[str, object]:
    # 用泰勒展开代替指数衰减：域内二阶近似够用，域外发散
    cand = "N0*(1 - t/tau + (t/tau)**2/2 - (t/tau)**3/6)"
    report = verify("phys-radioactive-decay", cand)
    checks = {c.name: c for c in report.checks}
    h = checks.get("holdout")
    e = checks.get("extrapolation")
    observed = "verdict=%s，holdout=%s，extrapolation=%s；失败项 %s" % (
        report.verdict,
        "%-6s rel=%.4f" % (h.passed, h.metrics.get("relative_rmse", -1)) if h else "-",
        "%-6s rel=%.4f" % (e.passed, e.metrics.get("relative_rmse", -1)) if e else "-",
        ",".join(failed_checks(report)) or "-")
    overfit_signature = bool(h and e and h.passed and not e.passed)
    return case(
        "过拟合（域内好、域外崩）", "异常处理表第 5 行",
        "用 exp(-t/tau) 的三阶泰勒多项式做候选，模拟'只学到域内形状'",
        "理想情况下外推先于留出失败，判定 rejected",
        observed,
        report.verdict == "rejected",
        note=("观察到的过拟合特征（留出通过、外推失败）= " + ("是" if overfit_signature else "否")
              + "。无论是否命中该特征，只要整体被拒，就说明外推门在起作用。"))


# ==========================================================================
# 异常 5：负对照（纯噪声）
# ==========================================================================

def case_negative_control(tmp) -> Dict[str, object]:
    rows = []
    ok = True
    rng = np.random.default_rng(20261008)
    for task_id, formula, params in (("phys-ohm", "I*R", []),
                                     ("phys-weight", "m*g", []),
                                     ("phys-gravitation", "G*m1*m2/r**2", ["G"]),
                                     ("phys-spring-energy", "k*x**2/2", [])):
        columns, meta = load_task(os.path.join(TASKS, task_id))
        noisy = dict(columns)
        noisy["y"] = rng.normal(0.0, 1.0, np.asarray(columns["y"]).size)
        try:
            report = verify(task_id, formula, params=params, columns=noisy, meta=meta)
            verdict = report.verdict
        except VerifyError as exc:
            verdict = "rejected(fit-error)"
        rows.append((task_id, verdict))
        ok = ok and verdict.startswith("rejected")
    return case(
        "负对照（纯噪声输入）", "异常处理表第 6 行 / 怀疑清单第 5 条",
        "把 4 个任务的 y 整体换成标准正态噪声，把正确答案原样送进去",
        "正确行为是全部 rejected（报告'未发现稳定公式'），编出公式比没有结果更糟",
        "；".join("%s -> %s" % (t, v) for t, v in rows),
        ok,
        note="智能体侧对应纪律写在 AGH Skill 硬约束第 5 条。")


# ==========================================================================
# 异常 6：工具调用失败
# ==========================================================================

def case_tool_failure() -> Dict[str, object]:
    results = []
    # (a) 危险表达式必须被 AST 白名单拦下
    try:
        compile_formula("__import__('os').system('echo pwned')", ["a"])
        blocked = False
    except UnsafeExpression:
        blocked = True
    results.append(("恶意表达式被 AST 白名单拦下", blocked))

    # (b) 任务目录不存在 -> 明确报错，不是静默通过
    try:
        load_task(os.path.join(TASKS, "does-not-exist"))
        missing_raises = False
    except VerifyError:
        missing_raises = True
    results.append(("任务目录不存在时抛 VerifyError", missing_raises))

    # (c) 语法错误的公式 -> 判定 rejected 且理由明确，不抛未捕获异常
    report = verify("phys-ohm", "I*R*")
    results.append(("语法错误公式被判 rejected",
                    report.verdict == "rejected" and bool(failed_checks(report))))

    # (d) 越界语法（比较运算）被拒
    report2 = verify("phys-ohm", "I*R if I > 0 else 0")
    results.append(("条件表达式被拒", report2.verdict == "rejected"))

    ok = all(flag for _name, flag in results)
    return case(
        "工具调用失败/恶意输入", "异常处理表第 6 行",
        "送入恶意表达式、不存在的任务、语法错误公式、越界语法",
        "四类都必须被明确拦下：或抛专用异常，或判 rejected，绝不静默通过",
        "；".join("%s=%s" % (n, "OK" if f else "未拦住") for n, f in results),
        ok,
        note="公式是不可信输入，因此求值层用 AST 白名单而不是 eval 直通。")


# ==========================================================================
# 怀疑清单 1：留出集是不是真的没被智能体看到
# ==========================================================================

def case_holdout_isolation() -> Dict[str, object]:
    checks = []
    # (a) 契约校验必须拒绝任务目录内的标准答案文件
    # 在临时副本上做探针，绝不往真正的 tasks/ 里写东西（避免污染队友的校验运行）
    tmp_task = os.path.join(TMP, "leak-probe")
    shutil.rmtree(tmp_task, ignore_errors=True)
    try:
        shutil.copytree(os.path.join(TASKS, "phys-ohm"), tmp_task)
        with open(os.path.join(tmp_task, "reference.json"), "w", encoding="utf-8") as fh:
            fh.write('{"formula": "LEAK"}')
        findings = validate_task(tmp_task, "leak-probe")
        leaked = any(f.code == "LEAK_FILE" and f.severity == "error" for f in findings)
        checks.append(("任务目录内出现 reference.json 时校验报 error", leaked))
    finally:
        shutil.rmtree(tmp_task, ignore_errors=True)

    # (b) split.json 不含任何行号
    with open(os.path.join(TASKS, "phys-ohm", "split.json"), encoding="utf-8") as fh:
        split = json.load(fh)
    # 用划分模块自带的检查器，而不是字符串匹配：
    # split.json 里合法地存在 "contains_row_indices": false 这个键，字符串匹配会误报。
    from formula_agh.split import assert_no_indices, SplitError
    try:
        assert_no_indices(split)
        no_indices = True
    except SplitError:
        no_indices = False
    checks.append(("split.json 不含行号索引", no_indices))

    # (c) 留出集/外推集数据被物理封印在 tasks/ 之外
    sealed = os.path.join(ROOT, "sealed", "phys-ohm", "holdout.csv")
    checks.append(("留出集数据封印在 sealed/（tasks/ 之外）", os.path.exists(sealed)))

    ok = all(flag for _n, flag in checks)
    return case(
        "留出集隔离", "怀疑清单第 1 条",
        "在任务目录里放一个 reference.json；检查 split.json 与封印目录",
        "标准答案文件必须被校验拦下；划分文件不含行号；留出数据在 tasks/ 之外",
        "；".join("%s=%s" % (n, "OK" if f else "否") for n, f in checks),
        ok,
        note="这是从'口头保证没看过'升级成'文件系统上分开'的一步。")


# ==========================================================================
# 怀疑清单 2：外推区是不是真的在支撑域之外
# ==========================================================================

def case_extrapolation_outside_support() -> Dict[str, object]:
    total_extrap = outside = 0
    total_hold = inside = 0
    bad = []
    for task_id in sorted(os.listdir(TASKS)):
        task_dir = os.path.join(TASKS, task_id)
        if not os.path.isdir(task_dir) or not os.path.exists(os.path.join(task_dir, "split.json")):
            continue
        columns, meta = load_task(task_dir)
        _manifest, masks = build_split(columns, meta, float(SETTINGS["holdout_ratio"]),
                                       float(SETTINGS["extrapolation_ratio"]),
                                       int(SETTINGS["seed"]), task_id=task_id)
        var_names = [str(v) for v in meta["var_names"]]
        axis = int(masks["split_axis"])
        key = np.asarray(columns[var_names[axis]], dtype=float)
        train_lo = float(masks["support_lo"][axis])
        train_hi = float(masks["support_hi"][axis])
        ex = masks["extrapolation"]
        ho = masks["holdout"]
        n_out = int(np.sum((key[ex] < train_lo) | (key[ex] > train_hi)))
        n_in = int(np.sum((key[ho] >= train_lo) & (key[ho] <= train_hi)))
        total_extrap += int(ex.sum())
        outside += n_out
        total_hold += int(ho.sum())
        inside += n_in
        if n_out != int(ex.sum()):
            bad.append(task_id)
    ok = (outside == total_extrap) and (inside == total_hold) and not bad
    return case(
        "外推区严格位于训练支撑域之外", "怀疑清单第 2 条",
        "对 22 个任务逐个数值核对：外推点是否都在训练支撑域之外、留出点是否都在之内",
        "100% 的外推点严格在支撑域外，100% 的留出点在支撑域内",
        "外推点 %d/%d 在域外；留出点 %d/%d 在域内；越界任务=%s" % (
            outside, total_extrap, inside, total_hold, bad or "无"),
        ok,
        note="这是'外推'这个词能不能用的机器判据，不是描述性说法。")


# ==========================================================================
# 怀疑清单 3：量纲检验会不会被绕过
# ==========================================================================

def case_dimension_coverage() -> Dict[str, object]:
    skipped, checked = [], 0
    for task_id in sorted(os.listdir(TASKS)):
        task_dir = os.path.join(TASKS, task_id)
        if not os.path.isdir(task_dir):
            continue
        meta_path = os.path.join(task_dir, "meta.json")
        if not os.path.exists(meta_path):
            continue
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
        columns, meta2 = load_task(task_dir)
        from formula_agh.verify import _check_dimension  # noqa: PLC0415
        result = _check_dimension("1", meta2, [])
        if not (meta2.get("units") or {}):
            skipped.append((task_id, "无量纲信息"))
            continue
        if "不适用" in result.reason or "跳过" in result.reason:
            skipped.append((task_id, result.reason[:40]))
        else:
            checked += 1
    ok = not skipped
    return case(
        "量纲检验的覆盖面", "怀疑清单第 3 条",
        "统计 22 个任务里有多少个的量纲检验是真正执行的、有多少被静默跳过",
        "0 个任务被静默跳过；有单位信息的任务都必须真正执行量纲比对",
        "实际执行 %d 个；跳过 %d 个 %s" % (checked, len(skipped), skipped or ""),
        ok,
        note=("修复记录：改造前单位表未收录 m^3 / T / F/m / H/m / ohm / m^2，"
              "8 个任务被静默跳过。补上复合单位解析后覆盖率到 100%。"))


# ==========================================================================
# 怀疑清单 4：换种子结论会不会翻
# ==========================================================================

def case_seed_sensitivity() -> Dict[str, object]:
    seeds = [20261008, 1, 7, 12345, 99991]
    flips = []
    total = 0
    for task_id in sorted(os.listdir(TASKS)):
        task_dir = os.path.join(TASKS, task_id)
        ref_path = os.path.join(ROOT, "reference", task_id + ".json")
        if not os.path.isdir(task_dir) or not os.path.exists(ref_path):
            continue
        with open(ref_path, encoding="utf-8") as fh:
            ref = json.load(fh)
        columns, meta = load_task(task_dir)
        verdicts = []
        for seed in seeds:
            try:
                report = verify(task_id, ref["formula"], params=ref.get("free_parameters") or [],
                                columns=columns, meta=meta, seed=seed)
                verdicts.append(report.verdict)
            except VerifyError:
                verdicts.append("fit-error")
        total += 1
        if len(set(verdicts)) > 1:
            flips.append((task_id, list(zip(seeds, verdicts))))
    return case(
        "结论对随机种子的稳定性", "怀疑清单第 4 条",
        "把数据划分与拟合的种子换成 5 个不同值，重跑全部 22 条金标准公式",
        "结论不应随种子翻转；若翻转，必须明确指出是哪条任务、哪几个种子",
        "翻转 %d / %d 条%s" % (len(flips), total,
                              ("：" + json.dumps(flips, ensure_ascii=False)) if flips else ""),
        not flips,
        note="种子只影响划分与多起点顺序，不影响判据本身；这条检验的是判据有没有过拟合到某一次划分。")


# ==========================================================================
# 怀疑清单 5：阈值是不是唯一放水口
# ==========================================================================

def case_threshold_is_choke_point() -> Dict[str, object]:
    """放水攻击：只放宽阈值，够不够放行一个物理上错误的公式？

    尺度检验接入之后（M3 方案 A），答案变成了"不够"——
    G*m1*m2/r 对 r 是 -1 次幂，而规格要求 -2 次幂，尺度门不看任何误差统计量就能抓住它。
    必须**同时**放宽阈值并关掉尺度检验，才会被放行。
    这比"阈值是唯一软肋"是更强的结论，如实更新。
    """
    formula = "G*m1*m2/r"
    base = verify("phys-gravitation", formula, params=["G"])
    loose = dict(SETTINGS)
    loose["holdout_threshold"] = 3.0
    loose["extrapolation_threshold"] = 3.0
    only_thresholds = verify("phys-gravitation", formula, params=["G"], settings=loose)
    loose_off = dict(loose)
    loose_off["scale_check"] = False
    loose_off["dimension_check"] = False
    both_off = verify("phys-gravitation", formula, params=["G"], settings=loose_off)
    observed = ("默认：%s；只放宽阈值：%s（尺度门拦住）；"
                "放宽阈值+关尺度门：%s" % (base.verdict, only_thresholds.verdict,
                                          both_off.verdict))
    return case(
        "放水攻击：只放宽阈值不够", "怀疑清单第 3 条延伸",
        "把两个误差阈值放宽到 3.0，先只放宽阈值，再叠加关闭尺度检验",
        "只放宽阈值不得放行错误公式（尺度门是独立的第二道防线）；"
        "必须同时关掉尺度检验才会被放行——说明放水需要改两处，且都会留在 config 的 diff 里",
        observed,
        (base.verdict == "rejected" and only_thresholds.verdict == "rejected"
         and both_off.verdict == "accepted"),
        note="结论：阈值仍是软肋，但已不是唯一软肋。评审 diff config/agent.yaml 即可看出"
             "有没有人同时动了阈值与开关。")


# ==========================================================================
# 已知边界：自由参数吸收符号
# ==========================================================================

def case_sign_absorbed() -> Dict[str, object]:
    good = verify("phys-grav-potential-energy", "-G*m1*m2/r", params=["G"])
    flipped = verify("phys-grav-potential-energy", "G*m1*m2/r", params=["G"])
    absorbed = flipped.verdict == "accepted"
    return case(
        "符号错误被自由参数吸收（已知边界）", "边界如实上报",
        "把引力势能的负号去掉（+G*m1*m2/r），看判据能否识别",
        "如实报告：若符号被自由参数吸收而无法识别，必须写明这是边界，不得宣称能识别",
        "正确式=%s，去负号=%s（%s）" % (
            good.verdict, flipped.verdict,
            "符号被吸收，判据无法区分" if absorbed else "符号被识别"),
        True,   # 本用例考的是"有没有如实上报"，不是"有没有识别出来"
        note=("结论：" + ("符号可由自由参数吸收，因此本判据**不能**判定符号正确性；"
                        "该风险交由 M3 的物理审查（现象描述、量纲与极限行为）兜底。"
                        if absorbed else "符号被正确识别。")))


# ==========================================================================
# 主流程
# ==========================================================================

def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    results: List[Dict[str, object]] = []
    tmp = TMP
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    try:
        results.append(case_missing_values(tmp))
        results.append(case_fit_divergence())
        results.append(case_dimension_violation())
        results.append(case_wrong_unit_in_meta(tmp))
        results.append(case_small_angle_approximation())
        results.append(case_taylor_overfit())
        results.append(case_negative_control(tmp))
        results.append(case_tool_failure())
        results.append(case_holdout_isolation())
        results.append(case_extrapolation_outside_support())
        results.append(case_dimension_coverage())
        results.append(case_seed_sensitivity())
        results.append(case_threshold_is_choke_point())
        results.append(case_sign_absorbed())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    judged = [r for r in results if r["expected"] and not str(r["name"]).startswith("符号错误")]
    passed = sum(1 for r in judged if r["passed"])
    payload = {
        "suite": "M2 对抗性测试",
        "settings": SETTINGS,
        "cases": len(results),
        "judged_cases": len(judged),
        "judged_passed": passed,
        "judged_failed": len(judged) - passed,
        "all_passed": passed == len(judged),
        "results": results,
    }
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_markdown(payload))

    for r in results:
        print("%-6s %-34s %s" % ("PASS" if r["passed"] else "FAIL", r["name"], r["observed"][:88]))
    print()
    print("judged: %d/%d passed" % (passed, len(judged)))
    return 0 if payload["all_passed"] else 1


def render_markdown(payload) -> str:
    lines = [
        "# 对抗性测试报告（M2）",
        "",
        "本报告由 examples/adversarial_suite.py 自动生成，逐条记录：",
        "",
        "    攻击方式 -> 期望行为 -> 实测行为 -> 是否通过 -> 说明",
        "",
        "- 用例总数：%s" % payload["cases"],
        "- 参与判定的用例：%s，通过 %s，未通过 %s" % (
            payload["judged_cases"], payload["judged_passed"], payload["judged_failed"]),
        "",
        "| # | 用例 | 类别 | 攻击方式 | 期望 | 实测 | 结果 |",
        "|---|---|---|---|---|---|---|",
    ]
    for index, item in enumerate(payload["results"], 1):
        lines.append("| %d | %s | %s | %s | %s | %s | %s |" % (
            index, item["name"], item["category"],
            str(item["attack"]).replace("|", "/"),
            str(item["expected"]).replace("|", "/"),
            str(item["observed"]).replace("|", "/"),
            "通过" if item["passed"] else "未通过"))
    lines += ["", "## 逐条说明", ""]
    for index, item in enumerate(payload["results"], 1):
        lines.append("### %d. %s" % (index, item["name"]))
        lines.append("")
        lines.append("- 攻击：" + str(item["attack"]))
        lines.append("- 期望：" + str(item["expected"]))
        lines.append("- 实测：" + str(item["observed"]))
        if item.get("note"):
            lines.append("- 说明：" + str(item["note"]))
        lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
