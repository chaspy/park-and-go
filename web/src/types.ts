export interface Location {
  lat: number;
  lng: number;
}

// --- Search ---

export interface SearchRequest {
  keyword: string;
  lat: number;
  lng: number;
  radius_m?: number;
}

export interface ParkingSummary {
  verdict: Verdict;
  confidence: number;
  vehicle_fit: VehicleFit;
  label: string;
  nearby_parking_count: number;
  nearest_parking_distance_m: number | null;
}

export interface SearchResultItem {
  place_id: string;
  name: string;
  address?: string;
  lat?: number;
  lng?: number;
  distance_m?: number;
  types: string[];
  rating?: number;
  website_url?: string;
  google_maps_uri?: string;
  parking: ParkingSummary;
}

export interface SearchResponse {
  keyword: string;
  location: Location;
  results: SearchResultItem[];
  total: number;
}

// --- Analyze (detail) ---

export type Verdict = "onsite" | "partner" | "nearby_only" | "unknown" | "avoid";
export type VehicleFit = "easy" | "ok" | "tight" | "unknown" | "avoid";

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
  verdict: Verdict;
  confidence: number;
  vehicle_fit: VehicleFit;
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
