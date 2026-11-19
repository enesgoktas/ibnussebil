import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

export type MapPoint = {
  lat: number;
  lon: number;
  label?: string;
  tone?: "green" | "gold" | "blue" | "red" | "muted";
};

export type MapLine = {
  points: Array<[number, number]>;
  color?: string;
};

export function MapView({
  points,
  lines = [],
  center = [41.0082, 28.9784],
  zoom = 12,
  height,
}: {
  points: MapPoint[];
  lines?: MapLine[];
  center?: [number, number];
  zoom?: number;
  height?: number;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      zoomControl: true,
      attributionControl: true,
    }).setView(center, zoom);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);
    layerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    const initialTimer = window.setTimeout(() => {
      if (mapRef.current === map) map.invalidateSize();
    }, 50);

    return () => {
      window.clearTimeout(initialTimer);
      map.remove();
      mapRef.current = null;
      layerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const layer = layerRef.current;
    if (!map || !layer) return;
    layer.clearLayers();

    for (const line of lines) {
      if (line.points.length > 1) {
        L.polyline(line.points, {
          color: line.color ?? "#0f3d2e",
          weight: 4,
          opacity: 0.82,
          lineJoin: "round",
        }).addTo(layer);
      }
    }

    const bounds: L.LatLngExpression[] = [];
    for (const point of points) {
      bounds.push([point.lat, point.lon]);
      const tone = point.tone ?? "green";
      const icon = L.divIcon({
        className: "map-pin-wrap",
        html: `<span class="map-pin map-pin-${tone}">${point.label ?? ""}</span>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15],
      });
      L.marker([point.lat, point.lon], { icon }).addTo(layer);
    }

    if (bounds.length === 1) {
      map.setView(bounds[0], 13);
    } else if (bounds.length > 1) {
      map.fitBounds(L.latLngBounds(bounds), { padding: [36, 36], maxZoom: 14 });
    }
    const resizeTimer = window.setTimeout(() => {
      if (mapRef.current === map) map.invalidateSize();
    }, 50);
    return () => window.clearTimeout(resizeTimer);
  }, [points, lines]);

  return <div ref={containerRef} className="map-canvas" style={height ? { height } : undefined} />;
}
