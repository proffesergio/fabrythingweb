import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import useApi from '../../hooks/APIHandler';
import { cacheKey, readCache, writeCache } from '../../hooks/apiCache';

const ZONES_KEY = cacheKey('food/zones/');

const Ctx = createContext(null);
export const useFoodLocation = () => useContext(Ctx);

// Great-circle distance (km) — mirrors backend food.geo.haversine_km so the
// "use my location" button can resolve to a serviceable zone client-side. The
// server re-validates serviceability authoritatively at order time.
const km = (aLat, aLng, xLat, xLng) => {
  const R = 6371;
  const dLat = ((xLat - aLat) * Math.PI) / 180;
  const dLng = ((xLng - aLng) * Math.PI) / 180;
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((aLat * Math.PI) / 180) * Math.cos((xLat * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
};

export function FoodLocationProvider({ children }) {
  const { callApi } = useApi();
  // Seed zones from cache for an instant paint, then revalidate in the background.
  const [zones, setZones] = useState(() => readCache(ZONES_KEY)?.data || []);
  const [zoneId, setZoneId] = useState(() => localStorage.getItem('food_zone') || '');
  const [villageId, setVillageId] = useState(() => localStorage.getItem('food_village') || '');
  const [lang, setLangState] = useState(() => localStorage.getItem('food_lang') || 'en');
  const [coords, setCoordsState] = useState(() => {
    try { return JSON.parse(localStorage.getItem('food_pin')) || null; } catch { return null; }
  });
  const [pickerOpen, setPickerOpen] = useState(false);

  const setZone = useCallback((id) => {
    setZoneId(id);
    localStorage.setItem('food_zone', id || '');
  }, []);

  const setVillage = useCallback((id) => {
    setVillageId(id ? String(id) : '');
    localStorage.setItem('food_village', id ? String(id) : '');
  }, []);

  // A dropped/detected map pin — persisted so checkout can reuse it.
  const setCoords = useCallback((c) => {
    setCoordsState(c);
    try { localStorage.setItem('food_pin', c ? JSON.stringify(c) : ''); } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    (async () => {
      const res = await callApi({ url: 'food/zones/', method: 'GET' });
      // Tolerate both the {data:[...]} envelope and a bare [...] list.
      const raw = res?.data;
      const z = Array.isArray(raw) ? raw : (raw?.data || []);
      if (z.length) {
        setZones(z);
        writeCache(ZONES_KEY, z);
        // Never leave checkout un-orderable: if the current zone is unset (or no
        // longer exists) and there's exactly one serviceable area, auto-select it.
        const saved = localStorage.getItem('food_zone') || '';
        const stillValid = saved && z.some((zz) => String(zz.id) === saved);
        if (!stillValid && z.length === 1) setZone(String(z[0].id));
        else if (!stillValid) setZone('');
      }
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const setLang = useCallback((l) => {
    setLangState(l);
    localStorage.setItem('food_lang', l);
  }, []);

  const detectLocation = useCallback(
    () =>
      new Promise((resolve, reject) => {
        if (!navigator.geolocation) return reject(new Error('Geolocation unavailable'));
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            const c = { lat: pos.coords.latitude, lng: pos.coords.longitude };
            setCoords(c);
            const hit = zones.find(
              (z) => km(Number(z.center_lat), Number(z.center_lng), c.lat, c.lng) <= Number(z.radius_km)
            );
            if (hit) setZone(String(hit.id));
            resolve({ coords: c, zone: hit || null });
          },
          (err) => reject(err),
          { enableHighAccuracy: true, timeout: 8000 }
        );
      }),
    [zones, setZone]
  );

  const currentZone = zones.find((z) => String(z.id) === String(zoneId)) || null;
  const currentVillage =
    (currentZone?.villages || []).find((v) => String(v.id) === String(villageId)) || null;

  return (
    <Ctx.Provider value={{
      zones, zoneId, currentZone, setZoneId: setZone,
      villageId, currentVillage, setVillageId: setVillage,
      lang, setLang, coords, setCoords, detectLocation,
      pickerOpen, openPicker: () => setPickerOpen(true), closePicker: () => setPickerOpen(false),
    }}>
      {children}
    </Ctx.Provider>
  );
}
