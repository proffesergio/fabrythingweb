import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Read-only counterpart to MapPicker: shows where the rider is relative to the
// delivery address, and never lets the customer move anything. Kept separate
// rather than adding a `readOnly` flag to MapPicker, because the two share only
// the Leaflet boilerplate — this one tracks a moving pin and auto-fits two
// points, which a picker must never do.
const CENTER = [23.7772, 90.7886];   // Bancharampur Upazila

// Emoji divIcons, for the same reason MapPicker uses them: Leaflet's default
// marker PNGs break under CRA/webpack without extra asset config.
const icon = (emoji, label) => L.divIcon({
  className: 'food-track-pin',
  html: `<div role="img" aria-label="${label}" style="font-size:28px;line-height:1">${emoji}</div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 26],
});
const RIDER_ICON = icon('🛵', 'Rider');
const HOME_ICON = icon('🏠', 'Delivery address');

const isNum = (v) => v != null && !Number.isNaN(Number(v));

export default function LiveTrackMap({ rider, destination, height = 240 }) {
  const elRef = useRef(null);
  const mapRef = useRef(null);
  const riderRef = useRef(null);
  const destRef = useRef(null);

  useEffect(() => {
    if (!elRef.current || mapRef.current) return undefined;
    let map;
    try {
      map = L.map(elRef.current, { center: CENTER, zoom: 14, zoomControl: false });
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19, attribution: '© OpenStreetMap',
      }).addTo(map);
      mapRef.current = map;
      // Mounted inside a card that may still be laying out; force a re-measure.
      setTimeout(() => map.invalidateSize(), 120);
    } catch {
      /* jsdom / no-DOM environments: render the container only. */
    }
    return () => { if (map) map.remove(); mapRef.current = null; riderRef.current = null; destRef.current = null; };
  }, []);

  // Move the pins as the rider's heartbeat lands, rather than tearing the map
  // down and rebuilding it on every poll.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const pts = [];

    if (isNum(rider?.lat) && isNum(rider?.lng)) {
      const at = [Number(rider.lat), Number(rider.lng)];
      if (riderRef.current) riderRef.current.setLatLng(at);
      else riderRef.current = L.marker(at, { icon: RIDER_ICON }).addTo(map);
      pts.push(at);
    }
    if (isNum(destination?.lat) && isNum(destination?.lng)) {
      const at = [Number(destination.lat), Number(destination.lng)];
      if (destRef.current) destRef.current.setLatLng(at);
      else destRef.current = L.marker(at, { icon: HOME_ICON }).addTo(map);
      pts.push(at);
    }

    if (pts.length > 1) map.fitBounds(pts, { padding: [42, 42], maxZoom: 16 });
    else if (pts.length === 1) map.setView(pts[0], 15);
  }, [rider?.lat, rider?.lng, destination?.lat, destination?.lng]);

  return (
    <div ref={elRef} aria-label="Live delivery map"
      style={{ height, width: '100%', borderRadius: 16, overflow: 'hidden', zIndex: 0 }} />
  );
}
