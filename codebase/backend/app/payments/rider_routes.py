from flask import Blueprint, request

from app.auth.decorators import require_role, current_user
from app.common.responses import success
from app.logistics.helpers import get_or_create_rider
from app.payments import wallet_service

rider_wallet_bp = Blueprint("rider_wallet", __name__, url_prefix="/api/v1/rider")


@rider_wallet_bp.route("/wallet", methods=["GET"])
@require_role("RIDER")
def get_wallet():
    rider = get_or_create_rider(current_user())
    wallet = wallet_service.get_or_create_wallet(rider)
    return success({"wallet": wallet.to_public_dict()})


@rider_wallet_bp.route("/wallet/transactions", methods=["GET"])
@require_role("RIDER")
def list_wallet_transactions():
    rider = get_or_create_rider(current_user())
    wallet = wallet_service.get_or_create_wallet(rider)
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    pagination = wallet_service.list_transactions(wallet, page=page, per_page=per_page)
    return success(
        {
            "transactions": [t.to_public_dict() for t in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "total_pages": pagination.pages,
            },
        }
    )
