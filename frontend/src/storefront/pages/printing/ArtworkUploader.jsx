import React, { useEffect, useRef, useState } from 'react';
import { Alert, Box, Button, Chip, LinearProgress, Stack, Typography } from '@mui/material';

const ACCEPTED = '.pdf,.ai,.psd,.eps,.tiff,.tif,.png,.jpeg,.jpg';

// Print-ready artwork upload + validation pipeline: type/size gate, aspect
// ratio vs the trim size, sub-300-DPI warning, and bleed (+3mm) / trim / safe
// zone bounding boxes drawn on canvas around the preview.
export function readImageDims(file) {
  return new Promise((resolve) => {
    if (!file.type.startsWith('image/')) { resolve(null); return; }
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => { resolve({ w: img.naturalWidth, h: img.naturalHeight }); URL.revokeObjectURL(url); };
    img.onerror = () => { resolve(null); URL.revokeObjectURL(url); };
    img.src = url;
  });
}

export function assessFile(file, dims, trim) {
  const warnings = [];
  const ext = (file.name.split('.').pop() || '').toLowerCase();
  const maxMb = trim.maxMb || 100;
  if (file.size > maxMb * 1024 * 1024) warnings.push(`exceeds the ${maxMb}MB limit`);
  if (dims && trim.width > 0 && trim.height > 0) {
    const trimRatio = Number(trim.width) / Number(trim.height);
    const fileRatio = dims.w / dims.h;
    if (Math.abs(fileRatio - trimRatio) / Math.max(trimRatio, 0.01) > 0.02) {
      warnings.push('aspect ratio does not match the selected print size');
    }
    const inches = trim.unit === 'ft' ? Number(trim.width) * 12 : trim.unit === 'mm' ? Number(trim.width) / 25.4 : Number(trim.width);
    if (inches > 0) {
      const dpi = dims.w / inches;
      if (dpi < 300) warnings.push(`~${Math.round(dpi)} DPI at print size — 300 DPI or higher is recommended`);
      return { warnings, dpi: Math.round(dpi * 10) / 10 };
    }
  }
  return { warnings, dpi: null };
}

function BleedPreview({ imageUrl, fileName }) {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width; const H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#f5f5f5';
    ctx.fillRect(0, 0, W, H);
    const drawGuides = (img) => {
      // Bleed area (+3mm ≈ 4% margin), trim line, safe zone (inset 7%).
      const m = Math.round(Math.min(W, H) * 0.04);
      const s = Math.round(Math.min(W, H) * 0.07);
      if (img) {
        const scale = Math.min((W - m * 2) / img.width, (H - m * 2) / img.height);
        const dw = img.width * scale; const dh = img.height * scale;
        ctx.drawImage(img, (W - dw) / 2, (H - dh) / 2, dw, dh);
      } else {
        ctx.fillStyle = '#9e9e9e';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(fileName || 'print file', W / 2, H / 2);
      }
      ctx.setLineDash([6, 4]);
      ctx.strokeStyle = '#d32f2f'; ctx.lineWidth = 2;
      ctx.strokeRect(m / 2, m / 2, W - m, H - m);
      ctx.setLineDash([]);
      ctx.strokeStyle = '#111'; ctx.lineWidth = 2;
      ctx.strokeRect(m, m, W - m * 2, H - m * 2);
      ctx.strokeStyle = '#2e7d32'; ctx.lineWidth = 1.5;
      ctx.strokeRect(m + s, m + s, W - (m + s) * 2, H - (m + s) * 2);
    };
    if (imageUrl) {
      const img = new Image();
      img.onload = () => drawGuides(img);
      img.onerror = () => drawGuides(null);
      img.src = imageUrl;
    } else {
      drawGuides(null);
    }
  }, [imageUrl, fileName]);
  return (
    <Box>
      <canvas ref={canvasRef} width={300} height={200} style={{ width: '100%', borderRadius: 8, border: '1px solid #e0e0e0' }} />
      <Stack direction="row" spacing={1} sx={{ mt: 0.5, flexWrap: 'wrap' }}>
        <Chip size="small" label="Bleed +3mm" sx={{ color: '#d32f2f', borderColor: '#d32f2f' }} variant="outlined" />
        <Chip size="small" label="Trim line" variant="outlined" />
        <Chip size="small" label="Safe zone" sx={{ color: '#2e7d32', borderColor: '#2e7d32' }} variant="outlined" />
      </Stack>
    </Box>
  );
}

export default function ArtworkUploader({ files, onChange, trim, uploadProgress }) {
  const [localWarnings, setLocalWarnings] = useState({});

  const addFiles = async (list) => {
    const incoming = Array.from(list || []).slice(0, 10 - files.length);
    const enriched = [];
    for (const file of incoming) {
      const dims = await readImageDims(file);
      const { warnings, dpi } = assessFile(file, dims, trim);
      enriched.push({
        file, name: file.name, size: file.size, contentType: file.type,
        widthPx: dims?.w || null, heightPx: dims?.h || null, dpi,
        previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
        preWarnings: warnings,
      });
    }
    setLocalWarnings((w) => {
      const next = { ...w };
      enriched.forEach((f, i) => { next[`${files.length + i}:${f.name}`] = f.preWarnings; });
      return next;
    });
    onChange([...files, ...enriched]);
  };

  const removeAt = (idx) => onChange(files.filter((_, i) => i !== idx));

  return (
    <Box>
      <Button variant="outlined" component="label" fullWidth sx={{ mb: 1 }}>
        Upload print-ready artwork (PDF, AI, PSD, EPS, TIFF, PNG, JPEG — up to {trim.maxMb || 100}MB each)
        <input type="file" hidden multiple accept={ACCEPTED} onChange={(e) => { addFiles(e.target.files); e.target.value = ''; }} />
      </Button>
      {Object.values(localWarnings).flat().length > 0 && (
        <Alert severity="warning" sx={{ mb: 1 }}>
          {Object.entries(localWarnings).filter(([, w]) => w.length).map(([k, w]) => (
            <Typography key={k} variant="caption" display="block">{k.split(':').slice(1).join(':')}: {w.join('; ')}</Typography>
          ))}
        </Alert>
      )}
      {files.map((f, i) => (
        <Box key={i} sx={{ mb: 2, p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="body2" fontWeight={700} sx={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {f.name}
            </Typography>
            {f.dpi && <Chip size="small" label={`${f.dpi} DPI`} color={f.dpi < 300 ? 'warning' : 'success'} />}
            <Button size="small" color="error" onClick={() => removeAt(i)}>Remove</Button>
          </Stack>
          <BleedPreview imageUrl={f.previewUrl} fileName={f.name} />
          {uploadProgress?.[i] != null && uploadProgress[i] < 100 && (
            <Box sx={{ mt: 1 }}>
              <LinearProgress variant="determinate" value={uploadProgress[i]} sx={{ height: 8, borderRadius: 4 }} />
              <Typography variant="caption" color="text.secondary">Uploading… {Math.round(uploadProgress[i])}%</Typography>
            </Box>
          )}
        </Box>
      ))}
      {files.length === 0 && (
        <Typography variant="caption" color="text.secondary">
          No artwork yet — you can order now and upload later from your order, but production starts after artwork review.
        </Typography>
      )}
    </Box>
  );
}
