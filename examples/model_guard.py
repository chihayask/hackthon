# -*- coding: utf-8 -*-
"""模型路由守卫：拒绝非 Agnes 路由。

依据：《关于举办 2026 年江苏省 AI+科学与工程创新实践黑客松（高校组）的通知》
五（二）——"作品中的所有模型调用仅限 Agnes 模型，不得接入或调用其他厂商、品牌或
第三方模型"。

为什么需要它（外部审计 2026-10-10 的第 2 条）：当时演示脚本允许自由传 `--model`，
传成别家模型就能跑起来，仓库里没有任何一处**拒绝**这种配置。主张"全程只用 Agnes"
时，只有靠人记得别改参数，等于没有控制。

本脚本只读配置、不启动守护进程，因此 AGH 实例不可用时也能做合规检查：
  * 读取 `~/.agh/profiles/<profile>/configuration.json`，检查每个启用的账号；
  * 也可直接校验命令行给出的路由串 `slot=provider/model`。

判定：账号 id 必须以 `agnes` 开头、baseUrl 主机名必须落在 agnes 域内、
模型 id 必须以 `agnes` 开头。任一不满足即退出码 2。"""
import argparse
import json
import os
import re
import sys

AGNES_PREFIX = "agnes"


def config_path(profile: str) -> str:
    home = os.environ.get("AGH_HOME") or os.path.join(
        os.environ.get("USERPROFILE") or os.environ.get("HOME") or "", ".agh")
    return os.path.join(home, "profiles", profile, "configuration.json")


def _host(url: str) -> str:
    m = re.match(r"^[a-z]+://([^/]+)", str(url or ""))
    return (m.group(1) if m else "").lower()


def check_accounts(profile: str) -> dict:
    path = config_path(profile)
    if not os.path.isfile(path):
        return {"ok": False, "reason": "找不到配置: " + path, "accounts": []}
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    accounts = []
    problems = []
    for acc in cfg.get("accounts") or []:
        enabled = bool(acc.get("enabled", True))
        provider = str(acc.get("id") or "")
        base = _host(acc.get("baseUrl"))
        model = str(acc.get("model") or "")
        models = [str(m.get("id") or "") for m in (acc.get("models") or [])
                  if isinstance(m, dict)]
        row = {"label": acc.get("label"), "provider": provider,
               "baseUrlHost": base, "model": model, "models": models,
               "enabled": enabled}
        if enabled:
            if not provider.lower().startswith(AGNES_PREFIX):
                problems.append("账号 %s 的 provider 不是 Agnes: %s" % (acc.get("label"), provider))
            if AGNES_PREFIX not in base:
                problems.append("账号 %s 的 baseUrl 不在 agnes 域内: %s" % (acc.get("label"), base))
            for mid in ([model] if model else []) + models:
                if mid and not mid.lower().startswith(AGNES_PREFIX):
                    problems.append("账号 %s 配了非 Agnes 模型: %s" % (acc.get("label"), mid))
        accounts.append(row)
    return {"ok": not problems and bool(accounts), "reason": "; ".join(problems),
            "path": path, "profile": profile, "accounts": accounts}


def check_routes(routes) -> dict:
    """校验 slot=provider/model 形式的路由串。"""
    problems = []
    parsed = []
    for raw in routes or []:
        text = str(raw).strip()
        if not text:
            continue
        body = text.split("=", 1)[1] if "=" in text else text
        provider = body.split("/", 1)[0] if "/" in body else body
        model = body.split("/", 1)[1] if "/" in body else ""
        parsed.append({"raw": text, "provider": provider, "model": model})
        if not provider.lower().startswith(AGNES_PREFIX):
            problems.append("路由 %s 的 provider 不是 Agnes: %s" % (text, provider))
        if model and not model.lower().startswith(AGNES_PREFIX):
            problems.append("路由 %s 指向非 Agnes 模型: %s" % (text, model))
    return {"ok": not problems, "reason": "; ".join(problems), "routes": parsed}


def main(argv=None):
    ap = argparse.ArgumentParser(description="拒绝非 Agnes 的模型路由（通知五（二））")
    ap.add_argument("--profile", default=os.environ.get("AGNES_PROFILE", "local-dev"))
    ap.add_argument("--route", action="append", default=[],
                    help="额外校验的路由串 slot=provider/model，可重复")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    accounts = check_accounts(args.profile)
    routes = check_routes(args.route)
    ok = bool(accounts.get("ok")) and bool(routes.get("ok"))
    report = {"ok": ok, "profile": args.profile,
              "accounts": accounts, "routes": routes,
              "notice": "通知五（二）：作品中的所有模型调用仅限 Agnes 模型。"}

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("模型路由守卫（通知五（二）：模型调用仅限 Agnes）")
        print("  配置: " + str(accounts.get("path")))
        for a in accounts.get("accounts") or []:
            print("  %s账号 %-12s provider=%-10s host=%-22s model=%s" % (
                "[启用] " if a["enabled"] else "[停用] ",
                a["label"], a["provider"], a["baseUrlHost"], a["model"]))
        for r in routes.get("routes") or []:
            print("  路由 %s -> provider=%s model=%s" % (r["raw"], r["provider"], r["model"]))
        print("")
        if ok:
            print("结论：全部启用账号与路由均为 Agnes，符合通知五（二）。")
        else:
            print("结论：发现非 Agnes 配置，**不得用于提交**。")
            if accounts.get("reason"):
                print("  账号问题: " + accounts["reason"])
            if routes.get("reason"):
                print("  路由问题: " + routes["reason"])
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
