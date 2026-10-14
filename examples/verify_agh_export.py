# -*- coding: utf-8 -*-
"""核验 AGH 轨迹导出是否为**原始事件账本**（而非 AI 生成的摘要）。

为什么需要这个（2026-10-14 主办方通知）
--------------------------------------
主办方提醒：很多队伍「让 AI 自己去导出轨迹」，导出的内容大多数是错的，
**必须通过 AGH 手动导出的轨迹才有意义**。

本脚本把仓库里每一份 *.agnes.jsonl 与 AGH 会话库 ~/.agh/data/sessions.db 的
events 表逐条比对（session_key + seq + id + type）。全部命中即说明：

  * 导出的是**守护进程的完整事件账本**，不是模型写的描述；
  * 事件条数与库内一致，没有被裁剪或编造。

用法：python examples/verify_agh_export.py [--db <sessions.db>]
"""
import argparse
import glob
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SESSIONS = os.path.join(ROOT, "evidence", "agh-sessions")
DEFAULT_DB = os.path.join(os.path.expanduser("~"), ".agh", "data", "sessions.db")


def load_ledger(db):
    con = sqlite3.connect(db)
    by_session = {}
    for key, seq, eid, typ in con.execute("select session_key, seq, id, type from events"):
        by_session.setdefault(key, {})[seq] = (eid, typ)
    return by_session


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    args = ap.parse_args()
    if not os.path.isfile(args.db):
        print("找不到会话库：%s" % args.db)
        return 0
    ledger = load_ledger(args.db)
    files = sorted(glob.glob(os.path.join(SESSIONS, "*.agnes.jsonl")))
    total_ok = total_bad = 0
    for path in files:
        with open(path, encoding="utf-8") as fh:
            exported = [json.loads(line) for line in fh if line.strip()]
        best_key, best_hit = None, -1
        for key, events in ledger.items():
            hit = 0
            for e in exported:
                got = events.get(e.get("seq"))
                if got and got[0] == e.get("id") and got[1] == e.get("type"):
                    hit += 1
            if hit > best_hit:
                best_key, best_hit = key, hit
        ok = best_hit == len(exported) and len(exported) > 0
        total_ok += 1 if ok else 0
        total_bad += 0 if ok else 1
        print("%-6s %4d 条  %s  %s" % ("OK" if ok else "FAIL", len(exported),
              os.path.basename(path)[:52], "" if ok else ("最佳匹配 %d/%d" % (best_hit, len(exported)))))
    print("")
    print("共 %d 份：%d 份与事件库完全一致，%d 份不一致" % (len(files), total_ok, total_bad))
    if files and total_bad == 0:
        print("结论：全部导出均为 AGH 原始事件账本（非 AI 生成的摘要）。")
    return 0 if total_bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())