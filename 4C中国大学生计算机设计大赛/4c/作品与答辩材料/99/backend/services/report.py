from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable

from db import fetch_all, fetch_one, tx
from llm import chat_completion
from services.cache_sync import get_fusion_context

CONFIDENCE_LIGHTS = [
    {"level": 1, "key": "red", "label": "红灯", "desc": "低置信度，仅供线索参考"},
    {"level": 2, "key": "yellow", "label": "黄灯", "desc": "中低置信度，需要补数据验证"},
    {"level": 3, "key": "blue", "label": "蓝灯", "desc": "中高置信度，可作为辅助判断"},
    {"level": 4, "key": "green", "label": "绿灯", "desc": "高置信度，数据较完整"},
]


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except Exception:
        return None


def _llm_json_default(value: Any):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _score_to_label(score: float | None, positive_high: bool = True) -> str:
    if score is None:
        return "暂无数据"
    if positive_high:
        if score >= 75:
            return "较强"
        if score >= 55:
            return "中性偏强"
        if score >= 35:
            return "中性偏弱"
        return "较弱"
    if score >= 75:
        return "偏高"
    if score >= 55:
        return "中等"
    if score >= 35:
        return "可控"
    return "较低"


def _make_investor_guidance(ctx: dict[str, Any]) -> dict[str, Any]:
    company = ctx.get("company") or {}
    metrics = ctx.get("latest_metrics") or {}
    fina = ctx.get("latest_fina_indicator") or {}
    valuation = ctx.get("latest_valuation") or {}

    profitability_score = _safe_float(metrics.get("profitability_score"))
    growth_score = _safe_float(metrics.get("growth_score"))
    solvency_score = _safe_float(metrics.get("solvency_score"))
    risk_score = _safe_float(metrics.get("risk_score"))
    pe_ttm = _safe_float(valuation.get("pe_ttm"))
    pb = _safe_float(valuation.get("pb"))
    roe = _safe_float(fina.get("roe"))
    debt_to_assets = _safe_float(fina.get("debt_to_assets"))
    netprofit_yoy = _safe_float(fina.get("netprofit_yoy"))

    strengths: list[str] = []
    risks: list[str] = []
    actions = ["先看近 3-4 个报告期的营收、净利润、ROE 是否持续改善，不要只看单期数据"]
    suitable_for: list[str] = []

    if profitability_score is not None and profitability_score >= 65:
        strengths.append("盈利评分较高，企业赚钱能力在同行中具备一定优势")
    if growth_score is not None and growth_score >= 65:
        strengths.append("成长评分较高，营收或利润增速具备一定弹性")
    if roe is not None and roe >= 12:
        strengths.append("ROE 处于相对较好水平，资本回报能力尚可")
    if pe_ttm is not None and pe_ttm > 0 and pe_ttm <= 25:
        strengths.append("PE(TTM) 不算激进，估值压力相对可控")

    if risk_score is not None and risk_score >= 70:
        risks.append("风险评分偏高，说明负债或现金流质量需要特别留意")
    if debt_to_assets is not None and debt_to_assets >= 65:
        risks.append("资产负债率较高，遇到行业下行时承压可能更明显")
    if netprofit_yoy is not None and netprofit_yoy < 0:
        risks.append("净利润同比为负，盈利改善趋势仍需继续验证")
    if pe_ttm is not None and pe_ttm > 45:
        risks.append("估值偏高，若基本面不持续兑现，回撤风险会放大")
    if pb is not None and pb > 5:
        risks.append("PB 偏高，市场对未来预期已经给出较高溢价")

    if pe_ttm is not None or pb is not None:
        actions.append("把当前 PE/PB 与公司历史区间、同行可比公司做横向对比，避免单看绝对值")
    if risk_score is not None and risk_score >= 60:
        actions.append("若继续跟踪，重点补查现金流、负债结构、行业景气度和大股东情况")
    else:
        actions.append("若继续跟踪，可进一步验证行业景气度、产品竞争力和未来 1-2 年业绩兑现能力")

    if profitability_score is not None and growth_score is not None and risk_score is not None:
        if profitability_score >= 65 and growth_score >= 60 and risk_score <= 45:
            suitable_for.append("更适合偏基本面、中长期观察型股民")
        if risk_score >= 60:
            suitable_for.append("不适合只看一两项指标就重仓决策")

    summary = (
        f"{company.get('name') or company.get('ts_code') or '该标的'}当前呈现出"
        f"盈利{_score_to_label(profitability_score)}、成长{_score_to_label(growth_score)}、"
        f"偿债{_score_to_label(solvency_score)}、风险{_score_to_label(risk_score, positive_high=False)}的特征。"
        "它更适合用来做基本面初筛与继续跟踪，不应直接替代买卖决策。"
    )
    return {
        "summary": summary,
        "strengths": strengths[:4],
        "risks": risks[:4],
        "actions": actions[:4],
        "suitable_for": suitable_for[:3],
        "valuation_snapshot": {"pe_ttm": pe_ttm, "pb": pb},
    }


def _compute_confidence(ctx: dict[str, Any], question: str | None = None) -> dict[str, Any]:
    company = ctx.get("company") or {}
    metrics = ctx.get("latest_metrics") or {}
    fina = ctx.get("latest_fina_indicator") or {}
    income = ctx.get("latest_income") or {}
    valuation = ctx.get("latest_valuation") or {}
    prices = ctx.get("price_snapshot") or {}
    fusion = ctx.get("fusion") or {}

    score = 0
    reasons: list[str] = []
    missing: list[str] = []

    if company:
        score += 10
        reasons.append("已获取企业基础信息")
    else:
        missing.append("企业基础信息")
    if metrics and any(metrics.get(k) is not None for k in ["profitability_score", "solvency_score", "growth_score", "risk_score"]):
        score += 28
        reasons.append("已有多维运营评分")
    else:
        missing.append("多维运营评分")
    fina_count = sum(1 for k in ["roe", "netprofit_margin", "debt_to_assets", "op_income_yoy", "netprofit_yoy", "ocf_to_or"] if fina.get(k) is not None)
    if fina_count >= 5:
        score += 24
        reasons.append("财务指标较完整")
    elif fina_count >= 3:
        score += 16
        reasons.append("财务指标部分可用")
    else:
        missing.append("关键财务指标")
    if income and any(income.get(k) is not None for k in ["revenue", "n_income", "operate_profit"]):
        score += 8
        reasons.append("利润表关键字段可用")
    else:
        missing.append("利润表字段")
    if valuation and any(valuation.get(k) is not None for k in ["pe_ttm", "pb", "total_mv"]):
        score += 12
        reasons.append("估值与市值数据可用")
    else:
        missing.append("估值数据")
    if prices and prices.get("trade_date"):
        score += 8
        reasons.append("存在最新行情快照")
    else:
        missing.append("近期行情")
    if (fusion.get("research_reports") or []) or (fusion.get("exchange_fin_reports") or []):
        score += 10
        reasons.append("存在融合文本信息用于交叉验证")
    else:
        reasons.append("暂无融合文本信息，结论主要依赖结构化数据")
    if question and any(x in question.strip() for x in ["明天", "下周", "涨停", "买点", "卖点", "翻倍", "预测股价"]):
        score = max(score - 18, 0)
        reasons.append("问题包含短期价格预测诉求，模型仅能提供辅助研究，不能精确预测")

    score = max(0, min(100, score))
    light = CONFIDENCE_LIGHTS[3] if score >= 85 else CONFIDENCE_LIGHTS[2] if score >= 65 else CONFIDENCE_LIGHTS[1] if score >= 40 else CONFIDENCE_LIGHTS[0]
    return {
        "score": score,
        "light": light,
        "reasons": reasons,
        "missing": missing,
        "guardrails": [
            "只基于本地结构化数据与已同步融合信息输出，不对缺失数据进行编造",
            "涉及短期涨跌、具体买卖点、收益承诺时，自动降低置信度并提示用户自行验证",
            "优先输出可验证的数据点、风险项与需要补充的数据，而非直接给确定性结论",
        ],
    }


def _wrap_answer_payload(answer: str, ctx: dict[str, Any], question: str) -> dict[str, Any]:
    return {
        "answer": answer,
        "confidence": _compute_confidence(ctx, question=question),
        "investor_guidance": ctx.get("investor_guidance") or _make_investor_guidance(ctx),
        "evidence": {
            "company": ctx.get("company"),
            "latest_metrics": ctx.get("latest_metrics"),
            "latest_valuation": ctx.get("latest_valuation"),
            "price_snapshot": ctx.get("price_snapshot"),
            "peer_valuation": ctx.get("peer_valuation"),
        },
    }

def build_company_context(ts_code: str) -> dict[str, Any]:
    with tx() as conn:
        base = fetch_one(conn, "SELECT ts_code, name, area, industry, market, exchange, list_date FROM company_basic WHERE ts_code=%(ts_code)s", {"ts_code": ts_code})
        latest_metrics = fetch_one(conn, "SELECT ts_code, end_date, industry, profitability_score, solvency_score, growth_score, risk_score, diagnosis_json FROM enterprise_metrics WHERE ts_code=%(ts_code)s ORDER BY end_date DESC LIMIT 1", {"ts_code": ts_code})
        latest_fina = fetch_one(conn, "SELECT * FROM fina_indicator WHERE ts_code=%(ts_code)s ORDER BY end_date DESC LIMIT 1", {"ts_code": ts_code})
        latest_income = fetch_one(conn, "SELECT end_date, revenue, n_income, operate_profit, total_profit FROM financial_income WHERE ts_code=%(ts_code)s ORDER BY end_date DESC LIMIT 1", {"ts_code": ts_code})
        latest_valuation = fetch_one(conn, "SELECT trade_date, pe_ttm, pb, total_mv, dv_ttm FROM daily_basic WHERE ts_code=%(ts_code)s ORDER BY trade_date DESC LIMIT 1", {"ts_code": ts_code})
        price_snapshot = fetch_one(conn, "SELECT trade_date, close, pct_chg, amount FROM daily_price WHERE ts_code=%(ts_code)s ORDER BY trade_date DESC LIMIT 1", {"ts_code": ts_code})
        peer_valuation = []
        if base and base.get("industry"):
            peer_valuation = fetch_all(conn, """
                SELECT cb.ts_code, cb.name, db.trade_date, db.pe_ttm, db.pb
                FROM company_basic cb
                JOIN daily_basic db ON db.ts_code = cb.ts_code
                JOIN (SELECT ts_code, MAX(trade_date) AS latest_trade_date FROM daily_basic GROUP BY ts_code) t
                  ON t.ts_code = db.ts_code AND t.latest_trade_date = db.trade_date
                WHERE cb.industry=%(industry)s
                ORDER BY db.trade_date DESC
                LIMIT 8
            """, {"industry": base.get("industry")})
        fusion = get_fusion_context(ts_code)

    if latest_metrics and latest_metrics.get("diagnosis_json"):
        try:
            latest_metrics["diagnosis"] = json.loads(latest_metrics["diagnosis_json"])
        except Exception:
            latest_metrics["diagnosis"] = latest_metrics["diagnosis_json"]

    slim_metrics = None
    if latest_metrics:
        slim_metrics = {
            "end_date": latest_metrics.get("end_date"),
            "profitability_score": latest_metrics.get("profitability_score"),
            "solvency_score": latest_metrics.get("solvency_score"),
            "growth_score": latest_metrics.get("growth_score"),
            "risk_score": latest_metrics.get("risk_score"),
            "diagnosis": latest_metrics.get("diagnosis"),
        }

    fusion = fusion or {}
    ctx = {
        "company": base,
        "latest_metrics": slim_metrics,
        "latest_fina_indicator": latest_fina,
        "latest_income": latest_income,
        "latest_valuation": latest_valuation,
        "price_snapshot": price_snapshot,
        "peer_valuation": peer_valuation,
        "fusion": {
            "research_reports": fusion.get("research_reports", [])[:2],
            "exchange_fin_reports": fusion.get("exchange_fin_reports", [])[:2],
        },
    }
    ctx["investor_guidance"] = _make_investor_guidance(ctx)
    ctx["confidence"] = _compute_confidence(ctx)
    return ctx


def generate_analysis_report(ts_code: str, user_goal: str | None = None, progress_callback: Callable[[int, str, str], None] | None = None) -> dict[str, Any]:
    def progress(percent: int, stage: str, message: str):
        if progress_callback:
            progress_callback(percent, stage, message)

    progress(15, "collecting", "正在读取企业基础信息、行情、估值与财务数据")
    ctx = build_company_context(ts_code)
    progress(35, "analyzing", "正在计算数据完整度、四灯置信度与辅助分析指引")
    if not ctx or not ctx.get("company"):
        progress(100, "done", "未找到企业数据，已生成提示信息")
        return {
            "report": "未找到该企业，请先在「企业查询」页同步企业基础信息与财务数据。",
            "confidence": _compute_confidence({}, None),
            "investor_guidance": None,
            "evidence": {},
        }

    goal = user_goal or "面向企业经营分析展示，输出经营表现、风险提示与后续建议，必要时补充投资辅助参考。"
    progress(55, "prompting", "正在组织报告目标、数据证据与生成约束")
    system = (
        "你是企业经营分析与决策支持助手。你必须严格基于给定结构化数据回答，"
        "不能编造不存在的数据，不能承诺收益，不能给出确定性的短线涨跌预测。"
        "如果数据不足，必须明确写出数据缺口与验证建议。"
        "输出结构：1) 经营结论摘要 2) 基本面与经营表现 3) 估值与市场观察 4) 主要风险 5) 后续建议 6) 如适用，再补充投资辅助参考。"
    )
    user = {
        "goal": goal,
        "data": ctx or {},
        "constraints": [
            "不要输出具体买入价、卖出价、收益承诺",
            "优先引用给定数据字段进行解释",
            "结论措辞使用概率性、条件性表达",
        ],
    }
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False, default=_llm_json_default)},
    ]
    progress(72, "generating", "正在调用大模型生成经营分析报告")
    answer = chat_completion(messages, temperature=0.15)
    progress(92, "wrapping", "正在整理报告、置信度和分析指引")
    result = _wrap_answer_payload(answer, ctx, question=goal)
    progress(100, "done", "报告生成完成")
    return result


def answer_question(question: str, ts_code: str | None = None, industry: str | None = None) -> dict[str, Any]:
    company_ctx = build_company_context(ts_code) if ts_code else {}
    system = (
        "你是企业经营分析问答助手。你只能基于给定数据回答，"
        "不能编造、不能补全缺失事实、不能承诺收益、不能给精确买卖点。"
        "回答必须包含：1) 结论 2) 关键依据数据点 3) 风险提示 4) 下一步验证建议。"
        "若问题涉及上市公司研究，可补充投资辅助参考，但不能偏离企业经营分析主线。"
    )
    payload = {
        "question": question,
        "ts_code": ts_code,
        "industry": industry,
        "company_context": company_ctx or None,
        "rules": {
            "forbidden": ["编造数据", "收益承诺", "具体买卖点", "确定性预测股价"],
            "preferred": ["引用给定数据", "说明不确定性", "提出验证步骤"],
        },
    }
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=_llm_json_default)},
    ]
    return _wrap_answer_payload(chat_completion(messages, temperature=0.2), company_ctx or {}, question=question)
