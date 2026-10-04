import { moduleForPath, MODULE_ORDER, visibleModules } from './registry';

describe('moduleForPath', () => {
  test('maps module homes', () => {
    expect(moduleForPath('/admin/shop')).toBe('shop');
    expect(moduleForPath('/admin/food')).toBe('food');
    expect(moduleForPath('/admin/news')).toBe('news');
  });
  test('maps business prefixes', () => {
    expect(moduleForPath('/admin/manage/food/orders')).toBe('food');
    expect(moduleForPath('/admin/manage/nobleseek')).toBe('news');
    expect(moduleForPath('/admin/manage/product')).toBe('shop');
    expect(moduleForPath('/admin/manage/salesorder')).toBe('shop');
  });
  test('shared pages keep the current module', () => {
    expect(moduleForPath('/admin/manage/users')).toBeNull();
    expect(moduleForPath('/admin/manage/analytics')).toBeNull();
    expect(moduleForPath('/admin/manage/chat/inbox')).toBeNull();
    expect(moduleForPath('/admin/home')).toBeNull();
    expect(moduleForPath('/shop')).toBeNull();
  });
});

describe('visibleModules', () => {
  test('legacy untagged menus show every module', () => {
    expect(visibleModules([])).toEqual(MODULE_ORDER);
    expect(visibleModules([{ id: 1, module_name: 'Products' }])).toEqual(MODULE_ORDER);
  });
  test('tagged menus expose only granted modules', () => {
    const items = [
      { id: 1, module_name: 'Products', module: 'shop', submenus: [] },
      { id: 2, module_name: 'Food', module: 'food', submenus: [] },
    ];
    expect(visibleModules(items)).toEqual(['shop', 'food']);
  });
  test('child tags count too', () => {
    const items = [
      {
        id: 1, module_name: 'News', module: 'news',
        submenus: [{ id: 2, module_name: 'Desk', module: 'news' }],
      },
    ];
    expect(visibleModules(items)).toEqual(['news']);
  });
});

describe('splitItems', () => {
  const { splitItems } = require('./registry');
  test('legacy backend shows everything unfiltered', () => {
    const items = [{ id: 1, module_name: 'Products', submenus: [] }];
    expect(splitItems(items, 'food')).toEqual({ mine: items, shared: [] });
  });
  test('splits module vs shared, hides other modules', () => {
    const items = [
      { id: 1, module_name: 'Products', module: 'shop', submenus: [] },
      { id: 2, module_name: 'Food', module: 'food', submenus: [] },
      { id: 3, module_name: 'Settings', module: 'shared', submenus: [] },
      { id: 4, module_name: 'NobleSeek News', module: 'news', submenus: [] },
    ];
    const { mine, shared } = splitItems(items, 'shop');
    expect(mine.map((i) => i.module_name)).toEqual(['Products']);
    expect(shared.map((i) => i.module_name)).toEqual(['Settings']);
  });
});

describe('filterMenuItems', () => {
  const { filterMenuItems } = require('./registry');
  const items = [
    { id: 1, module_name: 'Products', submenus: [{ id: 2, module_name: 'All Products' }] },
    { id: 3, module_name: 'Food', submenus: [{ id: 4, module_name: 'Riders' }] },
  ];
  test('empty query returns everything', () => {
    expect(filterMenuItems(items, '')).toHaveLength(2);
  });
  test('matches parents and keeps matching parents for child hits', () => {
    expect(filterMenuItems(items, 'prod')).toHaveLength(1);
    expect(filterMenuItems(items, 'rider')).toHaveLength(1);
    expect(filterMenuItems(items, 'zzz')).toHaveLength(0);
  });
});
