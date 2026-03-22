export interface Location {
  lat: number;
  lng: number;
}

export interface EvidenceItem {
  source: string;
  kind: string;
  text: string;
  weight: number;
}

export interface NearbyParkingItem {
  name: string;
  distance_m: number;
  walking_minutes: number;
  lat?: number;
  lng?: number;
}

export interface AnalyzeResponse {
  place_key: string;
  place_name: string;
  address?: string;
  location?: Location;
  verdict: "onsite" | "partner" | "nearby_only" | "unknown" | "avoid";
  confidence: number;
  vehicle_fit: "easy" | "ok" | "tight" | "unknown" | "avoid";
  summary: string;
  evidence: EvidenceItem[];
  nearby_parking: NearbyParkingItem[];
  fetched_at: string;
}

export interface AnalyzeRequest {
  google_maps_url?: string;
  name?: string;
  address?: string;
  lat?: number;
  lng?: number;
  force_refresh?: boolean;
}
