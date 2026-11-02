import React, { useEffect, useState } from 'react';
import {
  Alert, Box, Button, Card, Chip, CircularProgress, Grid,
  MenuItem, Stack, TextField, Typography,
} from '@mui/material';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import useApi from '../../../hooks/APIHandler';
import config from '../../../utils/config';
import { getToken } from '../../../utils/authToken';
import { isAuthenticated } from '../../../utils/Helper';
import usePressPricing, { PAYMENT_METHODS } from './usePressPricing';
import PressCalculator from './PressCalculator';
import ArtworkUploader from './ArtworkUploader';

const STATUS_COLORS = {
  PENDING_PAYMENT: 'warning', ARTWORK_REVIEW: 'info', IN_PRODUCTION: 'secondary',
  READY_FOR_DISPATCH: 'primary', SHIPPED: 'default', DELIVERED: 'success', CANCELLED: 'error',
};

// Storefront web-to-press flow: scannable product grid with bold prices →
// live calculator → artwork upload with validation → BD-localized checkout
// (BDT/USD, SSLCommerz/bKash/Nagad/Rocket/COD/partial) → order tracking.
export default function PressOrderWizard({ initialProductId }) {
  const pricing = usePressPricing(initialProductId);
  const { sel, patch, product, quoteBody, shopConfig } = pricing;
  const { callApi } = useApi();
  const navigate = useNavigate();
  const loggedIn = isAuthenticated();

  const [artFiles, setArtFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState({});
  const [address, setAddress] = useState({ name: '', phone: '', area: '', city: 'Dhaka', note: '' });
  const [paymentMethod, setPaymentMethod] = useState('SSLCOMMERZ');
  const [poNumber, setPoNumber] = useState('');
  const [isCorporate, setIsCorporate] = useState(false);
  const [placing, setPlacing] = useState(false);
  const [placed, setPlaced] = useState(null);
  const [formError, setFormError] = useState('');
  const [myOrders, setMyOrders] = useState([]);

  useEffect(() => {
    if (!loggedIn) return;
    (async () => {
      const res = await callApi({ url: 'print/press/orders/', silent: true });
      if (res?.data?.data) setMyOrders(res.data.data);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loggedIn, placed]);

  const uploadAll = async (orderId) => {
    for (let i = 0; i < artFiles.length; i += 1) {
      const entry = artFiles[i];
      const fd = new FormData();
      fd.append('file', entry.file);
      try {
        await axios.request({
          url: `${config.API_URL}print/press/orders/${orderId}/artwork/`,
          method: 'POST', data: fd,
          headers: { Authorization: getToken() ? `Bearer ${getToken()}` : '' },
          onUploadProgress: (e) => {
            const pct = e.total ? (e.loaded / e.total) * 100 : 50;
            setUploadProgress((p) => ({ ...p, [i]: pct }));
          },
        });
        setUploadProgress((p) => ({ ...p, [i]: 100 }));
      } catch {
        toast.error(`Could not upload ${entry.name} — retry it from your order.`);
      }
    }
  };

  const placeOrder = async () => {
    setFormError('');
    if (!loggedIn) { navigate('/auth/login'); return; }
    if (!quoteBody) { setFormError('Choose a product and size first — the calculator needs a complete configuration.'); return; }
    setPlacing(true);
    const body = {
      ...quoteBody,
      payment_method: paymentMethod,
      shipping_address: address,
      artwork_files: [],
      size_name: product?.size_presets?.find((sp) => String(sp.id) === String(sel.sizePreset))?.name || '',
      po_number: poNumber, is_corporate: isCorporate,
    };
    const res = await callApi({ url: 'print/press/checkout/', method: 'POST', body, rawError: true });
    if (res?.status === 201) {
      const order = res.data.data;
      if (artFiles.length > 0) await uploadAll(order.id);
      setPlaced(order);
      setArtFiles([]);
      toast.success(`Press order #${order.id} placed`);
    } else {
      setFormError(res?.data?.data ? JSON.stringify(res.data.data) : (res?.data?.message || 'Could not place your order. Please try again.'));
    }
    setPlacing(false);
  };

  const saveQuotation = async () => {
    if (!loggedIn) { navigate('/auth/login'); return; }
    if (!quoteBody) { toast.error('Complete the calculator first.'); return; }
    const res = await callApi({ url: 'print/press/quotations/', method: 'POST', body: { ...quoteBody, po_number: poNumber }, rawError: true });
    if (res?.status === 201) toast.success(`Quotation #${res.data.data.id} saved — find it under My Press Orders.`);
    else toast.error(res?.data?.message || 'Could not save the quotation.');
  };

  const simulatePay = async () => {
    if (!placed) return;
    const res = await callApi({
      url: `print/press/orders/${placed.id}/pay/callback/`, method: 'POST',
      body: { success: true, txn_id: placed.payment?.txn_id || '' }, rawError: true,
    });
    if (res?.status === 200) {
      setPlaced(res.data.data);
      toast.success('Payment recorded — your order is now in artwork review.');
    } else {
      toast.error(res?.data?.data || 'Payment failed — no amount was charged. Please retry or choose Cash on Delivery.');
    }
  };

  if (placed) {
    return (
      <Card sx={{ p: 3, maxWidth: 700 }}>
        <Typography variant="h6" fontWeight={800} sx={{ mb: 1 }}>Order #{placed.id} confirmed</Typography>
        <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
          <Chip size="small" label={placed.status.replace(/_/g, ' ')} color={STATUS_COLORS[placed.status] || 'default'} />
          <Chip size="small" variant="outlined" label={`${placed.payment_method} · ${placed.payment_status}`} />
        </Stack>
        <Typography variant="body2" sx={{ mb: 2 }}>
          Total <strong>৳{Number(placed.total_bdt).toLocaleString('en-US')}</strong>
          {placed.currency === 'USD' && <> (charged ${placed.total_charged})</>} incl. shipping.
        </Typography>
        {placed.payment?.gateway_url && placed.payment_status === 'PENDING' && (
          <Alert severity="info" sx={{ mb: 2 }}>
            This demo checkout simulates the {placed.payment_method} gateway. Press Pay to complete it —
            real SSLCommerz / bKash / Nagad / Rocket keys plug into the same endpoint.
            <Box sx={{ mt: 1 }}><Button variant="contained" onClick={simulatePay}>Pay {placed.currency === 'USD' ? `$${placed.total_charged}` : `৳${Number(placed.total_bdt).toLocaleString('en-US')}`} now</Button></Box>
          </Alert>
        )}
        {placed.payment_hint && <Alert severity="info" sx={{ mb: 2 }}>{placed.payment_hint}</Alert>}
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" onClick={() => setPlaced(null)}>Order another</Button>
          <Button variant="text" onClick={() => navigate('/custom-printing')}>Back to printing</Button>
        </Stack>
      </Card>
    );
  }

  return (
    <Box>
      {/* Scannable catalog grid with bold price indicators */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {pricing.products.filter((p) => p.is_active !== false).map((p) => {
          const active = String(sel.productId) === String(p.id);
          return (
            <Grid item xs={6} sm={4} md={3} lg={2} key={p.id}>
              <Card
                variant="outlined" onClick={() => patch({ productId: p.id, sizePreset: '', width: '', height: '' })}
                sx={{ p: 1.5, cursor: 'pointer', height: '100%', borderColor: active ? 'primary.main' : 'divider', borderWidth: active ? 2 : 1 }}
              >
                <Typography variant="body2" fontWeight={800}>{p.name}</Typography>
                <Typography variant="caption" color="text.secondary" display="block">{p.category}</Typography>
                <Typography variant="subtitle2" fontWeight={900} color="primary.main" sx={{ mt: 0.5 }}>
                  from ৳{p.from_price_bdt}
                </Typography>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} md={7}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight={800} sx={{ mb: 2 }}>Configure & price instantly</Typography>
            <PressCalculator pricing={pricing} />
          </Card>
          <Card sx={{ p: 3, mt: 2 }}>
            <Typography variant="h6" fontWeight={800} sx={{ mb: 1 }}>Artwork</Typography>
            <ArtworkUploader
              files={artFiles} onChange={setArtFiles} uploadProgress={uploadProgress}
              trim={{ width: sel.width, height: sel.height, unit: sel.unit, maxMb: shopConfig?.max_upload_mb || 100 }}
            />
          </Card>
        </Grid>
        <Grid item xs={12} md={5}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight={800} sx={{ mb: 2 }}>Checkout</Typography>
            {formError && <Alert severity="error" sx={{ mb: 2 }}>{formError}</Alert>}
            <TextField select fullWidth label="Payment method" value={paymentMethod}
              onChange={(e) => setPaymentMethod(e.target.value)} sx={{ mb: 2 }}>
              {PAYMENT_METHODS.map((m) => <MenuItem key={m.value} value={m.value}>{m.label}</MenuItem>)}
            </TextField>
            <Grid container spacing={1.5} sx={{ mb: 2 }}>
              <Grid item xs={12} sm={6}><TextField fullWidth size="small" label="Name" value={address.name} onChange={(e) => setAddress({ ...address, name: e.target.value })} /></Grid>
              <Grid item xs={12} sm={6}><TextField fullWidth size="small" label="Phone" value={address.phone} onChange={(e) => setAddress({ ...address, phone: e.target.value })} /></Grid>
              <Grid item xs={12} sm={6}><TextField fullWidth size="small" label="Area / Thana" value={address.area} onChange={(e) => setAddress({ ...address, area: e.target.value })} /></Grid>
              <Grid item xs={12} sm={6}><TextField fullWidth size="small" label="City / District" value={address.city} onChange={(e) => setAddress({ ...address, city: e.target.value })} /></Grid>
              <Grid item xs={12}><TextField fullWidth size="small" label="Delivery note (optional)" value={address.note} onChange={(e) => setAddress({ ...address, note: e.target.value })} /></Grid>
            </Grid>
            <Grid container spacing={1.5} sx={{ mb: 2 }}>
              <Grid item xs={12} sm={6}><TextField fullWidth size="small" label="PO number (corporate)" value={poNumber} onChange={(e) => setPoNumber(e.target.value)} /></Grid>
              <Grid item xs={12} sm={6}>
                <TextField select fullWidth size="small" label="Corporate order?" value={isCorporate ? 'yes' : 'no'}
                  onChange={(e) => setIsCorporate(e.target.value === 'yes')}>
                  <MenuItem value="no">No</MenuItem>
                  <MenuItem value="yes">Yes — bill my ledger</MenuItem>
                </TextField>
              </Grid>
            </Grid>
            <Button variant="contained" size="large" fullWidth disabled={placing} onClick={placeOrder} sx={{ mb: 1 }}>
              {placing ? <CircularProgress size={22} /> : (loggedIn ? 'Place press order' : 'Log in to order')}
            </Button>
            <Button size="small" fullWidth onClick={saveQuotation}>Save as quotation PDF instead</Button>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
              Partial advance is available to trusted corporate accounts only. Failed payments are never
              charged — just retry or switch to Cash on Delivery.
            </Typography>
          </Card>

          {loggedIn && myOrders.length > 0 && (
            <Card sx={{ p: 2, mt: 2 }}>
              <Typography variant="subtitle1" fontWeight={800} sx={{ mb: 1 }}>My press orders</Typography>
              {myOrders.map((o) => (
                <Box key={o.id} sx={{ display: 'flex', gap: 1, alignItems: 'center', py: 0.75, borderBottom: '1px solid', borderColor: 'divider' }}>
                  <Typography variant="body2" fontWeight={700}>#{o.id}</Typography>
                  <Typography variant="body2" sx={{ flex: 1 }}>{o.product_name} × {o.quantity}</Typography>
                  <Chip size="small" label={o.status.replace(/_/g, ' ')} color={STATUS_COLORS[o.status] || 'default'} />
                  <Typography variant="body2" fontWeight={800}>৳{Number(o.total_bdt).toLocaleString('en-US')}</Typography>
                </Box>
              ))}
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}
