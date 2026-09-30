"""
Location-aware vendor/branch discovery foundation.

Eligibility considers vendor status, branch status, and delivery-zone
coverage only - this part is unchanged since Phase 2. Phase 9 adds
ranking on top of that eligible set (distance/rating/name) and an
optional minimum-rating filter; polygon zones and sponsored placement
remain out of scope.
"""
from app.catalog.geo import haversine_distance_meters
from app.extensions import db
from app.models.branch import Branch, BranchStatus
from app.models.vendor import Vendor, VendorStatus

VALID_SORTS = ("distance", "rating", "name")


def find_branches_serving(
    latitude: float,
    longitude: float,
    search: str | None = None,
    min_rating: float | None = None,
    sort: str = "distance",
) -> list[tuple[Branch, float]]:
    """Active branches of active vendors that have at least one active
    delivery zone covering the supplied coordinate, ranked per `sort`.

    Returns (branch, distance_meters) pairs - distance is computed here
    (not stored) since it's only meaningful relative to the caller's
    coordinate, and every sort order still needs it for display.
    """
    query = Branch.query.join(Vendor).filter(
        Branch.status == BranchStatus.ACTIVE, Vendor.status == VendorStatus.ACTIVE
    )
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(db.or_(Branch.name.ilike(like), Vendor.name.ilike(like)))
    if min_rating is not None:
        # NULL ratings (no reviews yet) never satisfy a minimum-rating
        # filter - that's correct: an unrated vendor hasn't demonstrated
        # the quality bar the customer asked for.
        query = query.filter(Vendor.rating_average >= min_rating)

    candidates = query.order_by(Vendor.name, Branch.name).all()
    served = [
        (branch, haversine_distance_meters(latitude, longitude, float(branch.latitude), float(branch.longitude)))
        for branch in candidates
        if branch.is_served_at(latitude, longitude)
    ]

    if sort == "rating":
        served.sort(key=lambda pair: (pair[0].vendor.rating_average is None, -(pair[0].vendor.rating_average or 0)))
    elif sort == "name":
        served.sort(key=lambda pair: (pair[0].vendor.name.lower(), pair[0].name.lower()))
    else:  # "distance" (default) - also the natural fallback for an unknown value
        served.sort(key=lambda pair: pair[1])

    return served
