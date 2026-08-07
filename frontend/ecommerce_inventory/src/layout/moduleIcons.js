import {
  AccountCircle,
  AddCircleOutlineOutlined,
  Business as BusinessIcon,
  Category,
  Checkroom as CheckroomIcon,
  Chat as ChatIcon,
  CloudDownloadOutlined,
  DashboardOutlined,
  GroupOutlined,
  HowToReg,
  InventoryOutlined,
  Map as MapIcon,
  Payments,
  ReceiptLong,
  ReceiptOutlined,
  Restaurant as RestaurantIcon,
  Settings as SettingsIcon,
  ShoppingBasketRounded,
  ShoppingCartOutlined,
  StorefrontOutlined,
  Tune as TuneIcon,
  TwoWheeler,
  ViewCarousel as ViewCarouselIcon,
  WarehouseOutlined,
  WidgetsOutlined,
} from '@mui/icons-material';

// Sidebar modules are DB-driven: `ModuleUrls.module_icon` holds a NAME, and
// this table turns it into a component. Extracted from layout.js so it can be
// tested against the exact names the backend seeds -- an unmapped name used to
// fall through to a person icon, which is how Chat, Banners, Custom Printing
// and Print Setup all ended up looking like a user account in the sidebar.
//
// The full set of names in use lives in
// backend/EcommerceInventory/accounts/management/commands/seed_admin_modules.py
// and food/management/commands/seed_food_modules.py. moduleIcons.test.js pins
// that every one of them resolves to something other than the fallback.
const ICONS = {
  Add: AddCircleOutlineOutlined,
  Dashboard: DashboardOutlined,
  Store: ShoppingCartOutlined,
  Retail: StorefrontOutlined,
  Storefront: StorefrontOutlined,
  Restaurant: RestaurantIcon,
  Map: MapIcon,
  ReceiptLong: ReceiptLong,
  TwoWheeler: TwoWheeler,
  HowToReg: HowToReg,
  Payments: Payments,
  // The people-management module; the only one a person icon actually suits.
  AccountCircle: GroupOutlined,
  Settings: SettingsIcon,
  Inventory: InventoryOutlined,
  CloudDownload: CloudDownloadOutlined,
  Category: Category,
  Redeem: ShoppingBasketRounded,
  Receipt: ReceiptOutlined,
  Warehouse: WarehouseOutlined,
  ecommerce: BusinessIcon,
  // Previously unmapped -- these four are seeded by the backend and were all
  // rendering the generic fallback.
  Chat: ChatIcon,
  ViewCarousel: ViewCarouselIcon,
  Checkroom: CheckroomIcon,
  Tune: TuneIcon,
};

// A neutral "module" glyph. The old fallback was AccountCircle, which reads as
// "user account" and actively misleads on a module that is nothing of the sort.
export const FALLBACK_ICON = WidgetsOutlined;

export function getModuleIconComponent(name) {
  return ICONS[name] || FALLBACK_ICON;
}

/** The icon element for a `module_icon` name. */
export function getModuleIcon(name) {
  const Icon = getModuleIconComponent(name);
  return <Icon />;
}

export const MODULE_ICON_NAMES = Object.keys(ICONS);
