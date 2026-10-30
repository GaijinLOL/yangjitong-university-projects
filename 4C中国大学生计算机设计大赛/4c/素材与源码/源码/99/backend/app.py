from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from decimal import Decimal

from flask import Flask, jsonify, render_template, request

from config import Config, validate_required_config
from db import exec_one, fetch_all, fetch_one, tx
from services.analytics import compute_enterprise_metrics, get_company_timeseries
from services.cache_sync import (
    sync_daily_basic,
    sync_daily_price,
    sync_financial_tables,
    upsert_stock_basic,
)
from services.migrate import ensure_schema
from services.report import answer_question, generate_analysis_report


def _jsonable(x):
    """
    Flask jsonify 不能序列化 Decimal；MySQL DECIMAL 字段会以 Decimal 返回。
    这里做递归转换，保证 API 响应稳定。
    """
    if isinstance(x, Decimal):
        return float(x)
    if isinstance(x, datetime):
        return x.isoformat(timespec="seconds")
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_jsonable(v) for v in x]
    if isinstance(x, tuple):
        return [_jsonable(v) for v in x]
    return x


def _api_error_response(error: Exception, **extra):
    message = str(error)
    lower_message = message.lower()
    if "token" in lower_message or "权限" in message or "确认" in message:
        payload = {
            "ok": False,
            "error": "Tushare token 无效或权限不足，请检查 .env 中的 TUSHARE_TOKEN。",
            "detail": message,
            "hint": "登录 tushare.pro，在个人主页复制完整 TOKEN 到 .env，然后重启 Flask 服务。",
        }
        payload.update(extra)
        return jsonify(payload), 400
    payload = {"ok": False, "error": message}
    payload.update(extra)
    return jsonify(payload), 500
def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    try:
        ensure_schema()
    except Exception:
        pass

    @app.get("/")
    def index():
        missing = validate_required_config()
        return render_template("index.html", missing=missing)

    @app.get("/company")
    def company_page():
        q = (request.args.get("q") or "").strip()
        companies = []
        if q:
            with tx() as conn:
                companies = fetch_all(
                    conn,
                    """
                    SELECT ts_code, name, industry, area, market, exchange, list_date
                    FROM company_basic
                    WHERE ts_code LIKE %(q1)s OR name LIKE %(q2)s
                    ORDER BY list_date DESC
                    LIMIT 50
                    """,
                    {"q1": f"%{q}%", "q2": f"%{q}%"},
                )
        return render_template("company.html", q=q, companies=companies)

    @app.get("/qa")
    def qa_page():
        return render_template("qa.html")

    @app.get("/dashboard")
    def dashboard_page():
        ts_code = (request.args.get("ts_code") or "").strip()
        return render_template("dashboard.html", ts_code=ts_code)

    @app.get("/report")
    def report_page():
        ts_code = (request.args.get("ts_code") or "").strip()
        return render_template("report.html", ts_code=ts_code)

    @app.post("/api/sync/stock_basic")
    def api_sync_stock_basic():
        data = request.get_json(silent=True) or {}
        list_status = data.get("list_status", "L")
        try:
            res = upsert_stock_basic(list_status=list_status)
            return jsonify({"ok": True, "result": res})
        except Exception as e:
            return _api_error_response(e, action="sync_stock_basic")

    @app.post("/api/sync/company")
    def api_sync_company():
        data = request.get_json(silent=True) or {}
        ts_code = (data.get("ts_code") or "").strip()
        if not ts_code:
            return jsonify({"ok": False, "error": "ts_code is required"}), 400

        try:
            r1 = sync_daily_price(ts_code)
            r2 = sync_daily_basic(ts_code)
            r3 = sync_financial_tables(ts_code)
            r4 = compute_enterprise_metrics(ts_code)
            return jsonify(_jsonable({"ok": True, "daily_price": r1, "daily_basic": r2, "financial": r3, "metrics": r4}))
        except Exception as e:
            return _api_error_response(e, action="sync_company", ts_code=ts_code)

    @app.post("/api/company/clear")
    def api_clear_company_data():
        data = request.get_json(silent=True) or {}
        ts_code = (data.get("ts_code") or "").strip()
        clear_base = bool(data.get("clear_base", False))
        if not ts_code:
            return jsonify({"ok": False, "error": "ts_code is required"}), 400

        deleted: dict[str, int] = {}
        try:
            with tx() as conn:
                tables = [
                    ("daily_price", "DELETE FROM daily_price WHERE ts_code=%(ts_code)s"),
                    ("daily_basic", "DELETE FROM daily_basic WHERE ts_code=%(ts_code)s"),
                    ("fina_indicator", "DELETE FROM fina_indicator WHERE ts_code=%(ts_code)s"),
                    ("financial_income", "DELETE FROM financial_income WHERE ts_code=%(ts_code)s"),
                    ("financial_balancesheet", "DELETE FROM financial_balancesheet WHERE ts_code=%(ts_code)s"),
                    ("financial_cashflow", "DELETE FROM financial_cashflow WHERE ts_code=%(ts_code)s"),
                    ("enterprise_metrics", "DELETE FROM enterprise_metrics WHERE ts_code=%(ts_code)s"),
                    ("research_report", "DELETE FROM research_report WHERE ts_code=%(ts_code)s"),
                    ("exchange_fin_report", "DELETE FROM exchange_fin_report WHERE ts_code=%(ts_code)s"),
                    ("sync_state", "DELETE FROM sync_state WHERE source='tushare' AND key1=%(ts_code)s"),
                ]
                if clear_base:
                    tables.append(("company_basic", "DELETE FROM company_basic WHERE ts_code=%(ts_code)s"))

                for name, sql in tables:
                    deleted[name] = exec_one(conn, sql, {"ts_code": ts_code})

            return jsonify({
                "ok": True,
                "ts_code": ts_code,
                "clear_base": clear_base,
                "deleted": deleted,
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e), "ts_code": ts_code}), 500

    @app.get("/api/company/profile")
    def api_company_profile():
        ts_code = (request.args.get("ts_code") or "").strip()
        if not ts_code:
            return jsonify({"ok": False, "error": "ts_code is required"}), 400
        with tx() as conn:
            base = fetch_one(
                conn,
                """
                SELECT ts_code, name, area, industry, market, exchange, list_date
                FROM company_basic
                WHERE ts_code=%(ts_code)s
                """,
                {"ts_code": ts_code},
            )
            metrics = fetch_one(
                conn,
                """
                SELECT ts_code, end_date, profitability_score, solvency_score, growth_score, risk_score
                FROM enterprise_metrics
                WHERE ts_code=%(ts_code)s
                ORDER BY end_date DESC
                LIMIT 1
                """,
                {"ts_code": ts_code},
            )
        return jsonify(_jsonable({"ok": True, "company": base, "latest_metrics": metrics}))

    @app.get("/api/company/timeseries")
    def api_company_timeseries():
        ts_code = (request.args.get("ts_code") or "").strip()
        if not ts_code:
            return jsonify({"ok": False, "error": "ts_code is required"}), 400
        data = get_company_timeseries(ts_code, limit=180)
        return jsonify(_jsonable({"ok": True, "data": data}))

    @app.post("/api/metrics/recompute")
    def api_recompute_metrics():
        data = request.get_json(silent=True) or {}
        ts_code = (data.get("ts_code") or "").strip()
        end_date = (data.get("end_date") or "").strip() or None
        if not ts_code:
            return jsonify({"ok": False, "error": "ts_code is required"}), 400
        res = compute_enterprise_metrics(ts_code, end_date=end_date)
        return jsonify(res)

    @app.post("/api/qa")
    def api_qa():
        data = request.get_json(silent=True) or {}
        question = (data.get("question") or "").strip()
        ts_code = (data.get("ts_code") or "").strip() or None
        industry = (data.get("industry") or "").strip() or None
        if not question:
            return jsonify({"ok": False, "error": "question is required"}), 400
        job_id = uuid.uuid4().hex
        _set_qa_job(
            job_id,
            {
                "status": "queued",
                "question": question,
                "ts_code": ts_code,
                "industry": industry,
                "progress": 5,
                "stage": "queued",
                "message": "问题已提交，等待开始分析",
                "created_at": datetime.now().isoformat(timespec="seconds"),
            },
        )

        def _run():
            try:
                _set_qa_job(job_id, {"status": "running", "progress": 15, "stage": "context", "message": "正在读取企业与行业上下文"})
                _set_qa_job(job_id, {"progress": 35, "stage": "evidence", "message": "正在整理本地数据证据与问题边界"})
                _set_qa_job(job_id, {"progress": 60, "stage": "generating", "message": "正在生成智能回答"})
                result = answer_question(question=question, ts_code=ts_code, industry=industry)
                _set_qa_job(job_id, {"progress": 90, "stage": "wrapping", "message": "正在整理置信度和分析指引"})
                _set_qa_job(
                    job_id,
                    {
                        "status": "done",
                        "progress": 100,
                        "stage": "done",
                        "message": "智能回答生成完成",
                        "result": result,
                        "finished_at": datetime.now().isoformat(timespec="seconds"),
                    },
                )
            except Exception as e:
                import traceback

                _set_qa_job(job_id, {"status": "error", "progress": 100, "stage": "error", "message": "智能回答生成失败", "error": str(e), "traceback": traceback.format_exc()})

        threading.Thread(target=_run, daemon=True).start()
        return jsonify({"ok": True, "job_id": job_id})

    @app.get("/api/qa/status")
    def api_qa_status():
        job_id = (request.args.get("job_id") or "").strip()
        if not job_id:
            return jsonify({"ok": False, "error": "job_id is required"}), 400
        job = _get_qa_job(job_id)
        if not job:
            return jsonify({"ok": False, "error": "job not found"}), 404
        return jsonify(_jsonable({"ok": True, "job": job}))

    @app.post("/api/report")
    def api_report():
        data = request.get_json(silent=True) or {}
        ts_code = (data.get("ts_code") or "").strip()
        goal = (data.get("goal") or "").strip() or None
        if not ts_code:
            return jsonify({"ok": False, "error": "ts_code is required"}), 400
        job_id = uuid.uuid4().hex
        _set_job(
            job_id,
            {
                "status": "queued",
                "ts_code": ts_code,
                "progress": 5,
                "stage": "queued",
                "message": "任务已提交，等待开始生成",
                "created_at": datetime.now().isoformat(timespec="seconds"),
            },
        )

        def _run():
            _set_job(job_id, {"status": "running", "progress": 10, "stage": "starting", "message": "报告生成任务已启动"})

            def _progress(percent: int, stage: str, message: str):
                _set_job(job_id, {"status": "running", "progress": percent, "stage": stage, "message": message})

            try:
                rep = generate_analysis_report(ts_code=ts_code, user_goal=goal, progress_callback=_progress)
                _set_job(
                    job_id,
                    {
                        "status": "done",
                        "progress": 100,
                        "stage": "done",
                        "message": "报告生成完成",
                        "report": rep,
                        "generated_at": datetime.now().isoformat(timespec="seconds"),
                    },
                )
            except Exception as e:
                import traceback

                _set_job(job_id, {"status": "error", "progress": 100, "stage": "error", "message": "报告生成失败", "error": str(e), "traceback": traceback.format_exc()})

        threading.Thread(target=_run, daemon=True).start()
        return jsonify({"ok": True, "job_id": job_id})

    @app.get("/api/report/status")
    def api_report_status():
        job_id = (request.args.get("job_id") or "").strip()
        if not job_id:
            return jsonify({"ok": False, "error": "job_id is required"}), 400
        job = _get_job(job_id)
        if not job:
            return jsonify({"ok": False, "error": "job not found"}), 404
        return jsonify(_jsonable({"ok": True, "job": job}))

    @app.get("/api/health")
    def api_health():
        try:
            with tx() as conn:
                row = fetch_one(conn, "SELECT 1 AS ok")
            mysql_ok = bool(row and row.get("ok") == 1)
        except Exception:
            mysql_ok = False
        return jsonify(
            {
                "ok": True,
                "mysql_ok": mysql_ok,
                "llm_model": Config.LLM_MODEL,
            }
        )

    return app


app = create_app()

REPORT_JOBS: dict[str, dict] = {}
REPORT_JOBS_LOCK = threading.Lock()
QA_JOBS: dict[str, dict] = {}
QA_JOBS_LOCK = threading.Lock()


def _set_job(job_id: str, patch: dict):
    with REPORT_JOBS_LOCK:
        cur = REPORT_JOBS.get(job_id, {})
        cur.update(patch)
        REPORT_JOBS[job_id] = cur


def _get_job(job_id: str) -> dict | None:
    with REPORT_JOBS_LOCK:
        return REPORT_JOBS.get(job_id)


def _set_qa_job(job_id: str, patch: dict):
    with QA_JOBS_LOCK:
        cur = QA_JOBS.get(job_id, {})
        cur.update(patch)
        QA_JOBS[job_id] = cur


def _get_qa_job(job_id: str) -> dict | None:
    with QA_JOBS_LOCK:
        return QA_JOBS.get(job_id)


if __name__ == "__main__":
    app.run(host=Config.FLASK_HOST, port=Config.FLASK_PORT, debug=Config.FLASK_DEBUG)


