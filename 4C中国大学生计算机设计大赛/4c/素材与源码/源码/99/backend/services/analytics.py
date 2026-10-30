from __future__ import annotations

import json
from typing import Any

from decimal import Decimal

from db import exec_one, fetch_all, fetch_one, tx


def _clamp(v: float | None, lo: float, hi: float) -> float | None:
    if v is None:
        return None
    return max(lo, min(hi, v))


def _score_minmax(value: float | None, vmin: float, vmax: float, higher_is_better: bool = True) -> float | None:
    if value is None:
        return None
    if vmax <= vmin:
        return 50.0
    x = (value - vmin) / (vmax - vmin)
    if not higher_is_better:
        x = 1.0 - x
    return float(_clamp(x * 100.0, 0.0, 100.0) or 0.0)


def compute_enterprise_metrics(ts_code: str, end_date: str | None = None) -> dict[str, Any]:
    """
    计算企业运营指标（盈利/偿债/成长/风险）并落库 enterprise_metrics。
    指标依据：fina_indicator + 三大报表部分字段。
    """
    with tx() as conn:
        base = fetch_one(conn, "SELECT ts_code, name, industry FROM company_basic WHERE ts_code=%(ts_code)s", {"ts_code": ts_code})
        if not base:
            return {"ok": False, "error": "Company not found in company_basic. Please sync stock_basic first."}

        params = {"ts_code": ts_code}
        if end_date:
            ind = fetch_one(
                conn,
                """
                SELECT * FROM fina_indicator
                WHERE ts_code=%(ts_code)s AND end_date=%(end_date)s
                """,
                {"ts_code": ts_code, "end_date": end_date},
            )
        else:
            ind = fetch_one(
                conn,
                """
                SELECT * FROM fina_indicator
                WHERE ts_code=%(ts_code)s
                ORDER BY end_date DESC
                LIMIT 1
                """,
                params,
            )
        if not ind:
            return {"ok": False, "error": "No fina_indicator rows yet. Sync financial tables first."}

        end_date = ind["end_date"]
        industry = base.get("industry")

        # 行业对标：同一 end_date，取行业内分布（若行业为空则按全市场）
        if industry:
            peers = fetch_all(
                conn,
                """
                SELECT roe, netprofit_margin, debt_to_assets, current_ratio, quick_ratio, op_income_yoy, netprofit_yoy, ocf_to_or
                FROM fina_indicator fi
                JOIN company_basic cb ON cb.ts_code=fi.ts_code
                WHERE fi.end_date=%(end_date)s AND cb.industry=%(industry)s
                """,
                {"end_date": end_date, "industry": industry},
            )
        else:
            peers = fetch_all(
                conn,
                """
                SELECT roe, netprofit_margin, debt_to_assets, current_ratio, quick_ratio, op_income_yoy, netprofit_yoy, ocf_to_or
                FROM fina_indicator
                WHERE end_date=%(end_date)s
                """,
                {"end_date": end_date},
            )

        def _minmax(field: str) -> tuple[float, float]:
            vals = [p[field] for p in peers if p.get(field) is not None]
            if not vals:
                return (0.0, 1.0)
            return (float(min(vals)), float(max(vals)))

        roe_min, roe_max = _minmax("roe")
        npm_min, npm_max = _minmax("netprofit_margin")
        dta_min, dta_max = _minmax("debt_to_assets")
        cr_min, cr_max = _minmax("current_ratio")
        qr_min, qr_max = _minmax("quick_ratio")
        oiy_min, oiy_max = _minmax("op_income_yoy")
        npy_min, npy_max = _minmax("netprofit_yoy")
        ocf_min, ocf_max = _minmax("ocf_to_or")

        profitability = [
            _score_minmax(ind.get("roe"), roe_min, roe_max, True),
            _score_minmax(ind.get("netprofit_margin"), npm_min, npm_max, True),
        ]
        solvency = [
            _score_minmax(ind.get("current_ratio"), cr_min, cr_max, True),
            _score_minmax(ind.get("quick_ratio"), qr_min, qr_max, True),
            _score_minmax(ind.get("debt_to_assets"), dta_min, dta_max, False),
        ]
        growth = [
            _score_minmax(ind.get("op_income_yoy"), oiy_min, oiy_max, True),
            _score_minmax(ind.get("netprofit_yoy"), npy_min, npy_max, True),
        ]
        # 风险：高负债、高增长波动、经营现金流弱（示例化）
        risk_parts = [
            _score_minmax(ind.get("debt_to_assets"), dta_min, dta_max, True),  # 负债率越高风险越高
            _score_minmax(ind.get("ocf_to_or"), ocf_min, ocf_max, False),  # 经营现金流/营收越低风险越高
        ]

        def _avg(xs: list[float | None]) -> float | None:
            ys = [x for x in xs if x is not None]
            if not ys:
                return None
            return float(sum(ys) / len(ys))

        profitability_score = _avg(profitability)
        solvency_score = _avg(solvency)
        growth_score = _avg(growth)
        risk_score = _avg(risk_parts)

        diagnosis = {
            "ts_code": ts_code,
            "end_date": end_date,
            "industry": industry,
            "raw": {
                "roe": float(ind["roe"]) if isinstance(ind.get("roe"), Decimal) else ind.get("roe"),
                "netprofit_margin": float(ind["netprofit_margin"]) if isinstance(ind.get("netprofit_margin"), Decimal) else ind.get("netprofit_margin"),
                "debt_to_assets": float(ind["debt_to_assets"]) if isinstance(ind.get("debt_to_assets"), Decimal) else ind.get("debt_to_assets"),
                "current_ratio": float(ind["current_ratio"]) if isinstance(ind.get("current_ratio"), Decimal) else ind.get("current_ratio"),
                "quick_ratio": float(ind["quick_ratio"]) if isinstance(ind.get("quick_ratio"), Decimal) else ind.get("quick_ratio"),
                "op_income_yoy": float(ind["op_income_yoy"]) if isinstance(ind.get("op_income_yoy"), Decimal) else ind.get("op_income_yoy"),
                "netprofit_yoy": float(ind["netprofit_yoy"]) if isinstance(ind.get("netprofit_yoy"), Decimal) else ind.get("netprofit_yoy"),
                "ocf_to_or": float(ind["ocf_to_or"]) if isinstance(ind.get("ocf_to_or"), Decimal) else ind.get("ocf_to_or"),
            },
            "peer_scope": "industry" if industry else "market",
        }

        exec_one(
            conn,
            """
            INSERT INTO enterprise_metrics
              (ts_code, end_date, industry, profitability_score, solvency_score, growth_score, risk_score, diagnosis_json)
            VALUES
              (%(ts_code)s, %(end_date)s, %(industry)s, %(p)s, %(s)s, %(g)s, %(r)s, %(diag)s)
            ON DUPLICATE KEY UPDATE
              industry=VALUES(industry),
              profitability_score=VALUES(profitability_score),
              solvency_score=VALUES(solvency_score),
              growth_score=VALUES(growth_score),
              risk_score=VALUES(risk_score),
              diagnosis_json=VALUES(diagnosis_json)
            """,
            {
                "ts_code": ts_code,
                "end_date": end_date,
                "industry": industry,
                "p": profitability_score,
                "s": solvency_score,
                "g": growth_score,
                "r": risk_score,
                "diag": json.dumps(diagnosis, ensure_ascii=False),
            },
        )

    return {
        "ok": True,
        "ts_code": ts_code,
        "end_date": end_date,
        "industry": industry,
        "profitability_score": profitability_score,
        "solvency_score": solvency_score,
        "growth_score": growth_score,
        "risk_score": risk_score,
        "diagnosis": diagnosis,
    }


def get_company_timeseries(ts_code: str, limit: int = 120) -> dict[str, Any]:
    """
    给前端 ECharts 用：价格曲线 + 估值（PE/PB）+ 市值。
    """
    with tx() as conn:
        prices = fetch_all(
            conn,
            """
            SELECT trade_date, close
            FROM daily_price
            WHERE ts_code=%(ts_code)s
            ORDER BY trade_date DESC
            LIMIT %(limit)s
            """,
            {"ts_code": ts_code, "limit": limit},
        )
        basics = fetch_all(
            conn,
            """
            SELECT trade_date, pe_ttm, pb, total_mv
            FROM daily_basic
            WHERE ts_code=%(ts_code)s
            ORDER BY trade_date DESC
            LIMIT %(limit)s
            """,
            {"ts_code": ts_code, "limit": limit},
        )
        # 财务指标趋势（按报表期）
        finas = fetch_all(
            conn,
            """
            SELECT end_date, roe, netprofit_margin, debt_to_assets, op_income_yoy, netprofit_yoy
            FROM fina_indicator
            WHERE ts_code=%(ts_code)s
            ORDER BY end_date ASC
            LIMIT 40
            """,
            {"ts_code": ts_code},
        )

    prices = list(reversed(prices))
    basics = list(reversed(basics))
    return {"prices": prices, "basics": basics, "fina": finas}

