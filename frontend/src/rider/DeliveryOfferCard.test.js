import { render, screen, fireEvent, act } from '@testing-library/react';
import DeliveryOfferCard from './DeliveryOfferCard';

const OFFER = {
  offer_id: 1, seconds_left: 60, order_code: 'ABC123', restaurant_name: 'Dhaka Fast Food',
  delivery_address: 'Field 3, Bancharampur', distance_km: '4.20', payment_method: 'COD',
  total: '380.00', rider_pay: '57.00',
};

beforeEach(() => jest.useFakeTimers());
afterEach(() => { jest.runOnlyPendingTimers(); jest.useRealTimers(); });

test('shows what the rider is deciding: pay, distance and cash to carry', () => {
  render(<DeliveryOfferCard offer={OFFER} onAccept={jest.fn()} onDecline={jest.fn()} />);
  expect(screen.getByText('Dhaka Fast Food')).toBeInTheDocument();
  expect(screen.getByText(/৳57.00/)).toBeInTheDocument();
  expect(screen.getByText('4.20 km')).toBeInTheDocument();
  expect(screen.getByText('Collect ৳380.00 cash')).toBeInTheDocument();
});

test('a prepaid offer does not tell the rider to collect cash', () => {
  render(<DeliveryOfferCard offer={{ ...OFFER, payment_method: 'BKASH' }}
    onAccept={jest.fn()} onDecline={jest.fn()} />);
  expect(screen.queryByText(/Collect/)).not.toBeInTheDocument();
});

test('the countdown ticks down', () => {
  render(<DeliveryOfferCard offer={OFFER} onAccept={jest.fn()} onDecline={jest.fn()} />);
  expect(screen.getByText('60s')).toBeInTheDocument();
  act(() => jest.advanceTimersByTime(3000));
  expect(screen.getByText('57s')).toBeInTheDocument();
});

test('accept and decline call back', () => {
  const onAccept = jest.fn(); const onDecline = jest.fn();
  render(<DeliveryOfferCard offer={OFFER} onAccept={onAccept} onDecline={onDecline} />);
  fireEvent.click(screen.getByRole('button', { name: /Accept/ }));
  expect(onAccept).toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: /Decline/ }));
  expect(onDecline).toHaveBeenCalled();
});

test('accept is disabled once the offer has run out', () => {
  render(<DeliveryOfferCard offer={{ ...OFFER, seconds_left: 1 }}
    onAccept={jest.fn()} onDecline={jest.fn()} />);
  act(() => jest.advanceTimersByTime(2000));
  expect(screen.getByRole('button', { name: /Expired/ })).toBeDisabled();
});
