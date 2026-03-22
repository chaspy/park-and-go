import { useState, useEffect } from "react";
import { analyze, getRecent } from "./api";
import type { AnalyzeResponse } from "./types";
import { SearchForm } from "./components/SearchForm";
import { ResultCard } from "./components/ResultCard";
import { RecentList } from "./components/RecentList";
import "./App.css";

function App() {
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [recent, setRecent] = useState<AnalyzeResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRecent = async () => {
    const data = await getRecent();
    setRecent(data);
  };

  useEffect(() => {
    loadRecent();
  }, []);

  const handleAnalyze = async (
    url: string,
    name: string,
    address: string,
    forceRefresh: boolean
  ) => {
    setLoading(true);
    setError(null);
    try {
      const res = await analyze({
        google_maps_url: url || undefined,
        name: name || undefined,
        address: address || undefined,
        force_refresh: forceRefresh,
      });
      setResult(res);
      loadRecent();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectRecent = (item: AnalyzeResponse) => {
    setResult(item);
  };

  return (
    <div className="app">
      <header className="header">
        <h1>Parking Judge</h1>
        <p className="subtitle">店舗の駐車しやすさ判定</p>
      </header>

      <main className="main">
        <SearchForm onSubmit={handleAnalyze} loading={loading} />

        {error && <div className="error-banner">{error}</div>}

        {loading && <div className="loading">解析中...</div>}

        {result && !loading && <ResultCard result={result} onReanalyze={handleAnalyze} />}

        {recent.length > 0 && (
          <RecentList items={recent} onSelect={handleSelectRecent} />
        )}
      </main>
    </div>
  );
}

export default App;
