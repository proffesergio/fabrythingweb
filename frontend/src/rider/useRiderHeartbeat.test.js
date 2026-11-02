import { renderHook, act, waitFor } from "@testing-library/react";
import useRiderHeartbeat from "./useRiderHeartbeat";

const mockCallApi = jest.fn(() => Promise.resolve({ status: 200, data: { data: {} } }));
jest.mock("../hooks/APIHandler", () => () => ({ callApi: mockCallApi }));

describe("useRiderHeartbeat", () => {
    let watchers;
    beforeEach(() => {
        mockCallApi.mockClear();
        watchers = {};
        global.navigator.geolocation = {
            watchPosition: jest.fn((ok) => {
                watchers.ok = ok;
                return 7;
            }),
            clearWatch: jest.fn(),
        };
    });

    it("does nothing while offline", () => {
        renderHook(() => useRiderHeartbeat(false));
        expect(navigator.geolocation.watchPosition).not.toHaveBeenCalled();
        expect(mockCallApi).not.toHaveBeenCalled();
    });

    it("watches position and posts a heartbeat once online", async () => {
        const { result } = renderHook(() => useRiderHeartbeat(true));
        expect(navigator.geolocation.watchPosition).toHaveBeenCalled();

        act(() => watchers.ok({ coords: { latitude: 23.71, longitude: 90.93 } }));
        await waitFor(() => expect(result.current.position).toEqual({ lat: 23.71, lng: 90.93 }));

        await waitFor(() => expect(mockCallApi).toHaveBeenCalledWith(
            expect.objectContaining({ url: "food/rider/heartbeat/", method: "POST" })
        ));
    });

    it("stops watching when it goes offline", () => {
        const { rerender } = renderHook(({ online }) => useRiderHeartbeat(online),
            { initialProps: { online: true } });
        rerender({ online: false });
        expect(navigator.geolocation.clearWatch).toHaveBeenCalledWith(7);
    });
});
