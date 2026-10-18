# -*- coding: utf-8 -*-
"""Coze 智能体代理：令牌只放在服务端环境变量，前端只与本机 Flask 通信。"""
from __future__ import annotations

import json
import os
import time

import requests
from flask import Blueprint, Response, jsonify, request, stream_with_context

import coze_context
from auth import get_jwt_identity, requires_permission

coze_api = Blueprint("coze_api", __name__)

DEFAULT_BOT_ID = "7697962757626396687"
MAX_MESSAGE = 1000


def _config():
    base = os.environ.get("COZE_API_BASE", "https://api.coze.cn").rstrip("/")
    return {
        "base": base,
        "bot_id": os.environ.get("COZE_BOT_ID", DEFAULT_BOT_ID),
        "token": os.environ.get("COZE_API_TOKEN", "").strip(),
    }


def _sse(event: str, data: dict) -> str:
    return "event: %s\ndata: %s\n\n" % (event, json.dumps(data, ensure_ascii=False))


def _upstream_error(resp) -> str:
    try:
        payload = resp.json()
        return (payload.get("msg") or payload.get("message") or str(payload))[:300]
    except Exception:
        return (resp.text or "Coze 接口返回错误")[:300]


@coze_api.route("/api/coze/status", methods=["GET"])
@requires_permission("ai_view")
def status():
    cfg = _config()
    return jsonify({
        "code": 200,
        "message": "success",
        "data": {
            "configured": bool(cfg["token"]),
            "bot_id": cfg["bot_id"],
            "base": cfg["base"],
            "data_connected": True,
        },
    }), 200


@coze_api.route("/api/coze/context", methods=["GET"])
@requires_permission("ai_view")
def context():
    """给前端展示“后台确实读到了数据”的实时快照，也用于排查注入内容。"""
    data = coze_context.snapshot()
    return jsonify({"code": 200, "message": "success", "data": data}), 200


@coze_api.route("/api/coze/chat", methods=["POST"])
@requires_permission("ai_view")
def chat():
    cfg = _config()
    if not cfg["token"]:
        return jsonify({
            "code": 503,
            "message": "服务端未配置 COZE_API_TOKEN，请先在 .env 中设置并重启后台",
            "data": {},
        }), 503

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"code": 400, "message": "请输入消息", "data": {}}), 400
    if len(message) > MAX_MESSAGE:
        return jsonify({"code": 400, "message": "消息过长，请控制在 1000 字以内", "data": {}}), 400

    conversation_id = (data.get("conversation_id") or "").strip() or None
    user_id = get_jwt_identity() or "admin"
    # 把后台数据库快照注入本轮输入，Coze 才能回答本系统的真实数据
    prompt = coze_context.prompt_context() + "\n\n【用户问题】\n" + message
    payload = {
        "bot_id": cfg["bot_id"],
        "user_id": "admin-%s" % user_id,
        "stream": True,
        "auto_save_history": True,
        "additional_messages": [{
            "role": "user",
            "content": prompt,
            "content_type": "text",
        }],
    }
    if conversation_id:
        # Coze v3 的 conversation_id 是 query 参数，不是 body 字段
        params = {"conversation_id": conversation_id}
    else:
        params = {}

    def generate():
        upstream = None
        try:
            upstream = requests.post(
                cfg["base"] + "/v3/chat",
                params=params,
                headers={
                    "Authorization": "Bearer " + cfg["token"],
                    "Content-Type": "application/json",
                },
                json=payload,
                stream=True,
                timeout=(10, 180),
            )
        except Exception as exc:  # noqa: BLE001
            yield _sse("error", {"message": "连接 Coze 失败：%s" % str(exc)[:200]})
            return

        if upstream.status_code != 200:
            yield _sse("error", {"message": _upstream_error(upstream)})
            upstream.close()
            return

        event = None
        streamed = ""
        conv_id = conversation_id or ""
        chat_id = ""
        done_sent = False
        try:
            for raw in upstream.iter_lines(decode_unicode=False):
                if not raw:
                    continue
                line = raw.decode("utf-8", "replace")
                if line.startswith("event:"):
                    event = line[6:].strip()
                    continue
                if not line.startswith("data:"):
                    continue
                body = line[5:].strip()
                if body in ("[DONE]", '"[DONE]"'):
                    break
                try:
                    obj = json.loads(body)
                except Exception:
                    continue

                if event == "conversation.chat.created":
                    conv_id = obj.get("conversation_id") or conv_id
                    chat_id = obj.get("id") or ""
                    yield _sse("meta", {"conversation_id": conv_id, "chat_id": chat_id})

                elif event == "conversation.message.delta":
                    if obj.get("type") not in (None, "answer"):
                        continue
                    content = obj.get("content") or ""
                    if content:
                        streamed += content
                        yield _sse("delta", {"content": content})

                elif event == "conversation.message.completed":
                    if obj.get("type") not in (None, "answer"):
                        continue
                    content = obj.get("content") or ""
                    if content and content != streamed:
                        if content.startswith(streamed):
                            chunk = content[len(streamed):]
                        else:
                            chunk = content
                        if chunk:
                            streamed = content
                            yield _sse("delta", {"content": chunk})

                elif event == "conversation.chat.failed":
                    err = (obj.get("last_error") or {}).get("msg") or "Coze 对话失败"
                    yield _sse("error", {"message": str(err)[:300]})

                elif event == "conversation.chat.completed":
                    if not done_sent:
                        done_sent = True
                        yield _sse("done", {
                            "conversation_id": obj.get("conversation_id") or conv_id,
                            "chat_id": obj.get("id") or chat_id,
                            "status": obj.get("status") or "completed",
                        })

                elif event == "done":
                    break
        except Exception as exc:  # noqa: BLE001
            yield _sse("error", {"message": "读取 Coze 流失败：%s" % str(exc)[:200]})
        finally:
            if not done_sent:
                yield _sse("done", {"conversation_id": conv_id, "chat_id": chat_id,
                                    "status": "completed"})
            upstream.close()

    resp = Response(stream_with_context(generate()), mimetype="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    return resp
