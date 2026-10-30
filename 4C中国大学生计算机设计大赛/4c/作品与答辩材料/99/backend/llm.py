from __future__ import annotations

from typing import Any

import dashscope
import requests

from config import Config


class LLMServiceError(RuntimeError):
    def __init__(self, user_message: str, *, detail: str = "", code: str | None = None, provider: str = "dashscope"):
        super().__init__(user_message)
        self.user_message = user_message
        self.detail = detail
        self.code = code
        self.provider = provider

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "code": self.code,
            "message": self.user_message,
            "detail": self.detail,
        }


def _ensure_llm_config():
    if not Config.DASHSCOPE_API_KEY:
        raise LLMServiceError(
            "未配置 DashScope API Key，请检查 .env 中的 DASHSCOPE_API_KEY。",
            code="missing_api_key",
        )
    dashscope.api_key = Config.DASHSCOPE_API_KEY


def _normalize_dashscope_error(status_code: int | None, err: Any) -> LLMServiceError:
    detail = str(err)
    code = None
    message = "大模型调用失败，请稍后重试。"

    if isinstance(err, dict):
        code = str(err.get("code") or err.get("type") or err.get("param") or "") or None
        detail = str(err.get("message") or err.get("msg") or err)

    lower_detail = detail.lower()
    lower_code = (code or "").lower()

    if any(x in lower_detail for x in ["token", "quota", "insufficient", "余额", "额度", "remaining token", "当前模型剩余token不足"]):
        message = "DashScope 当前模型额度不足或剩余 token 不足，请登录阿里云百炼控制台检查余额、免费额度或模型配额。"
        code = code or "insufficient_quota"
    elif any(x in lower_detail for x in ["api key", "unauthorized", "invalid api key", "authentication", "鉴权", "access denied"]):
        message = "DashScope API Key 无效或无权限，请检查 .env 中的 DASHSCOPE_API_KEY。"
        code = code or "invalid_api_key"
    elif any(x in lower_detail for x in ["model", "not found", "unsupported", "does not exist"]):
        message = f"当前模型 `{Config.LLM_MODEL}` 不可用，请检查模型名称或账号权限。"
        code = code or "model_unavailable"
    elif status_code == 429:
        message = "DashScope 请求过于频繁或额度受限，请稍后再试。"
        code = code or "rate_limited"
    elif status_code and status_code >= 500:
        message = "DashScope 服务暂时不可用，请稍后重试。"
        code = code or "provider_unavailable"

    return LLMServiceError(message, detail=detail, code=code)


def _chat_completion_http_compatible(messages: list[dict[str, str]], temperature: float) -> str:
    """
    DashScope OpenAI-compatible mode.
    This avoids SDK incompatibilities across versions/models.
    """
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": Config.LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
    except requests.RequestException as e:
        raise LLMServiceError("无法连接 DashScope 服务，请检查网络后重试。", detail=str(e), code="network_error") from e

    try:
        j = r.json()
    except Exception:
        raise _normalize_dashscope_error(r.status_code, {"message": r.text[:500]})

    if r.status_code >= 400:
        raise _normalize_dashscope_error(r.status_code, j.get("error") or j)

    try:
        return j["choices"][0]["message"]["content"]
    except Exception:
        raise _normalize_dashscope_error(r.status_code, {"message": f"unexpected response: {j}"})


def chat_completion(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    """
    messages: [{"role":"system|user|assistant","content":"..."}]
    """
    _ensure_llm_config()

    try:
        return _chat_completion_http_compatible(messages, temperature)
    except LLMServiceError:
        raise
    except Exception as e:
        http_error = _normalize_dashscope_error(None, {"message": str(e)})

    resp: Any = dashscope.Generation.call(model=Config.LLM_MODEL, messages=messages, temperature=temperature, result_format="message")

    if resp is None:
        raise LLMServiceError(
            "DashScope 返回空响应，请检查网络、API Key 或模型权限。",
            code="empty_response",
        )

    if isinstance(resp, dict):
        if resp.get("code") and resp.get("code") != "200":
            raise _normalize_dashscope_error(None, resp)
        if resp.get("output", {}).get("choices"):
            return resp["output"]["choices"][0]["message"].get("content", "")
        if resp.get("output", {}).get("text"):
            return resp["output"]["text"]
        raise _normalize_dashscope_error(None, {"message": str(resp)})

    try:
        if hasattr(resp, "status_code") and getattr(resp, "status_code") not in (200, "200", None):
            msg = getattr(resp, "message", None) or getattr(resp, "code", None) or "unknown"
            raise _normalize_dashscope_error(getattr(resp, "status_code"), {"message": str(msg), "code": getattr(resp, "code", None)})
        return resp.output.choices[0].message.content
    except LLMServiceError:
        raise
    except Exception:
        try:
            return resp.output.text
        except Exception:
            raise http_error
