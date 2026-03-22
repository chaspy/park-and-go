import { useState } from "react";

interface Props {
  onSubmit: (url: string, name: string, address: string, forceRefresh: boolean) => void;
  loading: boolean;
}

export function SearchForm({ onSubmit, loading }: Props) {
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url && !name && !address) return;
    onSubmit(url, name, address, false);
  };

  return (
    <form className="search-form" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Google Maps URL"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
      />
      <input
        type="text"
        placeholder="店名"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <input
        type="text"
        placeholder="住所"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
      />
      <button type="submit" disabled={loading || (!url && !name && !address)}>
        {loading ? "解析中..." : "駐車場を判定"}
      </button>
    </form>
  );
}
