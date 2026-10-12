import { useEffect, useMemo, useRef, useState } from 'react';
import useApi from '../../../hooks/APIHandler';

// Calculator logic for the web-to-press storefront — kept separate from the
// presentation components (PressCalculator renders what this hook computes),
// per the module's code-generation strategy. The backend is the single source
// of truth: every keystroke debounces into POST print/press/quote/, the exact
// same formula checkout books, so the estimate can never disagree with the
// order. The async call keeps the main thread free while typing.
export const SIDES_OPTIONS = [
  { value: '4/0', label: 'Single-Sided (4/0)' },
  { value: '4/4', label: 'Double-Sided (4/4)' },
];

export const SHIPPING_ZONES = [
  { value: 'INSIDE_DHAKA_HOME', label: 'Inside Dhaka — Home Delivery (Pathao / Steadfast)' },
  { value: 'HUB_PICKUP', label: 'Hub Pickup (Free)' },
  { value: 'OUTSIDE_DHAKA', label: 'Outside Dhaka — Courier (Sundarban / SA Paribahan / Paperfly)' },
];

export const PAYMENT_METHODS = [
  { value: 'SSLCOMMERZ', label: 'SSLCommerz (Card / Mobile Banking)' },
  { value: 'BKASH', label: 'bKash' },
  { value: 'NAGAD', label: 'Nagad' },
  { value: 'ROCKET', label: 'Rocket' },
  { value: 'COD', label: 'Cash on Delivery' },
  { value: 'PARTIAL_ADVANCE', label: 'Partial Advance (trusted corporate)' },
];

const initialSelection = {
  productId: '', sizePreset: '', width: '', height: '', unit: 'in',
  paperStockId: '', sides: '4/0', finishingIds: [],
  quantity: 100, currency: 'BDT',
  shippingZone: 'INSIDE_DHAKA_HOME', shippingCourier: '',
};

export default function usePressPricing(initialProductId) {
  const { callApi } = useApi();
  const callRef = useRef(callApi);
  callRef.current = callApi;
  const initialRef = useRef(initialProductId);

  const [products, setProducts] = useState([]);
  const [papers, setPapers] = useState([]);
  const [finishings, setFinishings] = useState([]);
  const [shopConfig, setShopConfig] = useState(null);
  const [sel, setSel] = useState(initialSelection);
  const [quote, setQuote] = useState(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [quoteError, setQuoteError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [p, pa, f, c] = await Promise.all([
        callRef.current({ url: 'print/press/products/', silent: true }),
        callRef.current({ url: 'print/press/paper/', silent: true }),
        callRef.current({ url: 'print/press/finishing/', silent: true }),
        callRef.current({ url: 'print/press/config/', silent: true }),
      ]);
      if (cancelled) return;
      if (p?.data?.data) {
        setProducts(p.data.data);
        // Preselect the linked product (Order-this-design handoff) or the
        // first product so the calculator is alive on load.
        const wanted = initialRef.current && p.data.data.some((x) => String(x.id) === String(initialRef.current))
          ? initialRef.current : p.data.data[0]?.id || '';
        setSel((s) => (s.productId ? s : { ...s, productId: wanted }));
      }
      if (pa?.data?.data) setPapers(pa.data.data);
      if (f?.data?.data) setFinishings(f.data.data);
      if (c?.data?.data) setShopConfig(c.data.data);
    })();
    return () => { cancelled = true; };
  }, []);

  const product = useMemo(
    () => products.find((p) => String(p.id) === String(sel.productId)),
    [products, sel.productId],
  );

  // Showcase handoff after load: "Order this design" swaps the calculator
  // to the linked press product.
  useEffect(() => {
    if (initialProductId && products.some((p) => String(p.id) === String(initialProductId))) {
      setSel((s) => (String(s.productId) === String(initialProductId) ? s
        : { ...s, productId: initialProductId, sizePreset: '', width: '', height: '' }));
    }
  }, [initialProductId, products]);

  // Picking a preset fills W/H/unit; editing W/H manually clears the preset.
  const patch = (update) => setSel((s) => ({ ...s, ...update }));
  const applyPreset = (presetId) => {
    const preset = product?.size_presets?.find((sp) => String(sp.id) === String(presetId));
    if (!preset) { patch({ sizePreset: '' }); return; }
    patch({ sizePreset: presetId, width: String(preset.width), height: String(preset.height), unit: preset.unit });
  };
  const toggleFinishing = (id) => {
    setSel((s) => ({
      ...s,
      finishingIds: s.finishingIds.includes(id) ? s.finishingIds.filter((x) => x !== id) : [...s.finishingIds, id],
    }));
  };

  const quoteBody = useMemo(() => {
    if (!sel.productId || !sel.width || !sel.height) return null;
    return {
      product: Number(sel.productId),
      width: String(sel.width), height: String(sel.height), unit: sel.unit,
      paper_stock: sel.paperStockId ? Number(sel.paperStockId) : null,
      finishing_ids: sel.finishingIds, quantity: Number(sel.quantity) || 1,
      sides: sel.sides, currency: sel.currency,
      shipping_zone: sel.shippingZone, shipping_courier: sel.shippingCourier,
    };
  }, [sel]);

  useEffect(() => {
    if (!quoteBody) { setQuote(null); return; }
    setQuoteLoading(true);
    setQuoteError('');
    const t = setTimeout(async () => {
      try {
        const res = await callRef.current({ url: 'print/press/quote/', method: 'POST', body: quoteBody, silent: true });
        const payload = res?.data?.data;
        if (payload && typeof payload === 'object') setQuote(payload);
        else setQuoteError('Could not price this configuration — please check the size and quantity.');
      } catch {
        setQuoteError('Could not reach the pricing engine — please retry in a few seconds.');
      } finally {
        setQuoteLoading(false);
      }
    }, 350);
    return () => clearTimeout(t);
  }, [quoteBody]);

  const fmtMoney = (bdtValue) => {
    if (sel.currency === 'USD' && shopConfig?.usd_rate) {
      const usd = Number(bdtValue || 0) / Number(shopConfig.usd_rate);
      return `$${usd.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
    }
    return `৳${Number(bdtValue || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
  };

  return {
    products, papers, finishings, shopConfig,
    sel, patch, applyPreset, toggleFinishing,
    product, quote, quoteLoading, quoteError, quoteBody, fmtMoney,
  };
}
