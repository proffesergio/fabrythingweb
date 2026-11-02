import { useMemo, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Typography, FormGroup,
  FormControlLabel, Checkbox, Radio, RadioGroup, Box, Button, IconButton,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RemoveIcon from '@mui/icons-material/Remove';

export default function ItemOptionModal({ open, item, restaurant, onClose, onAdd }) {
  const [selected, setSelected] = useState({}); // groupId -> Set(optionId)
  const [qty, setQty] = useState(1);

  const flatOptions = useMemo(() => {
    const map = {};
    (item?.option_groups || []).forEach((g) => g.options.forEach((o) => { map[o.id] = { ...o, groupId: g.id }; }));
    return map;
  }, [item]);

  if (!item) return null;

  const toggle = (group, optId) => {
    setSelected((prev) => {
      const cur = new Set(prev[group.id] || []);
      if (group.max_select === 1) { cur.clear(); cur.add(optId); }
      else if (cur.has(optId)) cur.delete(optId);
      else if (cur.size < group.max_select) cur.add(optId);
      return { ...prev, [group.id]: cur };
    });
  };

  const missingRequired = (item.option_groups || []).some(
    (g) => g.is_required && (!selected[g.id] || selected[g.id].size < Math.max(1, g.min_select))
  );

  const submit = () => {
    const optionIds = Object.values(selected).flatMap((s) => Array.from(s));
    const selectedOptions = optionIds.map((id) => ({
      optionId: id, name: flatOptions[id].name, priceDelta: Number(flatOptions[id].price_delta),
    }));
    onAdd({
      lineId: `${item.id}:${optionIds.slice().sort((a, b) => a - b).join('-')}`,
      restaurantId: restaurant.id, restaurantSlug: restaurant.slug, restaurantName: restaurant.display_name,
      itemId: item.id, name: item.display_name, image: item.image || '',
      unitPrice: Number(item.effective_price ?? item.price), quantity: qty, selectedOptions,
    });
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>{item.display_name}</DialogTitle>
      <DialogContent dividers>
        {(item.option_groups || []).map((g) => (
          <Box key={g.id} sx={{ mb: 2 }}>
            <Typography variant="subtitle2">{g.name}{g.is_required ? ' *' : ''}</Typography>
            {g.max_select === 1 ? (
              <RadioGroup>
                {g.options.map((o) => (
                  <FormControlLabel
                    key={o.id}
                    control={<Radio checked={!!selected[g.id]?.has(o.id)} onChange={() => toggle(g, o.id)} />}
                    label={`${o.name}${Number(o.price_delta) ? ` +৳${o.price_delta}` : ''}`}
                  />
                ))}
              </RadioGroup>
            ) : (
              <FormGroup>
                {g.options.map((o) => (
                  <FormControlLabel
                    key={o.id}
                    control={<Checkbox checked={!!selected[g.id]?.has(o.id)} onChange={() => toggle(g, o.id)} />}
                    label={`${o.name}${Number(o.price_delta) ? ` +৳${o.price_delta}` : ''}`}
                  />
                ))}
              </FormGroup>
            )}
          </Box>
        ))}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <IconButton onClick={() => setQty((q) => Math.max(1, q - 1))}><RemoveIcon /></IconButton>
          <Typography>{qty}</Typography>
          <IconButton onClick={() => setQty((q) => q + 1)}><AddIcon /></IconButton>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="inherit">Cancel</Button>
        <Button variant="contained" onClick={submit} disabled={missingRequired}>Add to cart</Button>
      </DialogActions>
    </Dialog>
  );
}
