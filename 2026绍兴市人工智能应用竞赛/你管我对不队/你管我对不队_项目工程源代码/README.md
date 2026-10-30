# 工业视觉质检可视化应用

这是一个可直接运行的窗帘布缺陷检测应用包：运行时已内置，现场无需另行安装第三方库。当前模型属于窗帘布缺陷检测，规范类别为 `Hole`、`Ink`、`Broken_Filament`，无缺陷使用 `Ok`。

## 启动

在仓库根目录双击 `start_web.bat`，或执行：

```bat
runtime_cpu\python.exe backend\web_server.py --port 8080
```

打开 `http://127.0.0.1:8080`。随包 `runtime_cpu/` 是 CPU 便携运行环境（Python 3.11.9
+ torch 2.5.0+cpu），解压即用、无需安装任何依赖；若便携环境缺失，`start_web.bat`
会自动回退到系统 Python。如需 NVIDIA GPU 加速，在系统 Python 中按
`requirements/requirements-cuda.txt` 安装（驱动 >= 522.06）。

## 功能

- 单张/多张上传，原图绝对像素框、中文标签和两位置信度；
- 实时摄像头检测：浏览器调用本机摄像头，逐帧送后端推理并在画面上实时叠加
  缺陷框，展示帧率、推理耗时、OK/NG 判定与各类缺陷累计统计；彩色摄像头帧会
  自动转单通道灰度，与模型训练分布对齐；
- OK/NG 判定、单图耗时、目标坐标高亮、标注图 PNG 保存；
- 批量逐张进度与结果列表，支持上一张/下一张按钮与键盘方向键切换；
- 批次分析面板展示检测图片数、NG 数/占比、总缺陷数、平均耗时与类别分布；
- CSV 导出严格遵循竞赛《检测结果输出表格规范及字段说明》：8 列表头、
  Ok 占位行、像素绝对值坐标、置信度两位小数、同图多行耗时一致，导出前阻断式校验；
  文件名遵循 `团队名称_检测结果.csv`，团队名称可在页面工具栏填写（也可改 `config/classes.py`）；
- 批次质量指标（6 项），上传 GT 标注后自动评估（见下）。

## 批次质量指标（6 项）

上传测试图片的同时上传 GT 标注（与图片同名），点击「开始检测」后自动评估并写入历史批次。指标按后端批次记录的原始计数在前端实时计算，不硬编码数值。

| 指标 | 计算方式 | 分母 |
|---|---|---|
| 表面裂纹识别准确率 | correct_crack_count ÷ total_images | 测试图像总数 |
| 误检率 | false_ng_ok_count ÷ ok_sample_total | 实际 OK 样件总数 |
| 一致性准确率 | consistent_correct_count ÷ total_images | 测试图像总数 |
| mAP50 | 逐类 VOC 2010+ AP@0.5 取平均 | — |
| Precision | tp_count ÷ pred_box_count | 模型检测目标总数 |
| Recall | tp_count ÷ gt_box_count | 实际存在目标总数 |

- **概览卡片**：6 张卡片横向排列，显示当前批次数值，并标注与上一批次相比的升降箭头与差值；
- **明细表**：逐批展示 6 项指标历史数值，支持按批次号、时间区间筛选；
- **趋势图**：6 项指标随批次变化的折线（误检率红色系，其余蓝/绿色系）；
- **异常高亮**：误检率 >5%、mAP50 / Recall <0.85 时数值标红，卡片右上角显示告警角标；
- **口径备注**：页面底部「指标口径说明」展示每项指标的含义与计算方式；
- **联动刷新**：切换批次号 / 时间区间筛选后，卡片、明细表、趋势图同步刷新。

口径要点：mAP50 / Precision / Recall 均基于目标检测框级（IoU≥0.5 且类别一致，
贪心一对一匹配）统计，而非图像级；误检率、表面裂纹识别准确率、一致性准确率三者分母
不混用。本任务（窗帘布）中「表面裂纹状态」映射为缺陷状态 NG/OK 判断，计算口径不变。
批次历史持久化在 `outputs/batch_history.json`。

## GT 标注上传

- 框级标注（与图片同名的文件）：
  - `.txt` YOLO 格式，每行 `cls cx cy w h`（归一化中心点框），按图像宽高换算像素坐标；
  - `.json` 测试集标注格式（shapes 绝对像素坐标 + labelName）；
- 图级标注：`label.xlsx` 或同格式 CSV（列：file_name, hole, ink, broken_filament, ok）；
- 所有图片都具备 GT（框级或图级）时才会评估；缺失 GT 的图片会在状态栏列出。

后端评估接口与字段约束：

```text
POST /api/batch/evaluate   批次评估（12 字段：batch_id、total_images、
                           correct_crack_count、ok_sample_total、false_ng_ok_count、
                           consistent_correct_count、pred_box_count、gt_box_count、
                           tp_count、fp_count、fn_count、map50）
GET  /api/batch/history    历史批次（?batch_id= &start= &end= 过滤）
POST /api/gt/label         图级 GT 解析（label.xlsx / CSV）
```

## 目录

`backend/` Web 服务、批次指标计算（metrics.py）、CSV 校验；`frontend/` 模块化页面、API、指标渲染（metrics.js）、GT 解析（gt.js）与导出；`config/classes.py` 类别/团队常量；`predict.py` 原有推理入口；`model/` 权重；`samples/` 示例图。

## 需要手动确认

团队昵称已设为「你管我对不队」（`config/classes.py` 的 `TEAM_NAME`），CSV 文件名与批次记录将使用该名称；如需更换，改该常量或在页面工具栏的「团队名称」输入框填写（页面填写的名称优先）。竞赛提交要求：提交材料中不得出现学校名称、专业名称、指导教师姓名；文件与目录命名用团队昵称。应用只展示模型真实输出，不包含伪造标签或精度数据。
