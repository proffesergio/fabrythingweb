import { createSlice } from "@reduxjs/toolkit";

const loadCartFromStorage = () => {
    try {
        const saved = localStorage.getItem('fabrything_cart');
        return saved ? JSON.parse(saved) : [];
    } catch {
        return [];
    }
};

const saveCartToStorage = (items) => {
    localStorage.setItem('fabrything_cart', JSON.stringify(items));
};

const cartSlice = createSlice({
    name: 'cart',
    initialState: {
        items: loadCartFromStorage(),
    },
    reducers: {
        addToCart: (state, action) => {
            const { product, size, quantity } = action.payload;
            const existing = state.items.find(
                item => item.product.id === product.id && item.size === size
            );
            if (existing) {
                existing.quantity += quantity;
            } else {
                state.items.push({ product, size, quantity });
            }
            saveCartToStorage(state.items);
        },
        removeFromCart: (state, action) => {
            const { productId, size } = action.payload;
            state.items = state.items.filter(
                item => !(item.product.id === productId && item.size === size)
            );
            saveCartToStorage(state.items);
        },
        updateQuantity: (state, action) => {
            const { productId, size, quantity } = action.payload;
            const item = state.items.find(
                item => item.product.id === productId && item.size === size
            );
            if (item) {
                item.quantity = Math.max(1, quantity);
            }
            saveCartToStorage(state.items);
        },
        clearCart: (state) => {
            state.items = [];
            saveCartToStorage(state.items);
        },
    },
});

export const { addToCart, removeFromCart, updateQuantity, clearCart } = cartSlice.actions;

export const selectCartItems = (state) => state.cart.items;
export const selectCartItemCount = (state) =>
    state.cart.items.reduce((sum, item) => sum + item.quantity, 0);
export const selectCartTotal = (state) =>
    state.cart.items.reduce((sum, item) => {
        const price = item.product.discount_price || item.product.initial_selling_price;
        return sum + price * item.quantity;
    }, 0);

export default cartSlice.reducer;
