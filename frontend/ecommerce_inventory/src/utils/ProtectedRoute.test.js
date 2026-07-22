import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";

// Unauthenticated by default: Helper.isAuthenticated reads localStorage.
beforeEach(() => localStorage.clear());

const renderAt = (path) =>
    render(
        <MemoryRouter initialEntries={[path]}>
            <Routes>
                <Route path={path} element={<ProtectedRoute element={<div>PROTECTED</div>} />} />
                <Route path="/rider/login" element={<div>RIDER LOGIN</div>} />
                <Route path="/admin/auth" element={<div>ADMIN LOGIN</div>} />
                <Route path="/auth/login" element={<div>CUSTOMER LOGIN</div>} />
            </Routes>
        </MemoryRouter>
    );

describe("ProtectedRoute login target", () => {
    it("sends riders to the rider login, not the customer one", () => {
        // The customer page defaults its post-login redirect to "/", which is how
        // a rider ended up on the storefront homepage instead of /rider.
        renderAt("/rider");
        expect(screen.getByText("RIDER LOGIN")).toBeInTheDocument();
    });

    it("sends admins to the admin login", () => {
        renderAt("/admin/home");
        expect(screen.getByText("ADMIN LOGIN")).toBeInTheDocument();
    });

    it("sends everyone else to the customer login", () => {
        renderAt("/checkout");
        expect(screen.getByText("CUSTOMER LOGIN")).toBeInTheDocument();
    });
});
