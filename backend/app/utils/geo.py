"""Geodesic utility functions."""

import math

EARTH_RADIUS_M = 6_371_000
WALKING_SPEED_MPS = 1.2  # ~4.3 km/h average walking speed


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in meters between two coordinates using haversine formula."""
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_M * c


def walking_minutes(distance_m: float) -> int:
    """Estimate walking time in minutes from distance in meters."""
    if distance_m <= 0:
        return 0
    return max(1, round(distance_m / WALKING_SPEED_MPS / 60))
