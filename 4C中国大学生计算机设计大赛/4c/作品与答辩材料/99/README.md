# 智策：企业经营分析与决策支持系统（本地可部署）

技术栈：Flask + MySQL + Tushare + 通义千问（DashScope）+ Bootstrap + ECharts

> 说明：为避免密钥泄露，本项目**不在源码中明文写死真实密钥**。你只需要把密钥写入本地 `.env`（或通过环境变量注入），即可一键启动并本地使用（除 Tushare/大模型需要联网）。

---

## 项目定位

本项目的**主主题是企业经营分析展示与决策支持**，面向：

- 企业管理者
- 业务分析人员
- 产品演示与方案汇报场景
- 需要将结构化数据转化为可解释分析结果的使用者

在此基础上，系统也可**兼顾上市公司研究与投资辅助参考**，帮助用户从企业经营、财务表现、估值变化和风险提示等角度理解公司基本面；但这不是系统的核心定位，也**不构成投资建议或买卖指导**。

系统同时加入了：

- **抗幻觉约束**：强调仅基于本地已同步数据回答，对缺失数据明确说明
- **四灯置信度机制**：用红 / 黄 / 蓝 / 绿展示分析结果的可信程度与数据完整度

---

## 目录结构

```text
enterprise-agent-ops/
  backend/
    app.py
    config.py
    db.py
    llm.py
    tushare_client.py
    services/
      analytics.py
      cache_sync.py
      report.py
    templates/
      base.html
      index.html
      company.html
      qa.html
      dashboard.html
      report.html
    static/
      css/app.css
      js/app.js
      js/charts.js
  sql/
    init_mysql.sql
  scripts/
    start_windows.ps1
    start_mac_linux.sh
  requirements.txt
  .env.example
```

---

## 1) 环境准备

### Windows
- 安装 Python 3.10+（建议 3.11）
- 安装并启动 MySQL 8.x（确保端口 3306）

### macOS / Linux
- 安装 Python 3.10+
- 安装并启动 MySQL 8.x（确保端口 3306）

---

## 2) 配置密钥（必须）

复制一份示例配置为 `.env`：

```bash
cp .env.example .env
```

然后把你的密钥填进去：

- `DASHSCOPE_API_KEY`
- `TUSHARE_TOKEN`

MySQL 默认使用：

- host: `localhost`
- port: `3306`
- user: `root`
- password: `root`
- database: `enterprise_analysis`

如你本机不同，也可在 `.env` 中覆盖。

---

## 3) 初始化 MySQL

使用 MySQL 客户端执行初始化脚本（建库、建表、索引）：

```bash
mysql -uroot -proot < sql/init_mysql.sql
```

---

## 4) 一键启动

### Windows（PowerShell）

```powershell
cd "C:\Users\Lenovo\Desktop\99"
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start_windows.ps1
```

### macOS / Linux

```bash
chmod +x scripts/start_mac_linux.sh
./scripts/start_mac_linux.sh
```

启动后访问：

- 首页：`http://127.0.0.1:5000/`

---

## 5) 功能说明

### 核心能力（主线）

- **数据层**：拉取并缓存企业基础信息、行情、估值、财务指标；支持本地缓存、增量更新、去重和本地查询。
- **分析层**：计算盈利、偿债、成长、风险等多维运营指标，支持企业经营状态的结构化展示。
- **智能问答**：围绕企业经营分析、风险识别和后续建议进行自然语言问答，并提示数据边界与置信度。
- **报告生成**：自动输出适合展示、汇报和讨论使用的结构化经营分析报告。
- **可视化展示**：通过 ECharts 展示价格、估值、财务趋势和多维评分，增强分析表达效果。

### 扩展能力（辅助）

- 可从上市公司视角补充观察价格、估值和风险变化
- 可为普通投资者提供基本面研究辅助参考
- 输出结果仅作分析辅助，不替代投资决策

---

## 6) 使用建议

推荐的使用路径如下：

1. 先同步企业基础信息
2. 搜索目标企业并同步个股数据
3. 查看可视化分析看板
4. 使用智能问答获取结构化解释
5. 生成经营分析报告用于展示或讨论

如果需要补充投资者参考，可进一步查看：

- 价格趋势
- 估值与市值变化
- 财务关键指标趋势
- 风险评分与风险提示

---

## 常见问题

### Q: 没有密钥能跑吗？
A: 页面与数据库结构可以运行；但 Tushare 拉数与大模型问答需要联网与有效密钥。

### Q: 这个项目是不是投资建议系统？
A: 不是。本项目的核心定位是企业经营分析展示与决策支持；涉及上市公司观察的部分仅作辅助参考，不构成投资建议。
