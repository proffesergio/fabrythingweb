import React from 'react';
import { Alert, Box, Button, Card, CardContent, Chip, Grid, LinearProgress, Skeleton, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

// Shared building blocks for the three module overview dashboards.
// All widgets are theme-aware (no hardcoded light/dark colors) and share one
// loading / error / empty contract via WidgetState.

export const fmtBDT = (n) => `৳${Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
export const fmtNum = (n) => Number(n || 0).toLocaleString('en-US');

export function DeltaChip({ value, suffix = '%', invert = false }) {
  if (value === null || value === undefined) {
    return <Chip size="small" label="—" variant="outlined" />;
  }
  const good = invert ? value < 0 : value >= 0;
  return (
    <Chip
      size="small"
      label={`${value > 0 ? '▲' : value < 0 ? '▼' : ''} ${Math.abs(value)}${suffix}`}
      color={good ? 'success' : 'error'}
      variant="outlined"
    />
  );
}

export function Spark({ data, color = '#1976d2', height = 44 }) {
  if (!data || data.length === 0) return <Box sx={{ height }} />;
  return (
    <Box sx={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
          <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1.75} fill={color} fillOpacity={0.18} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </Box>
  );
}

export function WidgetState({ loading, error, empty, onRetry, height = 180 }) {
  if (loading) {
    return (
      <Box sx={{ p: 2 }}>
        <Skeleton variant="rectangular" height={height} sx={{ borderRadius: 2 }} />
      </Box>
    );
  }
  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="warning" action={<Button size="small" onClick={onRetry}>Retry</Button>}>
          Couldn't load this panel — the server may be waking up.
        </Alert>
      </Box>
    );
  }
  if (empty) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">Nothing here yet.</Typography>
      </Box>
    );
  }
  return null;
}

export function KpiCard({ label, value, delta, spark, color = '#1976d2', onClick }) {
  const inner = (
    <Card variant="outlined" sx={{ height: '100%', ...(onClick ? { cursor: 'pointer' } : {}) }}>
      <CardContent sx={{ pb: '12px !important' }}>
        <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.6 }}>
          {label}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mt: 0.5, flexWrap: 'wrap' }}>
          <Typography variant="h5" fontWeight={900}>{value}</Typography>
          <DeltaChip value={delta} />
        </Box>
        <Box sx={{ mt: 1 }}>
          <Spark data={(spark || []).map((p) => ({ v: p.total ?? p.count ?? p.v ?? 0 }))} color={color} />
        </Box>
      </CardContent>
    </Card>
  );
  return onClick ? <Box onClick={onClick}>{inner}</Box> : inner;
}

export function TrendPanel({ title, subtitle, data, dataKey = 'total', range, onRange, color = '#1976d2', formatY }) {
  return (
    <Card variant="outlined" sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, flexWrap: 'wrap' }}>
          <Typography variant="subtitle1" fontWeight={800}>{title}</Typography>
          <Box sx={{ flex: 1 }} />
          {onRange && [14, 30].map((d) => (
            <Button
              key={d} size="small" variant={range === d ? 'contained' : 'outlined'}
              onClick={() => onRange(d)}
            >
              {d === 14 ? 'Weeks' : 'Monthly'}
            </Button>
          ))}
        </Box>
        {subtitle && <Typography variant="caption" color="text.secondary">{subtitle}</Typography>}
        <Box sx={{ height: 260, mt: 1 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data || []} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.35} />
              <XAxis dataKey="day" tickFormatter={(d) => String(d || '').slice(5)} tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis tickFormatter={(v) => (formatY ? formatY(v) : v)} tick={{ fontSize: 11 }} width={52} />
              <Tooltip formatter={(v) => (formatY ? formatY(v) : v)} labelFormatter={(d) => `Day ${d}`} />
              <Area type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2.25} fill={color} fillOpacity={0.16} />
            </AreaChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}

export function TopItems({ title, items, actionLabel, onAction, valueLabel = 'Total' }) {
  const max = Math.max(1, ...(items || []).map((i) => i.value || 0));
  return (
    <Card variant="outlined" sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle1" fontWeight={800}>{title}</Typography>
          <Box sx={{ flex: 1 }} />
          {actionLabel && <Button size="small" onClick={onAction}>{actionLabel}</Button>}
        </Box>
        {(items || []).map((it, i) => (
          <Box key={i} sx={{ py: 1, borderBottom: i < items.length - 1 ? '1px solid' : 'none', borderColor: 'divider' }}>
            <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
              <Typography variant="body2" fontWeight={700} sx={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {it.name}
              </Typography>
              <Typography variant="body2" fontWeight={800}>{it.display}</Typography>
            </Box>
            {it.sub && <Typography variant="caption" color="text.secondary">{it.sub}</Typography>}
            <LinearProgress
              variant="determinate" value={Math.min(100, ((it.value || 0) / max) * 100)}
              sx={{ height: 6, borderRadius: 3, mt: 0.5 }}
            />
          </Box>
        ))}
        {(!items || items.length === 0) && (
          <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
            Nothing here yet.
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

export function RecentTable({ title, columns, rows, viewAllTo, viewAllLabel = 'View all' }) {
  return (
    <Card variant="outlined" sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle1" fontWeight={800}>{title}</Typography>
          <Box sx={{ flex: 1 }} />
          {viewAllTo && (
            <Button size="small" component={Link} to={viewAllTo}>{viewAllLabel} →</Button>
          )}
        </Box>
        {(rows || []).map((r, i) => (
          <Box
            key={i}
            sx={{
              display: 'flex', gap: 1.5, alignItems: 'center', py: 1,
              borderBottom: i < rows.length - 1 ? '1px solid' : 'none', borderColor: 'divider',
            }}
          >
            {columns.map((c) => (
              <Box key={c.key} sx={{ flex: c.flex || 1, textAlign: c.align || 'left', minWidth: 0 }}>
                {c.render ? c.render(r) : (
                  <Typography variant="body2" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {r[c.key]}
                  </Typography>
                )}
              </Box>
            ))}
          </Box>
        ))}
        {(!rows || rows.length === 0) && (
          <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
            Nothing here yet.
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

export function StatTrio({ items }) {
  return (
    <Grid container spacing={2}>
      {(items || []).map((s, i) => (
        <Grid item xs={12} sm={4} key={i}>
          <Card variant="outlined">
            <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box sx={{ width: 44, height: 44, borderRadius: 2, bgcolor: `${s.color}22`, color: s.color, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900 }}>
                ৳
              </Box>
              <Box>
                <Typography variant="h6" fontWeight={900}>{s.value}</Typography>
                <Typography variant="caption" color="text.secondary">{s.label}</Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}

export function AlertRow({ severity = 'warning', children, actionLabel, onAction, to }) {
  return (
    <Alert
      severity={severity}
      sx={{ mb: 1.25 }}
      action={
        actionLabel && (
          <Button size="small" {...(to ? { component: Link, to } : { onClick: onAction })}>
            {actionLabel}
          </Button>
        )
      }
    >
      {children}
    </Alert>
  );
}
