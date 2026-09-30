"""
Service-area abstraction for delivery zones.

Phase 2 implements radius-based coverage only: a DeliveryZone stores a
center point and a radius, and `covers(lat, lng)` answers whether a
given coordinate falls inside that circle. `DeliveryZone.zone_type` and
this module's strategy interface exist so a POLYGON-based
implementation can be added later without changing the model's public
API (`covers`) or any of its callers - `polygon_geojson` is already a
column on the model, reserved and unused until that lands.
"""
import math
from abc import ABC, abstractmethod

EARTH_RADIUS_METERS = 6_371_000


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lng points, in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * math.asin(min(1, math.sqrt(a)))


class ServiceAreaStrategy(ABC):
    @abstractmethod
    def covers(self, latitude: float, longitude: float) -> bool:
        """True if the supplied coordinate falls inside this service area."""


class RadiusServiceArea(ServiceAreaStrategy):
    def __init__(self, center_lat, center_lng, radius_meters):
        self.center_lat = center_lat
        self.center_lng = center_lng
        self.radius_meters = radius_meters

    def covers(self, latitude: float, longitude: float) -> bool:
        if self.center_lat is None or self.center_lng is None or not self.radius_meters:
            return False
        distance = haversine_distance_meters(
            float(self.center_lat), float(self.center_lng), float(latitude), float(longitude)
        )
        return distance <= float(self.radius_meters)


class PolygonServiceArea(ServiceAreaStrategy):
    """Reserved for a future phase."""

    def __init__(self, geojson):
        self.geojson = geojson

    def covers(self, latitude: float, longitude: float) -> bool:
        raise NotImplementedError("Polygon-based service areas are not implemented yet.")


def build_service_area(zone) -> ServiceAreaStrategy:
    if zone.zone_type == "POLYGON":
        return PolygonServiceArea(zone.polygon_geojson)
    return RadiusServiceArea(zone.center_latitude, zone.center_longitude, zone.radius_meters)
