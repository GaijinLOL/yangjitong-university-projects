from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from lxml import etree
import csv
import time
from pymongo import MongoClient
import requests
import os

# -------------------------- 配置项 --------------------------
TENCENT_NEWS_URL = "https://news.qq.com"
CSV_SAVE_PATH = "tencent_news.csv"  # 简化文件名（英文）
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB_NAME = "tencent_news_db"
MONGO_COLLECTION_NAME = "tencent_news_list"
IMAGE_SAVE_DIR = "tencent_news_images"
DOWNLOAD_IMAGES = True  # 开启图片下载（测试用）

# 创建图片保存目录
if DOWNLOAD_IMAGES and not os.path.exists(IMAGE_SAVE_DIR):
    os.makedirs(IMAGE_SAVE_DIR)


def crawl_tencent_news():
    print("开始加载腾讯新闻首页...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    try:
        driver.get(TENCENT_NEWS_URL)
        # 等待核心新闻列表加载
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "channel-feed-item")]'))
        )
        time.sleep(3)  # 等待图片资源加载
        html = etree.HTML(driver.page_source)
        news_list = []

        # 匹配新闻条目
        news_items = html.xpath('//div[contains(@class, "channel-feed-item")]')
        if not news_items:
            print("❌ 未找到新闻条目")
            return []

        # 解析每个新闻条目（全英文键）
        for idx, item in enumerate(news_items, 1):
            # 1. 提取标题
            title = item.xpath('.//span[contains(@class, "hot-article-title-text")]/text()')
            if not title:
                title = item.xpath('.//span[contains(@class, "question-title-text")]/text()')
            if not title:
                title = item.xpath('.//span[contains(@class, "article-title-text")]/text()')
            title = title[0].strip() if title else "no_title"

            # 2. 提取新闻链接（空链接替换为no_link）
            link = item.xpath('.//a[contains(@class, "article-base-info")]/@href')
            if not link:
                link = item.xpath('.//a[contains(@class, "question-title")]/@href')
            if not link:
                link = item.xpath('.//div[contains(@class, "article-cover")]/a/@href')
            link = link[0].strip() if link else "no_link"

            # 3. 提取图片URL
            img_url = item.xpath('.//img[contains(@class, "article-image")]/@src')
            if not img_url:
                img_url = item.xpath('.//img[contains(@class, "article-picture")]/@src')
            if not img_url:
                img_url = item.xpath('.//div[contains(@class, "answer-desc")]//img/@src')
            img_url = img_url[0].strip() if img_url else "no_image"

            # 4. 提取摘要
            summary = item.xpath('.//div[contains(@class, "answer-desc")]/text()')
            if not summary:
                summary = item.xpath('.//div[contains(@class, "hot-article-desc")]/text()')
            summary = ''.join([s.strip() for s in summary]) if summary else title

            # 5. 下载图片
            local_img_path = "not_enabled"
            if DOWNLOAD_IMAGES and img_url != "no_image":
                try:
                    img_filename = f"news_img_{idx}_{int(time.time())}.jpg"
                    local_img_path = os.path.join(IMAGE_SAVE_DIR, img_filename)
                    response = requests.get(img_url, timeout=10, stream=True)
                    if response.status_code == 200:
                        with open(local_img_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=1024):
                                if chunk:
                                    f.write(chunk)
                    else:
                        local_img_path = "download_failed"
                except Exception as e:
                    local_img_path = f"error: {str(e)[:20]}"

            # 构建新闻数据（全英文键，符合MongoDB规范）
            news_info = {
                "id": idx,  # 原“序号”
                "title": title,  # 原“标题”
                "news_link": link,  # 原“新闻链接”
                "img_url": img_url,  # 原“图片URL”
                "local_img_path": local_img_path,  # 原“本地图片路径”
                "source": "Tencent News",  # 原“来源”（英文更规范）
                "summary": summary,  # 原“摘要”
                "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S")  # 原“抓取时间”
            }
            news_list.append(news_info)
            print(f"✅ 第{idx}条：{title} | 图片：{img_url[:30]}...")

        print(f"\n✅ 共爬取 {len(news_list)} 条新闻")
        return news_list
    except Exception as e:
        print(f"❌ 爬取出错：{str(e)}")
        return []
    finally:
        driver.quit()


def save_to_csv(news_list):
    """保存到CSV（英文表头）"""
    if not news_list:
        print("❌ 无数据保存到CSV")
        return
    # 全英文表头
    fieldnames = ["id", "title", "news_link", "img_url", "local_img_path", "source", "summary", "crawl_time"]
    with open(CSV_SAVE_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(news_list)
    print(f"✅ CSV已保存到：{CSV_SAVE_PATH}")


def save_to_mongodb(news_list):
    """保存到MongoDB（全英文键）"""
    if not news_list:
        print("❌ 无数据保存到MongoDB")
        return
    try:
        client = MongoClient(MONGO_URI)
        client.admin.command('ping')  # 测试连接
        db = client[MONGO_DB_NAME]
        col = db[MONGO_COLLECTION_NAME]

        # 去重逻辑（英文键匹配）
        existing = set()
        for item in col.find({}, {"title": 1, "news_link": 1}):
            title = item.get("title", "no_title")
            news_link = item.get("news_link", "no_link")
            existing.add((title, news_link))

        new_news = []
        for n in news_list:
            key = (n["title"], n["news_link"])
            if key not in existing:
                new_news.append(n)

        if new_news:
            col.insert_many(new_news)
            print(f"✅ MongoDB新增 {len(new_news)} 条数据")
        else:
            print("✅ 无新增数据（已去重）")
        client.close()
    except Exception as e:
        print(f"❌ MongoDB保存失败：{str(e)}")
        print("💡 排查建议：1. 检查MongoDB是否启动 2. 确认本地27017端口未被占用")


if __name__ == "__main__":
    print("=" * 50)
    print("    Tencent News Crawler (English Field Version)")
    print("=" * 50)
    print(f"📌 图片下载：{'Enabled' if DOWNLOAD_IMAGES else 'Disabled'}")
    if DOWNLOAD_IMAGES:
        print(f"📌 图片目录：{os.path.abspath(IMAGE_SAVE_DIR)}")
    print("-" * 50)

    news_data = crawl_tencent_news()
    if news_data:
        save_to_csv(news_data)
        save_to_mongodb(news_data)
    print("\n✅ 操作完成！")