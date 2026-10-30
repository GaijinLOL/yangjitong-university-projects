from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from db import exec_many, exec_one, fetch_one, tx
from tushare_client import (
    fetch_balancesheet,
    fetch_cashflow,
    fetch_daily,
    fetch_daily_basic,
    fetch_fina_indicator,
    fetch_income,
    fetch_stock_basic,
)


def _df_to_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    # PyMySQL 无法处理 NaN/Inf，必须先转成 None
    df = df.replace([np.nan, np.inf, -np.inf], None)
    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient="records")


def _ensure_row_keys(rows: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    """
    Tushare 在权限/字段缺失时可能不返回某些列，导致 executemany 时 KeyError。
    这里统一把缺失 key 补为 None，保证入库稳定。
    """
    if not rows:
        return rows
    for r in rows:
        for k in keys:
            if k not in r:
                r[k] = None
    return rows


def upsert_stock_basic(list_status: str = "L") -> dict[str, Any]:
    df = fetch_stock_basic(list_status=list_status)
    rows = _df_to_rows(df)
    if not rows:
        return {"inserted": 0, "updated": 0, "total": 0}

    sql = """
    INSERT INTO company_basic
    (ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,list_status,list_date,delist_date,is_hs)
    VALUES
    (%(ts_code)s,%(symbol)s,%(name)s,%(area)s,%(industry)s,%(fullname)s,%(enname)s,%(cnspell)s,%(market)s,%(exchange)s,%(list_status)s,%(list_date)s,%(delist_date)s,%(is_hs)s)
    ON DUPLICATE KEY UPDATE
      symbol=VALUES(symbol),
      name=VALUES(name),
      area=VALUES(area),
      industry=VALUES(industry),
      fullname=VALUES(fullname),
      enname=VALUES(enname),
      cnspell=VALUES(cnspell),
      market=VALUES(market),
      exchange=VALUES(exchange),
      list_status=VALUES(list_status),
      list_date=VALUES(list_date),
      delist_date=VALUES(delist_date),
      is_hs=VALUES(is_hs)
    """

    with tx() as conn:
        exec_many(conn, sql, rows)
        exec_one(
            conn,
            """
            REPLACE INTO industry_stat (industry, company_count)
            SELECT industry, COUNT(*) FROM company_basic
            WHERE industry IS NOT NULL AND industry <> ''
            GROUP BY industry
            """,
        )

    return {"total": len(rows)}


def _get_last_trade_date(ts_code: str, dataset: str) -> str | None:
    with tx() as conn:
        row = fetch_one(
            conn,
            """
            SELECT last_trade_date FROM sync_state
            WHERE source='tushare' AND dataset=%(dataset)s AND key1=%(ts_code)s
            """,
            {"dataset": dataset, "ts_code": ts_code},
        )
        return row["last_trade_date"] if row else None


def _set_last_trade_date(ts_code: str, dataset: str, last_trade_date: str | None):
    with tx() as conn:
        exec_one(
            conn,
            """
            INSERT INTO sync_state (source, dataset, key1, last_trade_date, last_sync_at)
            VALUES ('tushare', %(dataset)s, %(ts_code)s, %(last_trade_date)s, %(now)s)
            ON DUPLICATE KEY UPDATE
              last_trade_date=VALUES(last_trade_date),
              last_sync_at=VALUES(last_sync_at)
            """,
            {"dataset": dataset, "ts_code": ts_code, "last_trade_date": last_trade_date, "now": datetime.now()},
        )


def sync_daily_price(ts_code: str) -> dict[str, Any]:
    last = _get_last_trade_date(ts_code, "daily_price")
    # Tushare start_date is inclusive; to avoid duplication we still upsert by PK.
    df = fetch_daily(ts_code=ts_code, start_date=last)
    rows = _df_to_rows(df)
    if not rows:
        return {"upserted": 0, "last_trade_date": last}

    sql = """
    INSERT INTO daily_price
    (ts_code,trade_date,open,high,low,close,pre_close,change_amount,pct_chg,vol,amount)
    VALUES
    (%(ts_code)s,%(trade_date)s,%(open)s,%(high)s,%(low)s,%(close)s,%(pre_close)s,%(change)s,%(pct_chg)s,%(vol)s,%(amount)s)
    ON DUPLICATE KEY UPDATE
      open=VALUES(open),high=VALUES(high),low=VALUES(low),close=VALUES(close),
      pre_close=VALUES(pre_close),change_amount=VALUES(change_amount),pct_chg=VALUES(pct_chg),
      vol=VALUES(vol),amount=VALUES(amount)
    """
    with tx() as conn:
        exec_many(conn, sql, rows)

    new_last = max(r["trade_date"] for r in rows if r.get("trade_date"))
    _set_last_trade_date(ts_code, "daily_price", new_last)
    return {"upserted": len(rows), "last_trade_date": new_last}


def sync_daily_basic(ts_code: str) -> dict[str, Any]:
    last = _get_last_trade_date(ts_code, "daily_basic")
    df = fetch_daily_basic(ts_code=ts_code, start_date=last)
    rows = _df_to_rows(df)
    if not rows:
        return {"upserted": 0, "last_trade_date": last}

    sql = """
    INSERT INTO daily_basic
    (ts_code,trade_date,turnover_rate,turnover_rate_f,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_share,float_share,free_share,total_mv,circ_mv)
    VALUES
    (%(ts_code)s,%(trade_date)s,%(turnover_rate)s,%(turnover_rate_f)s,%(volume_ratio)s,%(pe)s,%(pe_ttm)s,%(pb)s,%(ps)s,%(ps_ttm)s,%(dv_ratio)s,%(dv_ttm)s,%(total_share)s,%(float_share)s,%(free_share)s,%(total_mv)s,%(circ_mv)s)
    ON DUPLICATE KEY UPDATE
      turnover_rate=VALUES(turnover_rate),
      turnover_rate_f=VALUES(turnover_rate_f),
      volume_ratio=VALUES(volume_ratio),
      pe=VALUES(pe),
      pe_ttm=VALUES(pe_ttm),
      pb=VALUES(pb),
      ps=VALUES(ps),
      ps_ttm=VALUES(ps_ttm),
      dv_ratio=VALUES(dv_ratio),
      dv_ttm=VALUES(dv_ttm),
      total_share=VALUES(total_share),
      float_share=VALUES(float_share),
      free_share=VALUES(free_share),
      total_mv=VALUES(total_mv),
      circ_mv=VALUES(circ_mv)
    """
    with tx() as conn:
        exec_many(conn, sql, rows)

    new_last = max(r["trade_date"] for r in rows if r.get("trade_date"))
    _set_last_trade_date(ts_code, "daily_basic", new_last)
    return {"upserted": len(rows), "last_trade_date": new_last}


def _get_max_end_date(ts_code: str, table: str) -> str | None:
    with tx() as conn:
        row = fetch_one(
            conn,
            f"SELECT MAX(end_date) AS max_end_date FROM {table} WHERE ts_code=%(ts_code)s",
            {"ts_code": ts_code},
        )
        if not row:
            return None
        return row["max_end_date"]


def sync_financial_tables(ts_code: str) -> dict[str, Any]:
    start = _get_max_end_date(ts_code, "fina_indicator")
    df_fina = fetch_fina_indicator(ts_code=ts_code, start_date=start)
    df_inc = fetch_income(ts_code=ts_code, start_date=start)
    df_bal = fetch_balancesheet(ts_code=ts_code, start_date=start)
    df_cf = fetch_cashflow(ts_code=ts_code, start_date=start)

    rows_fina = _ensure_row_keys(
        _df_to_rows(df_fina),
        [
            "ts_code",
            "ann_date",
            "end_date",
            "roe",
            "roa",
            "netprofit_margin",
            "grossprofit_margin",
            "debt_to_assets",
            "current_ratio",
            "quick_ratio",
            "op_income_yoy",
            "netprofit_yoy",
            "eps",
            "bps",
            "ocf_to_or",
        ],
    )
    rows_inc = _ensure_row_keys(_df_to_rows(df_inc), ["ts_code", "ann_date", "end_date", "revenue", "n_income", "operate_profit", "total_profit"])
    rows_bal = _ensure_row_keys(
        _df_to_rows(df_bal),
        ["ts_code", "ann_date", "end_date", "total_assets", "total_liab", "total_hldr_eqy_exc_min_int", "inventories", "accounts_receiv", "monetary_cap"],
    )
    rows_cf = _ensure_row_keys(
        _df_to_rows(df_cf),
        ["ts_code", "ann_date", "end_date", "n_cashflow_act", "n_cashflow_inv_act", "n_cash_flows_fnc_act", "free_cashflow"],
    )

    with tx() as conn:
        if rows_fina:
            exec_many(
                conn,
                """
                INSERT INTO fina_indicator
                (ts_code,end_date,ann_date,roe,roa,netprofit_margin,grossprofit_margin,debt_to_assets,current_ratio,quick_ratio,op_income_yoy,netprofit_yoy,eps,bps,ocf_to_or)
                VALUES
                (%(ts_code)s,%(end_date)s,%(ann_date)s,%(roe)s,%(roa)s,%(netprofit_margin)s,%(grossprofit_margin)s,%(debt_to_assets)s,%(current_ratio)s,%(quick_ratio)s,%(op_income_yoy)s,%(netprofit_yoy)s,%(eps)s,%(bps)s,%(ocf_to_or)s)
                ON DUPLICATE KEY UPDATE
                  ann_date=VALUES(ann_date),
                  roe=VALUES(roe),roa=VALUES(roa),
                  netprofit_margin=VALUES(netprofit_margin),
                  grossprofit_margin=VALUES(grossprofit_margin),
                  debt_to_assets=VALUES(debt_to_assets),
                  current_ratio=VALUES(current_ratio),
                  quick_ratio=VALUES(quick_ratio),
                  op_income_yoy=VALUES(op_income_yoy),
                  netprofit_yoy=VALUES(netprofit_yoy),
                  eps=VALUES(eps),
                  bps=VALUES(bps),
                  ocf_to_or=VALUES(ocf_to_or)
                """,
                rows_fina,
            )

        if rows_inc:
            exec_many(
                conn,
                """
                INSERT INTO financial_income
                (ts_code,end_date,ann_date,revenue,n_income,operate_profit,total_profit)
                VALUES
                (%(ts_code)s,%(end_date)s,%(ann_date)s,%(revenue)s,%(n_income)s,%(operate_profit)s,%(total_profit)s)
                ON DUPLICATE KEY UPDATE
                  ann_date=VALUES(ann_date),
                  revenue=VALUES(revenue),
                  n_income=VALUES(n_income),
                  operate_profit=VALUES(operate_profit),
                  total_profit=VALUES(total_profit)
                """,
                rows_inc,
            )

        if rows_bal:
            exec_many(
                conn,
                """
                INSERT INTO financial_balancesheet
                (ts_code,end_date,ann_date,total_assets,total_liab,total_hldr_eqy_exc_min_int,inventories,accounts_receiv,monetary_cap)
                VALUES
                (%(ts_code)s,%(end_date)s,%(ann_date)s,%(total_assets)s,%(total_liab)s,%(total_hldr_eqy_exc_min_int)s,%(inventories)s,%(accounts_receiv)s,%(monetary_cap)s)
                ON DUPLICATE KEY UPDATE
                  ann_date=VALUES(ann_date),
                  total_assets=VALUES(total_assets),
                  total_liab=VALUES(total_liab),
                  total_hldr_eqy_exc_min_int=VALUES(total_hldr_eqy_exc_min_int),
                  inventories=VALUES(inventories),
                  accounts_receiv=VALUES(accounts_receiv),
                  monetary_cap=VALUES(monetary_cap)
                """,
                rows_bal,
            )

        if rows_cf:
            exec_many(
                conn,
                """
                INSERT INTO financial_cashflow
                (ts_code,end_date,ann_date,n_cashflow_act,n_cashflow_inv_act,n_cash_flows_fnc_act,free_cashflow)
                VALUES
                (%(ts_code)s,%(end_date)s,%(ann_date)s,%(n_cashflow_act)s,%(n_cashflow_inv_act)s,%(n_cash_flows_fnc_act)s,%(free_cashflow)s)
                ON DUPLICATE KEY UPDATE
                  ann_date=VALUES(ann_date),
                  n_cashflow_act=VALUES(n_cashflow_act),
                  n_cashflow_inv_act=VALUES(n_cashflow_inv_act),
                  n_cash_flows_fnc_act=VALUES(n_cash_flows_fnc_act),
                  free_cashflow=VALUES(free_cashflow)
                """,
                rows_cf,
            )

    return {
        "fina_indicator": len(rows_fina),
        "income": len(rows_inc),
        "balancesheet": len(rows_bal),
        "cashflow": len(rows_cf),
        "start_date_used": start,
    }


def save_research_report(ts_code: str, report_date: str, title: str, summary: str, source: str | None = None, rating: str | None = None):
    with tx() as conn:
        exec_one(
            conn,
            """
            INSERT INTO research_report (ts_code, report_date, source, title, summary, rating)
            VALUES (%(ts_code)s, %(report_date)s, %(source)s, %(title)s, %(summary)s, %(rating)s)
            """,
            {
                "ts_code": ts_code,
                "report_date": report_date,
                "source": source,
                "title": title,
                "summary": summary,
                "rating": rating,
            },
        )


def save_exchange_fin_abstract(ts_code: str, end_date: str, exchange: str, url: str | None, abstract: str | None):
    with tx() as conn:
        exec_one(
            conn,
            """
            INSERT INTO exchange_fin_report (ts_code, end_date, exchange, url, abstract)
            VALUES (%(ts_code)s, %(end_date)s, %(exchange)s, %(url)s, %(abstract)s)
            ON DUPLICATE KEY UPDATE url=VALUES(url), abstract=VALUES(abstract)
            """,
            {"ts_code": ts_code, "end_date": end_date, "exchange": exchange, "url": url, "abstract": abstract},
        )


def get_fusion_context(ts_code: str, limit: int = 3) -> dict[str, Any]:
    """
    为 LLM/报告提供融合上下文：研报 + 财报摘要（示例表，后续可扩展为爬虫/解析结果）。
    """
    with tx() as conn:
        rr = conn.cursor()
        # Research reports
        rr.execute(
            """
            SELECT report_date, source, title, summary, rating
            FROM research_report
            WHERE ts_code=%s
            ORDER BY report_date DESC
            LIMIT %s
            """,
            (ts_code, limit),
        )
        research = list(rr.fetchall())
        # Exchange financial abstracts
        rr.execute(
            """
            SELECT end_date, exchange, url, abstract
            FROM exchange_fin_report
            WHERE ts_code=%s
            ORDER BY end_date DESC
            LIMIT %s
            """,
            (ts_code, limit),
        )
        exchange_fin = list(rr.fetchall())

    return {"research_reports": research, "exchange_fin_reports": exchange_fin}

