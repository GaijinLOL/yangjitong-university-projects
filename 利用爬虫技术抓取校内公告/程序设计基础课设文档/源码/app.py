from flask import Flask, render_template
import csv
import os

# 初始化Flask应用
app = Flask(__name__,
            static_folder="tencent_news_images",  # 图片静态目录
            template_folder="templates")

# 配置项（与爬虫一致）
CSV_SAVE_PATH = "tencent_news.csv"


def read_news_data():
    """读取CSV数据（适配英文键）"""
    news_data = []
    if not os.path.exists(CSV_SAVE_PATH):
        return {"data": [], "count": 0}

    with open(CSV_SAVE_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 处理图片路径
            img_src = "no_image"
            # 本地图片
            if row["local_img_path"] not in ["not_enabled", "no", "download_failed"] and os.path.exists(
                    row["local_img_path"]):
                img_filename = os.path.basename(row["local_img_path"])
                img_src = f"/{img_filename}"
            # 在线图片（补全协议）
            elif row["img_url"] != "no_image":
                img_src = row["img_url"]
                if img_src.startswith("//"):
                    img_src = "https:" + img_src

            # 组装数据（前端展示用的变量名）
            news_data.append({
                "id": row["id"],
                "title": row["title"],
                "link": row["news_link"] if row["news_link"] != "no_link" else "#",
                "img": img_src,
                "summary": row["summary"],
                "source": row["source"],
                "crawl_time": row["crawl_time"]
            })
    return {"data": news_data, "count": len(news_data)}


@app.route('/')
def index():
    """首页展示"""
    news_info = read_news_data()
    return render_template("index.html",
                           news_list=news_info["data"],
                           total_count=news_info["count"])


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)