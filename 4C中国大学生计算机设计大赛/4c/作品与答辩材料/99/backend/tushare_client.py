from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import tushare as ts

from config import Config


@dataclass(frozen=True)
class TushareDatasets:
    STOCK_BASIC: str = "stock_basic"
    DAILY: str = "daily"
    DAILY_BASIC: str = "daily_basic"
    FINA_INDICATOR: str = "fina_indicator"
    INCOME: str = "income"
    BALANCESHEET: str = "balancesheet"
    CASHFLOW: str = "cashflow"


def _pro() -> Any:
    if not Config.TUSHARE_TOKEN:
        raise RuntimeError("Missing TUSHARE_TOKEN. Please set it in .env or environment variables.")
    ts.set_token(Config.TUSHARE_TOKEN)
    return ts.pro_api()


def _df(result) -> pd.DataFrame:
    if result is None:
        return pd.DataFrame()
    if isinstance(result, pd.DataFrame):
        return result
    return pd.DataFrame(result)


def fetch_stock_basic(list_status: str = "L") -> pd.DataFrame:
    pro = _pro()
    df = _df(
        pro.stock_basic(
            exchange="",
            list_status=list_status,
            fields="ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,list_status,list_date,delist_date,is_hs",
        )
    )
    return df


def fetch_daily(ts_code: str, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
    pro = _pro()
    df = _df(
        pro.daily(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields="ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount",
        )
    )
    return df


def fetch_daily_basic(ts_code: str, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
    pro = _pro()
    df = _df(
        pro.daily_basic(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields="ts_code,trade_date,turnover_rate,turnover_rate_f,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_share,float_share,free_share,total_mv,circ_mv",
        )
    )
    return df


def fetch_fina_indicator(ts_code: str, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
    pro = _pro()
    df = _df(
        pro.fina_indicator(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields="ts_code,ann_date,end_date,roe,roa,netprofit_margin,grossprofit_margin,debt_to_assets,current_ratio,quick_ratio,op_income_yoy,netprofit_yoy,eps,bps,ocf_to_or",
        )
    )
    return df


def fetch_income(ts_code: str, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
    pro = _pro()
    df = _df(
        pro.income(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields="ts_code,ann_date,end_date,revenue,n_income,operate_profit,total_profit",
        )
    )
    return df


def fetch_balancesheet(ts_code: str, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
    pro = _pro()
    df = _df(
        pro.balancesheet(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields="ts_code,ann_date,end_date,total_assets,total_liab,total_hldr_eqy_exc_min_int,inventories,accounts_receiv,monetary_cap",
        )
    )
    return df


def fetch_cashflow(ts_code: str, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
    pro = _pro()
    df = _df(
        pro.cashflow(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields="ts_code,ann_date,end_date,n_cashflow_act,n_cashflow_inv_act,n_cash_flows_fnc_act,free_cashflow",
        )
    )
    return df

