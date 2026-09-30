from flask import Blueprint

from app.common.responses import success

health_bp = Blueprint("health", __name__, url_prefix="/api/v1")


@health_bp.get("/health")
def health_check():
    return success({"status": "ok"}, message="Service is healthy.")
