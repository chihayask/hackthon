# -*- coding: utf-8 -*-
"""生成盲化任务集：把"点名定律"的那部分信息从智能体可见面拿掉。

为什么需要它（外部审计 2026-10-10 第 3 条 + hint_audit 的实测）：
22/22 个任务的可见面同时泄漏四类结构信息——任务名含现象词、phenomenon 文本写着定律、
source 链接直指定律条目、units 暴露量纲结构；物理规格里的 physics_note 更是把公式
直接写了出来。在这种输入下跑出来的结果，准确称谓是「带物理先验的已知定律恢复」，
而不是「从数据中发现」。要做去提示消融，先得有一个盲化过的任务集。

本脚本只做**派生**，不改动原任务集：
  blind/tasks/<anon>/          智能体可见面（meta 已去除 phenomenon/source，id 已匿名）
  blind/reference/<anon>.json  评分侧标准答案（formula 保留，只有评分脚本该看）
  blind/physics/scale_specs.json  物理规格（键已匿名，physics_note 已中性化）
  blind/mapping.json           匿名 id -> 真实 id 的映射，**不得进入智能体可见面**

严格档（--level strict）另外去掉 units，令量纲门降级为 skipped，得到"纯数据"支路。
注意：尺度反馈本身也会泄漏目标幂次（检验理由里会写"要求 -2"），
要跑"完全无先验"支路，运行验证时再加 --no-scale-check。"""
import argparse
import hashlib
import json
import os
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
LEVELS = ("metadata", "strict")
NEUTRAL_NOTE = "（盲化：本条物理规格的说明文字已移除，避免泄漏定律名称与函数结构）"


def anon_id(real_id: str) -> str:
    digest = hashlib.sha1(real_id.encode("utf-8")).hexdigest()[:8]
    return "t-" + digest


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _dump(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def build(out_root: str, level: str = "metadata") -> dict:
    if level not in LEVELS:
        raise SystemExit("level 必须是 " + "/".join(LEVELS))
    tasks_root = os.path.join(ROOT, "tasks")
    ref_root = os.path.join(ROOT, "reference")
    mapping = {}
    removed_fields = set()

    for name in sorted(os.listdir(tasks_root)):
        task_dir = os.path.join(tasks_root, name)
        if not os.path.isfile(os.path.join(task_dir, "meta.json")):
            continue
        anon = anon_id(name)
        dst = os.path.join(out_root, "tasks", anon)
        os.makedirs(dst, exist_ok=True)
        for fname in ("data.csv", "data_train.csv"):
            src = os.path.join(task_dir, fname)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dst, fname))

        meta = _load(os.path.join(task_dir, "meta.json"))
        for field in ("phenomenon", "source", "source_note", "domain"):
            if field in meta:
                meta.pop(field)
                removed_fields.add(field)
        # 契约要求 source 必填（可追溯出处）。盲化集不能指向真实出处（会点名定律），
        # 因此改指向评审侧映射文件；它不是 URL，契约会给 SOURCE_NOT_URL 警告——
        # 这是**设计如此**：盲化集用非严格模式校验，警告本身就是"来源在评审侧"的提示。
        meta["source"] = ["blind-set: 真实出处见 blind/mapping.json（评审侧，不进入智能体可见面）"]
        if level == "strict":
            for field in ("units",):
                if field in meta:
                    meta.pop(field)
                    removed_fields.add(field)
        meta["task_id"] = anon
        meta["blinded"] = {"level": level,
                           "note": "本任务集为盲化派生集，原任务标识与现象说明已移除"}
        _dump(os.path.join(dst, "meta.json"), meta)

        split_src = os.path.join(task_dir, "split.json")
        if os.path.isfile(split_src):
            split = _load(split_src)
            split["task_id"] = anon
            _dump(os.path.join(dst, "split.json"), split)

        # 封印数据（留出集/外推集）也要带过去并改名：验证引擎需要它才能划分。
        sealed_src = os.path.join(ROOT, "sealed", name)
        if os.path.isdir(sealed_src):
            sealed_dst = os.path.join(out_root, "sealed", anon)
            os.makedirs(sealed_dst, exist_ok=True)
            for fname in os.listdir(sealed_src):
                src = os.path.join(sealed_src, fname)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(sealed_dst, fname))
                    if fname.endswith(".json"):
                        try:
                            payload = _load(src)
                            if isinstance(payload, dict) and "task_id" in payload:
                                payload["task_id"] = anon
                                _dump(os.path.join(sealed_dst, fname), payload)
                        except (OSError, ValueError):
                            pass

        ref_src = os.path.join(ref_root, name + ".json")
        if os.path.isfile(ref_src):
            ref = _load(ref_src)
            ref["task_id"] = anon
            ref.pop("source", None)
            _dump(os.path.join(out_root, "reference", anon + ".json"), ref)

        mapping[anon] = {"real_id": name, "formula_hidden": True}

    specs_src = os.path.join(ROOT, "physics", "scale_specs.json")
    if os.path.isfile(specs_src):
        specs = _load(specs_src)
        inner = specs.get("tasks") or {}
        remapped = {}
        for real, spec in inner.items():
            anon = anon_id(real)
            spec = json.loads(json.dumps(spec))
            if "physics_note" in spec:
                spec["physics_note"] = NEUTRAL_NOTE
            remapped[anon] = spec
        specs["tasks"] = remapped
        specs["note"] = (str(specs.get("note", "")) +
                         " ｜ 盲化副本：任务键已匿名，physics_note 已中性化。")
        _dump(os.path.join(out_root, "physics", "scale_specs.json"), specs)

    _dump(os.path.join(out_root, "mapping.json"), {
        "level": level,
        "note": "匿名 id 到真实 id 的映射。仅用于评分与分析，**不得进入智能体可见面**。",
        "removed_meta_fields": sorted(removed_fields),
        "map": mapping,
    })
    return {"tasks": len(mapping), "level": level, "removed": sorted(removed_fields)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="生成盲化任务集（不改动原任务集）")
    ap.add_argument("--out", default=os.path.join("blind"), help="输出目录，默认 blind/")
    ap.add_argument("--level", default="metadata", choices=LEVELS,
                    help="metadata=去现象/来源；strict=另去 units")
    args = ap.parse_args(argv)
    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    result = build(out, args.level)
    print("盲化任务集已生成: " + out)
    print("  任务数 %d，档位 %s，移除字段 %s"
          % (result["tasks"], result["level"], ",".join(result["removed"])))
    print("  智能体可见面: %s" % os.path.join(out, "tasks"))
    print("  评分侧答案  : %s" % os.path.join(out, "reference"))
    print("  映射（勿泄漏）: %s" % os.path.join(out, "mapping.json"))
    print("")
    print("  校验方式：python -m formula_agh validate-tasks --tasks blind/tasks "
          "--reference blind/reference --require-split")
    print("  注意：盲化集的 source 是指向评审侧映射的占位串，会触发 SOURCE_NOT_URL 警告，")
    print("       请不要加 --strict（加了会把这条预期的警告当成失败）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
