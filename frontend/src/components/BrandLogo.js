import { Box } from "@mui/material";

// The single place that knows which logo file belongs to which brand, shape and
// canvas. Every header, footer and auth screen goes through it, so "Fabrything
// for the store, Fabrything Food for the food module" is enforced structurally
// rather than by remembering to pick the right filename each time.
//
// `mode` is the canvas the logo sits ON, not the app's theme name — a footer with
// a dark background needs mode="dark" even while the site is in light mode.
// Getting this wrong renders the logo invisible: the artwork is monochrome-on-
// transparent, so a light logo on a light background is simply not there.
const ASSETS = {
    fabrything: {
        horizontal: { light: "/fabrything-horizontal-light.png", dark: "/fabrything-horizontal-dark.png" },
        stacked: { light: "/fabrything-stacked-light.png", dark: "/fabrything-stacked-dark.png" },
    },
    food: {
        // The food files are named "vertical" rather than "stacked"; the mismatch
        // is absorbed here so callers use one vocabulary.
        horizontal: { light: "/food-horizontal-light.png", dark: "/food-horizontal-dark.png" },
        stacked: { light: "/food-vertical-light.png", dark: "/food-vertical-dark.png" },
    },
};

const ALT = { fabrything: "Fabrything", food: "Fabrything Food" };

export default function BrandLogo({
    brand = "fabrything",
    variant = "horizontal",
    mode = "light",
    height = 32,
    sx,
    ...rest
}) {
    const src = ASSETS[brand]?.[variant]?.[mode];
    if (!src) return null;

    return (
        <Box
            component="img"
            src={src}
            alt={ALT[brand]}
            sx={{
                height,
                width: "auto",
                display: "block",
                // Logos are decorative links in headers; stop the browser's drag
                // ghost and text-selection halo from appearing on click.
                userSelect: "none",
                WebkitUserDrag: "none",
                ...sx,
            }}
            {...rest}
        />
    );
}
