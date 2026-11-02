import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import RiderDashboard from "./RiderDashboard";

jest.mock("./DeliveryMap", () => () => <div data-testid="delivery-map" />);
jest.mock("react-toastify", () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockCallApi = jest.fn();
jest.mock("../hooks/APIHandler", () => () => ({ callApi: mockCallApi }));

const me = {
    name: "Rakib", rider_code: "RD01", total_deliveries: 5,
    total_earnings: "250.00", is_available: false,
};
const orders = [{
    id: 1, order_code: "FD1", status: "OUT_FOR_DELIVERY", restaurant_name: "Kacchi Ghor",
    guest_name: "Karim", guest_phone: "018", restaurant_phone: "017",
    delivery_address: "Ujanchar", restaurant_address: "Bazar", total: "340.00",
    payment_method: "COD", cash_to_collect: "340.00", items: [], notes: "",
}];
const earnings = { today: "50.00", lifetime: "250.00", cash_to_collect: "340.00", history: [] };

beforeEach(() => {
    mockCallApi.mockImplementation(({ url }) => {
        if (url === "food/rider/me/") return Promise.resolve({ status: 200, data: { data: me } });
        if (url === "food/rider/orders/") return Promise.resolve({ status: 200, data: { data: orders } });
        if (url === "food/rider/earnings/") return Promise.resolve({ status: 200, data: { data: earnings } });
        return Promise.resolve({ status: 200, data: { data: {} } });
    });
});
afterEach(() => jest.clearAllMocks());

const renderDash = () => render(<MemoryRouter><RiderDashboard /></MemoryRouter>);

describe("RiderDashboard", () => {
    it("shows the rider profile and their assigned delivery", async () => {
        renderDash();
        expect(await screen.findByText("Rakib")).toBeInTheDocument();
        expect(await screen.findByText("FD1")).toBeInTheDocument();
    });

    it("shows earnings totals", async () => {
        renderDash();
        await waitFor(() => expect(screen.getAllByText("৳250.00").length).toBeGreaterThan(0));
    });

    it("does not heartbeat while the rider is offline", async () => {
        renderDash();
        await screen.findByText("Rakib");
        expect(mockCallApi).not.toHaveBeenCalledWith(
            expect.objectContaining({ url: "food/rider/heartbeat/" }));
    });
});
