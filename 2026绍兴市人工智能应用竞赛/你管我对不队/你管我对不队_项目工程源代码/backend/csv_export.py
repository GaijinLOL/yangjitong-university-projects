"""CSV 结果规范与校验（前端导出使用同一份字段约束）。"""
import csv
from pathlib import Path
from config.classes import CSV_HEADERS, TEAM_NAME


def rows_for_result(result: dict):
    if not result["detections"]:
        return [[result["image_id"], "Ok", -1, -1, -1, -1, -1, result["inference_time_ms"]]]
    return [[result["image_id"], d["class_name"], f'{d["confidence"]:.2f}', d["x_min"], d["y_min"], d["x_max"], d["y_max"], result["inference_time_ms"]] for d in result["detections"]]


def validate_rows(rows, image_ids):
    """导出前阻止字段缺失、非法置信度、反向框和缺图记录。"""
    if len(CSV_HEADERS) != 8 or set(r[0] for r in rows) != set(image_ids):
        raise ValueError("CSV 校验失败：表头或图片记录不完整")
    for row in rows:
        if row[1] == "Ok":
            if row[2:7] != [-1, -1, -1, -1, -1]: raise ValueError("Ok 占位行不规范")
        elif not (0 <= float(row[2]) <= 1 and float(row[5]) > float(row[3]) and float(row[6]) > float(row[4])):
            raise ValueError("缺陷行置信度或像素框不合法")
    return True


def export_csv(results, output_dir: str | Path = "outputs", team_name: str = ""):
    """导出规范 CSV。文件名遵循竞赛规范：`团队名称_检测结果.csv`。

    team_name 缺省时取 config.classes.TEAM_NAME；Web 界面由前端传入用户填写的团队昵称。
    """
    name = (team_name or TEAM_NAME).strip() or TEAM_NAME
    rows = [row for result in results for row in rows_for_result(result)]
    validate_rows(rows, [r["image_id"] for r in results])
    path = Path(output_dir) / f"{name}_检测结果.csv"; path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh); writer.writerow(CSV_HEADERS); writer.writerows(rows)
    return path
