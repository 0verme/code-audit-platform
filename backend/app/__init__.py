from __future__ import annotations

import logging
import time
import uuid

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import BadRequest

from .logging_config import configure_logging
from .routes import BLUEPRINTS
from .services.audit_task_service import recover_orphan_tasks
from .settings import get_runtime_security_settings, load_backend_dotenv


def create_app(*, recover_tasks: bool = True) -> Flask:
    load_backend_dotenv()
    configure_logging()
    settings = get_runtime_security_settings()
    app = Flask(__name__)
    app.config.update(JSON_AS_ASCII=False, RUNTIME_SETTINGS=settings)
    CORS(app, resources={r"/api/*": {"origins": list(settings.cors_origins)}})
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)

    @app.before_request
    def begin_request():
        g.request_started_at = time.perf_counter()
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex

    @app.after_request
    def finish_request(response):
        response.headers["X-Request-ID"] = g.get("request_id", "")
        elapsed_ms = (time.perf_counter() - g.get("request_started_at", time.perf_counter())) * 1000
        app.logger.info("request method=%s path=%s status=%s duration_ms=%.1f request_id=%s",
                        request.method, request.path, response.status_code, elapsed_ms, g.get("request_id", ""))
        return response

    def error_payload(code: str, message: str, status: int):
        return jsonify({"error": {"code": code, "message": message}}), status

    @app.errorhandler(BadRequest)
    def bad_request(_error):
        return error_payload("BAD_REQUEST", "请求参数无效", 400)

    @app.errorhandler(404)
    def not_found(_error):
        return error_payload("NOT_FOUND", "请求的资源不存在", 404)

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return error_payload("METHOD_NOT_ALLOWED", "请求方法不被允许", 405)

    @app.errorhandler(500)
    def internal_error(error):
        logging.getLogger(__name__).exception("Unhandled request error", exc_info=error)
        return error_payload("INTERNAL_SERVER_ERROR", "服务端发生未预期异常", 500)

    if recover_tasks:
        recover_orphan_tasks()
    return app


__all__ = ["create_app"]
