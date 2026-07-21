import roleHome from "./roleHome";

describe("roleHome", () => {
    it("sends riders to the rider dashboard", () => {
        expect(roleHome("Rider")).toBe("/rider");
    });
    it("sends restaurant owners to the vendor panel", () => {
        expect(roleHome("Restaurant")).toBe("/vendor/orders");
    });
    it("sends admins to the admin home", () => {
        expect(roleHome("Admin")).toBe("/admin/home");
        expect(roleHome("Super Admin")).toBe("/admin/home");
    });
    it("falls back to admin home for unknown or missing roles", () => {
        expect(roleHome(undefined)).toBe("/admin/home");
        expect(roleHome("Wizard")).toBe("/admin/home");
    });
});
