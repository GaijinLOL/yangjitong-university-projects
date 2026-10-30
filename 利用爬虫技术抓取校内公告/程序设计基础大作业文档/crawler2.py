import requests
from lxml import etree
import csv
import time
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# -------------------------- 通用配置项 --------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9"
}
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB_NAME = "school_news_db"  # 共用数据库
DELAY = 1  # 防反爬延迟

# -------------------------- 科艺要闻配置 --------------------------
KYYW_TARGET_URL = "https://www.ky.zstu.edu.cn/kyyw.htm"
KYYW_CSV_PATH = "浙江理工科技与艺术学院科艺要闻.csv"
KYYW_MONGO_COL = "kyyw_news"

# -------------------------- 校园经纬配置（新增） --------------------------
XYJW_TARGET_URL = "https://www.ky.zstu.edu.cn/xyjw.htm"  # 对应你提供的页面URL
XYJW_CSV_PATH = "浙江理工科技与艺术学院校园经纬.csv"
XYJW_MONGO_COL = "xyjw_news"


# -------------------------- 通用数据抓取函数 --------------------------
def fetch_news_data(target_url, tag_name):
    """通用新闻抓取解析函数（适配科艺要闻/校园经纬）"""
    try:
        time.sleep(DELAY)
        # 发送请求
        response = requests.get(
            url=target_url,
            headers=HEADERS,
            timeout=15,
            verify=False
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        html = etree.HTML(response.text)

        # 定位新闻条目（页面结构与原科艺要闻一致）
        news_items = html.xpath('//div[@class="wlistee"]/ul/li')
        if not news_items:
            print(f"❌ 未找到【{tag_name}】条目，请检查网页结构")
            return []

        news_list = []
        for item in news_items:
            # 提取标签+标题（如【校园经纬】xxx）
            a_text = item.xpath('.//a/text()')[0].strip() if item.xpath('.//a/text()') else ""
            tag = a_text[:6]  # 标签固定6个字符（如【校园经纬】）
            title = a_text[6:].strip()

            # 提取并拼接链接
            link = item.xpath('.//a/@href')[0].strip() if item.xpath('.//a/@href') else ""
            if link and not link.startswith(("http://", "https://")):
                link = f"https://www.ky.zstu.edu.cn/{link}"

            # 提取发布日期
            publish_date = item.xpath('.//span/text()')[0].strip() if item.xpath('.//span/text()') else ""

            # 组装数据
            news_list.append({
                "tag": tag,
                "title": title,
                "link": link,
                "publish_date": publish_date
            })
            print(f"✅ 【{tag_name}】解析完成：{title} | {publish_date}")

        return news_list

    except requests.exceptions.RequestException as e:
        print(f"❌ 【{tag_name}】请求失败：{str(e)}")
        return []
    except Exception as e:
        print(f"❌ 【{tag_name}】解析失败：{str(e)}")
        return []


# -------------------------- 通用数据保存函数 --------------------------
def save_to_csv(data_list, csv_path):
    """通用CSV保存函数"""
    if not data_list:
        print(f"❌ 无数据可保存至{csv_path}")
        return
    fields = ["tag", "title", "link", "publish_date"]
    try:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data_list)
        print(f"✅ 已保存至CSV：{csv_path}")
    except Exception as e:
        print(f"❌ CSV保存失败：{str(e)}")


def save_to_mongo(data_list, collection_name):
    """通用MongoDB保存函数（自动去重）"""
    if not data_list:
        print(f"❌ 无数据可保存至Mongo集合{collection_name}")
        return
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        col = db[collection_name]

        # 去重（标题+日期唯一）
        existing = set((item["title"], item["publish_date"]) for item in col.find({}, {"title":1, "publish_date":1}))
        unique_data = [item for item in data_list if (item["title"], item["publish_date"]) not in existing]

        if not unique_data:
            print(f"✅ 【{collection_name}】无新增数据（已去重）")
            client.close()
            return

        # 批量插入
        result = col.insert_many(unique_data)
        print(f"✅ MongoDB集合{collection_name}插入{len(result.inserted_ids)}条数据")
        client.close()

    except PyMongoError as e:
        print(f"❌ MongoDB操作失败：{str(e)}")
    except Exception as e:
        print(f"❌ 连接MongoDB失败：{str(e)}")


# -------------------------- 主程序（同时爬取两个页面） --------------------------
def main():
    print("=== 开始抓取浙江理工科技与艺术学院新闻 ===")

    # 1. 爬取科艺要闻
    print("\n--- 【科艺要闻】抓取开始 ---")
    kyyw_data = fetch_news_data(KYYW_TARGET_URL, "科艺要闻")
    if kyyw_data:
        save_to_csv(kyyw_data, KYYW_CSV_PATH)
        save_to_mongo(kyyw_data, KYYW_MONGO_COL)
    else:
        print("--- 【科艺要闻】无数据 ---")

    # 2. 爬取校园经纬（新增）
    print("\n--- 【校园经纬】抓取开始 ---")
    xyjw_data = fetch_news_data(XYJW_TARGET_URL, "校园经纬")
    if xyjw_data:
        save_to_csv(xyjw_data, XYJW_CSV_PATH)
        save_to_mongo(xyjw_data, XYJW_MONGO_COL)
    else:
        print("--- 【校园经纬】无数据 ---")

    print("\n=== 所有抓取任务完成 ===")


if __name__ == "__main__":
    main()