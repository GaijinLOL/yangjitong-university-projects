"""用示例图调用本地服务并生成一份真实 CSV，供交付自检。

用法：先按 README 启动服务（默认 8080 端口），再执行：
    run_cpu.bat backend\\verify_demo.py [端口，默认 8080]
"""
import json
import sys
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from csv_export import export_csv
from config.classes import TEAM_NAME

root = Path(__file__).resolve().parents[1]
port = sys.argv[1] if len(sys.argv) > 1 else "8080"
image = root / "samples" / "val_0013.png"
result = requests.post(f"http://127.0.0.1:{port}/api/predict", files={"image": (image.name, image.open("rb"), "image/png")}, timeout=180).json()
if "detail" in result:
    print("调用失败:", result["detail"])
    sys.exit(1)
output = export_csv([result], root / "outputs", team_name=TEAM_NAME)
print(json.dumps({"status": result["status"], "defect_count": result["defect_count"], "csv": str(output)}, ensure_ascii=False))
print(output.read_text(encoding="utf-8-sig"))
