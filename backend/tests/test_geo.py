from app.utils.geo import haversine_distance, walking_minutes


def test_haversine_same_point():
    assert haversine_distance(35.6, 139.7, 35.6, 139.7) == 0.0


def test_haversine_known_distance():
    # Tokyo Station to Shibuya Station is roughly 5.5km
    dist = haversine_distance(35.6812, 139.7671, 35.6580, 139.7016)
    assert 5000 < dist < 7000


def test_walking_minutes_zero():
    assert walking_minutes(0) == 0


def test_walking_minutes_100m():
    mins = walking_minutes(100)
    assert 1 <= mins <= 2


def test_walking_minutes_500m():
    mins = walking_minutes(500)
    assert 5 <= mins <= 8
