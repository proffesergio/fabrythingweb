import { useEffect, useRef, useState } from "react";
import useApi from "../hooks/APIHandler";

const HEARTBEAT_MS = 20000;

// Keeps the rider marked present while the Online switch is on: watches the
// device position and posts it every 20s. Dispatch treats a rider as reachable
// only inside Rider.PRESENCE_WINDOW_MINUTES of the last beat, so closing this
// tab quietly removes them from the pool with no explicit "go offline" step.
//
// Location is only read while online, and only the latest position is sent —
// no trail is recorded anywhere.
export default function useRiderHeartbeat(online) {
    const { callApi } = useApi();
    const [position, setPosition] = useState(null);
    const [error, setError] = useState(null);
    const latest = useRef(null);

    useEffect(() => {
        if (!online) return undefined;

        let watchId = null;
        if (navigator.geolocation?.watchPosition) {
            watchId = navigator.geolocation.watchPosition(
                ({ coords }) => {
                    const p = { lat: coords.latitude, lng: coords.longitude };
                    latest.current = p;
                    setPosition(p);
                },
                (err) => setError(err?.message || "Location unavailable"),
                { enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 },
            );
        } else {
            setError("This device can't share location");
        }

        // Beat immediately so the rider becomes dispatchable without a 20s wait,
        // then on an interval. Coordinates are omitted until the first fix.
        const beat = () => callApi({
            url: "food/rider/heartbeat/", method: "POST",
            body: latest.current || {}, silent: true,
        });
        beat();
        const timer = setInterval(beat, HEARTBEAT_MS);

        return () => {
            clearInterval(timer);
            if (watchId !== null) navigator.geolocation.clearWatch(watchId);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [online]);

    return { position, error };
}
