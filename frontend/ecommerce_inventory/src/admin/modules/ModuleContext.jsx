import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useSelector } from 'react-redux';
import { useLocation } from 'react-router-dom';
import { MODULES, moduleForPath, visibleModules } from './registry';

const ModuleContext = createContext({
  active: 'shop', select: () => {}, visible: ['shop', 'food', 'news'],
  meta: MODULES.shop, fromPath: null,
});

// Owns the active business (Shop / Food / News) for the admin shell.
// Route wins when it names a module; otherwise the last manual pick (kept in
// localStorage) wins; otherwise the first visible module. Menus come from
// redux (backend getMenus), so permission filtering keeps working untouched.
export function ModuleProvider({ children }) {
  const location = useLocation();
  const items = useSelector((state) => state.sidebardata?.items) || [];
  const [manual, setManual] = useState(() => {
    try { return localStorage.getItem('admin_module'); } catch { return null; }
  });
  const visible = useMemo(() => visibleModules(items), [items]);
  const fromPath = moduleForPath(location.pathname);
  const active = (fromPath && visible.includes(fromPath)) ? fromPath
    : (manual && visible.includes(manual)) ? manual
    : (visible[0] || 'shop');
  useEffect(() => {
    try { localStorage.setItem('admin_module', active); } catch { /* private mode */ }
  }, [active]);
  const select = useCallback((m) => {
    setManual(m);
    try { localStorage.setItem('admin_module', m); } catch { /* private mode */ }
  }, []);
  const value = useMemo(() => ({
    active, select, visible, fromPath, meta: MODULES[active] || MODULES.shop,
  }), [active, select, visible, fromPath]);
  return <ModuleContext.Provider value={value}>{children}</ModuleContext.Provider>;
}

export function useModule() {
  return useContext(ModuleContext);
}
