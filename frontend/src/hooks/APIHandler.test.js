import { renderHook } from "@testing-library/react";
import axios from "axios";
import useApi from "./APIHandler";

jest.mock("axios");
jest.mock("react-toastify", () => ({ toast: { error: jest.fn(), success: jest.fn() } }));

describe("useApi callApi", () => {
    afterEach(() => jest.clearAllMocks());

    it("returns null on an HTTP error by default", async () => {
        axios.request.mockRejectedValue({
            message: "Request failed",
            response: { status: 400, data: { message: "Validation error", data: { price: ["Required."] } } },
        });
        const { result } = renderHook(() => useApi());
        const res = await result.current.callApi({ url: "food/admin/items/", method: "POST" });
        expect(res).toBeNull();
    });

    it("returns the error response when rawError is set", async () => {
        axios.request.mockRejectedValue({
            message: "Request failed",
            response: { status: 400, data: { message: "Validation error", data: { price: ["Required."] } } },
        });
        const { result } = renderHook(() => useApi());
        const res = await result.current.callApi({ url: "food/admin/items/", method: "POST", rawError: true });
        expect(res.status).toBe(400);
        expect(res.data.data).toEqual({ price: ["Required."] });
    });

    it("returns null with rawError when there is no response at all", async () => {
        axios.request.mockRejectedValue({ message: "Network Error" });
        const { result } = renderHook(() => useApi());
        const res = await result.current.callApi({ url: "food/admin/items/", rawError: true });
        expect(res).toBeNull();
    });

    it("silently refreshes an expired session and replays the request", async () => {
        localStorage.setItem("token", "expired-access");
        localStorage.setItem("refresh_token", "good-refresh");
        axios.request
            .mockRejectedValueOnce({
                message: "Request failed",
                response: { status: 401, data: { detail: "Given token not valid" } },
            })
            .mockResolvedValueOnce({ status: 200, data: { access: "new-access", refresh: "new-refresh" } })
            .mockResolvedValueOnce({ status: 200, data: { data: { ok: true } } });
        const { result } = renderHook(() => useApi());
        const res = await result.current.callApi({ url: "store/nobleseek/admin/stats/" });
        expect(res.status).toBe(200);
        expect(localStorage.getItem("token")).toBe("new-access");
        expect(localStorage.getItem("refresh_token")).toBe("new-refresh");
        localStorage.clear();
    });

    it("clears both tokens when refresh is rejected", async () => {
        localStorage.setItem("token", "dead-access");
        localStorage.setItem("refresh_token", "dead-refresh");
        axios.request
            .mockRejectedValueOnce({
                message: "Request failed",
                response: { status: 401, data: { detail: "Given token not valid" } },
            })
            .mockRejectedValueOnce({
                message: "Request failed",
                response: { status: 401, data: { detail: "Token is invalid or expired" } },
            })
            .mockRejectedValueOnce({
                message: "Request failed",
                response: { status: 401, data: { detail: "Given token not valid" } },
            });
        const { result } = renderHook(() => useApi());
        const res = await result.current.callApi({ url: "store/nobleseek/admin/stats/", silent: true });
        expect(res).toBeNull();
        expect(localStorage.getItem("token")).toBeNull();
        expect(localStorage.getItem("refresh_token")).toBeNull();
        localStorage.clear();
    });
});
