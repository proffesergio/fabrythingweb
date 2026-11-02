import { render, screen } from "@testing-library/react";
import DeliveryCard from "./DeliveryCard";

// Leaflet needs a real DOM size; the map is exercised separately.
jest.mock("./DeliveryMap", () => () => <div data-testid="delivery-map" />);

const order = {
    id: 1,
    order_code: "FD12345",
    status: "OUT_FOR_DELIVERY",
    restaurant_name: "Kacchi Ghor",
    restaurant_phone: "01711000000",
    restaurant_address: "Bancharampur Bazar",
    guest_name: "Karim",
    guest_phone: "01811000000",
    delivery_address: "Ujanchar",
    notes: "Extra salad please",
    total: "340.00",
    payment_method: "COD",
    cash_to_collect: "340.00",
    pickup_lat: "23.710400",
    pickup_lng: "90.928000",
    delivery_lat: "23.720000",
    delivery_lng: "90.930000",
    items: [
        {
            id: 1, item_name: "Kacchi", quantity: 2, line_total: "600.00",
            selected_options: [{ name: "Extra meat", price_delta: "40.00" }],
        },
    ],
};

describe("DeliveryCard", () => {
    it("lists what to pick up including options and the order note", () => {
        render(<DeliveryCard order={order} riderPosition={null} onAdvance={jest.fn()} />);
        // "2 × Kacchi" — distinct from the restaurant name "Kacchi Ghor".
        expect(screen.getByText("2 × Kacchi")).toBeInTheDocument();
        expect(screen.getByText(/Extra meat/)).toBeInTheDocument();
        expect(screen.getByText(/Extra salad please/)).toBeInTheDocument();
    });

    it("offers one-tap calls to both the customer and the restaurant", () => {
        render(<DeliveryCard order={order} riderPosition={null} onAdvance={jest.fn()} />);
        expect(screen.getByRole("link", { name: /call customer/i }))
            .toHaveAttribute("href", "tel:01811000000");
        expect(screen.getByRole("link", { name: /call restaurant/i }))
            .toHaveAttribute("href", "tel:01711000000");
    });

    it("shows the cash to collect for a COD order", () => {
        render(<DeliveryCard order={order} riderPosition={null} onAdvance={jest.fn()} />);
        expect(screen.getByText(/৳340.00 cash/)).toBeInTheDocument();
    });

    it("shows distance to the drop-off once the rider position is known", () => {
        render(<DeliveryCard order={order} riderPosition={{ lat: 23.71, lng: 90.928 }} onAdvance={jest.fn()} />);
        expect(screen.getByText(/km to drop-off/i)).toBeInTheDocument();
    });

    it("warns when the rider is moving away from the target", () => {
        const { rerender } = render(
            <DeliveryCard order={order} riderPosition={{ lat: 23.7190, lng: 90.9300 }} onAdvance={jest.fn()} />);
        // three consecutive positions, each further from the drop-off
        rerender(<DeliveryCard order={order} riderPosition={{ lat: 23.7150, lng: 90.9300 }} onAdvance={jest.fn()} />);
        rerender(<DeliveryCard order={order} riderPosition={{ lat: 23.7100, lng: 90.9300 }} onAdvance={jest.fn()} />);
        rerender(<DeliveryCard order={order} riderPosition={{ lat: 23.7050, lng: 90.9300 }} onAdvance={jest.fn()} />);
        expect(screen.getByText(/moving away/i)).toBeInTheDocument();
    });

    it("links out to Google Maps for turn-by-turn", () => {
        render(<DeliveryCard order={order} riderPosition={null} onAdvance={jest.fn()} />);
        expect(screen.getByRole("link", { name: /open in google maps/i }))
            .toHaveAttribute("href", expect.stringContaining("google.com/maps"));
    });
});
