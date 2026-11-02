import React from 'react';
import { Navigate } from 'react-router-dom';
import { MODULES } from './registry';

// /admin index → last-used module home (persisted by ModuleProvider).
// The legacy generic dashboard stays reachable via the Shared "Dashboard"
// menu entry (/admin/home) for anyone who still wants it.
export default function AdminIndex() {
  let stored = null;
  try { stored = localStorage.getItem('admin_module'); } catch { /* private mode */ }
  const home = (stored && MODULES[stored] ? MODULES[stored] : MODULES.shop).home;
  return <Navigate to={home} replace />;
}
