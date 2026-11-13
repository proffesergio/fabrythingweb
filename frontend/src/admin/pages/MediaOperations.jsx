import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, Button, CircularProgress, FormControlLabel, LinearProgress, Switch, TextField } from '@mui/material';
import { AutoFixHigh, Refresh, Restore, WhatsApp } from '@mui/icons-material';
import useApi from '../../hooks/APIHandler';
import './MediaOperations.css';

const API = 'store/admin/operations/';
const unwrap = (response) => response?.data?.data;
const failure = (response) => response?.data?.errors?.join(' ') || response?.data?.detail || response?.data?.message || 'The request failed. Try again.';
export const formatBytes = (bytes) => {
  if (bytes === null || bytes === undefined) return 'Unknown';
  if (bytes < 1024) return `${bytes} B`;
  const unit = Math.min(4, Math.floor(Math.log(bytes) / Math.log(1024)));
  return `${(bytes / 1024 ** unit).toFixed(1)} ${['B', 'KiB', 'MiB', 'GiB', 'TiB'][unit]}`;
};
const when = (date) => date ? new Date(date).toLocaleString() : 'Not measured yet';
const mib = (value) => value ? String(Math.round(value / 1024 ** 2 * 100) / 100) : '';
const policyForm = (policy) => ({ whatsapp_admin_number: policy.whatsapp_admin_number || '',
  whatsapp_template: policy.whatsapp_template, whatsapp_language: policy.whatsapp_language,
  database_budget: mib(policy.database_budget_bytes), object_budget: mib(policy.object_budget_bytes), budget_note: policy.budget_note || '' });
const statusLabel = (status) => ({ completed: 'Cleaned', processing: 'Processing', unknown: 'Unconfirmed · review Meta',
  accepted: 'Accepted by Meta', sending: 'Sending', delivered: 'Delivered', read: 'Read', queued: 'Queued',
  stale: 'Editor changed photo', review: 'Needs image review', restored: 'Original restored', failed: 'Failed', expired: 'Expired' }[status] || status);

function Usage({ title, item }) {
  const complete = item?.measurement_complete !== false;
  return <div className="mo-usage">
    <div><span>{title}</span><strong>{!complete && item?.used_bytes != null ? 'At least ' : ''}{formatBytes(item?.used_bytes)}</strong></div>
    {item?.percent !== null && item?.percent !== undefined
      ? <LinearProgress aria-label={`${title} budget usage`} variant="determinate" value={Math.min(100, item.percent)} className={`mo-progress mo-${item.status}`} />
      : <div className="mo-unknown-meter" aria-label={`${title} limit unverified`} />}
    <div className="mo-small"><span>{item?.budget_bytes ? `${formatBytes(item.remaining_bytes)} remaining of ${formatBytes(item.budget_bytes)} budget` : 'Limit unverified · set a capacity budget'}</span>
      <span className={`mo-status mo-${item?.status || 'unknown'}`}>{item?.percent != null ? `${item.percent}%` : 'Unknown headroom'}</span></div>
    <small>{item?.measured_at ? `Measured ${when(item.measured_at)}` : 'Not measured yet'}</small>
    {item?.projected_days_remaining !== null && item?.projected_days_remaining !== undefined && <small>Estimated {item.projected_days_remaining} days of headroom at measured growth</small>}
  </div>;
}

export default function MediaOperations() {
  const { callApi } = useApi();
  const api = useRef(callApi);
  api.current = callApi;
  const mounted = useRef(false);
  const loadingRef = useRef(false);
  const dirty = useRef(false);
  const actionRef = useRef(false);
  const revision = useRef(0);
  const reloadQueued = useRef(false);
  const refreshRef = useRef(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [selection, setSelection] = useState(null);
  const [ids, setIds] = useState(() => new URLSearchParams(window.location.search).get('products') || '');
  const [form, setForm] = useState(null);

  const refresh = useCallback(async () => {
    if (loadingRef.current) { reloadQueued.current = true; return; }
    loadingRef.current = true;
    const requestedRevision = revision.current;
    try {
      const response = await api.current({ url: API, silent: true, rawError: true, timeout: 25000 });
      if (!mounted.current) return;
      if (requestedRevision !== revision.current) { reloadQueued.current = true; return; }
      if (response?.status !== 200 || !unwrap(response)) throw new Error(failure(response));
      const snapshot = unwrap(response);
      setData(snapshot);
      if (!dirty.current) setForm(policyForm(snapshot.policy));
      setError('');
    } catch (problem) {
      if (mounted.current) setError(problem.message || 'Operations are unavailable. Retry to refresh.');
    } finally {
      loadingRef.current = false;
      if (mounted.current) setLoading(false);
      if (mounted.current && reloadQueued.current) { reloadQueued.current = false; refreshRef.current?.(); }
    }
  }, []);
  refreshRef.current = refresh;

  useEffect(() => {
    mounted.current = true;
    refresh();
    const timer = setInterval(() => { if (document.visibilityState === 'visible' && !actionRef.current) refresh(); }, 30000);
    return () => { mounted.current = false; clearInterval(timer); };
  }, [refresh]);

  const action = async (options, success) => {
    if (actionRef.current) return;
    actionRef.current = true;
    revision.current += 1;
    setBusy(true); setActionError(''); setMessage('');
    try {
      const response = await api.current({ ...options, silent: true, rawError: true, timeout: 25000 });
      if (!response || response.status < 200 || response.status >= 300) throw new Error(failure(response));
      if (mounted.current) { setMessage(success); await refresh(); }
    } catch (problem) {
      if (mounted.current) setActionError(problem.message || 'Action could not be completed.');
    } finally {
      actionRef.current = false;
      if (mounted.current) setBusy(false);
    }
  };
  const patch = (body, success) => action({ url: API, method: 'PATCH', body }, success);
  const update = (name, value) => { dirty.current = true; setForm((previous) => ({ ...previous, [name]: value })); };
  const saveAlerts = (event) => {
    event.preventDefault();
    patch({ whatsapp_admin_number: form.whatsapp_admin_number, whatsapp_template: form.whatsapp_template,
      whatsapp_language: form.whatsapp_language }, 'WhatsApp settings saved. Approved Meta templates and a connected worker are required.');
  };
  const saveBudgets = (event) => {
    event.preventDefault();
    patch({ database_budget_bytes: form.database_budget === '' ? null : Math.round(Number(form.database_budget) * 1024 ** 2),
      object_budget_bytes: form.object_budget === '' ? null : Math.round(Number(form.object_budget) * 1024 ** 2),
      budget_note: form.budget_note }, 'Capacity budgets saved. These are operator-entered limits.');
  };
  const productIds = [...new Set(ids.split(/[\s,]+/).filter(Boolean).map(Number))];
  const validIds = productIds.length > 0 && productIds.length <= 100 && productIds.every((id) => Number.isSafeInteger(id) && id > 0);
  const jobs = data?.jobs || [];
  const selected = jobs.find((job) => job.id === selection) || jobs[0];
  const capacity = data?.capacity;
  const worker = data?.worker;
  const workerReady = worker && !worker.stale && ['healthy', 'processing'].includes(worker.status);

  if (loading && !data) return <div className="mo-loading"><CircularProgress aria-label="Loading media operations" /></div>;
  return <div className="media-ops">
    <div className="mo-toolbar"><p>Product image consistency, measured storage and order alerts</p><Button startIcon={<Refresh />} onClick={refresh} disabled={busy}>Refresh</Button></div>
    {error && <Alert severity="warning">{error}{data ? ' Showing the last received snapshot.' : ''}</Alert>}
    {actionError && <Alert severity="error">{actionError}</Alert>}
    {message && <Alert severity="success">{message}</Alert>}
    {!data ? <Button onClick={refresh}>Retry operations</Button> : <div className="mo-layout">
      <div className="mo-main">
        <section className="mo-panel" aria-labelledby="mo-images-title">
          <header className="mo-panel-header"><div className="mo-heading"><AutoFixHigh /><div><h2 id="mo-images-title">Image background removal</h2><p>Consistent white canvas · originals retained</p></div></div>
            <FormControlLabel control={<Switch size="small" checked={data.policy.auto_clean_images} disabled={busy} onChange={(_, checked) => patch({ auto_clean_images: checked }, checked ? 'New product photos will be queued automatically.' : 'Automatic queueing paused. Existing queued work is retained.')} />} label="Auto-clean imports" /></header>
          <div className="mo-photo-pair">{[{ name: 'Before · source', url: selected?.original_url }, { name: 'After · cleaned', url: selected?.output_url }].map((photo) => <figure key={photo.name}>
            <figcaption>{photo.name}</figcaption><div className={`mo-photo ${photo.url ? '' : 'mo-photo-empty'}`}>
              {photo.url ? <img src={photo.url} alt={`${photo.name}: ${selected.product_name}`} width="1200" height="1200" loading="lazy" /> : <p>{selected ? 'The preview appears after processing.' : 'Queue product photos to see the original and cleaned result.'}</p>}
            </div></figure>)}</div>
          {selected && <div className="mo-preview-caption"><strong>{selected.product_name} · #{selected.product_id}</strong><span className={`mo-status mo-${selected.status}`}>{statusLabel(selected.status)}</span></div>}
          <div className="mo-panel-body"><form className="mo-queue-form" onSubmit={(event) => { event.preventDefault(); if (validIds) action({ url: `${API}images/`, method: 'POST', body: { product_ids: productIds } }, 'Photo request recorded. View the queue for current status; completed photos are kept.'); }}>
            <TextField label="Existing product IDs" placeholder="101, 102, 103" size="small" value={ids} onChange={(event) => setIds(event.target.value)} helperText="Select products in the catalog, or enter up to 100 IDs." />
            <Button variant="contained" type="submit" disabled={!validIds || busy} startIcon={<AutoFixHigh />}>Queue existing photos</Button>
          </form></div>
          <div className="mo-note">Background cleanup preserves product details. It cannot guarantee watermark removal; uncertain cutouts stay in review.</div>
        </section>
        <section className="mo-panel" aria-labelledby="mo-queue-title"><header className="mo-panel-header"><div><h2 id="mo-queue-title">Processing queue</h2><p>Latest 50 photos · {Object.entries(data.queue_counts).map(([key, count]) => `${count} ${key}`).join(' · ') || 'No jobs yet'}</p></div><span className={`mo-status ${workerReady ? 'mo-completed' : 'mo-review'}`}>{workerReady ? 'Worker connected' : 'Worker needs attention'}</span></header>
          {!workerReady && <div className="mo-note">{worker?.detail || 'No recent worker heartbeat. Jobs remain queued until a persistent worker connects.'}{worker?.stale ? ' Heartbeat is stale.' : ''} Last seen: {when(worker?.updated_at)}</div>}
          <div className="mo-table-wrap"><table><thead><tr><th>Product / photo</th><th>Status</th><th>Attempts</th><th>Action</th></tr></thead><tbody>{jobs.map((job) => <tr key={job.id} className={selected?.id === job.id ? 'mo-selected' : ''}>
            <td><button className="mo-select" onClick={() => setSelection(job.id)}>#{job.product_id} · {job.product_name}<small>Photo {job.slot + 1}</small></button></td><td><span className={`mo-status mo-${job.status}`}>{statusLabel(job.status)}</span>{job.error && <small>{job.error}</small>}</td><td>{job.attempts}/3</td><td>
              {job.status === 'completed' && <Button size="small" disabled={busy} startIcon={<Restore />} onClick={() => action({ url: `${API}images/${job.id}/restore/`, method: 'POST' }, 'Original photo restored.')}>Restore original</Button>}
              {['failed', 'review'].includes(job.status) && <Button size="small" disabled={busy} onClick={() => action({ url: `${API}images/${job.id}/retry/`, method: 'POST' }, 'Photo queued for retry.')}>Retry cleanup</Button>}
            </td></tr>)}</tbody></table>{!jobs.length && <p className="mo-empty">No photo jobs yet. New products queue automatically when auto-clean is on.</p>}</div>
        </section>
      </div>
      <aside className="mo-sidebar" aria-label="Storage and notification settings">
        <section className="mo-panel"><header className="mo-panel-header"><div><h2>Measured storage</h2><p>Usage and capacity provenance</p></div></header><div className="mo-panel-body">
          <Usage title="PostgreSQL total" item={capacity.database} /><Usage title={capacity.object_provider || 'Object storage'} item={capacity.object_storage} />
          <dl className="mo-facts"><div><dt>Database image payload</dt><dd>{formatBytes(capacity.database_image_bytes)}</dd></div><div><dt>Current image write destination</dt><dd>{capacity.storage_backend === 'object' ? capacity.object_provider || 'Object storage' : 'PostgreSQL blobs'}</dd></div><div><dt>Catalog image references</dt><dd>{capacity.image_locations.database} database · {capacity.image_locations.object} object · {capacity.image_locations.external} external</dd></div><div><dt>Object writes tracked since activation</dt><dd>{formatBytes(capacity.tracked_object_bytes)}</dd></div></dl>
          {capacity.stale && <Alert severity="info">Object inventory and growth history need a recent worker snapshot.</Alert>}
          <details className="mo-details"><summary>Set capacity budgets</summary>{form && <form className="mo-settings" onSubmit={saveBudgets}>
            <TextField size="small" label="Database limit / budget (MiB)" type="number" inputProps={{ min: 1, step: 'any' }} value={form.database_budget} onChange={(event) => update('database_budget', event.target.value)} />
            <TextField size="small" label="Object storage budget (MiB)" type="number" inputProps={{ min: 1, step: 'any' }} value={form.object_budget} onChange={(event) => update('object_budget', event.target.value)} />
            <TextField size="small" label="Plan / quota source note" value={form.budget_note} inputProps={{ maxLength: 200 }} onChange={(event) => update('budget_note', event.target.value)} />
            <p>Enter a limit from your current provider plan or a chosen spending budget. Blank means unverified. R2 free allowance is not a hard capacity limit.</p><Button type="submit" variant="outlined" disabled={busy}>Save capacity budgets</Button>
          </form>}</details><p className="mo-advice">{capacity.recommendation}</p>
        </div></section>
        <section className="mo-panel"><header className="mo-panel-header"><div className="mo-heading"><WhatsApp /><div><h2>WhatsApp order alerts</h2><p>New-order notifications to your admin number</p></div></div></header><div className="mo-panel-body">
          <FormControlLabel control={<Switch checked={data.policy.whatsapp_enabled} disabled={busy} onChange={(_, checked) => patch({ whatsapp_enabled: checked }, 'Order-alert setting saved.')} />} label="Enable new-order alerts" />
          <Alert severity={data.whatsapp.configured ? 'info' : 'warning'}>{data.whatsapp.configured ? 'Cloud API credentials are present. The template must be approved by Meta.' : 'Meta Cloud API credentials are missing. Alerts stay queued until configured.'}</Alert>
          {form && <form className="mo-settings" onSubmit={saveAlerts}>
            <TextField label="Admin WhatsApp number" size="small" required inputProps={{ pattern: '[1-9][0-9]{7,14}', inputMode: 'tel' }} helperText="International digits only, without +" value={form.whatsapp_admin_number} onChange={(event) => update('whatsapp_admin_number', event.target.value)} />
            <TextField label="Approved template name" size="small" required value={form.whatsapp_template} onChange={(event) => update('whatsapp_template', event.target.value)} />
            <TextField label="Template language" size="small" required value={form.whatsapp_language} onChange={(event) => update('whatsapp_language', event.target.value)} />
            <Button type="submit" variant="outlined" disabled={busy}>Save WhatsApp settings</Button>
          </form>}
          <p className="mo-advice">Accepted means Meta received the request. Delivery is confirmed by signed callbacks. Unconfirmed sends are held for review to avoid duplicates.</p>
          <p className="mo-small">Order alert worker: {data.whatsapp.worker && !data.whatsapp.worker.stale && data.whatsapp.worker.status === 'healthy' ? 'Connected · independent of image cleanup' : 'No healthy recent heartbeat'}</p>
          <p className="mo-small">Signed delivery callback: {data.whatsapp.webhook_configured ? 'Credentials present; verify subscription in Meta' : 'Not configured'}</p>
          <details className="mo-details"><summary>Recent order alerts ({data.whatsapp.alerts.length})</summary><ul className="mo-alerts">{data.whatsapp.alerts.map((alert) => <li key={alert.id}><strong>{alert.order_number}</strong><span className={`mo-status mo-${alert.status}`}>{statusLabel(alert.status)}</span><small>{when(alert.created_at)} · {alert.attempts} attempts</small>{alert.error && <p>{alert.error}</p>}</li>)}{!data.whatsapp.alerts.length && <li>No new-order alerts have been queued yet.</li>}</ul></details>
        </div></section>
      </aside>
    </div>}
    <footer className="mo-footer">Snapshot received {when(data?.measured_at)} · Refreshes every 30 seconds while visible</footer>
  </div>;
}
