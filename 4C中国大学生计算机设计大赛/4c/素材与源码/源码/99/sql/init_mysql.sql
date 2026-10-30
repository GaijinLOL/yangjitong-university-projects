-- 初始化数据库与表结构（MySQL 8.x）
-- 默认账号密码：root/root；库名：enterprise_analysis

CREATE DATABASE IF NOT EXISTS enterprise_analysis
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE enterprise_analysis;

-- 同步状态（用于增量更新与去重）
CREATE TABLE IF NOT EXISTS sync_state (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  source VARCHAR(64) NOT NULL,
  dataset VARCHAR(64) NOT NULL,
  key1 VARCHAR(128) NULL,
  last_trade_date VARCHAR(16) NULL,
  last_sync_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_sync_state (source, dataset, key1)
) ENGINE=InnoDB;

-- 企业基础信息（Tushare: stock_basic）
CREATE TABLE IF NOT EXISTS company_basic (
  ts_code VARCHAR(16) PRIMARY KEY,
  symbol VARCHAR(16) NULL,
  name VARCHAR(64) NULL,
  area VARCHAR(32) NULL,
  industry VARCHAR(64) NULL,
  fullname VARCHAR(128) NULL,
  enname VARCHAR(128) NULL,
  cnspell VARCHAR(64) NULL,
  market VARCHAR(32) NULL,
  exchange VARCHAR(16) NULL,
  list_status VARCHAR(8) NULL,
  list_date VARCHAR(16) NULL,
  delist_date VARCHAR(16) NULL,
  is_hs VARCHAR(8) NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_industry (industry),
  INDEX idx_area (area)
) ENGINE=InnoDB;

-- 行业分类（简单版：从 company_basic industry 派生 + 可扩展指数行业）
CREATE TABLE IF NOT EXISTS industry_stat (
  industry VARCHAR(64) PRIMARY KEY,
  company_count INT NOT NULL DEFAULT 0,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 日行情（Tushare: daily）
CREATE TABLE IF NOT EXISTS daily_price (
  ts_code VARCHAR(16) NOT NULL,
  trade_date VARCHAR(16) NOT NULL,
  open DECIMAL(12,4) NULL,
  high DECIMAL(12,4) NULL,
  low DECIMAL(12,4) NULL,
  close DECIMAL(12,4) NULL,
  pre_close DECIMAL(12,4) NULL,
  change_amount DECIMAL(12,4) NULL,
  pct_chg DECIMAL(10,4) NULL,
  vol DECIMAL(18,4) NULL,
  amount DECIMAL(18,4) NULL,
  PRIMARY KEY (ts_code, trade_date),
  INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB;

-- 日度基础指标（Tushare: daily_basic）
CREATE TABLE IF NOT EXISTS daily_basic (
  ts_code VARCHAR(16) NOT NULL,
  trade_date VARCHAR(16) NOT NULL,
  turnover_rate DECIMAL(10,4) NULL,
  turnover_rate_f DECIMAL(10,4) NULL,
  volume_ratio DECIMAL(10,4) NULL,
  pe DECIMAL(12,4) NULL,
  pe_ttm DECIMAL(12,4) NULL,
  pb DECIMAL(12,4) NULL,
  ps DECIMAL(12,4) NULL,
  ps_ttm DECIMAL(12,4) NULL,
  dv_ratio DECIMAL(10,4) NULL,
  dv_ttm DECIMAL(10,4) NULL,
  total_share DECIMAL(18,4) NULL,
  float_share DECIMAL(18,4) NULL,
  free_share DECIMAL(18,4) NULL,
  total_mv DECIMAL(18,4) NULL,
  circ_mv DECIMAL(18,4) NULL,
  PRIMARY KEY (ts_code, trade_date),
  INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB;

-- 财务指标（Tushare: fina_indicator）
CREATE TABLE IF NOT EXISTS fina_indicator (
  ts_code VARCHAR(16) NOT NULL,
  end_date VARCHAR(16) NOT NULL,
  ann_date VARCHAR(16) NULL,
  roe DECIMAL(12,6) NULL,
  roa DECIMAL(12,6) NULL,
  netprofit_margin DECIMAL(12,6) NULL,
  grossprofit_margin DECIMAL(12,6) NULL,
  debt_to_assets DECIMAL(12,6) NULL,
  current_ratio DECIMAL(12,6) NULL,
  quick_ratio DECIMAL(12,6) NULL,
  op_income_yoy DECIMAL(12,6) NULL,
  netprofit_yoy DECIMAL(12,6) NULL,
  eps DECIMAL(12,6) NULL,
  bps DECIMAL(12,6) NULL,
  ocf_to_or DECIMAL(12,6) NULL,
  PRIMARY KEY (ts_code, end_date),
  INDEX idx_end_date (end_date)
) ENGINE=InnoDB;

-- 三大报表（可用于更深的运营分析与风险指标构造）
CREATE TABLE IF NOT EXISTS financial_income (
  ts_code VARCHAR(16) NOT NULL,
  end_date VARCHAR(16) NOT NULL,
  ann_date VARCHAR(16) NULL,
  revenue DECIMAL(20,4) NULL,
  n_income DECIMAL(20,4) NULL,
  operate_profit DECIMAL(20,4) NULL,
  total_profit DECIMAL(20,4) NULL,
  PRIMARY KEY (ts_code, end_date),
  INDEX idx_end_date (end_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS financial_balancesheet (
  ts_code VARCHAR(16) NOT NULL,
  end_date VARCHAR(16) NOT NULL,
  ann_date VARCHAR(16) NULL,
  total_assets DECIMAL(20,4) NULL,
  total_liab DECIMAL(20,4) NULL,
  total_hldr_eqy_exc_min_int DECIMAL(20,4) NULL,
  inventories DECIMAL(20,4) NULL,
  accounts_receiv DECIMAL(20,4) NULL,
  monetary_cap DECIMAL(20,4) NULL,
  PRIMARY KEY (ts_code, end_date),
  INDEX idx_end_date (end_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS financial_cashflow (
  ts_code VARCHAR(16) NOT NULL,
  end_date VARCHAR(16) NOT NULL,
  ann_date VARCHAR(16) NULL,
  n_cashflow_act DECIMAL(20,4) NULL,
  n_cashflow_inv_act DECIMAL(20,4) NULL,
  n_cash_flows_fnc_act DECIMAL(20,4) NULL,
  free_cashflow DECIMAL(20,4) NULL,
  PRIMARY KEY (ts_code, end_date),
  INDEX idx_end_date (end_date)
) ENGINE=InnoDB;

-- 研报（占位：支持比赛扩展；可后续接入第三方/交易所披露）
CREATE TABLE IF NOT EXISTS research_report (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ts_code VARCHAR(16) NOT NULL,
  report_date VARCHAR(16) NOT NULL,
  source VARCHAR(64) NULL,
  title VARCHAR(256) NULL,
  summary TEXT NULL,
  rating VARCHAR(32) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ts_code_date (ts_code, report_date)
) ENGINE=InnoDB;

-- 交易所财报融合（占位：可存储财报关键摘要/链接/解析结果）
CREATE TABLE IF NOT EXISTS exchange_fin_report (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ts_code VARCHAR(16) NOT NULL,
  end_date VARCHAR(16) NOT NULL,
  exchange VARCHAR(16) NULL,
  url VARCHAR(512) NULL,
  abstract TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_exchange_fin (ts_code, end_date, exchange)
) ENGINE=InnoDB;

-- 运营指标（自动计算结果，供前端与大模型直接使用）
CREATE TABLE IF NOT EXISTS enterprise_metrics (
  ts_code VARCHAR(16) NOT NULL,
  end_date VARCHAR(16) NOT NULL,
  industry VARCHAR(64) NULL,
  profitability_score DECIMAL(10,4) NULL,
  solvency_score DECIMAL(10,4) NULL,
  growth_score DECIMAL(10,4) NULL,
  risk_score DECIMAL(10,4) NULL,
  diagnosis_json JSON NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (ts_code, end_date),
  INDEX idx_industry (industry),
  INDEX idx_end_date (end_date)
) ENGINE=InnoDB;

