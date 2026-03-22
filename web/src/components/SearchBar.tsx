import { useState } from "react";

interface Props {
  onSearch: (keyword: string) => void;
  loading: boolean;
}

const SUGGESTIONS = ["ラーメン", "ランチ", "カフェ", "クラフトビール", "焼肉", "寿司"];

export function SearchBar({ onSearch, loading }: Props) {
  const [keyword, setKeyword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyword.trim()) return;
    onSearch(keyword.trim());
  };

  const handleSuggestion = (s: string) => {
    setKeyword(s);
    onSearch(s);
  };

  return (
    <div className="search-section">
      <form className="search-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="何を探す？"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          autoFocus
        />
        <button type="submit" disabled={loading || !keyword.trim()}>
          検索
        </button>
      </form>
      <div className="suggestions">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            className="suggestion-chip"
            onClick={() => handleSuggestion(s)}
            disabled={loading}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
