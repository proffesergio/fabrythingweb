import { firstNavigableChild, isExpandable, resolveMenuTarget, toAdminPath } from './sidebarNav';

// Shapes copied from the real seeded menu
// (accounts/management/commands/seed_admin_modules.py). The six containers
// below are exactly the ones reported as dead: clicking them changed nothing
// because they carry no module_url of their own.
const products = {
  id: 2, module_name: 'Products', module_url: null,
  submenus: [
    { id: 21, module_name: 'All Products', module_url: '/manage/product' },
    { id: 22, module_name: 'Add Product', module_url: '/form/product' },
  ],
};

const customers = { id: 9, module_name: 'Customers', module_url: '/manage/customers', submenus: [] };

describe('container modules', () => {
  it('sends a URL-less container to its first navigable child', () => {
    expect(resolveMenuTarget(products).module_url).toBe('/manage/product');
  });

  it.each([
    ['Orders', '/manage/salesorder'],
    ['Inventory', '/manage/warehouse'],
    ['Settings', '/manage/users'],
    ['Food', '/manage/food/dashboard'],
    ['Custom Printing', '/manage/print/requests'],
  ])('%s opens %s', (name, firstChildUrl) => {
    const item = {
      module_name: name, module_url: null,
      submenus: [{ module_name: 'first', module_url: firstChildUrl }],
    };
    expect(resolveMenuTarget(item).module_url).toBe(firstChildUrl);
  });

  it('skips a child that has no URL of its own', () => {
    const item = {
      module_url: null,
      submenus: [
        { module_name: 'divider', module_url: '' },
        { module_name: 'real', module_url: '/manage/thing' },
      ],
    };
    expect(resolveMenuTarget(item).module_url).toBe('/manage/thing');
  });

  it('descends more than one level to find a target', () => {
    const item = {
      module_url: null,
      submenus: [{ module_url: null, submenus: [{ module_url: '/deep' }] }],
    };
    expect(firstNavigableChild(item).module_url).toBe('/deep');
  });

  it('returns null when a container has nowhere to go', () => {
    expect(resolveMenuTarget({ module_url: null, submenus: [{ module_url: null }] })).toBeNull();
    expect(resolveMenuTarget({ module_url: null, submenus: [] })).toBeNull();
    expect(resolveMenuTarget(null)).toBeNull();
  });
});

describe('leaf modules', () => {
  it('navigates to its own URL', () => {
    expect(resolveMenuTarget(customers).module_url).toBe('/manage/customers');
  });

  it('prefers its own URL over a child, when it has both', () => {
    const item = { module_url: '/manage/own', submenus: [{ module_url: '/manage/child' }] };
    expect(resolveMenuTarget(item).module_url).toBe('/manage/own');
  });
});

describe('path prefixing', () => {
  it('adds the /admin mount point', () => {
    expect(toAdminPath('/manage/product')).toBe('/admin/manage/product');
  });

  it('is idempotent for an already-prefixed URL', () => {
    expect(toAdminPath('/admin/manage/product')).toBe('/admin/manage/product');
  });

  it('returns null for no URL', () => {
    expect(toAdminPath('')).toBeNull();
    expect(toAdminPath(null)).toBeNull();
  });
});

describe('expandability', () => {
  it('is true only when there are submenus to show', () => {
    expect(isExpandable(products)).toBe(true);
    expect(isExpandable(customers)).toBe(false);
    expect(isExpandable(null)).toBe(false);
  });
});
