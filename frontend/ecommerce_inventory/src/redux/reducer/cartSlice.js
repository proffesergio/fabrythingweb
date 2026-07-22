import { createSlice } from "@reduxjs/toolkit";
import axios from "axios";
import config from "../../utils/config";
import { getToken } from "../../utils/authToken";

const STORAGE_KEY = "fabrything_cart_v2";

const loadCartFromStorage = () => {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved ? JSON.parse(saved) : [];
    } catch {
        return [];
    }
};

const saveCartToStorage = (items) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
};

/**
 * Cart items are keyed by variantId (a concrete size/color SKU) so that the
 * COD checkout can submit {variant_id, quantity} straight to the backend,
 * which locks and decrements that exact variant's stock.
 *
 * Item shape:
 *   { variantId, productId, name, slug, image, sku, size, color, price, stock, quantity }
 */
const cartSlice = createSlice({
    name: "cart",
    initialState: {
        items: loadCartFromStorage(),
    },
    reducers: {
        addToCart: (state, action) => {
            const item = action.payload;
            const existing = state.items.find((i) => i.variantId === item.variantId);
            if (existing) {
                existing.quantity += item.quantity;
                if (item.stock) existing.quantity = Math.min(existing.quantity, item.stock);
            } else {
                state.items.push({ ...item });
            }
            saveCartToStorage(state.items);
        },
        removeFromCart: (state, action) => {
            state.items = state.items.filter((i) => i.variantId !== action.payload.variantId);
            saveCartToStorage(state.items);
        },
        updateQuantity: (state, action) => {
            const { variantId, quantity } = action.payload;
            const item = state.items.find((i) => i.variantId === variantId);
            if (item) {
                item.quantity = Math.max(1, item.stock ? Math.min(quantity, item.stock) : quantity);
            }
            saveCartToStorage(state.items);
        },
        setCart: (state, action) => {
            state.items = action.payload || [];
            saveCartToStorage(state.items);
        },
        clearCart: (state) => {
            state.items = [];
            saveCartToStorage(state.items);
        },
    },
});

export const { addToCart, removeFromCart, updateQuantity, setCart, clearCart } = cartSlice.actions;

// ── Selectors ──
export const selectCartItems = (state) => state.cart.items;
export const selectCartItemCount = (state) =>
    state.cart.items.reduce((sum, item) => sum + item.quantity, 0);
export const selectCartTotal = (state) =>
    state.cart.items.reduce((sum, item) => sum + Number(item.price) * item.quantity, 0);

/**
 * Merge the guest's localStorage cart into the user's server cart right after
 * login/registration, then replace the local cart with the authoritative
 * server result. Failure is non-fatal — the local cart is kept.
 */
export const syncCartOnLogin = () => async (dispatch, getState) => {
    const token = getToken();   // an expired one would 401 the merge
    if (!token) return;
    const localItems = getState().cart.items;
    try {
        const body = {
            items: localItems.map((i) => ({ variant_id: i.variantId, quantity: i.quantity })),
        };
        const res = await axios.post(config.API_URL + "store/cart/merge/", body, {
            headers: { Authorization: `Bearer ${token}` },
        });
        const server = res?.data?.data || [];
        const merged = server.map((s) => ({
            variantId: s.variant_id,
            productId: s.product_id,
            name: s.product_name,
            slug: s.product_slug,
            image: "",
            sku: s.sku,
            size: s.size,
            color: s.color,
            price: Number(s.unit_price),
            stock: s.stock_quantity,
            quantity: s.quantity,
        }));
        dispatch(setCart(merged));
    } catch (e) {
        // Keep the local cart if the merge call fails.
    }
};

export default cartSlice.reducer;
