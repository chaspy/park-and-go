import { useState, useEffect, useCallback } from "react";
import { search, analyze } from "./api";
import type { SearchResultItem, AnalyzeResponse, Location } from "./types";
import { SearchBar } from "./components/SearchBar";
import { PlaceList } from "./components/PlaceList";
import { DetailView } from "./components/DetailView";
import "./App.css";

type View = "search" | "detail";

function App() {
  const [view, setView] = useState<View>("search");
  const [location, setLocation] = useState<Location | null>(null);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [detail, setDetail] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastKeyword, setLastKeyword] = useState("");

  // Get current location on mount
  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationError("位置情報がサポートされていません");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude });
      },
      () => {
        setLocationError("位置情報を許可してください");
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
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
      // If detailed analysis fails, build a minimal result from search data
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
        <DetailView
          detail={detail}
          loading={detailLoading}
          onBack={handleBack}
        />
      </div>
    );
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Parking Judge</h1>
      </header>

      {locationError && <div className="location-banner">{locationError}</div>}
      {location && !locationError && (
        <SearchBar onSearch={handleSearch} loading={loading} />
      )}

      {error && <div className="error-banner">{error}</div>}

      {loading && <div className="loading">検索中...</div>}

      {!loading && results.length > 0 && (
        <PlaceList
          items={results}
          keyword={lastKeyword}
          onSelect={handleSelectPlace}
        />
      )}

      {!loading && lastKeyword && results.length === 0 && !error && (
        <div className="empty">「{lastKeyword}」の検索結果がありません</div>
      )}
    </div>
  );
}

export default App;
