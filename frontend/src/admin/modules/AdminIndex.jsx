import React from 'react';
import { Navigate } from 'react-router-dom';
import { MODULES } from './registry';
import { useModule } from './ModuleContext';

// /admin index → last-used module home (persisted by ModuleProvider).
// The legacy generic dashboard stays reachable via the Shared "Dashboard"
// menu entry (/admin/home) for anyone who still wants it.
export default function AdminIndex() {
  const { active } = useModule();
  const home = (MODULES[active] || MODULES.shop).home;
  return <Navigate to={home} replace />;
}
