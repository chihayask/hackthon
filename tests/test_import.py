# -*- coding: utf-8 -*-
"""数据导入测试：任意表格 -> tasks/<id>/{data.csv, meta.json}，且导入结果必须过契约。

覆盖点：
  * 目标列被重命名为 y，原列名记入 meta.import（可追溯）
  * csv / tsv / json 记录数组 / json 列式 四种写法产出同一份数据
  * xlsx（openpyxl 可用时）
  * 违规输入被明确拒绝，且报的是输入本身的问题
  * 导入结果能被契约校验器接受，并可直接跑完验证
"""
import csv
import json
import os
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from formula_agh.contract import validate_task
from formula_agh.importer import DataImportError, convert, read_table
from formula_agh.settings import verify_settings
from formula_agh.split import build_split, load_split, seal_split, write_split
from formula_agh.verify import load_task, verify_formula

TMP = os.path.join(ROOT, "_import_tmp")


# --------------------------------------------------------------------------
# 夹具
# --------------------------------------------------------------------------

def _fresh(name):
    d = os.path.join(TMP, name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    return d


def _pe_data(n=200, seed=7):
    rng = np.random.default_rng(seed)
    k = rng.uniform(50.0, 400.0, n)
    x = rng.uniform(0.01, 0.20, n)
    pe = 0.5 * k * x ** 2
    return {"x": x, "k": k, "PE": pe}


def _write_csv(path, cols, delimiter=","):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter=delimiter)
        w.writerow(list(cols))
        for i in range(len(next(iter(cols.values())))):
            w.writerow([float(cols[c][i]) for c in cols])
    return path


def _expect_error(fn, *args, **kwargs):
    """运行并断言抛出 DataImportError，返回消息文本。

    不用 pytest.raises 的 as 形式：仓库自带的零依赖运行器提供的垫片
    （run_tests.py 里的 _RaisesContext）不暴露 .value，拿不到异常对象。

    必须传可调用对象（lambda）：若写成 _expect_error(_convert(...))，参数在调用方
    求值，异常发生在进入本函数之前，捕获不到。
    
    """
    try:
        fn(*args, **kwargs)
    except DataImportError as exc:
        return str(exc)
    raise AssertionError("预期 DataImportError，但没有抛出")


def _convert(root, source, task_id="t-imp", **kw):
    kw.setdefault("target", "PE")
    kw.setdefault("tasks_root", os.path.join(root, "tasks"))
    return convert(source=source, task_id=task_id, **kw)


# --------------------------------------------------------------------------
# 正常路径
# --------------------------------------------------------------------------

def test_csv_import_renames_target_and_records_provenance():
    root = _fresh("csv")
    src = _write_csv(os.path.join(root, "d.csv"), _pe_data())
    report = _convert(root, src)

    assert report["errors"] == 0, report["findings"]
    assert report["var_names"] == ["x", "k"]
    assert report["target_renamed_from"] == "PE"

    with open(report["data_csv"], encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    assert header[0] == "y", header
    assert sorted(header[1:]) == ["k", "x"]

    with open(report["meta_json"], encoding="utf-8") as fh:
        meta = json.load(fh)
    assert meta["task_id"] == "t-imp"
    assert meta["var_names"] == ["x", "k"]
    assert meta["layer"] == "base"
    assert meta["import"]["target_column_original"] == "PE"
    assert meta["import"]["target_column_renamed_to"] == "y"
    assert set(meta["sampling"]) == {"x", "k"}
    assert meta["sample_count"] == 200


def test_four_text_formats_produce_the_same_table():
    root = _fresh("formats")
    cols = _pe_data()
    csv_path = _write_csv(os.path.join(root, "a.csv"), cols)
    tsv_path = _write_csv(os.path.join(root, "a.tsv"), cols, delimiter="\t")

    rec = [{c: float(cols[c][i]) for c in cols} for i in range(200)]
    rec_path = os.path.join(root, "a.json")
    with open(rec_path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh)

    col_path = os.path.join(root, "b.json")
    with open(col_path, "w", encoding="utf-8") as fh:
        json.dump({c: [float(v) for v in cols[c]] for c in cols}, fh)

    tables = []
    for i, path in enumerate([csv_path, tsv_path, rec_path, col_path]):
        header, body, _info = read_table(path)
        assert header == ["x", "k", "PE"], (path, header)
        assert len(body) == 200
        tables.append((header, body))
        _convert(root, path, task_id="t-%d" % i)
    for header, body in tables[1:]:
        assert body == tables[0][1]


def test_xlsx_import_when_openpyxl_available():
    try:
        from openpyxl import Workbook
    except ImportError:
        return  # 可选依赖缺失时跳过，不算失败
    root = _fresh("xlsx")
    cols = _pe_data(n=60)
    path = os.path.join(root, "d.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.append(list(cols))
    for i in range(60):
        ws.append([float(cols[c][i]) for c in cols])
    wb.save(path)

    report = _convert(root, path)
    assert report["errors"] == 0, report["findings"]
    assert report["rows"] == 60


# --------------------------------------------------------------------------
# 违规输入必须被拒绝，且报的是输入本身的问题
# --------------------------------------------------------------------------

def test_non_numeric_cell_rejected():
    root = _fresh("bad-text")
    path = os.path.join(root, "d.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("x,k,y\n1,2,3\noops,4,5\n")
    msg = _expect_error(lambda: _convert(root, path, target="y"))
    assert "不是数值" in msg


def test_empty_cell_rejected():
    root = _fresh("bad-empty")
    path = os.path.join(root, "d.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("x,k,y\n1,,3\n2,4,5\n")
    msg = _expect_error(lambda: _convert(root, path, target="y"))
    assert "为空" in msg


def test_missing_target_column_rejected():
    root = _fresh("bad-target")
    path = _write_csv(os.path.join(root, "d.csv"), {"x": [1.0, 2.0], "z": [3.0, 4.0]})
    msg = _expect_error(lambda: _convert(root, path, target="PE"))
    assert "不在表头里" in msg


def test_duplicate_header_rejected():
    root = _fresh("dup")
    path = os.path.join(root, "d.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("x,x,y\n1,2,3\n")
    msg = _expect_error(lambda: _convert(root, path, target="y"))
    assert "重复列名" in msg


def test_too_few_rows_rejected():
    root = _fresh("few")
    cols = _pe_data(n=30)
    path = _write_csv(os.path.join(root, "d.csv"), cols)
    msg = _expect_error(lambda: _convert(root, path))
    assert "50" in msg


def test_single_variable_rejected():
    root = _fresh("one-var")
    path = _write_csv(os.path.join(root, "d.csv"),
                      {"x": np.linspace(1.0, 2.0, 60), "PE": np.linspace(3.0, 4.0, 60)})
    msg = _expect_error(lambda: _convert(root, path))
    assert "至少 2 个" in msg


def test_target_cannot_also_be_a_variable():
    root = _fresh("conflict")
    path = _write_csv(os.path.join(root, "d.csv"), _pe_data(n=60))
    msg = _expect_error(lambda: _convert(root, path, variables=["PE", "x"]))
    assert "不能同时作为自变量" in msg


def test_existing_task_dir_requires_force():
    root = _fresh("exists")
    path = _write_csv(os.path.join(root, "d.csv"), _pe_data())
    _convert(root, path)
    msg = _expect_error(lambda: _convert(root, path))
    assert "已存在" in msg
    # --force 后可覆盖
    report = _convert(root, path, force=True)
    assert report["errors"] == 0


def test_unsupported_extension_rejected():
    root = _fresh("ext")
    path = os.path.join(root, "d.dat")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("x,k,y\n1,2,3\n")
    msg = _expect_error(lambda: _convert(root, path, target="y"))
    assert "不支持的扩展名" in msg


# --------------------------------------------------------------------------
# 导入结果必须能用：过契约 -> 划分 -> 验证通过
# --------------------------------------------------------------------------

def test_reference_written_when_formula_given():
    root = _fresh("ref")
    path = _write_csv(os.path.join(root, "d.csv"), _pe_data())
    report = _convert(root, path, formula="0.5*k*x**2",
                      reference_root=os.path.join(root, "reference"))
    assert os.path.isfile(report["reference_json"])
    with open(report["reference_json"], encoding="utf-8") as fh:
        ref = json.load(fh)
    assert ref["formula"] == "0.5*k*x**2"
    assert ref["task_id"] == "t-imp"


def test_imported_task_is_contract_clean():
    root = _fresh("contract")
    path = _write_csv(os.path.join(root, "d.csv"), _pe_data())
    report = _convert(root, path, units={"x": "m", "k": "N/m", "y": "J"},
                      source_url="https://example.org/hooke")
    findings = validate_task(report["task_dir"], "t-imp")
    errors = [f for f in findings if f.severity == "error"]
    assert errors == [], errors
    assert isinstance(findings, list)


def test_imported_task_verifies_accepted():
    root = _fresh("e2e")
    path = _write_csv(os.path.join(root, "d.csv"), _pe_data(n=240))
    report = _convert(root, path, units={"x": "m", "k": "N/m", "y": "J"},
                      source_url="https://example.org/hooke")
    assert report["errors"] == 0, report["findings"]

    task_dir = report["task_dir"]
    cfg = verify_settings()
    columns, meta = load_task(task_dir)
    manifest, masks = build_split(columns, meta, cfg["holdout_ratio"],
                                  cfg["extrapolation_ratio"], cfg["seed"], "t-imp")
    write_split(task_dir, manifest)
    seal_split(task_dir, os.path.join(root, "sealed"), columns, masks, manifest)
    assert load_split(task_dir) is not None

    result = verify_formula("0.5*k*x**2", columns, meta)
    assert result.verdict == "accepted", [(c.name, c.passed, c.reason) for c in result.checks]
    # 错的幂次必须被拒：导入的数据同样具备判别力
    wrong = verify_formula("0.5*k*x", columns, meta)
    assert wrong.verdict == "rejected", [(c.name, c.passed) for c in wrong.checks]


def test_no_empty_temp_dirs_left_behind():
    """run_tests 会检查空目录；确保夹具目录被清理。"""
    if os.path.isdir(TMP):
        shutil.rmtree(TMP, ignore_errors=True)
    assert not os.path.isdir(TMP)
