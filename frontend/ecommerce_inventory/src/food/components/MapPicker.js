import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Bancharampur Upazila — approximate centre + a bounding box so the map can't be
// dragged out of the service area.
const CENTER = [23.7772, 90.7886];
const BOUNDS = [[23.66, 90.70], [23.87, 90.87]];

// Emoji divIcon avoids Leaflet's default marker PNG assets (which break under
// CRA/webpack without extra config).
const pinIcon = L.divIcon({
  className: 'food-map-pin',
  html: '<div style="font-size:30px;line-height:1">📍</div>',
  iconSize: [30, 30],
  iconAnchor: [15, 28],
});

export default function MapPicker({ value, onChange, height = 220 }) {
  const elRef = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    if (!elRef.current || mapRef.current) return undefined;
    let map;
    try {
      const start = value?.lat ? [value.lat, value.lng] : CENTER;
      map = L.map(elRef.current, {
        center: start, zoom: 13, maxBounds: BOUNDS, maxBoundsViscosity: 0.8,
      });
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19, attribution: '© OpenStreetMap',
      }).addTo(map);
      const marker = L.marker(start, { icon: pinIcon, draggable: true }).addTo(map);
      const emit = (latlng) =>
        onChangeRef.current?.({ lat: +latlng.lat.toFixed(6), lng: +latlng.lng.toFixed(6) });
      marker.on('dragend', () => emit(marker.getLatLng()));
      map.on('click', (e) => { marker.setLatLng(e.latlng); emit(e.latlng); });
      mapRef.current = map;
      markerRef.current = marker;
      // Dialogs mount hidden; force a re-measure once visible so tiles fill.
      setTimeout(() => map.invalidateSize(), 120);
    } catch {
      /* jsdom / no-DOM environments: render the container only. */
    }
    return () => { if (map) map.remove(); mapRef.current = null; markerRef.current = null; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Reflect external changes (e.g. "use my location", picking a union).
  useEffect(() => {
    if (markerRef.current && mapRef.current && value?.lat) {
      markerRef.current.setLatLng([value.lat, value.lng]);
      mapRef.current.panTo([value.lat, value.lng]);
    }
  }, [value?.lat, value?.lng]);

  return (
    <div ref={elRef} aria-label="Delivery location map"
      style={{ height, width: '100%', borderRadius: 16, overflow: 'hidden', zIndex: 0 }} />
  );
}
