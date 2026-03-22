import { useState } from "react";

interface Props {
  onSubmit: (query: string) => void;
}

const PRESETS = ["東京駅", "渋谷駅", "新宿駅", "横浜駅", "大宮駅"];

export function LocationInput({ onSubmit }: Props) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    onSubmit(query.trim());
  };

  return (
    <div className="location-input">
      <p className="location-input-label">場所を入力してください</p>
      <form className="location-input-form" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="駅名・住所・場所"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
        <button type="submit" disabled={!query.trim()}>決定</button>
      </form>
      <div className="location-presets">
        {PRESETS.map((p) => (
          <button key={p} className="preset-chip" onClick={() => onSubmit(p)}>
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
