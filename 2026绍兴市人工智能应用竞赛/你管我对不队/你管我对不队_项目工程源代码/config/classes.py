"""竞赛展示和落盘使用的统一类别配置。"""

TEAM_NAME = "你管我对不队"
CLASS_NAME_ZH = {
    "Hole": "破洞",
    "Ink": "脏污",
    "Broken_Filament": "断丝",
    "Surface_Crack": "表面裂纹",
    "Ok": "合格",
}

# 当前权重输出与竞赛规范类别名之间的唯一转换入口。
MODEL_CLASS_TO_STANDARD = {
    "hole": "Hole",
    "ink": "Ink",
    "broken_filament": "Broken_Filament",
    "Surface_Crack": "Surface_Crack",
}

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
CSV_HEADERS = [
    "image_id", "class_name", "confidence", "x_min", "y_min", "x_max", "y_max",
    "inference_time_ms",
]
