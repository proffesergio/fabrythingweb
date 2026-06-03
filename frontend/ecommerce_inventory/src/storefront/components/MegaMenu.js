import React, { useState } from 'react';
import {
    Box, Typography, Paper, Grid,
    List, ListItemButton, ListItemText, Collapse,
} from '@mui/material';
import { ExpandMore, ExpandLess } from '@mui/icons-material';
import { Link } from 'react-router-dom';

const navItems = [
    { label: 'Home',  path: '/',     type: 'link' },
    { label: 'Shop',  path: '/shop', type: 'link' },
    { label: 'Men',   gender: 'MEN',   type: 'mega' },
    { label: 'Women', gender: 'WOMEN', type: 'mega' },
    { label: 'Kids',  gender: 'KIDS',  type: 'mega' },
];

// Desktop mega menu
export default function MegaMenu({ categories }) {
    const [activeMenu, setActiveMenu] = useState(null);

    const getCategoryChildren = (label) => {
        const parent = categories?.find(c => c.slug === label.toLowerCase());
        return parent?.children || [];
    };

    return (
        <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
            {navItems.map(item => (
                <Box
                    key={item.label}
                    // ── Hover zone: includes the label AND the absolutely-positioned
                    //    dropdown, so mouse moving between them never fires onMouseLeave.
                    onMouseEnter={() => item.type === 'mega' && setActiveMenu(item.label)}
                    onMouseLeave={() => item.type === 'mega' && setActiveMenu(null)}
                    sx={{ position: 'relative' }}
                >
                    {/* Nav label */}
                    <Typography
                        component={Link}
                        to={item.path || `/shop?gender=${item.gender}`}
                        sx={{
                            display: 'block',
                            textDecoration: 'none',
                            color: activeMenu === item.label ? 'primary.main' : 'text.primary',
                            fontSize: '0.92rem',
                            fontWeight: 600,
                            px: 1.5, py: 1,
                            borderRadius: 2,
                            letterSpacing: '0.01em',
                            transition: 'color 0.15s',
                            '&:hover': { color: 'primary.main' },
                        }}
                    >
                        {item.label}
                    </Typography>

                    {/* Dropdown — only for mega items, only when active */}
                    {item.type === 'mega' && activeMenu === item.label && (
                        <>
                            {/*
                             * Transparent 8-px bridge between the label bottom and the Paper top.
                             * It has no background but IS inside the hover container, so crossing
                             * it does NOT trigger onMouseLeave on the parent Box.
                             */}
                            <Box sx={{
                                position: 'absolute', top: '100%', left: 0,
                                width: '100%', height: 8,
                                zIndex: 1300,
                            }} />

                            <Paper
                                elevation={10}
                                sx={{
                                    position: 'absolute',
                                    top: 'calc(100% + 8px)',
                                    left: 0,
                                    zIndex: 1300,
                                    minWidth: 420,
                                    maxWidth: 580,
                                    borderRadius: 3,
                                    p: 3,
                                    border: '1px solid',
                                    borderColor: 'divider',
                                    backdropFilter: 'blur(14px)',
                                }}
                            >
                                <MegaMenuContent
                                    label={item.label}
                                    gender={item.gender}
                                    children={getCategoryChildren(item.label)}
                                    onClose={() => setActiveMenu(null)}
                                />
                            </Paper>
                        </>
                    )}
                </Box>
            ))}
        </Box>
    );
}

function MegaMenuContent({ label, children, gender, onClose }) {
    return (
        <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, letterSpacing: '-0.01em' }}>
                    {label}'s Collection
                </Typography>
                <Typography
                    component={Link}
                    to={`/shop?gender=${gender}`}
                    onClick={onClose}
                    variant="body2"
                    sx={{
                        color: 'secondary.main', textDecoration: 'none',
                        fontWeight: 600, fontSize: '0.82rem',
                        '&:hover': { textDecoration: 'underline' },
                    }}
                >
                    View All →
                </Typography>
            </Box>

            <Grid container spacing={1}>
                {children.map(cat => (
                    <Grid item xs={6} sm={4} key={cat.id}>
                        <Box
                            component={Link}
                            to={`/shop?category=${cat.slug}`}
                            onClick={onClose}
                            sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                textDecoration: 'none',
                                color: 'text.primary',
                                py: 0.75, px: 1.25,
                                borderRadius: 2,
                                fontSize: '0.88rem',
                                fontWeight: 500,
                                transition: 'all 0.15s',
                                '&:hover': {
                                    bgcolor: 'action.hover',
                                    color: 'primary.main',
                                    pl: 1.75,
                                },
                            }}
                        >
                            <span>{cat.name}</span>
                            {cat.product_count > 0 && (
                                <Typography
                                    component="span"
                                    variant="caption"
                                    sx={{
                                        ml: 0.5, px: 0.75, py: 0.1,
                                        bgcolor: 'action.selected',
                                        borderRadius: 1,
                                        fontSize: '0.7rem',
                                        color: 'text.secondary',
                                        fontWeight: 600,
                                    }}
                                >
                                    {cat.product_count}
                                </Typography>
                            )}
                        </Box>
                    </Grid>
                ))}
            </Grid>
        </Box>
    );
}

// ── Mobile accordion menu (Drawer) ────────────────────────────
export function MobileCategoryMenu({ categories, onClose }) {
    const [expanded, setExpanded] = useState(null);
    const genderSlugs = ['men', 'women', 'kids'];

    return (
        <List>
            <ListItemButton component={Link} to="/" onClick={onClose}>
                <ListItemText primary="Home" primaryTypographyProps={{ fontWeight: 600 }} />
            </ListItemButton>
            <ListItemButton component={Link} to="/shop" onClick={onClose}>
                <ListItemText primary="Shop All" primaryTypographyProps={{ fontWeight: 600 }} />
            </ListItemButton>
            {genderSlugs.map(slug => {
                const parent = categories?.find(c => c.slug === slug);
                if (!parent) return null;
                const isOpen = expanded === slug;
                return (
                    <React.Fragment key={slug}>
                        <ListItemButton onClick={() => setExpanded(isOpen ? null : slug)}>
                            <ListItemText primary={parent.name} primaryTypographyProps={{ fontWeight: 600 }} />
                            {isOpen ? <ExpandLess /> : <ExpandMore />}
                        </ListItemButton>
                        <Collapse in={isOpen}>
                            <List disablePadding>
                                <ListItemButton
                                    component={Link}
                                    to={`/shop?gender=${slug.toUpperCase()}`}
                                    onClick={onClose}
                                    sx={{ pl: 4 }}
                                >
                                    <ListItemText
                                        primary={`All ${parent.name}`}
                                        primaryTypographyProps={{ fontSize: '0.9rem', color: 'primary.main', fontWeight: 600 }}
                                    />
                                </ListItemButton>
                                {parent.children?.map(child => (
                                    <ListItemButton
                                        key={child.id}
                                        component={Link}
                                        to={`/shop?category=${child.slug}`}
                                        onClick={onClose}
                                        sx={{ pl: 4 }}
                                    >
                                        <ListItemText
                                            primary={child.name}
                                            secondary={child.product_count > 0 ? `${child.product_count} items` : null}
                                            primaryTypographyProps={{ fontSize: '0.9rem' }}
                                            secondaryTypographyProps={{ fontSize: '0.75rem' }}
                                        />
                                    </ListItemButton>
                                ))}
                            </List>
                        </Collapse>
                    </React.Fragment>
                );
            })}
        </List>
    );
}
