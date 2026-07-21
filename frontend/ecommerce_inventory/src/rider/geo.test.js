import { haversineKm, bearingDeg } from "./geo";

describe("geo", () => {
    it("measures ~0 km between a point and itself", () => {
        expect(haversineKm({ lat: 23.7104, lng: 90.928 }, { lat: 23.7104, lng: 90.928 })).toBeCloseTo(0, 3);
    });

    it("measures a known short distance", () => {
        // ~1.11 km per 0.01 degree of latitude
        const d = haversineKm({ lat: 23.7104, lng: 90.928 }, { lat: 23.7204, lng: 90.928 });
        expect(d).toBeGreaterThan(1.0);
        expect(d).toBeLessThan(1.2);
    });

    it("reports due north as ~0 degrees and due east as ~90", () => {
        expect(bearingDeg({ lat: 23.71, lng: 90.92 }, { lat: 23.72, lng: 90.92 })).toBeCloseTo(0, 0);
        expect(bearingDeg({ lat: 23.71, lng: 90.92 }, { lat: 23.71, lng: 90.93 })).toBeCloseTo(90, 0);
    });
});
