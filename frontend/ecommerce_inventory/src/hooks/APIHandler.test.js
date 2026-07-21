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
});
