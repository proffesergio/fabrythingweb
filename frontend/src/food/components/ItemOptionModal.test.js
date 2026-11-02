import { render, screen, fireEvent } from '@testing-library/react';
import ItemOptionModal from './ItemOptionModal';

const item = {
  id: 10, display_name: 'Biriyani', price: '120.00', effective_price: '120.00',
  option_groups: [{
    id: 1, name: 'Size', min_select: 1, max_select: 1, is_required: true,
    options: [
      { id: 5, name: 'Large', price_delta: '50.00' },
      { id: 6, name: 'Regular', price_delta: '0.00' },
    ],
  }],
};

test('requires a required group before adding and emits a line', () => {
  const onAdd = jest.fn();
  render(
    <ItemOptionModal
      open item={item}
      restaurant={{ id: 1, slug: 'r1', display_name: 'R1' }}
      onClose={() => {}} onAdd={onAdd}
    />
  );
  fireEvent.click(screen.getByText(/^Large/));
  fireEvent.click(screen.getByRole('button', { name: /add to cart/i }));
  expect(onAdd).toHaveBeenCalledTimes(1);
  const line = onAdd.mock.calls[0][0];
  expect(line.itemId).toBe(10);
  expect(line.selectedOptions).toHaveLength(1);
  expect(line.selectedOptions[0].optionId).toBe(5);
});
