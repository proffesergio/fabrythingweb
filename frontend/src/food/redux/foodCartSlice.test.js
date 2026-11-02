import reducer, {
  addFoodItem, removeFoodItem, updateFoodQty, clearFoodCart,
  selectFoodSubtotal, selectFoodCount,
} from './foodCartSlice';

const line = (over = {}) => ({
  lineId: 'l1', restaurantId: 1, restaurantSlug: 'r1', restaurantName: 'R1',
  itemId: 10, name: 'Biriyani', image: '', unitPrice: 120, quantity: 1,
  selectedOptions: [{ optionId: 5, name: 'Large', priceDelta: 50 }], ...over,
});

test('adds an item and computes subtotal (unit+options)*qty', () => {
  const s = reducer(undefined, addFoodItem(line()));
  expect(s.items).toHaveLength(1);
  expect(selectFoodSubtotal({ foodCart: s })).toBe(170);
  expect(selectFoodCount({ foodCart: s })).toBe(1);
});

test('rejects an item from a different restaurant without force', () => {
  let s = reducer(undefined, addFoodItem(line()));
  s = reducer(s, addFoodItem(line({ lineId: 'l2', restaurantId: 2, restaurantSlug: 'r2' })));
  expect(s.items).toHaveLength(1);
  expect(s.restaurantId).toBe(1);
});

test('force replaces the cart with the new restaurant', () => {
  let s = reducer(undefined, addFoodItem(line()));
  s = reducer(s, addFoodItem(line({ lineId: 'l2', restaurantId: 2, restaurantSlug: 'r2', force: true })));
  expect(s.items).toHaveLength(1);
  expect(s.restaurantId).toBe(2);
});

test('updateFoodQty clamps to a minimum of 1', () => {
  let s = reducer(undefined, addFoodItem(line()));
  s = reducer(s, updateFoodQty({ lineId: 'l1', quantity: 0 }));
  expect(s.items[0].quantity).toBe(1);
});

test('removeFoodItem clears restaurant when last line goes', () => {
  let s = reducer(undefined, addFoodItem(line()));
  s = reducer(s, removeFoodItem({ lineId: 'l1' }));
  expect(s.items).toHaveLength(0);
  expect(s.restaurantId).toBeNull();
});

test('clearFoodCart empties everything', () => {
  let s = reducer(undefined, addFoodItem(line()));
  s = reducer(s, clearFoodCart());
  expect(s.items).toHaveLength(0);
  expect(s.restaurantId).toBeNull();
});
