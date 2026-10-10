# -*- coding: utf-8 -*-
"""一键复现（M2 交付 6/8）。

验收标准（对应分工表 10-12）
---------------------------
"在干净目录下执行成功，输出与历史记录一致。"

用法
----
    python reproduce.py                     # 在当前目录跑完整流水线并与基线比对
    python reproduce.py --update-baseline   # 首次运行：把当前结果固化为基线
    python reproduce.py --clean D:\repro     # 先把仓库复制到干净目录，再在那里跑
    python reproduce.py --skip-clean-copy   # 只跑，不复制

为什么不是"一张命令清单"
------------------------
复现的难点不是"命令能不能跑"，而是"跑出来的东西是不是同一个东西"。
所以本脚本每一步都产出**指纹**，最后与 expected/reproduction_baseline.json 逐字段比对：

    差异 0 处  -> 复现成功（退出码 0）
    差异 N 处  -> 明确指出哪个任务的哪个字段对不上（退出码 1），不笼统说"失败"

指纹只取 6 位有效数字并显式四舍五入，避免浮点末位噪声造成假阳性。

环境差异不算失败
----------------
指纹里有两类东西：**结论**（tasks / splits / runs / scoring / adversarial / ...）与
**环境**（python 版本、numpy 版本、操作系统）。只有结论判成败：换一台机器、换一个
解释器，只要逐条判定与指标一字不差，就是复现成功，环境差异照常打印出来备查。
需要连环境也逐字比对的场合（维护者重建基线、在基准解释器上做验收）加 --strict-env，
此时环境差异按失败处理。
"""
from __future__ import annotations

import argparse
import filecmp
import json
import os
import platform
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))

BASELINE = os.path.join(HERE, "expected", "reproduction_baseline.json")
# 只排除"由流水线生成"的东西与本地环境。源码目录（含队友的 physics/ 等）一律带入，
# 否则干净目录里跑出来的不是同一套东西。
EXCLUDE_DIRS = {"runs", "evidence", "recheck", "sealed", "superseded", "__pycache__",
                ".venv", "venv", ".git", "_m3", "_adversarial_tmp", "_contract_tmp",
                "_isolation_tmp"}

# 绝不带进干净目录的文件。.env 里是密钥：
# 干净复现目录经常被整个打包发给别人，把密钥复制进去等于把密钥交出去。
# 这条是加 .env 时差点漏掉的——所以用"黑名单文件"显式挡住，并同步更新 .gitignore。
EXCLUDE_FILES = {".env", ".env.local", ".env.production"}


class StepFailed(RuntimeError):
    """某个步骤以非预期退出码结束——流水线必须立刻停，而不是继续跑完再说。"""


def run_step(name, args, cwd, timeout=1800, expect=(0, 1)):
    """执行一个步骤，并按 expect 校验退出码。

    为什么要有 expect 与 fail-fast（外部审计 2026-10-10 的建议）：
    原实现对任何非零退出只**记录**不终止，于是某一步崩掉之后，后面所有依赖它的步骤
    都在残缺输入上继续跑，最后拿一个"指纹不一致"的结论收场——真实原因（哪一步崩了）
    被埋在一屏日志里。退出码 1 是"检查未通过"的正常语义，所以默认允许 0 与 1；
    其余（2 及以上、超时、异常）一律立刻终止，并打印非零退出。
    """
    cmd = [sys.executable, "-X", "utf8"] + args
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(cwd, "src")
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        print("  [%s] 超时（%ds）——终止复现" % (name, timeout))
        raise StepFailed("步骤 %s 超时" % name)
    except OSError as exc:
        print("  [%s] 无法启动：%s——终止复现" % (name, exc))
        raise StepFailed("步骤 %s 无法启动" % name)
    tail = (proc.stdout or "").strip().splitlines()[-3:]
    line = "  [%s] %s (exit=%d)" % (name, " | ".join(tail)[:150], proc.returncode)
    print(line)
    if proc.returncode not in expect:
        err = (proc.stderr or "").strip().splitlines()[-12:]
        for item in err:
            print("        stderr| " + item[:160])
        print("  [%s] 非预期退出码 %d（期望 %s）——终止复现，后续步骤不再执行"
              % (name, proc.returncode, "/".join(str(v) for v in expect)))
        raise StepFailed("步骤 %s 退出码 %d" % (name, proc.returncode))
    if not tail:
        err = (proc.stderr or "").strip().splitlines()[-8:]
        for item in err:
            print("        stderr| " + item[:160])
    return proc


def _round(value, digits=6):
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return str(value)
        return float("%.*g" % (digits, value))
    return value


def fingerprint(root):
    """采集整条流水线的可比对指纹。"""
    # other_runs 只用于打印提示，不进指纹：干净目录里它必然是 0，
    # 而共享工作区里它随队友的实验变化。它不描述"我们复现得对不对"。
    fp = {"environment": {}, "tasks": [], "splits": {}, "runs": {}, "scoring": {},
          "adversarial": {}, "manifest_integrity": {},
          "discrimination": {}, "negative_control": {}}

    import numpy
    from formula_agh import __version__
    fp["environment"] = {
        "engine_version": __version__,
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "platform": platform.system(),
    }

    tasks_root = os.path.join(root, "tasks")
    if os.path.isdir(tasks_root):
        fp["tasks"] = sorted(d for d in os.listdir(tasks_root)
                             if os.path.isdir(os.path.join(tasks_root, d)))

    for task_id in fp["tasks"]:
        split_file = os.path.join(tasks_root, task_id, "split.json")
        if not os.path.exists(split_file):
            continue
        with open(split_file, encoding="utf-8") as fh:
            split = json.load(fh)
        fp["splits"][task_id] = {
            "counts": split.get("counts"),
            "seed": (split.get("rule") or {}).get("seed"),
            "fingerprint": {k: str(v.get("sha256"))[:16]
                            for k, v in (split.get("fingerprint") or {}).items()},
        }

    # 只把"本流水线自己产出的运行"纳入指纹：
    #   refcheck-*  金标准自检
    #   variant-*   判别力
    #   *-candNN    候选式批量验证
    # 队友的产出（scale-*、discrim-*、extrap-* 等）由另外的判定套件生成，
    # 会随时增减；把它们混进指纹会让"复现"变成"工作区没被人动过"，
    # 那不是我们要检验的东西。它们的存在情况记录在 other_runs 里备查。
    runs_root = os.path.join(root, "runs")
    # 注意用 search 而不是 match：re.match 只在字符串开头尝试，
    # 写成 "^(refcheck-|variant-)|(-cand\d+$)" 时后半段永远不会命中，
    # 候选运行会被静默排除在指纹之外——那正是最该被复现覆盖的一层。
    #
    # 前缀说明：refcheck/variant 是 M2 的金标准与判别力；-candNN 是候选式批量；
    # scale-ref/scale-variant 是 M3 的尺度检验；discrim- 是 M3 的判别力报告；
    # negctl- 是 M3 的负对照。既然流水线会重新生成它们，就都纳入指纹。
    owned = re.compile(r"^(refcheck-|variant-|scale-ref-|scale-variant-|discrim-|negctl-)"
                       r"|-cand\d+$")
    other_runs = []
    if os.path.isdir(runs_root):
        for run_id in sorted(os.listdir(runs_root)):
            run_dir = os.path.join(runs_root, run_id)
            if not os.path.isdir(run_dir):
                continue
            if not owned.search(run_id):
                other_runs.append(run_id)
                continue
            result_file = os.path.join(run_dir, "result.json")
            if not os.path.exists(result_file):
                continue
            with open(result_file, encoding="utf-8") as fh:
                result = json.load(fh)
            checks = {}
            for check in result.get("checks") or []:
                metrics = check.get("metrics") or {}
                checks[check["name"]] = {
                    "passed": bool(check.get("passed")),
                    "relative_error_median": _round(metrics.get("relative_error_median")),
                }
            fp["runs"][run_id] = {
                "task_id": result.get("task_id"),
                "verdict": result.get("verdict"),
                "formula": result.get("formula"),
                "checks": checks,
            }
            manifest = os.path.join(run_dir, "manifest.sha256")
            if os.path.exists(manifest):
                from formula_agh.evidence import verify_manifest
                fp["manifest_integrity"][run_id] = bool(verify_manifest(run_dir).get("ok"))

    scoring_file = os.path.join(root, "evidence", "scoring", "comparison.json")
    if os.path.exists(scoring_file):
        with open(scoring_file, encoding="utf-8") as fh:
            payload = json.load(fh)
        summary = payload.get("summary") or {}
        # 「智能体发现」层刻意**不进指纹**：它由真实 AGH 会话产生，
        # 需要 AGH 实例 + 模型凭据 + 会话授权才能复现，而本流水线不含这三样。
        # 把它算进指纹，等于要求"干净目录里也必须有 AGH 运行"，那是另一回事。
        # 它单独记录、单独汇报，见 agent_layer。
        # 这些字段取决于工作区里有没有 AGH 产生的运行（本机有、干净目录没有），
        # 因此必须排除出指纹，否则"干净复现"会必然报差异。
        # 教训（2026-10-10）：新增 agent_candidates_bound / _unbound 等绑定字段时漏加到这里，
        # 干净 clone 立刻报 /scoring/agent_candidates_unbound: 22 != 0。
        agent_keys = {"agent_candidates", "agent_accepted", "agent_matches_reference",
                      "agent_match_rate",
                      "agent_candidates_bound", "agent_candidates_unbound",
                      "agent_matches_reference_bound", "agent_match_rate_bound"}
        fp["scoring"] = {k: _round(v) for k, v in summary.items()
                         if k != "by_layer" and k not in agent_keys}
        by_layer = {}
        for layer, bucket in (summary.get("by_layer") or {}).items():
            # 空桶（tasks == 0）不带信息，只反映"本工作区多跑了别的套件"：
            # scoring 会给每个出现过的 layer 建桶，而本机 runs/ 里有 extrap-* 等
            # 非流水线运行，于是多出一个 unknown 桶，干净目录里没有。
            # 教训（2026-10-10）：不剔除空桶，干净 clone 报 /scoring/by_layer/unknown 缺失。
            if int(bucket.get("tasks") or 0) == 0:
                continue
            by_layer[layer] = {k: v for k, v in bucket.items()
                               if k not in ("agent_match", "agent_total")}
        fp["scoring"]["by_layer"] = by_layer
        agent_layer = {
            "candidates": summary.get("agent_candidates"),
            "matches_reference": summary.get("agent_matches_reference"),
            "bound": summary.get("agent_candidates_bound"),
            "unbound": summary.get("agent_candidates_unbound"),
            "note": ("由真实 AGH 会话产生，需要 AGH 实例与凭据，不在本流水线复现范围内；"
                     "它的证据是 runs/<run_id>/ 与 AGH 的会话导出"),
        }

    adv_file = os.path.join(root, "evidence", "adversarial", "report.json")
    if os.path.exists(adv_file):
        with open(adv_file, encoding="utf-8") as fh:
            payload = json.load(fh)
        fp["adversarial"] = {item["name"]: bool(item["passed"])
                             for item in payload.get("results") or []}

    disc_file = os.path.join(root, "evidence", "discrimination.json")
    if os.path.exists(disc_file):
        with open(disc_file, encoding="utf-8") as fh:
            disc = json.load(fh)
        fp["discrimination"] = {
            "reference_count": disc.get("reference_count"),
            "wrong_count": disc.get("wrong_count"),
            "buckets": disc.get("buckets"),
        }

    neg_file = os.path.join(root, "evidence", "negative-control", "negative_control.json")
    if os.path.exists(neg_file):
        with open(neg_file, encoding="utf-8") as fh:
            neg = json.load(fh)
        summary = neg.get("summary") or {}
        fp["negative_control"] = {k: _round(v) for k, v in summary.items()
                                  if not isinstance(v, (list, dict))}

    return fp, len(other_runs), agent_layer


def diff_fingerprints(expected, actual, path=""):
    diffs = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in expected:
                diffs.append(path + "/" + str(key) + ": 新增 " + repr(actual[key])[:60])
            elif key not in actual:
                diffs.append(path + "/" + str(key) + ": 缺失（基线为 " + repr(expected[key])[:60] + "）")
            else:
                diffs.extend(diff_fingerprints(expected[key], actual[key], path + "/" + str(key)))
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            diffs.append("%s: 长度 %d != %d" % (path, len(expected), len(actual)))
        else:
            for index, (a, b) in enumerate(zip(expected, actual)):
                diffs.extend(diff_fingerprints(a, b, "%s[%d]" % (path, index)))
    elif expected != actual:
        diffs.append("%s: %r != %r" % (path, expected, actual))
    return diffs


def split_environment_diffs(diffs):
    """把指纹差异分成（结论差异, 环境差异）。

    python/numpy 版本与操作系统属于**复现环境**；tasks / splits / runs / scoring /
    adversarial 才是**结论**。只有结论判成败：换台机器、换个解释器，只要逐条判定与
    指标一字不差就是复现成功。把两者混在同一次比对里，会把这种成功判成失败——
    那是把环境当结论。真实事故：基线固化于 python 3.12.14 / numpy 2.3.5，
    照 README 用本机的 3.13.5 / 2.4.6 跑，15 步全过、指纹逐字段相同，却报「复现失败」。
    """
    env = [d for d in diffs if d.startswith("/environment/")]
    hard = [d for d in diffs if not d.startswith("/environment/")]
    return hard, env


def copy_clean(source, dest):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest, exist_ok=True)
    for name in sorted(os.listdir(source)):
        src = os.path.join(source, name)
        if os.path.isdir(src):
            if name in EXCLUDE_DIRS:
                continue
            shutil.copytree(src, os.path.join(dest, name),
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            if name in EXCLUDE_FILES:
                continue
            shutil.copy2(src, os.path.join(dest, name))
    print("  已复制到干净目录：" + dest)
    print("  已排除目录：" + ", ".join(sorted(EXCLUDE_DIRS)))
    print("  已排除文件：" + ", ".join(sorted(EXCLUDE_FILES)) + "（密钥不入副本）")
    # 防回归：如果干净目录里出现了密钥文件，直接报错，不要静默放过。
    leaked = sorted(f for f in EXCLUDE_FILES if os.path.exists(os.path.join(dest, f)))
    if leaked:
        raise RuntimeError("干净目录里出现了本不该复制的文件：" + ", ".join(leaked))


def main(argv=None):
    parser = argparse.ArgumentParser(description="FORMULA-AGH 一键复现")
    parser.add_argument("--clean", default="", help="先复制到该干净目录再复现")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--baseline", default=BASELINE)
    parser.add_argument("--skip-steps", action="store_true", help="只比对指纹，不重跑")
    parser.add_argument("--strict-env", action="store_true",
                        help="把 python/numpy/系统差异也当作复现失败（默认只提示）")
    args = parser.parse_args(argv)

    root = HERE
    if args.clean:
        copy_clean(HERE, args.clean)
        root = os.path.abspath(args.clean)

    if not args.skip_steps:
        print("第一步：数据契约校验")
        run_step("validate-tasks",
                 ["-m", "formula_agh", "validate-tasks", "--tasks", "tasks",
                  "--reference", "reference", "--require-split", "--strict",
                  "--report", "evidence/contract_report.json"], root)
        print("第二步：三段划分落盘与物理封印（干净目录里 sealed/ 不存在，必须能重建）")
        run_step("split-build",
                 ["-m", "formula_agh", "split", "--tasks", "tasks", "--sealed", "sealed",
                  "--report", "evidence/split_report.json"], root)
        print("第三步：划分一致性（重算并与 split.json 逐位比对）")
        run_step("split-check",
                 ["-m", "formula_agh", "split", "--tasks", "tasks", "--check",
                  "--report", "evidence/split_check.json"], root)
        print("第四步：单元测试")
        run_step("tests", ["run_tests.py"], root)
        print("第五步：金标准自检（标准答案必须被接受）")
        run_step("reference_check", ["examples/reference_check.py"], root)
        print("第六步：判别力（结构错误的候选必须被拒绝）")
        run_step("variant_check", ["examples/variant_check.py"], root)
        print("第七步：候选式批量验证（生成智能体候选层，供评分脚本对照）")
        run_step("batch", ["-m", "formula_agh", "batch", "--tasks", "tasks",
                           "--out", "runs"], root)
        # 以下四步来自 M3《交叉评审发现》发现 2：
        # 换判定口径会让某些结论翻转，所以判别力必须跟着一起重跑，
        # 而不是只改阈值。四个脚本都不需要人工判断，适合进流水线。
        print("第八步：判别力报告（金标准 vs 结构错误式，M3 维护）")
        run_step("discrimination", ["examples/discrimination_report.py"], root)
        print("第九步：尺度检验——参考公式应全部通过")
        run_step("scale-ref", ["examples/scale_check_all.py"], root)
        print("第十步：尺度检验——错误候选式应全部被否决")
        run_step("scale-variant", ["examples/scale_check_all.py", "--variants"], root)
        print("第十一步：负对照实验（纯噪声下不得编造公式）")
        run_step("negative-control", ["examples/negative_control.py"], root)
        print("第十二步：对抗性测试")
        run_step("adversarial", ["examples/adversarial_suite.py"], root)
        print("第十三步：独立复算（对每条运行重新划分、重新拟合、重新判定）")
        run_step("recheck", ["-m", "formula_agh", "recheck", "--runs", "runs",
                             "--tasks", "tasks", "--out", "recheck"], root)
        print("第十四步：与标准答案对照（评分，独立于智能体）")
        run_step("scoring",
                 ["src/scoring/compare.py", "--runs", "runs", "--tasks", "tasks",
                  "--reference", "reference", "--out", "evidence/scoring"], root)
        print("第十五步：证据归档与孤儿检测")
        run_step("archive", ["-m", "formula_agh", "archive", "--runs", "runs",
                             "--out", "evidence"], root)
        # 提示泄漏审计进流水线：它量化"智能体可见面泄漏了多少定律信息"。
        # 放进来的理由——这条数字支撑 README 里"带先验的已知定律恢复"这个自我限定，
        # 如果只手工跑过一次，之后任务集改了它就会悄悄失真。它只写
        # evidence/hint_leak_audit.json，不进指纹，因此不影响复现判定。
        print("第十六步：提示泄漏审计（智能体可见面泄漏了什么）")
        run_step("hint-audit", ["examples/hint_audit.py"], root)
        # 交付报告也进流水线：外推崩溃分析 / 判别力与阈值敏感性 / 失败案例档案 /
        # 标准答案一致性审查，全部从前面各步已经产生的证据里重建。
        # 之前这几份报告"标着完成但文件不在仓库里"（外部审计的数字核验项），
        # 放进流水线才能保证它们与证据始终一致、不会再次过期。
        print("第十七步：重建交付报告（外推分析 / 判别力与阈值敏感性 / 失败档案 / 答案审查）")
        run_step("delivery-reports", ["examples/make_delivery_reports.py"], root)

    print("采集指纹 ...")
    actual, other_runs, agent_layer = fingerprint(root)
    print("  本流水线运行 %d 条；另有 %d 条由其它判定套件产出（不计入复现范围）"
          % (len(actual["runs"]), other_runs))
    print("  智能体发现层：候选 %s 条，与标准答案一致 %s 条（需 AGH 环境，不在复现范围）"
          % (agent_layer.get("candidates"), agent_layer.get("matches_reference")))

    if args.update_baseline:
        os.makedirs(os.path.dirname(args.baseline), exist_ok=True)
        with open(args.baseline, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(actual, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
        print("基线已写入：" + args.baseline)
        print("  任务 %d，运行 %d，对抗用例 %d" % (
            len(actual["tasks"]), len(actual["runs"]), len(actual["adversarial"])))
        return 0

    if not os.path.exists(args.baseline):
        print("没有基线文件，先运行 --update-baseline。")
        return 2
    with open(args.baseline, encoding="utf-8") as fh:
        expected = json.load(fh)

    diffs = diff_fingerprints(expected, actual)
    # 「环境」与「结论」分开算。python/numpy 版本是复现环境，结论由 tasks/ splits/ runs/
    # scoring/ 里的逐条判定与指标决定。把版本号混进同一次比对，会把"换台机器、结果一字
    # 不差"判成复现失败——那是把环境当结论：照 README 换一个解释器就报失败，而我们明明
    # 复现成功了。所以环境差异照常采集、照常打印，默认不判失败；要严格比对加 --strict-env。
    hard_diffs, env_diffs = split_environment_diffs(diffs)
    if args.strict_env:                      # 维护者模式：环境也必须逐字相同
        hard_diffs = hard_diffs + env_diffs
        env_diffs = []
    print()
    print("=" * 72)
    if not hard_diffs:
        if env_diffs:
            print("复现成功：结论逐位一致；另有 %d 处环境差异（不影响判定）。" % len(env_diffs))
        else:
            print("复现成功：指纹与基线完全一致。")
        print("  任务 %d 个，本流水线运行 %d 条，对抗用例 %d 项，全部逐位一致。" % (
            len(actual["tasks"]), len(actual["runs"]), len(actual["adversarial"])))
        for line in env_diffs:
            print("  - 环境：" + line)
        if env_diffs:
            exp_env = expected.get("environment") or {}
            act_env = actual.get("environment") or {}
            print("  基线环境：python %s / numpy %s / %s；本次环境：python %s / numpy %s / %s"
                  % (exp_env.get("python"), exp_env.get("numpy"), exp_env.get("platform"),
                     act_env.get("python"), act_env.get("numpy"), act_env.get("platform")))
            print("  要环境也逐字相同：用基线记录的解释器重跑；要把它当失败：加 --strict-env。")
        bad_manifest = [k for k, v in (actual.get("manifest_integrity") or {}).items() if not v]
        if bad_manifest:
            print("  注意：以下运行的 SHA256 清单不完整 -> " + ", ".join(sorted(bad_manifest)))
        print("=" * 72)
        return 0
    print("复现失败：与基线有 %d 处差异。" % len(hard_diffs))
    for line in hard_diffs[:40]:
        print("  - " + line)
    if len(hard_diffs) > 40:
        print("  ... 另有 %d 处" % (len(hard_diffs) - 40))
    if env_diffs:
        print("  另：本次还换了复现环境（默认不算差异，但可能是上面差异的原因）：")
        for line in env_diffs:
            print("  - " + line)
    print("=" * 72)
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except StepFailed as exc:
        # 分步 fail-fast 的终点：把"哪一步崩了"讲清楚，而不是甩一段 traceback。
        print("")
        print("=" * 72)
        print("复现中止：" + str(exc))
        print("  某一步以非预期退出码结束（或超时/无法启动），后续步骤没有执行，")
        print("  因此**没有**产生可比对的指纹——不要把它读成'复现结果不一致'。")
        print("  上面标注 [步骤名] 的那一行是失败点，紧随其后的 stderr| 行是它的错误输出。")
        print("=" * 72)
        sys.exit(2)
