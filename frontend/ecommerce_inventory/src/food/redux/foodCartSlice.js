import { createSlice } from '@reduxjs/toolkit';

const STORAGE_KEY = 'food_cart_v1';

const empty = { restaurantId: null, restaurantSlug: null, restaurantName: null, items: [], tip: 0 };

const load = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : { ...empty };
  } catch {
    return { ...empty };
  }
};

const persist = (state) => {
  const { restaurantId, restaurantSlug, restaurantName, items, tip } = state;
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ restaurantId, restaurantSlug, restaurantName, items, tip }));
};

const lineTotal = (i) =>
  (Number(i.unitPrice) + (i.selectedOptions || []).reduce((s, o) => s + Number(o.priceDelta || 0), 0)) * i.quantity;

const foodCartSlice = createSlice({
  name: 'foodCart',
  initialState: load(),
  reducers: {
    addFoodItem: (state, { payload }) => {
      const differs = state.restaurantId != null && state.restaurantId !== payload.restaurantId;
      if (differs && !payload.force) return; // guard: component prompts, then re-dispatches with force
      if (differs && payload.force) {
        state.items = []; state.tip = 0;
      }
      state.restaurantId = payload.restaurantId;
      state.restaurantSlug = payload.restaurantSlug;
      state.restaurantName = payload.restaurantName;
      const existing = state.items.find((i) => i.lineId === payload.lineId);
      if (existing) existing.quantity += payload.quantity;
      else state.items.push({
        lineId: payload.lineId, itemId: payload.itemId, name: payload.name, image: payload.image,
        unitPrice: payload.unitPrice, quantity: payload.quantity, selectedOptions: payload.selectedOptions || [],
      });
      persist(state);
    },
    removeFoodItem: (state, { payload }) => {
      state.items = state.items.filter((i) => i.lineId !== payload.lineId);
      if (state.items.length === 0) {
        state.restaurantId = null; state.restaurantSlug = null; state.restaurantName = null; state.tip = 0;
      }
      persist(state);
    },
    updateFoodQty: (state, { payload }) => {
      const i = state.items.find((x) => x.lineId === payload.lineId);
      if (i) i.quantity = Math.max(1, payload.quantity);
      persist(state);
    },
    setTip: (state, { payload }) => { state.tip = Math.max(0, Number(payload) || 0); persist(state); },
    clearFoodCart: (state) => { Object.assign(state, { ...empty }); persist(state); },
  },
});

export const { addFoodItem, removeFoodItem, updateFoodQty, setTip, clearFoodCart } = foodCartSlice.actions;

export const selectFoodCart = (s) => s.foodCart.items;
export const selectFoodRestaurant = (s) => ({ id: s.foodCart.restaurantId, slug: s.foodCart.restaurantSlug, name: s.foodCart.restaurantName });
export const selectFoodCount = (s) => s.foodCart.items.reduce((n, i) => n + i.quantity, 0);
export const selectFoodSubtotal = (s) => s.foodCart.items.reduce((sum, i) => sum + lineTotal(i), 0);
export const selectFoodTip = (s) => s.foodCart.tip;

export default foodCartSlice.reducer;
