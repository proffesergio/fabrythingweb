import React from 'react';
import { Card, CardMedia, CardContent, Typography, Box, Rating, Button, IconButton } from '@mui/material';
import { ShoppingCart, FavoriteBorder, Visibility } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

export default function ProductCard({ product, showFlashBadge }) {
    const navigate = useNavigate();

    const price = product.discount_price || product.initial_selling_price;
    const hasDiscount = product.discount_price && product.discount_price < product.initial_selling_price;
    const discountPct = product.discount_percentage || (
        hasDiscount ? Math.round((1 - product.discount_price / product.initial_selling_price) * 100) : 0
    );

    const isNew = product.created_at && (
        (new Date() - new Date(product.created_at)) / (1000 * 60 * 60 * 24) < 7
    );

    const imageUrl = Array.isArray(product.image) && product.image.length > 0
        ? product.image[0]
        : '/placeholder.png';

    const handleQuickAdd = (e) => {
        // Size/variant must be chosen on the product page, so route there.
        e.stopPropagation();
        navigate(`/product/${product.slug}`);
    };

    return (
        <motion.div
            whileHover={{ y: -6 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
            style={{ height: '100%' }}
        >
            <Card
                sx={{
                    cursor: 'pointer',
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    position: 'relative',
                    overflow: 'hidden',
                    '&:hover .quick-add': { opacity: 1, transform: 'translateY(0)' },
                    '&:hover .card-overlay': { opacity: 1 },
                    '&:hover .action-icons': { opacity: 1, transform: 'translateX(0)' },
                }}
                onClick={() => navigate(`/product/${product.slug}`)}
            >
                {/* Badges */}
                <Box sx={{ position: 'absolute', top: 8, left: 8, zIndex: 2, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                    {hasDiscount && (
                        <motion.div
                            animate={showFlashBadge ? { scale: [1, 1.08, 1] } : {}}
                            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                        >
                            <Box sx={{
                                bgcolor: showFlashBadge ? '#ff1744' : 'secondary.main',
                                color: 'white', px: 1, py: 0.25,
                                borderRadius: 1, fontSize: '0.75rem', fontWeight: 700,
                                boxShadow: showFlashBadge ? '0 2px 8px rgba(255,23,68,0.4)' : 'none',
                            }}>
                                -{discountPct}%
                            </Box>
                        </motion.div>
                    )}
                    {isNew && !hasDiscount && (
                        <Box sx={{
                            bgcolor: '#00C853', color: 'white', px: 1, py: 0.25,
                            borderRadius: 1, fontSize: '0.7rem', fontWeight: 700,
                        }}>
                            NEW
                        </Box>
                    )}
                </Box>

                {/* Action icons (right side) */}
                <Box
                    className="action-icons"
                    sx={{
                        position: 'absolute', top: 8, right: 8, zIndex: 2,
                        display: 'flex', flexDirection: 'column', gap: 0.5,
                        opacity: { xs: 1, md: 0 },
                        transform: { xs: 'translateX(0)', md: 'translateX(10px)' },
                        transition: 'all 0.3s ease',
                    }}
                >
                    {/* p bumped on xs only — these sit permanently visible on mobile
                        (opacity xs:1 above), so their ~30px default small-IconButton
                        hit area is genuinely tappable rather than a hover affordance;
                        desktop padding is left at the component default. */}
                    <IconButton
                        size="small"
                        onClick={(e) => e.stopPropagation()}
                        sx={{
                            p: { xs: 1.25 },
                            bgcolor: 'white', boxShadow: 1,
                            '&:hover': { bgcolor: 'secondary.main', color: 'white' },
                        }}
                    >
                        <FavoriteBorder fontSize="small" />
                    </IconButton>
                    <IconButton
                        size="small"
                        onClick={(e) => { e.stopPropagation(); navigate(`/product/${product.slug}`); }}
                        sx={{
                            p: { xs: 1.25 },
                            bgcolor: 'white', boxShadow: 1,
                            '&:hover': { bgcolor: 'primary.main', color: 'white' },
                        }}
                    >
                        <Visibility fontSize="small" />
                    </IconButton>
                </Box>

                {/* Image — flatter aspect ratio on mobile so the card doesn't run tall;
                    unchanged on desktop. */}
                <Box sx={{ position: 'relative', overflow: 'hidden' }}>
                    <CardMedia
                        component="img"
                        sx={{
                            aspectRatio: { xs: '1 / 1', md: '3/4' },
                            objectFit: 'cover',
                            transition: 'transform 0.4s ease',
                            '&:hover': { transform: 'scale(1.05)' },
                        }}
                        image={imageUrl}
                        alt={product.name}
                        onError={(e) => { e.target.src = 'https://placehold.co/300x400/e2e8f0/64748b?text=No+Image'; }}
                    />
                </Box>

                <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column', gap: { xs: 0.25, md: 0.5 }, p: { xs: 1, md: 1.5 }, '&:last-child': { pb: { xs: 1, md: 1.5 } } }}>
                    <Typography variant="body2" color="text.secondary" sx={{ fontSize: { xs: '0.62rem', md: '0.7rem' }, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        {product.brand || product.category_name}
                    </Typography>
                    {/* Clamped to 2 lines — catalog names (e.g. full laptop model strings)
                        run 60-115+ characters and would otherwise wrap to 4+ lines and
                        stretch the card, breaking the mobile grid's row heights. */}
                    <Typography variant="subtitle2" sx={{
                        fontWeight: 600, lineHeight: 1.25,
                        fontSize: { xs: '0.78rem', md: '0.875rem' },
                        overflow: 'hidden', textOverflow: 'ellipsis',
                        display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                    }}>
                        {product.name}
                    </Typography>

                    {product.average_rating > 0 && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Rating value={product.average_rating} size="small" precision={0.5} readOnly />
                            <Typography variant="caption" color="text.secondary">
                                ({product.review_count})
                            </Typography>
                        </Box>
                    )}

                    <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mt: 'auto' }}>
                        <Typography variant="h6" sx={{ fontWeight: 700, fontSize: { xs: '0.95rem', md: '1.1rem' }, color: hasDiscount ? 'secondary.main' : 'text.primary' }}>
                            ৳{price?.toLocaleString()}
                        </Typography>
                        {hasDiscount && (
                            <Typography variant="body2" sx={{ textDecoration: 'line-through', color: 'text.secondary', fontSize: '0.85rem' }}>
                                ৳{product.initial_selling_price?.toLocaleString()}
                            </Typography>
                        )}
                    </Box>
                </CardContent>

                {/* Quick-add is a hover affordance on desktop. On mobile there's no
                    hover state to reveal it, so it would just sit permanently visible,
                    reserving ~40px of card height for a button that duplicates
                    "tap the card" (which already routes to the product page). Dropping
                    it from the mobile layout is most of what buys back the 2-cards-per-
                    screen target; tapping the card is still the way to act on it. */}
                <Button
                    className="quick-add"
                    size="small"
                    variant="contained"
                    color="secondary"
                    startIcon={<ShoppingCart fontSize="small" />}
                    onClick={handleQuickAdd}
                    sx={{
                        display: { xs: 'none', md: 'flex' },
                        mx: 1.5, mb: 1.5,
                        opacity: { md: 0 },
                        transform: { md: 'translateY(10px)' },
                        transition: 'all 0.3s ease',
                        fontWeight: 600,
                    }}
                >
                    Add to Cart
                </Button>
            </Card>
        </motion.div>
    );
}
