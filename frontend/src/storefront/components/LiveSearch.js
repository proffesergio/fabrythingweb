import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Box, TextField, InputAdornment, IconButton, Popper, Paper,
    List, ListItemButton, ListItemAvatar, Avatar, ListItemText,
    Typography, CircularProgress, ClickAwayListener, Divider, Fade,
} from '@mui/material';
import { Search, Close, TrendingUp } from '@mui/icons-material';
import useApi from '../../hooks/APIHandler';

const FALLBACK_IMG = 'https://placehold.co/80x100/e2e8f0/64748b?text=%20';

/**
 * Header live-search: debounced product lookup that shows a dropdown of
 * matching products with thumbnail + brand + price. Enter (or "see all")
 * routes to the full catalog search.
 */
export default function LiveSearch({ fullWidth = false, autoFocus = false, onNavigate }) {
    const [query, setQuery]     = useState('');
    const [results, setResults] = useState([]);
    const [open, setOpen]       = useState(false);
    const [loading, setLoading] = useState(false);
    const anchorRef             = useRef(null);
    const navigate              = useNavigate();
    const { callApi }           = useApi();

    // Debounced fetch as the user types.
    useEffect(() => {
        const q = query.trim();
        if (q.length < 2) {
            setResults([]);
            setLoading(false);
            return;
        }
        setLoading(true);
        const t = setTimeout(async () => {
            const res = await callApi({ url: 'store/products/', params: { search: q, page: 1 } });
            const list = res?.data?.data?.data || [];
            setResults(list.slice(0, 6));
            setLoading(false);
            setOpen(true);
        }, 280);
        return () => clearTimeout(t);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [query]);

    const go = (path) => {
        setOpen(false);
        setQuery('');
        onNavigate?.();
        navigate(path);
    };

    const submit = (e) => {
        e?.preventDefault();
        if (query.trim()) go(`/shop?search=${encodeURIComponent(query.trim())}`);
    };

    const priceOf = (p) => p.discount_price || p.initial_selling_price;

    return (
        <ClickAwayListener onClickAway={() => setOpen(false)}>
            <Box ref={anchorRef} sx={{ position: 'relative', width: fullWidth ? '100%' : { md: 340, lg: 420 } }}>
                <form onSubmit={submit}>
                    <TextField
                        size="small"
                        fullWidth
                        autoFocus={autoFocus}
                        placeholder="Search for brands, products…"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onFocus={() => results.length && setOpen(true)}
                        sx={{
                            '& .MuiOutlinedInput-root': {
                                bgcolor: 'background.paper',
                                borderRadius: 999,
                                pr: 0.5,
                                '& fieldset': { borderColor: 'divider' },
                                '&:hover fieldset': { borderColor: 'primary.light' },
                                '&.Mui-focused fieldset': { borderColor: 'primary.main', borderWidth: 2 },
                            },
                        }}
                        InputProps={{
                            startAdornment: (
                                <InputAdornment position="start">
                                    <Search fontSize="small" color="action" />
                                </InputAdornment>
                            ),
                            endAdornment: (
                                <InputAdornment position="end">
                                    {query ? (
                                        <IconButton size="small" onClick={() => { setQuery(''); setResults([]); }}>
                                            <Close fontSize="small" />
                                        </IconButton>
                                    ) : null}
                                    <IconButton
                                        size="small" type="submit" color="secondary"
                                        sx={{ bgcolor: 'secondary.main', color: 'white', ml: 0.5, '&:hover': { bgcolor: 'secondary.dark' } }}
                                    >
                                        <Search fontSize="small" />
                                    </IconButton>
                                </InputAdornment>
                            ),
                        }}
                    />
                </form>

                <Popper
                    open={open && query.trim().length >= 2}
                    anchorEl={anchorRef.current}
                    placement="bottom-start"
                    transition
                    style={{ zIndex: 1300, width: anchorRef.current?.offsetWidth }}
                    modifiers={[{ name: 'offset', options: { offset: [0, 8] } }]}
                >
                    {({ TransitionProps }) => (
                        <Fade {...TransitionProps} timeout={180}>
                            <Paper elevation={8} sx={{ borderRadius: 3, overflow: 'hidden', border: '1px solid', borderColor: 'divider' }}>
                                {loading ? (
                                    <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                                        <CircularProgress size={22} />
                                    </Box>
                                ) : results.length === 0 ? (
                                    <Box sx={{ py: 3, textAlign: 'center' }}>
                                        <Typography variant="body2" color="text.secondary">
                                            No products match “{query.trim()}”.
                                        </Typography>
                                    </Box>
                                ) : (
                                    <List disablePadding>
                                        {results.map((p) => {
                                            const hasDiscount = p.discount_price && p.discount_price < p.initial_selling_price;
                                            const img = Array.isArray(p.image) && p.image[0] ? p.image[0] : FALLBACK_IMG;
                                            return (
                                                <ListItemButton
                                                    key={p.id}
                                                    onClick={() => go(`/product/${p.slug}`)}
                                                    sx={{ py: 1, gap: 0.5 }}
                                                >
                                                    <ListItemAvatar>
                                                        <Avatar
                                                            variant="rounded" src={img} alt={p.name}
                                                            imgProps={{ onError: (e) => { e.target.src = FALLBACK_IMG; } }}
                                                            sx={{ width: 46, height: 58, bgcolor: 'action.hover' }}
                                                        />
                                                    </ListItemAvatar>
                                                    <ListItemText
                                                        primary={
                                                            <Typography variant="body2" fontWeight={600} noWrap sx={{ maxWidth: 260 }}>
                                                                {p.name}
                                                            </Typography>
                                                        }
                                                        secondary={
                                                            <Typography variant="caption" color="text.secondary" noWrap>
                                                                {p.brand || p.category_name}
                                                            </Typography>
                                                        }
                                                    />
                                                    <Box sx={{ textAlign: 'right', pl: 1 }}>
                                                        <Typography variant="subtitle2" fontWeight={800} color={hasDiscount ? 'secondary.main' : 'text.primary'}>
                                                            ৳{priceOf(p)?.toLocaleString()}
                                                        </Typography>
                                                        {hasDiscount && (
                                                            <Typography variant="caption" sx={{ textDecoration: 'line-through', color: 'text.disabled' }}>
                                                                ৳{p.initial_selling_price?.toLocaleString()}
                                                            </Typography>
                                                        )}
                                                    </Box>
                                                </ListItemButton>
                                            );
                                        })}
                                        <Divider />
                                        <ListItemButton onClick={submit} sx={{ justifyContent: 'center', py: 1.2 }}>
                                            <TrendingUp fontSize="small" sx={{ mr: 1, color: 'secondary.main' }} />
                                            <Typography variant="body2" fontWeight={700} color="secondary.main">
                                                See all results for “{query.trim()}”
                                            </Typography>
                                        </ListItemButton>
                                    </List>
                                )}
                            </Paper>
                        </Fade>
                    )}
                </Popper>
            </Box>
        </ClickAwayListener>
    );
}
