import math

from app.geo import haversine_km, min_distance_km


def test_haversine_zero_distance():
    assert haversine_km(12.0, 77.0, 12.0, 77.0) == 0.0


def test_haversine_known_distance():
    # Distance between Delhi (28.6139, 77.2090) and Mumbai (19.0760, 72.8777)
    distance = haversine_km(28.6139, 77.2090, 19.0760, 72.8777)
    assert math.isclose(distance, 1150, rel_tol=0.05)


def test_min_distance_km():
    base = (10.0, 10.0)
    points = [(10.1, 10.1), (11.0, 11.0)]
    assert min_distance_km(base, points) < 16
