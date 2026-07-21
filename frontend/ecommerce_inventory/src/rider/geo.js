// Distance and bearing for the rider map. Mirrors food/geo.py::haversine_km on
// the backend so the two never disagree about how far away a drop-off is.
const R_KM = 6371;
const rad = (d) => (d * Math.PI) / 180;
const deg = (r) => (r * 180) / Math.PI;

export const haversineKm = (a, b) => {
    const dPhi = rad(b.lat - a.lat);
    const dLambda = rad(b.lng - a.lng);
    const p1 = rad(a.lat);
    const p2 = rad(b.lat);
    const h = Math.sin(dPhi / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dLambda / 2) ** 2;
    return 2 * R_KM * Math.asin(Math.sqrt(h));
};

// Compass bearing from → to, 0 = north, clockwise.
export const bearingDeg = (from, to) => {
    const p1 = rad(from.lat);
    const p2 = rad(to.lat);
    const dLambda = rad(to.lng - from.lng);
    const y = Math.sin(dLambda) * Math.cos(p2);
    const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dLambda);
    return (deg(Math.atan2(y, x)) + 360) % 360;
};
