import React from 'react';
import { Box, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { getModuleIcon } from '../../layout/moduleIcons';
import { MODULES } from './registry';
import { useModule } from './ModuleContext';

// Top business switcher: Shop / Food / News branded tabs. Single-module
// users see nothing (no dead single tab); everyone else gets one-tap context.
export default function ModuleSwitcher({ compact = false }) {
  const { active, select, visible } = useModule();
  const navigate = useNavigate();
  if (visible.length <= 1) return null;
  const go = (id) => {
    if (id === active) return;
    select(id);
    navigate(MODULES[id].home);
  };
  return (
    <Box sx={{
      display: 'flex', gap: 0.5, overflowX: 'auto', flexShrink: 0,
      '&::-webkit-scrollbar': { display: 'none' }, scrollbarWidth: 'none',
    }}>
      {visible.map((id) => {
        const m = MODULES[id];
        const on = id === active;
        return (
          <Box
            key={id}
            onClick={() => go(id)}
            sx={{
              display: 'flex', alignItems: 'center', gap: 1,
              px: compact ? 1.25 : 2, py: 1, cursor: 'pointer', whiteSpace: 'nowrap',
              borderBottom: on ? `3px solid ${m.color}` : '3px solid transparent',
              color: on ? 'text.primary' : 'text.secondary',
              fontWeight: on ? 800 : 600, fontSize: '0.9rem',
              '&:hover': { color: 'text.primary' },
            }}
          >
            <Box sx={{ display: 'flex', color: on ? m.color : 'inherit' }}>
              {getModuleIcon(m.icon)}
            </Box>
            <Typography variant="body2" fontWeight={on ? 800 : 600}>
              {compact ? m.short : m.label}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}
