import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Box } from "@mui/material";

// A deliberately simple map: rider, pickup, drop-off, and a straight dashed line
// for the leg in progress. We do NOT run a routing engine — real turn-by-turn is
// a Google Maps hand-off from DeliveryCard, which keeps this free of API keys,
// rate limits and an extra production dependency.
const icon = (emoji, size = 28) => L.divIcon({
    html: `<div style="font-size:${size}px;line-height:1">${emoji}</div>`,
    className: "", iconSize: [size, size], iconAnchor: [size / 2, size / 2],
});

const num = (v) => (v === null || v === undefined || v === "" ? null : Number(v));

export default function DeliveryMap({ riderPosition, pickup, dropoff, leg }) {
    const el = useRef(null);
    const map = useRef(null);
    const layer = useRef(null);

    useEffect(() => {
        if (!el.current || map.current) return;
        map.current = L.map(el.current, { zoomControl: false, attributionControl: false });
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 })
            .addTo(map.current);
        layer.current = L.layerGroup().addTo(map.current);
        map.current.setView([23.7104, 90.928], 13); // Bancharampur, until we know better
    }, []);

    useEffect(() => {
        if (!map.current || !layer.current) return;
        layer.current.clearLayers();

        const points = [];
        const pick = pickup && num(pickup.lat) !== null ? [num(pickup.lat), num(pickup.lng)] : null;
        const drop = dropoff && num(dropoff.lat) !== null ? [num(dropoff.lat), num(dropoff.lng)] : null;
        const me = riderPosition ? [riderPosition.lat, riderPosition.lng] : null;

        if (pick) { L.marker(pick, { icon: icon("🍳") }).addTo(layer.current); points.push(pick); }
        if (drop) { L.marker(drop, { icon: icon("🏠") }).addTo(layer.current); points.push(drop); }
        if (me) { L.marker(me, { icon: icon("🛵", 32) }).addTo(layer.current); points.push(me); }

        // Dashed line for the leg currently being ridden.
        const target = leg === "PICKUP" ? pick : drop;
        if (me && target) {
            L.polyline([me, target], { color: "#E8452B", weight: 3, dashArray: "8 8" })
                .addTo(layer.current);
        }

        if (points.length > 1) {
            map.current.fitBounds(L.latLngBounds(points).pad(0.25));
        } else if (points.length === 1) {
            map.current.setView(points[0], 15);
        }
    }, [riderPosition, pickup, dropoff, leg]);

    return <Box ref={el} sx={{ height: 220, borderRadius: 2, overflow: "hidden", my: 1.5 }} />;
}
