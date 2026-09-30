"""
Candidate-ranking strategy for dispatch, kept isolated from
dispatch_service.py's candidate-filtering/offer-lifecycle logic so a future
phase can swap in a smarter strategy (predictive ETA, batching-aware
scoring, live traffic) without touching anything else (SRS 8: "Rank
candidates using an isolated deterministic proximity strategy... isolate
the strategy for future replacement").

Mirrors the ABC-plus-default-implementation shape of
app/catalog/geo.py's ServiceAreaStrategy, reusing its
`haversine_distance_meters` rather than re-deriving distance math.
"""
from abc import ABC, abstractmethod

from app.catalog.geo import haversine_distance_meters


class DispatchRankingStrategy(ABC):
    @abstractmethod
    def rank(self, candidates: list, pickup_latitude: float, pickup_longitude: float) -> list:
        """Returns `candidates` (a list of Rider instances, each with a
        fresh current_latitude/current_longitude) ordered best-first."""


class ProximityRankingStrategy(DispatchRankingStrategy):
    """Deterministic nearest-to-pickup-first ranking. Ties are broken by
    rider id (ascending) so the ordering is 100% reproducible - useful for
    tests and for reasoning about "why did rider X get offered first".
    """

    def rank(self, candidates: list, pickup_latitude: float, pickup_longitude: float) -> list:
        def distance_meters(rider) -> float:
            return haversine_distance_meters(
                float(rider.current_latitude), float(rider.current_longitude),
                pickup_latitude, pickup_longitude,
            )

        return sorted(candidates, key=lambda rider: (distance_meters(rider), rider.id))


def default_strategy() -> DispatchRankingStrategy:
    return ProximityRankingStrategy()
