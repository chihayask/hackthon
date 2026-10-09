# -*- coding: utf-8 -*-
"""证据自动归档（M2 交付 4/8）。

验收标准（对应分工表 10-11）
---------------------------
"证据目录与运行记录一一对应，无孤立文件"。

做法
----
* runs/<run_id>/ 生成后**只读不改**；归档是把它复制进 evidence/runs/ 并登记索引，
  原件保留在原处，评审可以直接核对"归档副本 == 原始运行"（比对 manifest.sha256）。
* 命名遵循赛事证据包规范：<日期>_<任务编号>_<类型>_<序号>。
* 索引 evidence/index.json 是唯一权威映射表；ARCHIVE.md 是人可读版本。
* **双向孤儿检测**：
    - runs/ 下有运行但索引里没有  -> orphan_run（漏归档）
    - 索引/证据目录里有但 runs/ 下已无源 -> orphan_evidence（凭空多出的证据）
  任一方向有问题，check 模式返回非零。这是"无孤立文件"的机器判据。
* 归档时会读取 recheck/<run_id>.json（若存在），把该运行的"可独立复算"状态写进索引，
  这样评审一眼能看出哪些证据是复算过的。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
from datetime import datetime, timezone
from typing import Dict, List, Mapping, Optional

INDEX_NAME = "index.json"
RUNS_SUBDIR = "runs"
_NAME_SAFE = re.compile(r"[^0-9A-Za-z._\-]+")


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe(text: str, fallback: str = "unknown") -> str:
    cleaned = _NAME_SAFE.sub("-", str(text or "")).strip("-")
    return cleaned or fallback


def _read_json(path: str) -> Optional[Mapping[str, object]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, Mapping) else None


def _run_date(run_dir: str) -> str:
    env = _read_json(os.path.join(run_dir, "env.json")) or {}
    stamp = str(env.get("timestamp_utc") or "")
    if len(stamp) >= 10:
        return stamp[:10].replace("-", "")
    return datetime.fromtimestamp(os.path.getmtime(run_dir)).strftime("%Y%m%d")


def _run_type(run_meta: Mapping[str, object], run_id: str, verdict: str) -> str:
    if run_id.startswith("refcheck-"):
        return "refcheck"
    if run_id.startswith("variant-"):
        return "variant"
    return _safe(verdict, "run")


def _source_digest(run_dir: str) -> str:
    manifest = os.path.join(run_dir, "manifest.sha256")
    if os.path.exists(manifest):
        return _sha256_file(manifest)
    digest = hashlib.sha256()
    for root, _dirs, files in os.walk(run_dir):
        for name in sorted(files):
            digest.update(os.path.relpath(os.path.join(root, name), run_dir)
                          .replace(os.sep, "/").encode("utf-8"))
    return digest.hexdigest()


def is_run_dir(path: str) -> bool:
    """只有含 run.json 的目录才算一次运行。

    runs/ 下也可能出现队友放的汇总目录（例如负对照实验的总结），
    把它们的副本塞进证据包只会制造噪声，所以显式跳过并单独列出。
    """
    return os.path.isdir(path) and os.path.exists(os.path.join(path, "run.json"))


def _sync_tree(src: str, dst: str) -> Dict[str, int]:
    """增量同步目录：只复制真正变化的文件，删掉目标端多出来的文件。

    为什么不用 shutil.copytree
    -------------------------
    本机工作区的**单文件写入开销极大**：实测复制一个 14 文件、30 KB 的运行目录要 2.8 秒
    （约 0.2 秒/文件，应该是文件沙箱与同步盘叠加的结果）。152 条运行全量重拷要十几分钟，
    表现上就像"卡死"。而实际上归档时绝大多数文件与上一次完全相同。

    这个函数先比 (大小, mtime)，相同就跳过——copy2 会保留 mtime，所以第一次拷贝之后
    后续归档几乎零拷贝。真正的复制只发生在内容变化的那几个文件上。
    """
    os.makedirs(dst, exist_ok=True)
    copied = skipped = removed = 0
    src_files = set()
    for root, _dirs, files in os.walk(src):
        rel_root = os.path.relpath(root, src)
        target_root = dst if rel_root == "." else os.path.join(dst, rel_root)
        if rel_root != ".":
            os.makedirs(target_root, exist_ok=True)
        for name in files:
            rel = name if rel_root == "." else os.path.join(rel_root, name)
            src_files.add(rel)
            source_path = os.path.join(src, rel)
            dest_path = os.path.join(dst, rel)
            try:
                source_stat = os.stat(source_path)
                dest_stat = os.stat(dest_path)
                if (source_stat.st_size == dest_stat.st_size
                        and source_stat.st_mtime_ns == dest_stat.st_mtime_ns):
                    skipped += 1
                    continue
            except OSError:
                pass
            shutil.copy2(source_path, dest_path)
            copied += 1

    for root, dirs, files in os.walk(dst, topdown=False):
        rel_root = os.path.relpath(root, dst)
        for name in files:
            rel = name if rel_root == "." else os.path.join(rel_root, name)
            if rel not in src_files:
                try:
                    os.remove(os.path.join(dst, rel))
                    removed += 1
                except OSError:
                    pass
        for name in dirs:
            path = os.path.join(root, name)
            try:
                if not os.listdir(path):
                    os.rmdir(path)
            except OSError:
                pass
    return {"copied": copied, "skipped": skipped, "removed": removed}


def _load_index(out_dir: str) -> Dict[str, object]:
    path = os.path.join(out_dir, INDEX_NAME)
    data = _read_json(path)
    if isinstance(data, Mapping) and isinstance(data.get("entries"), dict):
        return dict(data)
    return {"version": 1, "entries": {}}


def archive_runs(runs_root: str = "runs",
                 out_dir: str = "evidence",
                 recheck_dir: str = "recheck",
                 only: Optional[Sequence[str]] = None) -> Dict[str, object]:
    """把 runs/ 下所有运行归档到 evidence/runs/，维护索引，返回归档摘要。

    only 非空时只处理列出的 run_id：AGH 每调用一次验证工具就自动归档一条，
    这时不需要把上百条历史运行重新哈希一遍。
    已归档的目录名不会因为新增运行而改变（见下方命名稳定性说明）。
    """
    only_set = set(str(x) for x in only) if only else None
    started_at = time.time()
    runs_out = os.path.join(out_dir, RUNS_SUBDIR)
    os.makedirs(runs_out, exist_ok=True)
    index = _load_index(out_dir)
    entries: Dict[str, object] = dict(index.get("entries") or {})

    run_ids: List[str] = []
    not_a_run: List[str] = []
    if os.path.isdir(runs_root):
        for entry in sorted(os.listdir(runs_root)):
            full = os.path.join(runs_root, entry)
            if not os.path.isdir(full):
                continue
            if not is_run_dir(full):
                not_a_run.append(entry)
                continue
            if only_set is not None and entry not in only_set:
                continue
            run_ids.append(entry)

    # 先算出每条运行的 (日期, 任务, 类型)，命名要用
    planned: Dict[str, Dict[str, str]] = {}
    for run_id in run_ids:
        run_dir = os.path.join(runs_root, run_id)
        meta = _read_json(os.path.join(run_dir, "run.json")) or {}
        planned[run_id] = {
            "date": _run_date(run_dir),
            "task": _safe(meta.get("task_id") or run_id, "task"),
            "type": _run_type(meta, run_id, str(meta.get("verdict") or "")),
        }

    # 命名稳定性（这里踩过一个真实的坑）
    # ------------------------------------------------------------------
    # 最初的做法是"每次按当前运行集合重新编号"。结果是：只要 runs/ 里新来一条运行，
    # 同组的既有证据目录就会被重新编号，旧目录立刻变成孤儿。
    # 在一个三名成员共享、随时有人在跑实验的工作区里，这会让孤儿检测永远报错。
    #
    # 现在改成**只追加**：已归档的 run_id 永久保留它第一次拿到的目录名，
    # 新运行领取该组下一个未被占用的序号。这样证据目录一旦生成就不再改名。
    def _prefix(info):
        return "%s_%s_%s_" % (info["date"], info["task"], info["type"])

    existing_names = set()
    if os.path.isdir(runs_out):
        existing_names |= set(os.listdir(runs_out))
    for value in entries.values():
        if isinstance(value, Mapping):
            name = os.path.basename(str(value.get("evidence_path") or ""))
            if name:
                existing_names.add(name)

    used: Dict[str, set] = {}
    for info in planned.values():
        used.setdefault(_prefix(info), set())
    for name in existing_names:
        for prefix in used:
            if name.startswith(prefix):
                tail = name[len(prefix):]
                if tail.isdigit():
                    used[prefix].add(int(tail))
    next_seq: Dict[str, int] = {}

    def _take(prefix: str) -> int:
        candidate = next_seq.get(prefix, 1)
        while candidate in used[prefix]:
            candidate += 1
        used[prefix].add(candidate)
        next_seq[prefix] = candidate + 1
        return candidate

    created: List[str] = []
    unchanged: List[str] = []
    changed: List[str] = []
    file_deltas: Dict[str, Dict[str, int]] = {}
    for run_id in run_ids:
        run_dir = os.path.join(runs_root, run_id)
        info = planned[run_id]
        prefix = _prefix(info)
        old = entries.get(run_id) if isinstance(entries.get(run_id), Mapping) else None
        if old and old.get("evidence_path"):
            # 已经归档过：沿用原目录名，绝不改名
            evidence_name = os.path.basename(str(old["evidence_path"]))
            tail = evidence_name[len(prefix):] if evidence_name.startswith(prefix) else ""
            if tail.isdigit():
                used[prefix].add(int(tail))
        else:
            evidence_name = prefix + "%02d" % _take(prefix)
        dest = os.path.join(runs_out, evidence_name)
        source_digest = _source_digest(run_dir)

        if old and old.get("evidence_path") == (RUNS_SUBDIR + "/" + evidence_name) \
                and old.get("source_manifest_sha256") == source_digest \
                and os.path.isdir(dest):
            unchanged.append(run_id)
        else:
            if old and old.get("source_manifest_sha256") not in (None, source_digest):
                changed.append(run_id)
            sync = _sync_tree(run_dir, dest)
            file_deltas[run_id] = sync
            if sync["copied"] or sync["removed"]:
                created.append(run_id)
            else:
                unchanged.append(run_id)

        recheck = _read_json(os.path.join(recheck_dir, run_id + ".json")) or {}
        meta = _read_json(os.path.join(run_dir, "run.json")) or {}
        entries[run_id] = {
            "run_id": run_id,
            "task_id": meta.get("task_id"),
            "verdict": meta.get("verdict"),
            "formula": meta.get("formula"),
            # 假设来源：决定这条证据能不能用来支撑"智能体自主发现"。
            # 只有 agh-llm 才算真正的自主闭环；其余如实标注。
            "hypothesis_source": meta.get("hypothesis_source") or "unclassified",
            "evidence_path": (RUNS_SUBDIR + "/" + evidence_name),
            "source_path": run_dir.replace(os.sep, "/"),
            "source_manifest_sha256": source_digest,
            "archived_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "file_count": sum(len(files) for _r, _d, files in os.walk(dest)),
            "independent_recheck": recheck.get("status") or "not-run",
            "reproducible": bool(recheck.get("agrees")),
        }

    index = {
        "version": 1,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runs_root": runs_root.replace(os.sep, "/"),
        "naming_rule": "<日期>_<任务编号>_<类型>_<序号>",
        "entries": entries,
    }
    index_path = os.path.join(out_dir, INDEX_NAME)
    with open(index_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")

    # 归档完立刻做一次双向孤儿检测，并把结果落盘（评审不必再跑一次才有报告）。
    orphans = check_archive(runs_root, out_dir, write=True)

    # 这个工作区是三名成员共享的，随时可能有人在跑新实验。
    # "归档过程中新冒出来的运行"不是归档缺陷，单独列出来，不污染一致性判定。
    arrived = []
    for run_id in orphans["orphan_run"]:
        full = os.path.join(runs_root, run_id)
        try:
            if os.path.getmtime(full) >= started_at:
                arrived.append(run_id)
        except OSError:
            pass
    real_orphan_run = [r for r in orphans["orphan_run"] if r not in arrived]
    consistent = (not real_orphan_run) and (not orphans["orphan_evidence"]) \
        and (not orphans["dangling_index"]) and (not orphans["index_without_source"])

    source_counts: Dict[str, int] = {}
    for value in entries.values():
        if isinstance(value, Mapping):
            key = str(value.get("hypothesis_source") or "unclassified")
            source_counts[key] = source_counts.get(key, 0) + 1
    unclassified = [rid for rid, value in entries.items()
                    if isinstance(value, Mapping)
                    and str(value.get("hypothesis_source")) == "unclassified"]

    summary = {
        "runs_total": len(run_ids),
        "hypothesis_source_counts": dict(sorted(source_counts.items())),
        "unclassified_runs": sorted(unclassified)[:20],
        "skipped_not_a_run": not_a_run,
        "archived_new": len(created),
        "archived_unchanged": len(unchanged),
        "source_changed": changed,
        "files_copied": sum(v["copied"] for v in file_deltas.values()),
        "files_skipped": sum(v["skipped"] for v in file_deltas.values()),
        "index_path": index_path.replace(os.sep, "/"),
        "orphan_run": real_orphan_run,
        "arrived_during_archive": sorted(arrived),
        "orphan_evidence": orphans["orphan_evidence"],
        "non_run_dirs": orphans.get("non_run_dirs") or [],
        "consistent": consistent,
    }
    with open(os.path.join(out_dir, "ARCHIVE.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_archive_markdown(index, summary))
    return summary


def check_archive(runs_root: str = "runs",
                  out_dir: str = "evidence",
                  write: bool = True) -> Dict[str, object]:
    """双向孤儿检测：runs/ <-> evidence/ 必须一一对应。"""
    index = _load_index(out_dir)
    entries: Dict[str, object] = dict(index.get("entries") or {})
    runs_out = os.path.join(out_dir, RUNS_SUBDIR)

    actual_runs = set()
    non_run_dirs = set()
    if os.path.isdir(runs_root):
        for entry in os.listdir(runs_root):
            full = os.path.join(runs_root, entry)
            if not os.path.isdir(full):
                continue
            (actual_runs if is_run_dir(full) else non_run_dirs).add(entry)
    indexed = set(entries.keys())
    orphan_run = sorted(actual_runs - indexed)

    referenced = {os.path.basename(str(v.get("evidence_path") or ""))
                  for v in entries.values() if isinstance(v, Mapping)}
    actual_evidence = set()
    if os.path.isdir(runs_out):
        actual_evidence = {e for e in os.listdir(runs_out)
                           if os.path.isdir(os.path.join(runs_out, e))}
    orphan_evidence = sorted(actual_evidence - referenced)
    dangling = sorted(referenced - actual_evidence)

    missing_source = sorted(run_id for run_id in indexed
                            if not os.path.isdir(os.path.join(runs_root, run_id)))
    ok = not (orphan_run or orphan_evidence or dangling or missing_source)
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runs": len(actual_runs),
        "indexed": len(indexed),
        "evidence_dirs": len(actual_evidence),
        "orphan_run": orphan_run,
        "orphan_evidence": orphan_evidence,
        "dangling_index": dangling,
        "index_without_source": missing_source,
        # 不是运行、也没有被归档的目录（例如队友放在 runs/ 下的汇总）。
        # 只报告不算失败：它们本来就不该进证据包。
        "non_run_dirs": sorted(non_run_dirs - indexed),
        "ok": ok,
    }
    if write:
        path = os.path.join(out_dir, "orphan_report.json")
        os.makedirs(out_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    return report


def prune_orphan_evidence(out_dir: str = "evidence",
                          runs_root: str = "runs") -> Dict[str, object]:
    """删除 evidence/runs/ 下**未被索引引用**的证据目录。

    只动 evidence/，绝不动 runs/ 下的原始运行；而且必须先看到清单才会执行
    （调用方负责打印）。这些目录通常是早期版本编号规则留下的重复副本，
    留着会让"一一对应"这句话不成立。
    """
    report = check_archive(runs_root, out_dir, write=False)
    runs_out = os.path.join(out_dir, RUNS_SUBDIR)
    removed = []
    for name in report["orphan_evidence"]:
        target = os.path.join(runs_out, name)
        if not os.path.isdir(target):
            continue
        # 二次确认：解析后的路径必须确实位于 evidence/runs/ 之内
        if os.path.dirname(os.path.abspath(target)) != os.path.abspath(runs_out):
            continue
        shutil.rmtree(target)
        removed.append(name)
    after = check_archive(runs_root, out_dir, write=True)
    return {"removed": removed, "remaining_orphans": after["orphan_evidence"],
            "consistent": after["ok"]}


def _archive_markdown(index: Mapping[str, object], summary: Mapping[str, object]) -> str:
    entries = index.get("entries") or {}
    lines = [
        "# 证据归档索引（M2 维护）",
        "",
        "运行目录 runs/<run_id>/ 一经生成即视为不可变证据；本目录保存其只读副本。",
        "命名规则：" + str(index.get("naming_rule")),
        "",
        "- 最近更新（UTC）：" + str(index.get("updated_at_utc")),
        "- 运行总数：" + str(summary.get("runs_total")),
        "- 本次新增归档：" + str(summary.get("archived_new")),
        "- 未变化（幂等跳过）：" + str(summary.get("archived_unchanged")),
        "- 一致性：%s" % ("通过（无孤立文件）" if summary.get("consistent") else "不通过，见 orphan_report.json"),
        "",
        '## 假设来源分布（决定哪些运行能支撑「自主发现」）',
        "",
        "| 来源 | 条数 | 含义 |",
        "|---|---|---|",
    ]
    from .evidence import HYPOTHESIS_SOURCES
    for key, count in sorted((summary.get("hypothesis_source_counts") or {}).items()):
        lines.append("| %s | %d | %s |" % (key, count,
                                          HYPOTHESIS_SOURCES.get(key, "未在词表中")))
    unknown = summary.get("unclassified_runs") or []
    if unknown:
        lines += ["", "未标注来源的运行（前 20 条，需补齐后才能计入任何能力声明）：", ""]
        for run_id in unknown:
            lines.append("- " + str(run_id))
    lines += [
        "",
        "| run_id | 任务 | 判定 | 来源 | 归档目录 | 可独立复算 |",
        "|---|---|---|---|---|---|",
    ]
    for run_id in sorted(entries):
        entry = entries[run_id]
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            run_id, entry.get("task_id"), entry.get("verdict"),
            entry.get("hypothesis_source"),
            entry.get("evidence_path"), entry.get("independent_recheck")))
    lines.append("")
    return "\n".join(lines) + "\n"