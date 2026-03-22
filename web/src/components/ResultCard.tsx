import type { AnalyzeResponse } from "../types";

interface Props {
  result: AnalyzeResponse;
  onReanalyze: (url: string, name: string, address: string, forceRefresh: boolean) => void;
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

export function ResultCard({ result, onReanalyze }: Props) {
  return (
    <div className="result-card">
      <div className="result-header">
        <h2>{result.place_name}</h2>
        <span className={`badge badge-${result.verdict}`}>
          {VERDICT_LABELS[result.verdict] || result.verdict}
        </span>
      </div>

      {result.address && <div style={{ fontSize: 13, color: "#888" }}>{result.address}</div>}

      <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
        <span className={`badge vehicle-badge vehicle-${result.vehicle_fit}`}>
          {VEHICLE_LABELS[result.vehicle_fit] || result.vehicle_fit}
        </span>
        <span className="confidence">
          信頼度: {Math.round(result.confidence * 100)}%
        </span>
      </div>

      <p className="summary">{result.summary}</p>

      {result.evidence.length > 0 && (
        <>
          <div className="section-title">根拠</div>
          <ul className="evidence-list">
            {result.evidence.map((ev, i) => (
              <li key={i}>
                <span className="evidence-source">[{ev.source}]</span>
                {ev.text}
              </li>
            ))}
          </ul>
        </>
      )}

      {result.nearby_parking.length > 0 && (
        <>
          <div className="section-title">近隣駐車場</div>
          <ul className="parking-list">
            {result.nearby_parking.map((p, i) => (
              <li key={i}>
                <span>{p.name}</span>
                <span className="parking-distance">
                  {p.distance_m}m (徒歩{p.walking_minutes}分)
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      <button
        className="reanalyze-btn"
        onClick={() =>
          onReanalyze("", result.place_name, result.address || "", true)
        }
      >
        再判定
      </button>
    </div>
  );
}
