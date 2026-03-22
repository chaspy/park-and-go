import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { SearchResultItem, NearbyParkingPin, Location } from "../types";

interface Props {
  center: Location;
  items: SearchResultItem[];
  parkingPins: NearbyParkingPin[];
  onSelect: (item: SearchResultItem) => void;
}

const VERDICT_COLORS: Record<string, string> = {
  onsite: "#16a34a",
  partner: "#2563eb",
  nearby_only: "#ca8a04",
  unknown: "#6b7280",
  avoid: "#dc2626",
};

function createStoreIcon(color: string) {
  return L.divIcon({
    className: "map-pin",
    html: `<div style="
      width: 28px; height: 28px;
      background: ${color};
      border: 2px solid white;
      border-radius: 50%;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    "></div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -16],
  });
}

const parkingIcon = L.divIcon({
  className: "map-pin-parking",
  html: `<div style="
    width: 22px; height: 22px;
    background: #7c3aed;
    border: 2px solid white;
    border-radius: 4px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 12px;
    font-weight: 700;
    line-height: 1;
  ">P</div>`,
  iconSize: [22, 22],
  iconAnchor: [11, 11],
  popupAnchor: [0, -13],
});

const currentLocationIcon = L.divIcon({
  className: "map-pin-current",
  html: `<div style="
    width: 16px; height: 16px;
    background: #3b82f6;
    border: 3px solid white;
    border-radius: 50%;
    box-shadow: 0 0 0 4px rgba(59,130,246,0.3), 0 2px 6px rgba(0,0,0,0.3);
  "></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

export function MapView({ center, items, parkingPins, onSelect }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMap = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current) return;

    if (leafletMap.current) {
      leafletMap.current.remove();
    }

    const map = L.map(mapRef.current, {
      zoomControl: false,
    }).setView([center.lat, center.lng], 15);

    L.control.zoom({ position: "bottomright" }).addTo(map);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
      maxZoom: 19,
    }).addTo(map);

    // Current location
    L.marker([center.lat, center.lng], { icon: currentLocationIcon })
      .addTo(map)
      .bindPopup("現在地");

    const bounds = L.latLngBounds([[center.lat, center.lng]]);

    // Nearby parking pins (P markers)
    parkingPins.forEach((p) => {
      L.marker([p.lat, p.lng], { icon: parkingIcon })
        .addTo(map)
        .bindPopup(`
          <div style="font-size:12px">
            <strong>${p.name}</strong><br>
            ${p.distance_m}m
          </div>
        `);
      bounds.extend([p.lat, p.lng]);
    });

    // Store result markers
    items.forEach((item) => {
      if (!item.lat || !item.lng) return;

      const color = VERDICT_COLORS[item.parking.verdict] || "#6b7280";
      const icon = createStoreIcon(color);

      const marker = L.marker([item.lat, item.lng], { icon })
        .addTo(map)
        .bindPopup(`
          <div style="font-size:13px;min-width:140px">
            <strong>${item.name}</strong><br>
            <span style="color:${color};font-weight:600">${item.parking.label}</span><br>
            ${item.distance_m != null ? `${item.distance_m}m` : ""}
            ${item.rating ? ` ★${item.rating}` : ""}
          </div>
        `);

      marker.on("click", () => marker.openPopup());
      marker.on("popupopen", () => {
        const popupEl = marker.getPopup()?.getElement();
        if (popupEl) {
          popupEl.style.cursor = "pointer";
          popupEl.onclick = () => onSelect(item);
        }
      });

      bounds.extend([item.lat, item.lng]);
    });

    if (items.length > 0) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
    }

    leafletMap.current = map;

    return () => {
      map.remove();
      leafletMap.current = null;
    };
  }, [center, items, parkingPins, onSelect]);

  return <div ref={mapRef} className="map-container" />;
}
