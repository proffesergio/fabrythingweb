import React from 'react';
import {
  Alert, Box, Chip, CircularProgress, Grid, MenuItem, Stack, TextField, Typography,
} from '@mui/material';
import { SIDES_OPTIONS, SHIPPING_ZONES } from './usePressPricing';

// Presentation for the dynamic pricing calculator. All state and math live in
// usePressPricing — this component only renders props, so the pricing logic
// stays testable without a DOM.
export default function PressCalculator({ pricing }) {
  const {
    products, papers, finishings, shopConfig,
    sel, patch, applyPreset, toggleFinishing,
    product, quote, quoteLoading, quoteError, fmtMoney,
  } = pricing;

  const sideFinishings = finishings.filter((f) => f.kind === 'SIDE');
  const lamination = finishings.filter((f) => f.kind === 'LAMINATION');
  const extra = finishings.filter((f) => f.kind === 'FINISHING');

  const renderChipGroup = (items) => (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
      {items.map((f) => {
        const on = sel.finishingIds.includes(f.id);
        return (
          <Chip
            key={f.id} label={`${f.name} (+৳${f.price}${f.per_unit ? '/pc' : ''})`}
            color={on ? 'primary' : 'default'}
            variant={on ? 'filled' : 'outlined'}
            onClick={() => toggleFinishing(f.id)}
          />
        );
      })}
      {items.length === 0 && <Typography variant="caption" color="text.secondary">—</Typography>}
    </Box>
  );

  return (
    <Box>
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6}>
          <TextField select fullWidth label="Product" value={sel.productId}
            onChange={(e) => { patch({ productId: e.target.value, sizePreset: '', width: '', height: '' }); }}>
            {products.map((p) => (
              <MenuItem key={p.id} value={p.id}>{p.name} — from ৳{p.from_price_bdt}</MenuItem>
            ))}
          </TextField>
        </Grid>
        <Grid item xs={12} sm={6}>
          <TextField select fullWidth label="Paper stock / GSM" value={sel.paperStockId}
            onChange={(e) => patch({ paperStockId: e.target.value })}>
            <MenuItem value="">Standard</MenuItem>
            {papers.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
          </TextField>
        </Grid>
      </Grid>

      <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>Size</Typography>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1.5 }}>
        {(product?.size_presets || []).map((sp) => (
          <Chip
            key={sp.id} label={`${sp.name} (${sp.width}×${sp.height}${sp.unit})`}
            color={String(sel.sizePreset) === String(sp.id) ? 'primary' : 'default'}
            variant={String(sel.sizePreset) === String(sp.id) ? 'filled' : 'outlined'}
            onClick={() => applyPreset(sp.id)}
          />
        ))}
      </Box>
      <Grid container spacing={2}>
        <Grid item xs={4}>
          <TextField fullWidth label="Width" value={sel.width}
            onChange={(e) => patch({ width: e.target.value, sizePreset: '' })} />
        </Grid>
        <Grid item xs={4}>
          <TextField fullWidth label="Height" value={sel.height}
            onChange={(e) => patch({ height: e.target.value, sizePreset: '' })} />
        </Grid>
        <Grid item xs={4}>
          <TextField select fullWidth label="Unit" value={sel.unit} onChange={(e) => patch({ unit: e.target.value })}>
            <MenuItem value="in">inches</MenuItem>
            <MenuItem value="ft">feet</MenuItem>
            <MenuItem value="mm">mm</MenuItem>
          </TextField>
        </Grid>
      </Grid>

      <Grid container spacing={2} sx={{ mt: 0.5 }}>
        <Grid item xs={12} sm={4}>
          <TextField select fullWidth label="Printing side" value={sel.sides} onChange={(e) => patch({ sides: e.target.value })}>
            {SIDES_OPTIONS.map((o) => <MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>)}
          </TextField>
        </Grid>
        <Grid item xs={12} sm={4}>
          <TextField fullWidth type="number" label={`Quantity (min ${product?.min_qty || 1})`} value={sel.quantity}
            inputProps={{ min: product?.min_qty || 1 }}
            onChange={(e) => patch({ quantity: Math.max(1, parseInt(e.target.value, 10) || 1) })} />
        </Grid>
        <Grid item xs={12} sm={4}>
          <TextField select fullWidth label="Currency" value={sel.currency} onChange={(e) => patch({ currency: e.target.value })}>
            <MenuItem value="BDT">BDT (৳)</MenuItem>
            <MenuItem value="USD">USD ($) {shopConfig?.usd_rate ? `(≈ ৳${shopConfig.usd_rate}/$)` : ''}</MenuItem>
          </TextField>
        </Grid>
      </Grid>

      {sideFinishings.length > 0 && (
        <><Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>Side options</Typography>{renderChipGroup(sideFinishings)}</>
      )}
      <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>Lamination</Typography>
      {renderChipGroup(lamination)}
      <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>Finishing (Spot UV · Die-Cutting · Foil…)</Typography>
      {renderChipGroup(extra)}

      <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>Delivery</Typography>
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6}>
          <TextField select fullWidth label="Shipping zone" value={sel.shippingZone} onChange={(e) => patch({ shippingZone: e.target.value })}>
            {SHIPPING_ZONES.map((z) => <MenuItem key={z.value} value={z.value}>{z.label}</MenuItem>)}
          </TextField>
        </Grid>
        <Grid item xs={12} sm={6}>
          <TextField fullWidth label="Preferred courier (optional)" placeholder="Pathao, Steadfast, Sundarban…" value={sel.shippingCourier}
            onChange={(e) => patch({ shippingCourier: e.target.value })} />
        </Grid>
      </Grid>

      <Box sx={{ mt: 2 }}>
        {quoteLoading && <Stack direction="row" spacing={1} alignItems="center"><CircularProgress size={18} /><Typography variant="body2">Pricing…</Typography></Stack>}
        {quoteError && <Alert severity="error">{quoteError}</Alert>}
        {quote && !quoteLoading && (
          <Alert severity="success">
            <Typography variant="body2">
              Material ৳{quote.material_per_unit}/pc × {quote.quantity || sel.quantity}
              {Number(quote.discount_percent) > 0 && ` (−${quote.discount_percent}% bulk)`} + setup ৳{quote.base_setup} + finishing ৳{quote.finishing_addons}
              {' '}→ <strong>{sel.currency === 'USD' ? `$${Number(quote.grand_total_charged).toLocaleString('en-US', { maximumFractionDigits: 2 })}` : `৳${Number(quote.grand_total_bdt).toLocaleString('en-US', { maximumFractionDigits: 0 })}`} total</strong>
              {' '}incl. shipping ৳{quote.shipping_fee_bdt} via {quote.shipping_courier}.
            </Typography>
            <Typography variant="caption">
              Total = (Setup + Material × Qty − bulk discount + Finishing) × {quote.margin_factor} margin.
            </Typography>
          </Alert>
        )}
      </Box>
    </Box>
  );
}
