import type { AnalyzeResponse } from "../types";

interface Props {
  items: AnalyzeResponse[];
  onSelect: (item: AnalyzeResponse) => void;
}

const VERDICT_SHORT: Record<string, string> = {
  onsite: "専用あり",
  partner: "提携",
  nearby_only: "近隣P",
  unknown: "不明",
  avoid: "困難",
};

export function RecentList({ items, onSelect }: Props) {
  return (
    <div className="recent-section">
      <h3>最近見た店</h3>
      <ul className="recent-list">
        {items.map((item) => (
          <li
            key={item.place_key}
            className="recent-item"
            onClick={() => onSelect(item)}
          >
            <span className="recent-name">{item.place_name}</span>
            <span className={`badge badge-${item.verdict} recent-verdict`}>
              {VERDICT_SHORT[item.verdict] || item.verdict}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
