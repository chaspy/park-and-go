import { useState, useEffect, useCallback } from "react";
import { search, analyze, geocode, reverseGeocode } from "./api";
import type { SearchResultItem, NearbyParkingPin, AnalyzeResponse, Location } from "./types";
import { SearchBar } from "./components/SearchBar";
import { PlaceList } from "./components/PlaceList";
import { MapView } from "./components/MapView";
import { DetailView } from "./components/DetailView";
import { LocationInput } from "./components/LocationInput";
import "./App.css";

type View = "search" | "detail";
type ResultMode = "map" | "list";

function App() {
  const [view, setView] = useState<View>("search");
  const [resultMode, setResultMode] = useState<ResultMode>("map");
  const [location, setLocation] = useState<Location | null>(null);
  const [locationName, setLocationName] = useState<string | null>(null);
  const [locationLoading, setLocationLoading] = useState(true);
  const [geoFailed, setGeoFailed] = useState(false);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [parkingPins, setParkingPins] = useState<NearbyParkingPin[]>([]);
  const [detail, setDetail] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastKeyword, setLastKeyword] = useState("");

  // Try GPS on mount
  useEffect(() => {
    if (!navigator.geolocation) {
      setGeoFailed(true);
      setLocationLoading(false);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const loc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        setLocation(loc);
        setLocationLoading(false);
        try {
          const name = await reverseGeocode(loc.lat, loc.lng);
          setLocationName(name);
        } catch {
          setLocationName(`${loc.lat.toFixed(4)}, ${loc.lng.toFixed(4)}`);
        }
      },
      () => {
        setGeoFailed(true);
        setLocationLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }, []);

  const handleSetLocation = useCallback(async (query: string) => {
    setLocationLoading(true);
    try {
      const result = await geocode(query);
      setLocation({ lat: result.lat, lng: result.lng });
      setLocationName(result.name);
      setGeoFailed(false);
    } catch {
      setError("場所が見つかりませんでした");
    } finally {
      setLocationLoading(false);
    }
  }, []);

  const handleChangeLocation = useCallback(() => {
    setLocation(null);
    setLocationName(null);
    setGeoFailed(true);
    setResults([]);
    setLastKeyword("");
  }, []);

  const handleSearch = useCallback(
    async (keyword: string) => {
      if (!location) return;
      setLoading(true);
      setError(null);
      setLastKeyword(keyword);
      try {
        const res = await search({
          keyword,
          lat: location.lat,
          lng: location.lng,
          radius_m: 2000,
        });
        setResults(res.results);
        setParkingPins(res.nearby_parking_pins || []);
      } catch (e) {
        setError(e instanceof Error ? e.message : "検索に失敗しました");
      } finally {
        setLoading(false);
      }
    },
    [location]
  );

  const handleSelectPlace = useCallback(async (item: SearchResultItem) => {
    setView("detail");
    setDetailLoading(true);
    setDetail(null);
    try {
      const res = await analyze({
        name: item.name,
        address: item.address || undefined,
        lat: item.lat || undefined,
        lng: item.lng || undefined,
      });
      setDetail(res);
    } catch {
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handleBack = useCallback(() => {
    setView("search");
    setDetail(null);
  }, []);

  if (view === "detail") {
    return (
      <div className="app">
        <DetailView detail={detail} loading={detailLoading} onBack={handleBack} />
      </div>
    );
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Parking Judge</h1>
      </header>

      {locationLoading && (
        <div className="location-banner">位置情報を取得中...</div>
      )}

      {!locationLoading && geoFailed && !location && (
        <LocationInput onSubmit={handleSetLocation} />
      )}

      {location && !locationLoading && (
        <>
          <div className="location-status">
            <span>📍 {locationName || "現在地を特定中..."}</span>
            <button className="change-location-btn" onClick={handleChangeLocation}>
              変更
            </button>
          </div>
          <SearchBar onSearch={handleSearch} loading={loading} />
        </>
      )}

      {error && <div className="error-banner">{error}</div>}

      {loading && <div className="loading">検索中...</div>}

      {!loading && results.length > 0 && location && (
        <>
          <div className="mode-toggle">
            <button
              className={`mode-btn ${resultMode === "map" ? "active" : ""}`}
              onClick={() => setResultMode("map")}
            >
              マップ
            </button>
            <button
              className={`mode-btn ${resultMode === "list" ? "active" : ""}`}
              onClick={() => setResultMode("list")}
            >
              リスト
            </button>
          </div>

          {resultMode === "map" && (
            <MapView center={location} items={results} parkingPins={parkingPins} onSelect={handleSelectPlace} />
          )}

          {resultMode === "list" && (
            <PlaceList items={results} keyword={lastKeyword} onSelect={handleSelectPlace} />
          )}
        </>
      )}

      {!loading && lastKeyword && results.length === 0 && !error && (
        <div className="empty">「{lastKeyword}」の検索結果がありません</div>
      )}
    </div>
  );
}

export default App;
