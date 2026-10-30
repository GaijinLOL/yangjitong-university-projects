# -*- coding: utf-8 -*-
"""【已由 make_project_plan_v2.py 取代，保留作历史版本】

本脚本生成的是方案初版，指标口径为训练期评测（原模型 mAP50 0.285）。
正式提交版请运行：

    runtime_cpu\\python.exe tools\\make_project_plan_v2.py

v2 版补齐了算法选型论证、FDE 部署策略、优化前后对比、集中参数表与图表结论，
并区分“部署包记录”与“独立复评”两套指标口径。
"""
from pathlib import Path
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'你管我对不队_项目方案.docx'
IMG=ROOT/'runs'/'optimized_20260924'

def set_font(run,size=12,bold=False,color='000000'):
    run.font.name='宋体'; run._element.rPr.rFonts.set(qn('w:eastAsia'),'宋体'); run.font.size=Pt(size); run.bold=bold; run.font.color.rgb=RGBColor.from_string(color)
def shade(cell,fill):
    tcPr=cell._tc.get_or_add_tcPr(); shd=OxmlElement('w:shd'); shd.set(qn('w:fill'),fill); tcPr.append(shd)
def table(doc,heads,rows):
    t=doc.add_table(rows=1,cols=len(heads)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.style='Table Grid'
    for c,h in zip(t.rows[0].cells,heads):
        c.text=''; p=c.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER; set_font(p.add_run(h),10,True,'FFFFFF'); shade(c,'1F4E79')
    for ri,row in enumerate(rows):
        cells=t.add_row().cells
        for i,v in enumerate(row):
            cells[i].text=''; p=cells[i].paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER if i==0 else WD_ALIGN_PARAGRAPH.LEFT; set_font(p.add_run(str(v)),9.5); cells[i].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if ri%2==1: shade(cells[i],'F2F6FA')
    doc.add_paragraph().paragraph_format.space_after=Pt(2)
def addp(doc,text,indent=True):
    p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(6); p.paragraph_format.space_after=Pt(6); p.paragraph_format.line_spacing=1
    if indent: p.paragraph_format.first_line_indent=Cm(.74)
    set_font(p.add_run(text),12); return p
def h(doc,text,level=1):
    p=doc.add_paragraph(style=f'Heading {level}'); p.paragraph_format.keep_with_next=True; set_font(p.add_run(text),16 if level==1 else 14,True); return p

d=Document(); s=d.sections[0]; s.page_width=Cm(21); s.page_height=Cm(29.7); s.top_margin=Cm(2); s.bottom_margin=Cm(2); s.left_margin=Cm(2); s.right_margin=Cm(2); s.gutter=Cm(1)
for name in ['Normal','Title','Heading 1','Heading 2','Heading 3']:
    st=d.styles[name]; st.font.name='宋体'; st._element.rPr.rFonts.set(qn('w:eastAsia'),'宋体'); st.font.color.rgb=RGBColor(0,0,0)
d.styles['Normal'].font.size=Pt(12); d.styles['Normal'].paragraph_format.line_spacing=1; d.styles['Normal'].paragraph_format.space_before=Pt(6); d.styles['Normal'].paragraph_format.space_after=Pt(6)
# cover
p=d.add_paragraph(style='Title'); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(80); set_font(p.add_run('你管我对不队\n窗帘布瑕疵智能视觉质检项目方案'),22,True)
p=d.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(30); set_font(p.add_run('参赛赛道：智能制造与工业智能 AI 视觉质检应用赛道'),14)
p=d.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(150); set_font(p.add_run('项目类别：窗帘布瑕疵检测\n提交材料：项目方案（Word）'),12)
d.add_page_break()
h(d,'一 项目概述'); addp(d,'本项目面向窗帘布生产过程中的破洞、脏污和断丝三类典型表面缺陷，构建一套可运行、可复现、可评估的工业视觉质检工程。系统以灰度布面图像为输入，采用 YOLO11n 目标检测模型完成缺陷类别识别与像素级矩形定位，并通过重叠切片推理、跨切片置信度加权融合和可视化应用实现从图像导入到结果导出的完整闭环。')
table(d,['项目要素','方案内容'],[['检测对象','窗帘布表面破洞、脏污、断丝'],['模型输出','缺陷类别、置信度、像素坐标框、OK/NG判定'],['核心模型','YOLO11n，3类目标检测'],['工程能力','单图检测、批量检测、实时摄像头、可视化展示、CSV导出'],['交付形态','Windows CPU/CUDA 便携运行包，模型与源代码可复现']])
h(d,'二 研究现状与应用意义'); addp(d,'传统窗帘布质检主要依赖人工目检，存在检测速度受限、人员疲劳导致一致性下降、细小缺陷容易漏检以及结果难以追溯等问题。窗帘布纹理具有重复性和方向性，缺陷又呈现小目标、低对比度、形态多变等特征，单纯依靠固定阈值或人工规则难以覆盖复杂工况。'); addp(d,'深度学习目标检测能够同时学习纹理背景与缺陷外观，并输出缺陷位置，适合建立统一的自动化检测接口。本项目将模型训练、切片推理、可视化交互、结构化导出和部署验证整合为一个工程，目标是降低人工质检压力，提高检测稳定性，并为纺织、薄膜、印刷等相近工业表面检测任务提供可迁移的技术框架。')
h(d,'三 目标与解决思路'); table(d,['目标','实现方式','验收依据'],[['准确识别三类缺陷','YOLO11n多类别监督学习','验证集输出分类与定位结果'],['提高小缺陷检出能力','大图重叠切片推理','切片框映射回原图并融合'],['满足竞赛结果规范','8字段CSV、Ok占位行、像素绝对坐标','导出文件可被评分工具读取'],['实现可部署应用','便携运行时、CLI、Web可视化','CPU自检和样例回归通过'],['便于质量追溯','保存可视化结果、批次CSV','检测结果可复核']])
h(d,'四 数据集与预处理'); addp(d,'项目使用赛题窗帘布瑕疵数据，按照训练集与验证集划分进行实验。当前工程包含 136 张训练图和 34 张验证图，标注采用 YOLO 格式，每个目标记录类别编号及归一化中心点、宽高。模型类别顺序为 hole、ink、broken_filament，并在竞赛导出层转换为规定名称 Hole、Ink、Broken_Filament。'); table(d,['处理环节','具体做法'],[['图像统一','灰度内容转换为三通道 BGR，保持与训练分布一致'],['尺寸策略','训练与常规推理采用 640 输入；大图可启用重叠切片'],['增强策略','Mosaic、HSV亮度扰动、翻转与 copy-paste，增强小样本缺陷'],['标注检查','缓存校验、类别范围检查、训练/验证分割固定随机种子42'],['输出转换','模型框转为原图像素绝对坐标，保留两位置信度']])
h(d,'五 算法设计与实现'); h(d,'5.1 检测模型',2); addp(d,'核心模型采用 YOLO11n 检测网络，共 2,590,425 个参数，输入尺寸 640×640。网络使用主干特征提取、多尺度特征融合和检测头，对不同尺度的破洞、脏污及断丝目标进行联合预测。训练从已有最佳权重开始微调，使用 AdamW 优化器、固定随机种子 42，并由验证集最优结果保存 best.pt。')
h(d,'5.2 切片推理与框融合',2); addp(d,'对于分辨率较大或缺陷尺寸较小的图像，系统将原图按可配置切片尺寸分块，切片之间默认重叠 20%，分别完成检测后将局部坐标平移回原图。对于重叠区域产生的同类框，按照置信度进行加权坐标融合，减少切片边界重复框；最终再限制框坐标到原图范围，并按置信度排序输出。')
h(d,'5.3 阈值策略',2); addp(d,'项目提供阈值扫描脚本，在验证集上记录 Precision、Recall、F1、mAP50 和 mAP50-95。当前基准置信度 0.37 的验证结果为 Precision 0.4541、Recall 0.4545、F1 0.4543、mAP50 0.5201、mAP50-95 0.2852。考虑工业质检优先降低漏检风险，默认部署阈值采用 0.37；若现场更重视误报控制，可提高至约 0.50–0.55。')
h(d,'六 工程实现与应用功能'); table(d,['功能模块','实现内容'],[['图像导入','支持 PNG、JPG、JPEG、BMP，单图和文件夹批量处理'],['检测运行','CPU/CUDA 自动选择，支持常规推理和切片推理'],['结果展示','绘制类别、置信度和缺陷框，显示 OK/NG 状态'],['结果导出','输出 UTF-8 CSV，严格包含8个规定字段'],['空图处理','无缺陷图片输出 Ok 占位行，坐标与置信度填 -1'],['部署方式','run_cpu.bat、run_cuda.bat、Web服务及模块接口'],['质量追溯','保存可视化结果、批次记录和SHA256校验信息']])
h(d,'七 算法结果与结果分析'); addp(d,'重新训练后的候选模型在 34 张验证图、49 个标注实例上进行评估，验证结果如下。由于验证集样本量有限，指标用于工程方案对比与阈值选择，不将其表述为测试集最终成绩。'); table(d,['指标','原模型','优化模型','变化'],[['Precision','0.556','0.722','提升'],['Recall','0.448','0.483','提升'],['mAP50','0.285','0.534','显著提升'],['mAP50-95','0.087','0.270','显著提升']])
addp(d,'从类别结果看，破洞和脏污类别具有较好的定位表现；断丝样本数量少、形态细长且与布面纹理相似，是当前最需要继续补充样本和优化增强策略的类别。切片推理有助于保留小目标细节，但会增加推理耗时，因此系统将其设计为可选模式：常规图像使用整图推理，较大图像或小缺陷场景启用切片融合。')
for fn,cap in [('results.png','图1 训练过程与验证指标曲线'),('val_batch0_pred.jpg','图2 验证集检测结果示例')]:
    if (IMG/fn).is_file():
        p=d.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run().add_picture(str(IMG/fn),width=Cm(15.5)); c=d.add_paragraph(cap); c.alignment=WD_ALIGN_PARAGRAPH.CENTER
h(d,'八 竞赛要求符合性说明'); table(d,['要求','本项目落实情况'],[['项目方案','A4纵向，2cm页边距及1cm装订线，正文宋体小四、单倍行距'],['源代码','工程目录清晰，关键模块含注释，模型、训练脚本、推理脚本和运行时完整'],['CSV结果','UTF-8逗号分隔，文件名按团队昵称_检测结果.csv，字段严格遵循附件规范'],['像素坐标','x_min、y_min、x_max、y_max均为原图绝对像素坐标'],['无缺陷图片','输出 class_name=Ok、confidence=-1、坐标=-1的占位记录'],['隐私合规','材料使用团队昵称和角色分工，不出现学校、专业、指导教师信息'],['可视化应用','支持图像导入、检测、结果展示、批量导出和保存'],['视频展示','可按“问题—算法—运行—导出—复盘”流程录制不超过10分钟演示']])
h(d,'九 团队介绍及分工'); addp(d,'团队名称：你管我对不队。团队成员根据专长分工协作，覆盖数据标注、模型训练、前后端开发、系统调试、PPT制作和视频展示等工作。',False); table(d,['成员','主要负责工作'],[['宇文朱彤','负责项目演示视频的策划、录制与后期制作'],['杨济同','负责后端功能'],['陈俊炜','负责训练模型、标注数据相关工作'],['李勇','负责前端代码及系统调试修改'],['李芸霞','负责项目介绍PPT制作']])
h(d,'十 后续优化计划'); addp(d,'第一，补充断丝类别的多尺度样本与困难负样本，针对细长结构增加更适合的裁剪和增强策略。第二，使用测试前的独立验证集复核阈值，避免因单一小验证集造成过拟合。第三，在现场相机分辨率和节拍确定后，选择整图或切片模式并测量端到端延迟。第四，继续完善结果导出校验，确保每张测试图片都生成记录并与主办方文件名完全一致。')
h(d,'十一 结论'); addp(d,'本项目围绕窗帘布三类表面缺陷，完成了数据处理、模型训练、切片推理融合、可视化应用、规范化CSV导出和便携部署。优化模型在现有验证集上相较原模型获得明显提升，工程链路能够支撑竞赛要求的检测、展示和结果提交。项目同时保留了阈值扫描、模型校验和批量导出能力，便于在测试集提交前进行最后一轮合规检查与参数确认。')
for sec in d.sections:
    p=sec.footer.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER; set_font(p.add_run('你管我对不队  项目方案'),9)
d.core_properties.title='你管我对不队 窗帘布瑕疵智能视觉质检项目方案'; d.core_properties.author='你管我对不队'; d.save(OUT); print(OUT)
