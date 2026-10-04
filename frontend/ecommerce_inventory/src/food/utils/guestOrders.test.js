import { readGuestOrders, recordGuestOrder, removeGuestOrder } from './guestOrders';

const KEY = 'food_guest_orders';

beforeEach(() => localStorage.clear());

describe('guest order registry', () => {
  test('records and reads back entries newest-first', () => {
    recordGuestOrder({ code: 'A1', phone: '01', restaurant: 'R1', total: 200 });
    recordGuestOrder({ code: 'B2', phone: '02', restaurant: 'R2', total: 300 });
    const list = readGuestOrders();
    expect(list.map((o) => o.code)).toEqual(['B2', 'A1']);
    expect(list[0].phone).toBe('02');
  });

  test('re-recording the same code moves it to front without duplicating', () => {
    recordGuestOrder({ code: 'A1', phone: '01' });
    recordGuestOrder({ code: 'B2', phone: '02' });
    recordGuestOrder({ code: 'A1', phone: '01' });
    expect(readGuestOrders().map((o) => o.code)).toEqual(['A1', 'B2']);
  });

  test('removes entries and caps the list', () => {
    recordGuestOrder({ code: 'A1', phone: '01' });
    removeGuestOrder('A1');
    expect(readGuestOrders()).toEqual([]);
    for (let i = 0; i < 25; i++) recordGuestOrder({ code: `C${i}`, phone: '0' });
    expect(readGuestOrders()).toHaveLength(20);
  });

  test('drops entries older than 30 days on read', () => {
    const old = [{ code: 'OLD', phone: '0', at: Date.now() - 31 * 24 * 3600 * 1000 }];
    localStorage.setItem(KEY, JSON.stringify(old));
    expect(readGuestOrders()).toEqual([]);
  });

  test('corrupt storage reads as empty, never throws', () => {
    localStorage.setItem(KEY, 'not-json{{{');
    expect(readGuestOrders()).toEqual([]);
  });
});
