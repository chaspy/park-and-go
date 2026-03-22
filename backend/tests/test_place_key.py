from app.utils.place_key import extract_place_id_from_url, normalize_place_key


def test_normalize_with_name_and_address():
    key = normalize_place_key(name="Test Store", address="Shibuya, Tokyo")
    assert key == "test_store_shibuya_tokyo"


def test_normalize_with_url_only():
    key = normalize_place_key(
        google_maps_url="https://www.google.com/maps/place/My+Cafe/@35.0,139.0"
    )
    assert "my" in key.lower()


def test_normalize_empty_input():
    key = normalize_place_key()
    assert key == "unknown"


def test_normalize_japanese():
    key = normalize_place_key(name="焼肉太郎", address="東京都渋谷区")
    assert "焼肉太郎" in key
    assert "東京都渋谷区" in key


def test_extract_place_id_from_url():
    url = "https://www.google.com/maps/place/Test+Shop/@35.6,139.7,17z"
    result = extract_place_id_from_url(url)
    assert result == "Test+Shop"


def test_extract_place_id_from_empty():
    assert extract_place_id_from_url("") is None
    assert extract_place_id_from_url("https://google.com") is None
