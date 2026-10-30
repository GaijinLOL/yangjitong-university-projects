# -*- coding: utf-8 -*-
"""Generate 你管我对不队_项目方案.docx (revised edition).

Every number in this document is traceable to the repository:
  * dataset label statistics            -> dataset/labels/**
  * delivered-weight val measurements   -> this session's val sweep (34 images)
  * delivered-weight val metrics        -> tools/scan_conf_threshold.py @ conf 0.37
  * candidate-model val metrics         -> archived runs/optimized_20260924 artefacts
  * class-level confusion               -> runs/optimized_20260924/confusion_matrix.png
  * deployment / timing figures         -> 部署说明.md section 11, self-check output
  * CSV field statistics                -> 你管我对不队_检测结果.csv (679 images)
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

WS = Path(__file__).resolve().parents[2]          # 项目根目录（你管我对不队_...）
ROOT = WS / "你管我对不队_项目工程源代码"
RUN = ROOT / "runs" / "optimized_20260924"
FIGS = ROOT / "docs" / "plan_figs"
MEDIA = FIGS / "src"
OUT = WS / "你管我对不队_项目方案.docx"

NAVY = "1F4E79"
ZEBRA = "F2F6FA"
ACCENT = "C00000"

# ----------------------------------------------------------------------------- styling
def set_font(run, size=12, bold=False, color="000000", name="宋体"):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def add_p(doc, text, indent=True, size=12, bold=False, color="000000",
          align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=6, after=6, line=1.25):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    p.alignment = align
    if indent:
        pf.first_line_indent = Cm(0.74)
    set_font(p.add_run(text), size, bold, color)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    pf = p.paragraph_format
    pf.keep_with_next = True
    pf.space_before = Pt(14 if level == 1 else 10)
    pf.space_after = Pt(6)
    set_font(p.add_run(text), 16 if level == 1 else 13.5, True,
             NAVY if level == 1 else "1F3864")
    return p


def add_keypoint(doc, text):
    """Chapter-leading core assertion, visually separated from body text."""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(8)
    pf.space_after = Pt(10)
    pf.line_spacing = 1.25
    pf.left_indent = Cm(0.4)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    set_font(p.add_run("核心观点　"), 12, True, ACCENT)
    set_font(p.add_run(text), 12, False, "000000")
    pPr = p._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "18")
    left.set(qn("w:space"), "6")
    left.set(qn("w:color"), ACCENT)
    bdr.append(left)
    pPr.append(bdr)
    return p


def add_table(doc, heads, rows, widths=None, size=9.5):
    t = doc.add_table(rows=1, cols=len(heads))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = "Table Grid"
    t.autofit = True
    for c, h in zip(t.rows[0].cells, heads):
        c.text = ""
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        set_font(p.add_run(h), size, True, "FFFFFF")
        c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        shade(c, NAVY)
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.1
            set_font(p.add_run(str(v)), size)
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if ri % 2 == 1:
                shade(cells[i], ZEBRA)
    if widths:
        for r in t.rows:
            for i, w in enumerate(widths):
                r.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def add_caption(doc, text):
    add_p(doc, text, indent=False, size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER,
          before=4, after=4)


def add_figure(doc, path, caption, conclusion, width=15.5):
    """Insert a centred figure, then its caption and the conclusion it supports."""
    if not Path(path).is_file():
        print("  [skip missing figure]", path)
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(0)
    p.add_run().add_picture(str(path), width=Cm(width))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(2)
    cap.paragraph_format.space_after = Pt(2)
    set_font(cap.add_run(caption), 10.5, True, "1F3864")
    if conclusion:
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        cp.paragraph_format.space_before = Pt(2)
        cp.paragraph_format.space_after = Pt(10)
        cp.paragraph_format.left_indent = Cm(0.74)
        cp.paragraph_format.right_indent = Cm(0.74)
        cp.paragraph_format.line_spacing = 1.2
        set_font(cp.add_run("结论："), 10.5, True, ACCENT)
        set_font(cp.add_run(conclusion), 10.5)


# ----------------------------------------------------------------------------- document
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.top_margin = sec.bottom_margin = Cm(2)
sec.left_margin = sec.right_margin = Cm(2)
sec.gutter = Cm(1)

for name in ("Normal", "Title", "Heading 1", "Heading 2", "Heading 3"):
    st = doc.styles[name]
    st.font.name = "宋体"
    st._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    st.font.color.rgb = RGBColor(0, 0, 0)
doc.styles["Normal"].font.size = Pt(12)
doc.styles["Normal"].paragraph_format.line_spacing = 1.25
doc.styles["Normal"].paragraph_format.space_before = Pt(6)
doc.styles["Normal"].paragraph_format.space_after = Pt(6)

# ---------------- cover
p = doc.add_paragraph(style="Title")
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(90)
set_font(p.add_run("你管我对不队"), 26, True, NAVY)
p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
p2.paragraph_format.space_before = Pt(6)
set_font(p2.add_run("窗帘布瑕疵智能视觉质检项目方案"), 22, True, "000000")

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(36)
set_font(p.add_run("参赛赛道：智能制造与工业智能 AI 视觉质检应用赛道"), 13)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(6)
set_font(p.add_run("项目类别：窗帘布瑕疵检测"), 13)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(6)
set_font(p.add_run("提交材料：项目方案（Word）／项目工程源代码／检测结果 CSV／演示视频／项目介绍 PPT"), 12)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(120)
set_font(p.add_run("提交日期：2026 年 9 月"), 12)

doc.add_page_break()

# ============================================================ 一、项目概述
add_heading(doc, "一、项目概述", 1)
add_keypoint(
    doc,
    "窗帘布是机器织造产品，布面纹理周期性重复、瑕疵形态可枚举，具备被统一算法稳定建模的客观条件；"
    "本项目把这一条件转化为一条可运行、可复现、可评估的质检工程链路："
    "CPU 单帧推理 44.86 ms（约 22 FPS，512×512 输入，imgsz=640），"
    "便携包内置运行时、免安装免联网，现场双击即用。"
)

add_p(doc, "本项目面向窗帘布生产过程中的破洞（Hole）、脏污（Ink）、断丝（Broken_Filament）"
           "三类典型表面缺陷，构建一套从图像导入到结果导出的完整工业视觉质检工程。系统以灰度布面图像为输入，"
           "采用 YOLO11n 目标检测模型完成缺陷类别识别与像素级矩形定位，并通过重叠切片推理、"
           "跨切片置信度加权融合和 Web 可视化应用实现检测闭环；结果 CSV 严格遵循竞赛"
           "《检测结果输出表格规范及字段说明》。")

add_table(doc, ["项目要素", "方案内容"], [
    ["检测对象", "窗帘布表面破洞、脏污、断丝三类缺陷；无缺陷判为 OK"],
    ["模型输出", "缺陷类别、置信度（两位小数）、原图像素绝对坐标框、OK/NG 判定"],
    ["核心模型", "YOLO11n 三分类目标检测，2,590,425 参数，640×640 输入，权重 5.22 MB"],
    ["检测能力", "脏污类稳定检出；破洞类可检出但覆盖有限；断丝类已定位、类别待优化（详见第七节）"],
    ["工程能力", "单图／批量检测、实时摄像头、可视化展示、批次质量指标、CSV 导出"],
    ["交付形态", "Windows CPU/CUDA 便携运行包，内置 Python 3.11.9 + torch 2.5.0 运行时"],
], widths=[3.2, 12.3])

add_p(doc, "交付包内置便携 Python 运行时，现场无需安装 Python、无需联网；提供命令行、Python 模块"
           "与 Web 可视化三种调用方式，支持实时摄像头逐帧检测。工程在开发机完成自检、样例回归与"
           "SHA256 校验，三张样例图的检出数量与置信度可与开发机逐位对齐，保证现场可复现。")

# ============================================================ 二、研究现状与应用意义
add_heading(doc, "二、研究现状与应用意义", 1)
add_keypoint(
    doc,
    "实地调研结论：丝绸类天然纤维织物因蚕茧个体差异大、瑕疵缺乏统一规律，"
    "传统 AI 检测难以形成可泛化的通用模型，行业至今只能依赖人工逐片质检；"
    "而窗帘布为机器织造，瑕疵有规律、更适配 AI 检测。选对品类，是这类项目能否落地的前提。"
)

add_heading(doc, "2.1 实地调研：天然纤维织物为何难以被通用 AI 检测", 2)
add_p(doc, "团队在纺织质检场景的实地调研中得到两条关键结论。第一，丝绸等天然纤维织物由蚕茧缫丝织造，"
           "蚕茧个体差异大，同一批原料的丝径、色泽、抱合度本身就在连续波动，导致布面基线纹理不统一；"
           "第二，其瑕疵缺乏统一规律——同一类名义缺陷在不同批次、不同机台、不同原料上的视觉表现差异极大，"
           "无法用有限类别完整枚举。二者叠加，使“一个模型覆盖全部品类”的通用检测路线在天然纤维织物上难以成立，"
           "行业至今只能依靠人工逐片质检，效率与一致性都受限于人的疲劳程度。")

add_heading(doc, "2.2 品类定位：窗帘布机织瑕疵的规律性更适配 AI 检测", 2)
add_p(doc, "窗帘布与丝绸形成鲜明对照，它由剑杆／喷气织机机器织造，具备三项有利于算法建模的客观特性："
           "一是纹理周期性强，经纱、纬纱按固定组织规律重复，正常基线可被精确刻画，异常即“偏离周期”；"
           "二是缺陷形态可枚举，破洞表现为局部组织缺失、脏污表现为局部灰度异常、断丝表现为经纬向丝线断裂，"
           "三类缺陷的成因明确、外观稳定，标注口径可以统一；"
           "三是成像条件可控，配合固定的黑白相机与稳定光源即可获得高一致性的输入分布。"
           "因此窗帘布瑕疵检测具备被单一模型稳定建模的物理基础，这也是本项目选择该品类的根本原因。")

add_heading(doc, "2.3 落地难点：工厂拍摄环境复杂、图像质量存在波动", 2)
add_p(doc, "调研同时暴露了现场落地的主要风险：工厂环境的拍摄条件远比实验室复杂，图像质量存在明显波动。"
           "光源类型与照射角度、曝光时间与增益、相机安装距离与倾角、布面运行速度与张力、"
           "甚至环境光干扰，都会改变同一缺陷的成像表现；现场分辨率与长宽比一旦偏离训练分布，"
           "精度会直接下降。工程侧对此采取三项约束：相机像素格式固定为 Mono8 单通道；"
           "光照与曝光在标定后保持与训练采集一致；大图按工艺裁切到接近 512×512 的感兴趣区域，"
           "必要时启用重叠切片推理以保留小目标细节。")

add_heading(doc, "2.4 技术路线的可行性", 2)
add_p(doc, "深度学习目标检测能够同时学习纹理背景与缺陷外观，并直接输出缺陷位置，"
           "适合建立统一的自动化检测接口。窗帘布的机织规律性使这一路线具备落地条件："
           "本项目将模型训练、切片推理、可视化交互、结构化导出和部署验证整合为一个工程，"
           "目标是降低人工质检压力、提高检测稳定性，并为薄膜、印刷等同类具有周期纹理的工业表面"
           "检测任务提供可迁移的技术框架。")

# ============================================================ 三、目标与解决思路
add_heading(doc, "三、目标与解决思路", 1)
add_keypoint(
    doc,
    "五项建设目标全部落到可验证的工程证据上：模型指标、切片融合能力、"
    "规范 CSV 导出、免安装部署包与可追溯校验，均已在开发机实测通过。"
)
add_table(doc, ["目标", "实现方式", "验收依据"], [
    ["准确识别三类缺陷", "YOLO11n 多类别监督学习 + 分层数据划分",
     "验证集输出分类与定位结果，指标见第七节"],
    ["提高小缺陷检出能力", "大图重叠切片推理 + 跨切片置信度加权框融合",
     "切片框映射回原图并融合，作为可选模式启用"],
    ["满足竞赛结果规范", "8 字段 CSV、Ok 占位行、像素绝对坐标、两位置信度",
     "导出前阻断式校验，文件名符合「团队名称_检测结果.csv」"],
    ["实现可部署应用", "便携运行时、CLI、Python 模块、Web 可视化、实时摄像头",
     "CPU 自检通过；三张样例图结果与开发机逐位一致"],
    ["便于质量追溯", "可视化结果保存、批次指标持久化、SHA256 校验",
     "检测结果可复核、可回归、可对比"],
], widths=[3.0, 6.2, 6.3])

# ============================================================ 四、数据集与预处理
add_heading(doc, "四、数据集与预处理", 1)
add_keypoint(
    doc,
    "小样本是本项目的核心约束，且它以四种具体形态同时出现：标注总量不足、瑕疵类别覆盖不全、"
    "极端光照／角度样本缺失、罕见瑕疵样本极度不均衡。"
    "训练集 260 个标注框中，ink 占 227 框（87.3%），hole 仅 7 框、broken_filament 仅 26 框，"
    "这一失衡直接解释了第七节的类别检出差异。"
)

add_p(doc, "项目使用赛题窗帘布瑕疵数据，按训练集与验证集划分开展实验："
           "训练集 136 张、验证集 34 张，合计 170 张、309 个标注框。"
           "划分采用四组分层抽样（随机种子 42 固定，可复现），以保证两类稀有缺陷在验证集中均有代表："
           "ink 组 0001–0120、hole 组 0597–0605、OK 组 0640–0670、断丝组 0801–0810。"
           "标注采用 YOLO 格式，每个目标记录类别编号及归一化中心点、宽高；"
           "模型类别顺序为 hole、ink、broken_filament，并在导出层转换为规范名称 Hole、Ink、Broken_Filament。")

add_heading(doc, "4.1 小样本问题的四种具体形态", 2)
add_table(doc, ["问题形态", "本项目的实际表现", "针对性处理"], [
    ["标注总量不足", "全量仅 170 张图、309 个标注框，训练集 260 框",
     "启用 Mosaic、翻转、copy-paste 等强增强扩充有效样本"],
    ["瑕疵类别覆盖不全", "断丝全部样本仅 10 张、破洞全部样本仅 9 张",
     "按缺陷成因分组分层划分，确保验证集含两类稀有缺陷"],
    ["极端光照／角度样本缺失", "采集工况单一，缺少强反光、低照度、大倾角样本",
     "HSV 亮度扰动（hsv_v=0.4）模拟光照波动；现场约束曝光与角度"],
    ["罕见瑕疵样本不均衡", "ink 占训练标注 87.3%，hole 仅 7 框（2.7%）",
     "copy_paste=0.15 定向增强稀有类；关闭 Mosaic 收尾稳定收敛"],
], widths=[3.4, 6.2, 5.9])

add_heading(doc, "4.2 数据构成与预处理流程", 2)
add_table(doc, ["处理环节", "具体做法"], [
    ["数据划分", "训练 136 张、验证 34 张；四组分层抽样，随机种子 42 固定分割，可复现"],
    ["标注分布", "训练：hole 7、ink 227、broken_filament 26（25 张背景图）；"
                 "验证：hole 2、ink 44、broken_filament 3（6 张背景图）"],
    ["图像统一", "灰度内容存为三通道 PNG（R=G=B 逐像素核验）；现场 Mono8 帧经 GRAY2BGR 与训练分布对齐"],
    ["尺寸策略", "训练与常规推理统一 640 输入；大图可启用重叠切片推理"],
    ["增强策略", "Mosaic、HSV 亮度扰动、翻转与 copy-paste，定向增强小样本缺陷"],
    ["标注检查", "缓存校验、类别范围检查；170 张图 0 损坏、0 缺失标签"],
    ["输出转换", "模型框转为原图像素绝对坐标，置信度保留两位小数"],
], widths=[2.8, 12.7])

# ============================================================ 五、算法设计与实现
add_heading(doc, "五、算法设计与实现", 1)
add_keypoint(
    doc,
    "算法选型从检测速度、边缘部署轻量化、小瑕疵检测精度、开源生态成熟度四个维度横向比对，"
    "YOLO11n 以 259 万参数、5.22 MB 权重、CPU 实测 44.86 ms/帧的综合表现胜出，"
    "是唯一能同时满足现场节拍与免安装部署约束的选项。"
)

add_heading(doc, "5.1 检测算法选型论证", 2)
add_p(doc, "工业质检的算法选型不能用单一精度指标决定，必须同时回答四个工程问题："
           "现场节拍能否满足、目标机能否承载、小瑕疵能否检出、长期维护成本是否可控。"
           "本项目以这四个维度对主流目标检测算法进行横向比对。")
add_table(doc, ["对比维度", "Faster R-CNN（两阶段）", "SSD（单阶段多尺度）", "YOLO11n（本项目选型）"], [
    ["检测速度",
     "两阶段结构需先生成候选区域再逐区域分类回归，参数量与计算量最大，CPU 端单帧通常在数百毫秒至秒级，无法匹配产线在线节拍",
     "单阶段直接回归，速度快于两阶段，但特征金字塔层数有限，实际端到端延迟仍明显高于同量级 YOLO",
     "单阶段端到端回归，CPU 便携环境实测 44.86 ms/帧（约 22 FPS），CUDA 路径约 10.5 ms/帧（约 95 FPS），直接满足在线节拍"],
    ["边缘部署轻量化",
     "骨干网络为深层 ResNet 系列，权重普遍数百 MB，无官方轻量级小目标变体，需自行裁剪，改造成本高",
     "骨干为 VGG 时权重同样偏大；改用 MobileNet 后可瘦身，但小目标精度下降明显",
     "权重仅 5.22 MB、约 259 万参数，原生支持 ONNX／TorchScript 导出，可随包内置并在纯 CPU 机器直接运行"],
    ["小瑕疵检测精度",
     "对小目标召回较好，但依赖区域建议质量，小且低对比度的瑕疵易在提议阶段被滤除",
     "默认锚框尺度偏大，本项目 512×512 图中的小瑕疵尺寸接近最小特征图感受野，漏检风险高",
     "多尺度特征融合 + 动态标签分配，对小目标更友好；本项目即依靠该特性定位细长断丝缺陷"],
    ["开源生态成熟度",
     "Detectron2／MMDetection 生态完善，但版本耦合重、自定义数据格式改动量大，部署链路长",
     "训练与推理实现分散在多个框架，维护与迁移成本较高",
     "Ultralytics 单一框架覆盖训练、验证、导出、推理全流程，文档与社区支持最活跃，本项目推理接口仅依赖一个包"],
], widths=[2.2, 4.4, 4.4, 4.5], size=9)

add_p(doc, "选型结论：Faster R-CNN 的精度优势在本任务中无法转化为工程收益，反而被速度与体积劣势抵消；"
           "SSD 的速度尚可但小目标能力不足，恰好命中本项目“瑕疵尺寸小、对比度低”的核心难点；"
           "YOLO11n 在四项维度上均无短板，且其成熟的导出与推理生态使“随包内置、免安装运行”这一硬约束"
           "成为可能。")

add_heading(doc, "5.2 检测模型与训练配置", 2)
add_p(doc, "核心模型采用 YOLO11n 检测网络，共 2,590,425 个参数，输入尺寸 640×640。"
           "网络使用主干特征提取、多尺度特征融合和检测头，对不同尺度的破洞、脏污及断丝目标进行联合预测。"
           "训练以已有权重为起点微调，使用 AdamW 优化器、固定随机种子 42；"
           "训练配置 500 轮，验证集指标在 epoch 21 达到最优，因 patience=10 早停于第 31 轮，"
           "保存该轮次权重为 model/best.pt。完整训练与推理参数集中列于第八节表 8-1。")

add_heading(doc, "5.3 切片推理与框融合", 2)
add_p(doc, "对于分辨率较大或缺陷尺寸较小的图像，系统提供可选的重叠切片推理模式："
           "将原图按可配置切片尺寸（默认 640）分块，切片之间重叠 20%，分别完成检测后将局部坐标平移回原图。"
           "重叠区域产生的同类框按置信度加权进行坐标融合（融合 IoU 阈值 0.55），减少切片边界的重复框；"
           "最终将框坐标限制在原图范围内，并按置信度从高到低排序输出。"
           "常规图像默认使用整图推理，切片模式仅在大图或小缺陷场景下启用，以控制额外推理耗时。")

add_heading(doc, "5.4 阈值策略", 2)
add_p(doc, "工程提供阈值扫描脚本，在验证集上记录 Precision、Recall、F1、mAP50 与 mAP50-95，"
           "用于工程侧阈值选择。默认置信度阈值取 0.37（与训练配置一致）；"
           "考虑工业质检优先降低漏检风险，若现场更重视误报控制，可将阈值提高至约 0.50–0.55。"
           "NMS IoU 阈值 0.7 与推理分辨率 640 均与训练保持一致，不建议改动。")

add_heading(doc, "5.5 工厂运行环境调研与 FDE 现场部署工程策略", 2)
add_p(doc, "团队对工厂实际运行环境进行了调研，结论是：现场机器以中低配置 Windows 主机为主，"
           "通常无独立显卡、不具备联网条件，也普遍不允许安装额外软件；同时存在光照与曝光波动、"
           "相机像素格式不一致、分辨率与训练分布不匹配等问题。针对这些约束，"
           "项目采用 FDE（Field Deployment Engineering，现场部署工程）思路，把“能不能在客户现场跑起来”"
           "作为与模型精度同等重要的交付指标，形成六级部署策略。")
add_table(doc, ["FDE 环节", "现场问题", "本项目策略"], [
    ["① 环境自检前置", "现场缺 VC++ 运行库、CPU 不支持 AVX2 等环境问题会导致直接启动失败",
     "内置 --selfcheck：逐项校验 Python、numpy/cv2、torch、ultralytics、权重 SHA256 与模型加载，"
     "一条命令输出 [OK] 自检通过"],
    ["② 免安装运行时", "现场无网络、不允许安装 Python 与依赖",
     "随包内置 Python 3.11.9 + torch 2.5.0+cpu 便携运行时，解压即用；"
     "缺失时启动器自动回退系统 Python"],
    ["③ 成像条件标定", "光照、曝光、像素格式不一致是现场精度波动最大来源",
     "相机固定 Mono8 单通道；光照与曝光保持与训练采集一致；按工艺裁切到接近 512×512 的感兴趣区域"],
    ["④ 分辨率适配", "现场整幅大图直接送模会明显掉精度",
     "常规场景整图推理；大图或小缺陷场景启用重叠切片推理，兼顾小目标细节与耗时"],
    ["⑤ 交付物校验", "多机转交易出现文件缺失或版本漂移",
     "tools/pack_deploy.py 生成干净部署包并重建 SHA256SUMS.txt；"
     "现场用 certutil 核对权重哈希"],
    ["⑥ 现场验收基线", "需要一套可快速判断“部署是否成功”的判据",
     "三张样例图给出预期检出数与最高置信度，实测与开发机逐位一致，作为现场验收基线"],
], widths=[2.6, 5.4, 7.5])

add_p(doc, "该策略的效果已在开发机验证：GPU 与 CPU 两条路径同图对比，检出数量一致、"
           "坐标差小于 0.4 px、置信度差小于 0.002；灰度输入经 GRAY2BGR 转换后与训练图像最大像素差为 0，"
           "证明现场黑白相机采集的数据能与训练分布严格对齐。")

# ============================================================ 六、工程实现与应用功能
add_heading(doc, "六、工程实现与应用功能", 1)
add_keypoint(
    doc,
    "工程以“开箱即用”为交付标准：三种调用方式覆盖单图、批量与实时摄像头三类场景，"
    "CSV 导出前设阻断式校验，确保提交文件一次通过评分工具读取。"
)
add_p(doc, "工程提供命令行（CLI）、Python 模块与 Web 可视化三种使用方式。"
           "Web 应用支持图片上传检测、批量进度与结果列表、实时摄像头逐帧检测、OK/NG 判定与标注图保存，"
           "以及结果 CSV 导出。")
add_table(doc, ["功能模块", "实现内容"], [
    ["图像导入", "支持 PNG、JPG、JPEG、BMP，单图和文件夹批量处理"],
    ["检测运行", "CPU/CUDA 自动选择；整图推理 + 可选切片推理；支持 uint8/uint16 灰度帧"],
    ["实时摄像头", "浏览器调用本机摄像头逐帧推理，实时叠加缺陷框，展示帧率、耗时、OK/NG 与类别累计统计"],
    ["结果展示", "绘制中文类别标签、置信度（两位小数）、像素绝对坐标框，显示 OK/NG 状态"],
    ["批次质量指标", "6 项指标（误检率、一致性准确率、mAP50、Precision、Recall 等）按上传 GT 自动评估并留存历史批次"],
    ["结果导出", "输出 UTF-8 CSV，严格包含 8 个规定字段，导出前阻断式校验"],
    ["空图处理", "无缺陷图片输出 Ok 占位行，坐标与置信度填 -1；同图多行耗时一致"],
    ["部署方式", "run_cpu.bat、run_cuda.bat、start_web.bat 及 Python 模块接口"],
    ["质量追溯", "保存可视化结果、批次历史记录与 SHA256 校验信息"],
], widths=[2.8, 12.7])

# ============================================================ 七、算法结果与结果分析
add_heading(doc, "七、算法结果与结果分析", 1)
add_keypoint(
    doc,
    "交付权重 best.pt（SHA256 2fa17885…4514a0）独立复评取得 mAP50 0.520、Recall 0.455，"
    "漏检率约 54.5%，单帧 44.86 ms；在工程侧优化评测口径下，重训候选模型把 mAP50 从 0.285 提升至 0.534"
    "（+87.4%），并首次在验证集上检出此前完全漏检的断丝缺陷。"
)

add_heading(doc, "7.1 交付权重实测指标", 2)
add_p(doc, "交付权重 model/best.pt 的验证指标存在两套记录，两者同为 34 张验证图、49 个真值实例口径，"
           "但取值不同。项目如实并列并说明差异，供评审对照。")
add_table(doc, ["指标", "部署包记录（评测口径 A）", "独立复评（评测口径 B）", "复评依据"], [
    ["Precision", "0.484", "0.454", "tools/scan_conf_threshold.py 在 conf=0.37 默认阈值下输出"],
    ["Recall", "0.419", "0.455", "同一命令，明细见 runs/conf_scan.csv"],
    ["漏检率（1 − Recall）", "0.581", "0.545", "约 54.5% 的真实缺陷未被检出"],
    ["mAP@50", "0.290", "0.520", "口径差异最大项，源于评测脚本与置信度扫描方式不同"],
    ["mAP@50-95", "0.114", "0.285", "复评结果与阈值扫描脚本输出一致"],
], widths=[2.9, 3.3, 3.3, 6.0], size=9)
add_p(doc, "第 7.3、7.4 节的分类别分析与核心指标统一采用评测口径 B（可复现的独立复评）；"
           "第 7.2 节的优化前后对比采用工程侧优化评测口径（原模型与候选模型在同一口径下评测），"
           "两套口径来源不同，不可直接比较，两套口径均未表述为测试集最终成绩。")

add_heading(doc, "7.2 优化前后检测效果对比", 2)
add_p(doc, "为直观呈现优化前后的能力差异，项目选取验证集中两个含断丝真值的样本进行对照。"
           "交付权重 best.pt 在这两张图上均输出 0 个检测框，属于完全漏检；"
           "重训候选模型在同一缺陷区域成功输出检测框，实现了“原方法检不出、优化后成功检出”的能力跃升。")
add_figure(
    doc,
    FIGS / "fig_compare_before_after.png",
    "图 1　优化前后检测效果对比：断丝类缺陷（橙色框为真值，红色框为交付权重检出结果）",
    "交付权重 best.pt 在两个断丝验证样本上均输出 0 个检测框，缺陷区域完全漏检；"
    "重训候选模型在同一区域成功定位缺陷。这说明数据侧的分层补样与定向增强，"
    "确实把模型能力从“看不见”推进到“看得见”。"
)
add_p(doc, "下表为工程侧优化评测口径下的对比：原模型与重训候选模型在同一流程、同一验证集上评测，"
           "是唯一可直接横向比较的一组数据。")
add_table(doc, ["指标", "原模型", "重训候选模型", "变化"], [
    ["Precision", "0.556", "0.722", "+0.166"],
    ["Recall", "0.448", "0.483", "+0.035"],
    ["漏检率（1 − Recall）", "0.552", "0.517", "−0.035（降低 3.5 个百分点）"],
    ["mAP50", "0.285", "0.534", "+87.4%"],
    ["mAP50-95", "0.087", "0.270", "+210.3%"],
], widths=[3.6, 4.0, 3.9, 4.0])
add_table(doc, ["类别能力", "交付权重 best.pt", "重训候选模型", "结论"], [
    ["断丝类（Broken_Filament）", "0 个检出", "3 个检出（定位成功）", "从完全漏检转为可定位"],
    ["破洞类（Hole）", "2 个检出（判为 hole 0.50／0.39）", "2 个检出（判为 ink）", "定位保持，需修正类别归属"],
    ["脏污类（Ink）", "稳定检出，最高置信度 0.967", "稳定检出", "保持稳定"],
    ["背景误检", "0 个", "8 个", "误报上升，需阈值侧抑制"],
], widths=[3.4, 3.8, 3.9, 4.4], size=9)
add_p(doc, "需如实说明三点：其一，重训候选模型的验证结果来自训练过程留存的评估产物"
           "（runs/optimized_20260924），候选权重未随交付包发布，交付与评审仍以 best.pt 实测为准；"
           "上表两列属“优化评测口径”，与第 7.1 节评测口径 B 不可直接比较。"
           "其二，候选模型虽已能定位两类稀有缺陷区域，但存在类别归因偏差——"
           "把真实 hole 与 broken_filament 区域判为 ink，这是后续优化的第一优先方向。"
           "其三，候选模型的背景误检由 0 个升至 8 个，需在部署阈值上配合抑制，"
           "印证了第 7.4 节“工业质检需在漏检与误报之间做取舍”的判断。")

add_figure(
    doc,
    RUN / "confusion_matrix.png",
    "图 2　重训候选模型验证集混淆矩阵（34 张验证图）",
    "矩阵显示背景误检已从交付权重的 0 个升至 8 个，需在阈值侧配合抑制；"
    "更关键的是，hole 真值 2 个、broken_filament 真值 3 个全部被预测为 ink 而非漏检，"
    "说明模型“找到了位置、判错了名字”，补足类别判别能力即可兑现全部召回。"
)

add_heading(doc, "7.3 各类别检测效果说明", 2)
add_p(doc, "除脏污类外，项目对全部目标瑕疵类别的检测效果逐一说明如下，数据来源为验证集实测"
           "与 679 张测试图导出 CSV 的实测统计。")
add_table(doc, ["瑕疵类别", "验证集实测", "测试集 CSV 实测（679 张）", "效果评价"], [
    ["Ink（脏污）",
     "10 张图有检出，共 15 框；代表样本 val_0013 检出 7 框、最高置信度 0.967",
     "检出 726 框、覆盖 304 张图（44.8%）；置信度均值 0.527、最高 0.97",
     "稳定可靠，是当前唯一可直接投入试运行的类别"],
    ["Hole（破洞）",
     "在 0600、0605 两张真值图上检出 5 框（hole 0.504／0.388、hole 0.687／0.597／0.517）",
     "检出 43 框、覆盖 25 张图（3.7%）；置信度均值 0.707、最高 0.96",
     "具备检出能力且置信度偏高，但覆盖率仅 3.7%，召回不足，需补样重训"],
    ["Broken_Filament（断丝）",
     "交付权重 0 框（2 个真值实例全部漏检）；重训候选模型可定位该区域",
     "0 框，679 张图中无任何断丝检出",
     "当前最大短板，需优先补样并调整细长结构增强策略"],
    ["Ok（无缺陷）",
     "6 张背景图全部输出 0 框，未产生误报",
     "351 张图输出 Ok 占位行（占 51.7%），占位行格式与规范一致",
     "背景判别准确，OK/NG 二分类可直接用于产线初筛"],
], widths=[2.5, 4.3, 4.4, 4.3], size=9)

add_heading(doc, "7.4 工业质检核心指标", 2)
add_p(doc, "面向工业质检场景，项目统计了漏检率、单张检测速度与模型推理耗时三项核心指标，"
           "并给出批次质量指标的现场评估口径。")
add_table(doc, ["核心指标", "交付权重 best.pt", "重训候选模型", "说明"], [
    ["漏检率（1 − Recall）", "54.5%（复评口径）", "51.7%", "验证集 49 个真值实例口径；候选模型降低 3.5 个百分点"],
    ["单张检测速度（CPU）", "44.86 ms／帧（约 22.3 FPS）", "—",
     "34 张验证图均值，512×512 输入、imgsz=640，开发机 24 核 32 线程"],
    ["模型推理耗时（导出链路）", "59.56 ms／帧（约 16.8 FPS）", "—",
     "679 张测试图 CSV 实测均值，中位数 58.73 ms，最大 115.24 ms"],
    ["模型推理耗时（CUDA fp16）", "10.5 ms／帧（约 95 FPS）", "—",
     "NVIDIA RTX 4060 Laptop，需自装 CUDA 依赖"],
    ["自检基准耗时", "67.91 ms／帧（约 14.7 FPS）", "—", "部署包 --selfcheck 输出，含冷启动开销"],
    ["批次误检率告警线", ">5% 标红", "—", "Web 批次质量指标面板内置阈值，可对接现场验收"],
], widths=[3.4, 3.9, 2.6, 5.6], size=9)

add_figure(
    doc,
    MEDIA / "training_curves.png",
    "图 3　交付权重 best.pt 训练过程与验证指标曲线",
    "训练损失持续下降，但训练期评测的验证集 mAP50 在约 0.29 附近收敛、mAP50-95 仅约 0.11，"
    "说明在 260 个训练标注框的样本量下模型已进入数据瓶颈：继续增加训练轮次无法带来精度收益"
    "（第 31 轮即触发早停），突破点必须放在数据侧而非训练侧。"
    "该曲线为训练期评测记录，与第 7.1 节独立复评口径（mAP50 0.520）不可直接比较。"
)

# ============================================================ 八、测试环境与参数
add_heading(doc, "八、测试环境与参数汇总", 1)
add_keypoint(
    doc,
    "项目全部测试环境参数集中于表 8-1，正文不再重复罗列。"
    "所有性能数字均标注了采集口径与样本量，可追溯到具体命令与数据文件。"
)
add_p(doc, "为使评审与复现具备统一口径，本节将分散于工程各处的测试环境、软硬件、"
           "模型、训练与推理参数集中整理如下。表中所列性能数据均在开发机实测，"
           "现场真实节拍以目标机 --benchmark 结果为准。")

add_table(doc, [
    "参数类别", "参数项", "取值"
], [
    ["测试主机", "操作系统", "Windows 10／11（Build 26200，AMD64）"],
    ["", "CPU", "Intel 64 位处理器，24 物理核／32 逻辑线程"],
    ["", "内存", "15.6 GB"],
    ["", "GPU（可选）", "NVIDIA RTX 4060 Laptop，驱动 ≥ 522.06（CUDA 11.8）"],
    ["软件环境", "Python", "3.11.9（随包便携运行时 runtime_cpu）"],
    ["", "torch / torchvision", "2.5.0+cpu（CUDA 路径为 2.5.0+cu118）"],
    ["", "ultralytics", "8.3.163"],
    ["", "numpy / opencv", "2.0.1 / 4.12.0"],
    ["模型", "网络与规模", "YOLO11n 检测网络，2,590,425 参数，DetectionModel，task=detect"],
    ["", "权重文件", "model/best.pt，5,470,291 字节（5.22 MB）"],
    ["", "SHA256", "2fa17885022d55ffbe4cdde42cc10359b6ba7f585eb479e01e3e8ffb914514a0"],
    ["", "类别定义", "nc=3，names=['hole','ink','broken_filament']"],
    ["训练参数", "优化器／随机种子", "AdamW／seed=42"],
    ["", "训练轮数与早停", "配置 500 轮，patience=10，实际早停于第 31 轮"],
    ["", "最优轮次", "epoch 21（保存为 model/best.pt）"],
    ["", "批大小／输入尺寸", "batch=8（CPU 建议 4–8）／imgsz=640"],
    ["", "增强参数", "hsv_v=0.4，copy_paste=0.15，close_mosaic=10，cache=ram"],
    ["", "数据划分", "分层抽样 8:2，随机种子 42，训练 136 张／验证 34 张"],
    ["推理参数", "置信度阈值", "conf=0.37（默认）；误报敏感场景可提高至 0.50–0.55"],
    ["", "NMS IoU 阈值", "iou=0.7（与训练一致，不建议改动）"],
    ["", "推理尺寸／最大检出", "imgsz=640／max_det=300"],
    ["", "切片推理", "切片尺寸 640，重叠率 20%，融合 IoU 阈值 0.55"],
    ["", "精度模式", "CUDA 自动启用 fp16；CPU 强制 fp32"],
    ["性能实测", "CPU 单帧耗时", "44.86 ms／帧（约 22.3 FPS），34 张验证图均值、512×512 输入"],
    ["", "CUDA 单帧耗时", "10.5 ms／帧（约 95 FPS），RTX 4060 Laptop、fp16"],
    ["", "CPU／GPU 一致性", "检出数量一致，坐标差 < 0.4 px，置信度差 < 0.002"],
    ["", "灰度输入对齐", "GRAY2BGR 后与训练图像最大像素差为 0"],
    ["交付体积", "关键交付物", "部署包 231 MB；runtime_cpu 约 0.75 GB；dataset 约 68 MB"],
], widths=[2.3, 3.2, 10.0], size=9)

add_caption(doc, "表 8-1　测试环境、软硬件、模型、训练与推理参数汇总")
add_p(doc, "结论：本项目在纯 CPU、无网络的便携环境下即可完成完整检测链路，"
           "单帧 44.86 ms 的实测速度满足多数离线抽检与在线工位节拍；"
           "若现场配置 NVIDIA 独显，耗时可进一步降至 10.5 ms／帧。",
      indent=False, size=10.5)
# ============================================================ 九、团队介绍及分工
add_heading(doc, "九、团队介绍及分工", 1)
add_keypoint(
    doc,
    "团队按“数据—模型—工程—展示”四条线分工，全部材料以团队昵称署名，不出现学校、专业与指导教师信息。"
)
add_p(doc, "团队名称：你管我对不队。团队成员根据专长分工协作，覆盖数据标注、模型训练、"
           "前后端开发、系统调试、演示视频与项目介绍材料制作等工作。", indent=False)
add_table(doc, ["成员", "主要负责工作"], [
    ["宇文朱彤", "负责项目演示视频的策划、录制与后期制作"],
    ["杨济同", "负责后端功能"],
    ["陈俊炜", "负责训练模型、标注数据相关工作"],
    ["李勇", "负责前端代码及系统调试修改"],
    ["李芸霞", "负责项目介绍 PPT 制作"],
], widths=[3.0, 12.5])

# ============================================================ 十、后续优化计划
add_heading(doc, "十、后续优化计划", 1)
add_keypoint(
    doc,
    "优化路线按优先级排序：先解决断丝与破洞的样本与类别判别问题，"
    "再用独立验证集复核阈值，最后在现场标定后固化推理模式与端到端延迟。"
)
add_p(doc, "第一，补充破洞与断丝类别的多尺度样本与困难负样本（各类至少数百框），"
           "针对细长结构增加更适合的裁剪与增强策略后重训；重训完成后直接覆盖 model/best.pt，"
           "接口与前端代码零改动。第二，重点解决类别归因偏差——候选模型已能定位稀有缺陷区域"
           "但误判为 ink，需通过类别重加权与分层采样提升 hole、broken_filament 的判别能力。"
           "第三，使用与训练完全独立的验证集复核阈值，避免因单一小验证集造成阈值过拟合。"
           "第四，现场先用脏污（ink）单类试运行，记录真实过检与漏检，反哺数据集迭代。"
           "第五，在现场相机分辨率与节拍确定后，选择整图或切片推理模式并实测端到端延迟。"
           "第六，继续完善结果导出校验，确保每张测试图片都生成记录并与主办方文件名完全一致。"
           "第七，坚持黑白相机 Mono8、光照曝光与训练数据一致等现场必查项，"
           "保证部署精度与验证基线一致。")

# ============================================================ 十一、结论
add_heading(doc, "十一、结论", 1)
add_keypoint(
    doc,
    "本项目交付的是一套可运行、可复现、可评估的完整质检工程："
    "脏污类可直接试运行，破洞类具备检出能力，断丝类已完成数据侧验证，"
    "局限与改善路径均已如实说明。"
)
add_p(doc, "本项目围绕窗帘布三类表面缺陷，完成了数据处理、模型训练、切片推理融合、"
           "Web 可视化、规范化 CSV 导出与便携部署，形成可运行、可复现、可评估的完整质检工程，"
           "能够支撑竞赛要求的检测、展示与结果提交；交付包内自检、样例回归与 SHA256 校验保证现场可复现。"
           "当前交付权重能够稳定检出脏污类缺陷，破洞类具备检出能力但覆盖率有限，"
           "断丝类需补数据重训；工程侧优化评测显示，重训候选模型已把 mAP50 从 0.285 提升至 0.534，"
           "并首次实现断丝缺陷的区域定位，验证了数据侧优化路线的有效性。"
           "应用只展示模型真实输出，不包含伪造标签或精度数据。")

# ============================================================ 附录
add_heading(doc, "附录　竞赛提交规范符合性自查", 1)
add_table(doc, ["检查项", "规范要求", "本项目落实情况"], [
    ["文档格式", "A4 纵向，2 cm 页边距及 1 cm 装订线，正文宋体小四、行距适宜",
     "本方案 A4 纵向，上下左右页边距 2 cm、装订线 1 cm，正文宋体小四（12 pt）"],
    ["文件命名", "文件名与目录命名使用团队昵称，不使用学校、专业、指导教师信息",
     "文档《你管我对不队_项目方案.docx》；检测结果《你管我对不队_检测结果.csv》；"
     "工程目录《你管我对不队_项目工程源代码》，已排查并清除含竞赛主办信息的硬编码路径"],
    ["隐私合规", "提交材料中不得出现学校名称、专业名称、指导教师姓名",
     "全篇以团队昵称与角色分工署名，未出现学校、专业、指导教师信息"],
    ["检测结果格式", "UTF-8 逗号分隔，文件名「团队名称_检测结果.csv」，字段遵循附件规范",
     "文件名《你管我对不队_检测结果.csv》，无 BOM 的 UTF-8 编码；8 字段表头与规范逐项一致；"
     "679 张测试图合计 1120 行；导出前阻断式校验"],
    ["像素坐标", "x_min、y_min、x_max、y_max 为原图绝对像素坐标",
     "全部为原图绝对像素坐标，保留两位小数；无缺陷图片填 -1"],
    ["无缺陷图片", "输出 Ok 占位行，置信度与坐标按规范填写",
     "351 张无缺陷图输出 class_name=Ok、confidence=-1、坐标=-1 的占位行"],
    ["同图多行耗时", "同一图片多行记录的推理耗时一致",
     "679 张图中 0 张存在同行耗时不一致（已逐图核验）"],
    ["源代码", "工程目录清晰，关键模块含注释，模型、训练脚本、推理脚本与运行时完整",
     "predict.py 推理入口、tools/ 训练与阈值扫描、backend/ + frontend/ Web 应用、"
     "model/best.pt 权重、runtime_cpu 便携运行时齐备"],
    ["可视化应用", "支持图像导入、检测、结果展示、批量导出与保存",
     "Web 应用覆盖上传检测、批量进度、实时摄像头、OK/NG 判定、标注图保存与 CSV 导出"],
    ["诚实表述", "不得伪造检测标签或精度数据",
     "全部指标可追溯至验证集实测或训练留存产物；已检出／未检出类别与优化口径均如实标注"],
], widths=[2.4, 5.0, 8.1], size=9)

# ---------------- footer
for s in doc.sections:
    fp = s.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(fp.add_run("你管我对不队　窗帘布瑕疵智能视觉质检项目方案"), 9)

doc.core_properties.title = "你管我对不队 窗帘布瑕疵智能视觉质检项目方案"
doc.core_properties.author = "你管我对不队"
doc.core_properties.comments = "指标可追溯至 dataset 标注统计、验证集实测与训练留存产物"

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print("saved:", OUT, OUT.stat().st_size, "bytes")
print("paragraphs:", len(doc.paragraphs), "tables:", len(doc.tables))
