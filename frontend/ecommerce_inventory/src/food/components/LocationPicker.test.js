import { render, screen, fireEvent } from '@testing-library/react';

jest.mock('react-toastify', () => ({ toast: { success: jest.fn(), error: jest.fn(), info: jest.fn() } }));
// Leaflet touches DOM APIs jsdom doesn't implement; the real MapPicker is covered
// by its own try/catch, so stub it here to keep this test about the village cascade.
jest.mock('./MapPicker', () => () => <div data-testid="map" />);

// jest.mock factories may only reference `mock`-prefixed vars.
const mockSetZoneId = jest.fn();
const mockSetVillageId = jest.fn();
jest.mock('../context/FoodLocationContext', () => ({
  useFoodLocation: () => ({
    zones: [
      { id: 1, name: 'Bancharampur', name_bn: 'বাঞ্ছারামপুর',
        villages: [{ id: 11, name: 'Alipur', name_bn: 'আলীপুর' }] },
      { id: 2, name: 'Dariadaulat', name_bn: 'দরিয়াদৌলত', villages: [] },
    ],
    zoneId: '', villageId: '', lang: 'en', coords: null,
    setZoneId: mockSetZoneId, setVillageId: mockSetVillageId,
    setCoords: jest.fn(), detectLocation: jest.fn(),
    pickerOpen: true, closePicker: jest.fn(),
  }),
}));

import LocationPicker from './LocationPicker';

// Union is an Autocomplete (typeable), not a Select — open it with the arrow
// button and pick from the listbox.
// Returns the input, because once the listbox is open the shrunk label makes
// getByLabelText('Union') ambiguous.
const openUnion = () => {
  const input = screen.getByLabelText('Union');
  fireEvent.mouseDown(input);
  fireEvent.keyDown(input, { key: 'ArrowDown' });
  return input;
};

test('confirming a picked union commits the zone', () => {
  render(<LocationPicker />);
  openUnion();
  fireEvent.click(screen.getByRole('option', { name: 'Bancharampur' }));
  fireEvent.click(screen.getByRole('button', { name: /confirm area/i }));
  expect(mockSetZoneId).toHaveBeenCalledWith('1');
});

test('union and village are typeable comboboxes, not plain selects', () => {
  render(<LocationPicker />);
  // 13 unions and 121 villages are too many to scroll; both fields must accept
  // typed search. A MUI Select renders role="combobox" on a div with no text
  // input — an Autocomplete renders a real <input>, which is what we assert.
  const union = screen.getByLabelText('Union');
  expect(union.tagName).toBe('INPUT');
  expect(union).toHaveAttribute('aria-autocomplete', 'list');

  openUnion();
  expect(screen.getAllByRole('option').map((o) => o.textContent))
    .toEqual(['Bancharampur', 'Dariadaulat']);
});

test('confirm is disabled until a union is picked', () => {
  render(<LocationPicker />);
  expect(screen.getByRole('button', { name: /confirm area/i })).toBeDisabled();
  openUnion();
  fireEvent.click(screen.getByRole('option', { name: 'Bancharampur' }));
  expect(screen.getByRole('button', { name: /confirm area/i })).not.toBeDisabled();
});
