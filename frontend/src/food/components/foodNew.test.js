import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DishDetailModal from './DishDetailModal';
import FoodFooter from './FoodFooter';

const ITEM = {
  id: 7, display_name: 'Set Menu-4', description: 'Rice, chicken, salad, drinks.',
  image: '', effective_price: '250.00', price: '250.00', discount_price: null,
  tags: ['popular'], is_veg: false, is_featured: true, spice_level: 'Medium',
  prep_minutes: 20, available_from: '10:00', available_to: '22:00',
  available_days: [], available_now: true, option_groups: [{ id: 1, name: 'Drinks', options: [] }],
};

describe('DishDetailModal', () => {
  test('shows full dish story and customize entry when options exist', () => {
    const onCustomize = jest.fn();
    render(
      <DishDetailModal open item={ITEM} restaurantClosed={false} lang="en"
        onClose={() => {}} onCustomize={onCustomize} onAdd={() => {}} />
    );
    expect(screen.getByText('Set Menu-4')).toBeInTheDocument();
    expect(screen.getByText(/Rice, chicken, salad/)).toBeInTheDocument();
    expect(screen.getByText(/Medium/)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Customize/));
    expect(onCustomize).toHaveBeenCalledWith(ITEM);
  });

  test('closed restaurant disables ordering but still shows details', () => {
    render(
      <DishDetailModal open item={{ ...ITEM, option_groups: [] }} restaurantClosed lang="en"
        onClose={() => {}} onCustomize={() => {}} onAdd={() => {}} />
    );
    expect(screen.getByText('Set Menu-4')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /closed/i })).toBeDisabled();
  });

  test('renders nothing without an item', () => {
    const { container } = render(
      <DishDetailModal open={false} item={null} onClose={() => {}} onCustomize={() => {}} onAdd={() => {}} />
    );
    expect(container.textContent).toBe('');
  });
});

describe('FoodFooter', () => {
  test('links home, orders and the partner page', () => {
    render(<MemoryRouter><FoodFooter /></MemoryRouter>);
    const partnerLinks = screen.getAllByText(/Partner/);
    expect(partnerLinks.length).toBeGreaterThan(0);
    expect(partnerLinks[0].closest('a')).toHaveAttribute('href', '/food/partner');
    expect(screen.getByText('My orders').closest('a')).toHaveAttribute('href', '/food/orders');
  });
});
