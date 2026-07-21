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
    zones: [{ id: 1, name: 'Bancharampur', name_bn: 'বাঞ্ছারামপুর',
              villages: [{ id: 11, name: 'Alipur', name_bn: 'আলীপুর' }] }],
    zoneId: '', villageId: '', lang: 'en', coords: null,
    setZoneId: mockSetZoneId, setVillageId: mockSetVillageId,
    setCoords: jest.fn(), detectLocation: jest.fn(),
    pickerOpen: true, closePicker: jest.fn(),
  }),
}));

import LocationPicker from './LocationPicker';

test('confirming a picked union commits the zone', () => {
  render(<LocationPicker />);
  fireEvent.mouseDown(screen.getByLabelText('Union'));
  fireEvent.click(screen.getByRole('option', { name: 'Bancharampur' }));
  fireEvent.click(screen.getByRole('button', { name: /confirm area/i }));
  expect(mockSetZoneId).toHaveBeenCalledWith('1');
});
