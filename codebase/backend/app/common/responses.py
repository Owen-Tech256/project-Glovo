"""
Consistent API response envelope used by every endpoint in the system.

Success:
    {"success": true, "message": "...", "data": {...}}

Error:
    {"success": false, "error": {"code": "...", "message": "..."}}
"""
from flask import jsonify


def success(data=None, message: str = "OK", status_code: int = 200):
    payload = {"success": True, "message": message, "data": data if data is not None else {}}
    return jsonify(payload), status_code


def error(code: str, message: str, status_code: int = 400, details=None):
    payload = {"success": False, "error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return jsonify(payload), status_code
