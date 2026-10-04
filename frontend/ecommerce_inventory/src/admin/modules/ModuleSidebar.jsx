import React, { useMemo, useState } from 'react';
import { Box, Collapse, List, ListItem, ListItemIcon, ListItemText, ListSubheader, TextField } from '@mui/material';
import { ExpandLess, ExpandMore, Dashboard as DashboardIcon } from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { getModuleIcon } from '../../layout/moduleIcons';
import { expandItem, activateItem } from '../../redux/reducer/sidebardata';
import { isExpandable, resolveMenuTarget, toAdminPath } from '../../layout/sidebarNav';
import { filterMenuItems, splitItems } from './registry';
import { useModule } from './ModuleContext';

// Module-filtered drawer body: Overview entry + this business's menus +
// a Shared group. Untagged (legacy) backends render everything unfiltered,
// and children render as granted (the backend already permission-filters).
export default function ModuleSidebar({ onNavigate }) {
  const items = useSelector((state) => state.sidebardata?.items) || [];
  const { active, meta } = useModule();
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [q, setQ] = useState('');

  const { mine, shared } = useMemo(() => splitItems(items, active), [items, active]);
  const shownMine = useMemo(() => filterMenuItems(mine, q), [mine, q]);
  const shownShared = useMemo(() => filterMenuItems(shared, q), [shared, q]);

  const go = (sidebarItem) => {
    if (isExpandable(sidebarItem)) dispatch(expandItem({ id: sidebarItem.id }));
    const target = resolveMenuTarget(sidebarItem);
    if (!target) return;
    dispatch(activateItem({ item: target }));
    const adminUrl = toAdminPath(target.module_url);
    if (adminUrl) navigate(adminUrl);
    if (onNavigate) onNavigate();
  };

  const renderItem = (sidebarItem, depth = 0) => (
    <React.Fragment key={sidebarItem.id || sidebarItem.module_name}>
      <ListItem
        onClick={() => go(sidebarItem)}
        className={(sidebarItem?.active && (sidebarItem.submenus || []).length === 0) ? 'active-sidebar' : ''}
        sx={{
          pl: 2 + depth * 2,
          '&.Mui-selected': { backgroundColor: 'action.selected' },
          '&:hover': { backgroundColor: 'primary.light', borderRadius: '10px' },
        }}
      >
        <ListItemIcon>{getModuleIcon(sidebarItem.module_icon)}</ListItemIcon>
        <ListItemText primary={sidebarItem.module_name} />
        {(sidebarItem.submenus || []).length > 0 && (
          (sidebarItem?.expanded || sidebarItem?.active) ? <ExpandLess /> : <ExpandMore />
        )}
      </ListItem>
      {(sidebarItem.submenus || []).length > 0 && (
        <Collapse in={!!(sidebarItem?.expanded || sidebarItem?.active)} timeout="auto" unmountOnExit>
          <List component="div" disablePadding>
            {sidebarItem.submenus.map((child) => (
              <ListItem
                button
                sx={{ pl: 4 + depth * 2 }}
                key={child.id || child.module_name}
                onClick={() => go(child)}
                className={child?.active ? 'active-sidebar' : ''}
              >
                <ListItemIcon>{getModuleIcon(child.module_icon)}</ListItemIcon>
                <ListItemText primary={child.module_name} />
              </ListItem>
            ))}
          </List>
        </Collapse>
      )}
    </React.Fragment>
  );

  return (
    <>
      <Box sx={{ px: 1, pb: 1 }}>
        <TextField
          fullWidth size="small" placeholder="Filter menu…"
          value={q} onChange={(e) => setQ(e.target.value)}
        />
      </Box>
      <List sx={{ '& .MuiListItem-root': { transition: 'background-color 0.3s' } }}>
        <ListItem
          component={Link} to={meta.home}
          onClick={onNavigate}
          className={location.pathname === meta.home ? 'active-sidebar' : ''}
          sx={{ borderLeft: `3px solid ${meta.color}`, mb: 0.5 }}
        >
          <ListItemIcon sx={{ color: meta.color }}><DashboardIcon /></ListItemIcon>
          <ListItemText primary={`${meta.short} Overview`} />
        </ListItem>
        {shownMine.map((it) => renderItem(it))}
        {shownShared.length > 0 && (
          <>
            <ListSubheader sx={{ bgcolor: 'transparent', lineHeight: '32px' }}>
              Shared
            </ListSubheader>
            {shownShared.map((it) => renderItem(it))}
          </>
        )}
        {shownMine.length === 0 && shownShared.length === 0 && (
          <ListItem>
            <ListItemText
              primary={q ? 'No menu matches.' : 'No menus granted.'}
              primaryTypographyProps={{ variant: 'body2', color: 'text.secondary' }}
            />
          </ListItem>
        )}
      </List>
    </>
  );
}
