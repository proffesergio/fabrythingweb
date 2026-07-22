import { render, screen } from "@testing-library/react";
import BrandLogo from "./BrandLogo";

// The brand rule is "Fabrything for the store, Fabrything Food for the food
// module". These pin the mapping, because the failure mode is silent: the
// artwork is monochrome-on-transparent, so picking the wrong `mode` renders an
// invisible logo rather than a broken image, and picking the wrong `brand`
// renders a perfectly fine logo for the wrong product.
describe("BrandLogo", () => {
    it("serves each brand from its own asset family", () => {
        const { rerender } = render(<BrandLogo brand="fabrything" />);
        expect(screen.getByAltText("Fabrything"))
            .toHaveAttribute("src", expect.stringContaining("/fabrything-"));

        rerender(<BrandLogo brand="food" />);
        expect(screen.getByAltText("Fabrything Food"))
            .toHaveAttribute("src", expect.stringContaining("/food-"));
    });

    it("picks artwork by the canvas it sits on, not the app theme name", () => {
        const { rerender } = render(<BrandLogo brand="fabrything" mode="light" />);
        expect(screen.getByAltText("Fabrything"))
            .toHaveAttribute("src", "/fabrything-horizontal-light.png");

        rerender(<BrandLogo brand="fabrything" mode="dark" />);
        expect(screen.getByAltText("Fabrything"))
            .toHaveAttribute("src", "/fabrything-horizontal-dark.png");
    });

    it("maps the stacked variant onto the food files' 'vertical' naming", () => {
        render(<BrandLogo brand="food" variant="stacked" mode="dark" />);
        expect(screen.getByAltText("Fabrything Food"))
            .toHaveAttribute("src", "/food-vertical-dark.png");
    });

    it("renders nothing rather than a broken image for an unknown combination", () => {
        const { container } = render(<BrandLogo brand="nope" />);
        expect(container).toBeEmptyDOMElement();
    });

    it("covers every brand/variant/mode combination with a real file", () => {
        for (const brand of ["fabrything", "food"]) {
            for (const variant of ["horizontal", "stacked"]) {
                for (const mode of ["light", "dark"]) {
                    const { unmount } = render(
                        <BrandLogo brand={brand} variant={variant} mode={mode} />);
                    expect(screen.getByRole("img")).toHaveAttribute(
                        "src", expect.stringMatching(/^\/[\w-]+\.png$/));
                    unmount();
                }
            }
        }
    });
});
