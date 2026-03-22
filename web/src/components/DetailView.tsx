import type { AnalyzeResponse } from "../types";

interface Props {
  detail: AnalyzeResponse | null;
  loading: boolean;
  onBack: () => void;
}

const VERDICT_LABELS: Record<string, string> = {
  onsite: "専用駐車場あり",
  partner: "提携駐車場",
  nearby_only: "近隣パーキング",
  unknown: "不明",
  avoid: "駐車困難",
};

const VEHICLE_LABELS: Record<string, string> = {
  easy: "余裕あり",
  ok: "OK",
  tight: "狭い可能性",
  unknown: "車適合不明",
  avoid: "サイズ超過",
};

export function DetailView({ detail, loading, onBack }: Props) {
  return (
    <div className="detail-view">
      <button className="back-btn" onClick={onBack}>← 戻る</button>

      {loading && <div className="loading">詳細を解析中...</div>}

      {!loading && !detail && (
        <div className="error-banner">詳細の取得に失敗しました</div>
      )}

      {!loading && detail && (
        <>
          <div className="detail-header">
            <h2>{detail.place_name}</h2>
            <span className={`verdict-badge verdict-${detail.verdict}`}>
              {VERDICT_LABELS[detail.verdict] || detail.verdict}
            </span>
          </div>

          {detail.address && (
            <div className="detail-address">{detail.address}</div>
          )}

          <div className="detail-tags">
            <span className={`vehicle-tag vehicle-${detail.vehicle_fit}`}>
              車: {VEHICLE_LABELS[detail.vehicle_fit] || detail.vehicle_fit}
            </span>
            <span className="confidence-tag">
              信頼度 {Math.round(detail.confidence * 100)}%
            </span>
          </div>

          <p className="detail-summary">{detail.summary}</p>

          {detail.evidence.length > 0 && (
            <div className="detail-section">
              <h3>根拠</h3>
              <ul className="evidence-list">
                {detail.evidence.map((ev, i) => (
                  <li key={i}>
                    <span className="ev-source">[{ev.source}]</span> {ev.text}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {detail.nearby_parking.length > 0 && (
            <div className="detail-section">
              <h3>近隣駐車場</h3>
              <ul className="nearby-list">
                {detail.nearby_parking.map((p, i) => (
                  <li key={i}>
                    <span className="np-name">{p.name}</span>
                    <span className="np-dist">
                      {p.distance_m}m・徒歩{p.walking_minutes}分
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {detail.location && (
            <a
              className="maps-link"
              href={`https://www.google.com/maps/search/?api=1&query=${detail.location.lat},${detail.location.lng}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              Google Maps で開く
            </a>
          )}
        </>
      )}
    </div>
  );
}
