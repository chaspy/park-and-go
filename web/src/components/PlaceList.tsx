import type { SearchResultItem } from "../types";

interface Props {
  items: SearchResultItem[];
  keyword: string;
  onSelect: (item: SearchResultItem) => void;
}

const VERDICT_COLORS: Record<string, string> = {
  onsite: "#16a34a",
  partner: "#2563eb",
  nearby_only: "#ca8a04",
  unknown: "#6b7280",
  avoid: "#dc2626",
};

export function PlaceList({ items, keyword, onSelect }: Props) {
  return (
    <div className="place-list">
      <div className="list-header">
        「{keyword}」の結果 ({items.length}件)
      </div>
      {items.map((item) => (
        <button
          key={item.place_id}
          className="place-card"
          onClick={() => onSelect(item)}
        >
          <div className="place-card-main">
            <div className="place-name">{item.name}</div>
            <div className="place-meta">
              {item.distance_m != null && (
                <span className="place-distance">
                  {item.distance_m < 1000
                    ? `${item.distance_m}m`
                    : `${(item.distance_m / 1000).toFixed(1)}km`}
                </span>
              )}
              {item.rating && (
                <span className="place-rating">★ {item.rating}</span>
              )}
            </div>
            {item.address && (
              <div className="place-address">{item.address}</div>
            )}
          </div>
          <div className="place-card-parking">
            <span
              className="parking-badge"
              style={{
                background: `${VERDICT_COLORS[item.parking.verdict]}18`,
                color: VERDICT_COLORS[item.parking.verdict],
                borderColor: `${VERDICT_COLORS[item.parking.verdict]}40`,
              }}
            >
              {item.parking.label}
            </span>
            {item.parking.nearest_parking_distance_m != null && (
              <span className="nearest-p">
                最寄P {item.parking.nearest_parking_distance_m}m
              </span>
            )}
          </div>
        </button>
      ))}
    </div>
  );
}
