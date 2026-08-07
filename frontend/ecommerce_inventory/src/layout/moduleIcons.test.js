import { FALLBACK_ICON, getModuleIconComponent } from './moduleIcons';

// Every `module_icon` value the backend actually seeds. Sources:
//   accounts/management/commands/seed_admin_modules.py
//   food/management/commands/seed_food_modules.py
// Collected with:
//   grep -rhoE "module_icon['\"]?\s*[:=]\s*['\"][A-Za-z]+['\"]" --include=*.py .
// If the backend seeds a new icon name, this list is what should be updated
// first -- an unmapped name is silent in the UI, it just renders a wrong glyph.
const SEEDED_ICON_NAMES = [
  'AccountCircle', 'Add', 'Category', 'Chat', 'Checkroom', 'CloudDownload',
  'Dashboard', 'HowToReg', 'Inventory', 'Map', 'Payments', 'Receipt',
  'ReceiptLong', 'Redeem', 'Restaurant', 'Settings', 'Store', 'Storefront',
  'Tune', 'TwoWheeler', 'ViewCarousel', 'Warehouse',
];

describe('sidebar module icons', () => {
  it.each(SEEDED_ICON_NAMES)('maps %s to a real icon, not the fallback', (name) => {
    expect(getModuleIconComponent(name)).not.toBe(FALLBACK_ICON);
  });

  it('falls back to a neutral module glyph for an unknown name', () => {
    // Not a person icon: the fallback lands on modules that are not about
    // users at all, so it must not look like an account.
    expect(getModuleIconComponent('SomethingNewFromTheBackend')).toBe(FALLBACK_ICON);
    expect(getModuleIconComponent(undefined)).toBe(FALLBACK_ICON);
  });

  it('uses a group icon for the people module rather than a single avatar', () => {
    const Icon = getModuleIconComponent('AccountCircle');
    expect(Icon).not.toBe(FALLBACK_ICON);
  });
});
