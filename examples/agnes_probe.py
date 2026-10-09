# -*- coding: utf-8 -*-
"""Agnes 接入自检：一条命令判断「密钥 + 端点」到底能不能用。

为什么单独做成一个脚本
----------------------
接入失败的表现通常是"调用没反应/报错"，而报错信息往往指不到真正的原因。
本脚本把问题拆成三个可以分别回答的问题：

    1. .env 里的配置读到了吗？（不发请求就能答）
    2. 网关活着吗、这个 key 能通过鉴权吗？（GET /models）
    3. 能真的跑推理吗？（POST /chat/completions）

第 2 问和第 3 问**必须分开测**——实测遇到过"某 key 偶发能过 /models 但
/chat/completions 稳定 401"的情况，只看第一层会误判成"密钥有效"。

用法：
    python examples/agnes_probe.py            # 人读的报告
    python examples/agnes_probe.py --json     # 机器可读
    python examples/agnes_probe.py --tries 30 # 加大重试（网关偶发 401 时有用）

退出码：0 全部通过 | 2 配置有问题 | 3 鉴权失败 | 4 推理不可用
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))


def load_env(path=None):
    path = path or os.path.join(ROOT, '.env')
    cfg = {}
    if not os.path.exists(path):
        return cfg
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                cfg[key.strip()] = value.strip()
    return cfg


def request(url, token=None, payload=None, timeout=60):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    data = json.dumps(payload).encode('utf-8') if payload else None
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method='POST' if payload else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode('utf-8', 'replace'), None
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode('utf-8', 'replace'), None
    except Exception as exc:  # noqa: BLE001 - 网络异常要如实回报
        return None, '', type(exc).__name__ + ': ' + str(exc)


def retry_until_ok(url, token, payload=None, tries=1, gap=1.0, ok=lambda s, b: s == 200):
    attempts = 0
    last = (None, '', None)
    while attempts < tries:
        attempts += 1
        last = request(url, token, payload)
        status, body, err = last
        if ok(status, body):
            return status, body, err, attempts
        if status not in (401, 429, 503) and err is None:
            break
        if attempts < tries:
            time.sleep(gap)
    return last[0], last[1], last[2], attempts


def main(argv=None):
    parser = argparse.ArgumentParser(description='Agnes 接入自检')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--tries', type=int, default=8, help='每个请求最多重试几次')
    args = parser.parse_args(argv)

    cfg = load_env()
    token = cfg.get('AGNES_API_KEY', '')
    base = cfg.get('AGNES_BASE_URL', '').rstrip('/')
    model = cfg.get('AGNES_MODEL', '')

    report = {'config': {'env_file': os.path.join(ROOT, '.env'),
                         'base_url': base, 'model': model,
                         'key_present': bool(token), 'key_length': len(token)}}

    if not token or not base:
        report['verdict'] = 'config-missing'
        report['hint'] = '缺少 AGNES_API_KEY 或 AGNES_BASE_URL，请检查 .env（参照 .env.example）'
        _emit(report, args.json)
        return 2

    # 第 2 问：端点活着吗？key 能过鉴权吗？
    status, body, err, tries = retry_until_ok(
        base + '/models', token, tries=args.tries, ok=lambda s, b: s == 200)
    report['auth'] = {'endpoint': base + '/models', 'http': status,
                      'attempts': tries, 'error': err, 'excerpt': body[:200]}
    if status != 200:
        report['verdict'] = 'auth-failed'
        report['hint'] = ('网关拒绝了这个 key。注意区分两种报错：'
                          '"Token not provided" 是没带令牌，'
                          '"Invalid token" 是令牌本身不被接受。'
                          '若 /models 能过但推理过不了，多半是免费 key 没有推理配额，'
                          '需要在控制台换一个 Token Plan 类型的 key。')
        _emit(report, args.json)
        return 3
    try:
        report['auth']['models'] = [m['id'] for m in json.loads(body).get('data', [])]
    except Exception:  # noqa: BLE001
        report['auth']['models'] = []

    # 第 3 问：能真的跑推理吗？（与第 2 问分开，因为实测存在"能过 /models、过不了推理"的 key）
    payload = {'model': model or 'agnes-3.0-flash',
               'messages': [{'role': 'user', 'content': '只回复两个字：连通'}],
               'max_tokens': 24, 'temperature': 0}
    status, body, err, tries = retry_until_ok(
        base + '/chat/completions', token, payload, tries=args.tries)
    entry = {'endpoint': base + '/chat/completions', 'http': status,
             'attempts': tries, 'error': err, 'excerpt': body[:200]}
    if status == 200:
        try:
            parsed = json.loads(body)
            entry['reply'] = parsed['choices'][0]['message']['content']
            entry['usage'] = parsed.get('usage')
        except Exception:  # noqa: BLE001
            entry['reply'] = None
    report['inference'] = entry

    if status != 200:
        report['verdict'] = 'inference-unavailable'
        report['hint'] = ('鉴权这一层过了，但推理端点返回 %s。'
                          '实测遇到过同一 key 在 /models 上偶发放行、'
                          '在 /chat/completions 上稳定被拒的情况——'
                          '这通常意味着该 key 没有推理权限或配额。'
                          '请到平台控制台确认 key 类型（免费 key 与 Token Plan key 是不同限制池）。'
                          % status)
        _emit(report, args.json)
        return 4

    report['verdict'] = 'ok'
    report['hint'] = '密钥与推理端点均可用。'
    _emit(report, args.json)
    return 0


def _emit(report, as_json):
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    cfg = report['config']
    print('=' * 74)
    print('Agnes 接入自检')
    print('=' * 74)
    print('  .env        :', cfg['env_file'])
    print('  base_url    :', cfg['base_url'])
    print('  model       :', cfg['model'])
    print('  key         :', '已配置 (len=%d)' % cfg['key_length'] if cfg['key_present'] else '缺失')
    print('-' * 74)
    for label, key in (('鉴权 GET /models', 'auth'), ('推理 POST /chat/completions', 'inference')):
        if key not in report:
            continue
        item = report[key]
        print('  %-30s HTTP %-6s 重试 %d 次' % (label, item['http'], item['attempts']))
        if item.get('models'):
            print('      可用模型 %d 个：%s' % (len(item['models']), ', '.join(item['models'][:6])))
        if item.get('reply'):
            print('      回复：%s' % item['reply'])
            print('      用量：%s' % item.get('usage'))
        if item['http'] != 200:
            print('      响应：%s' % item['excerpt'][:150])
    print('-' * 74)
    print('  结论：', report['verdict'])
    print('  说明：', report.get('hint', ''))
    print('=' * 74)


if __name__ == '__main__':
    sys.exit(main())
