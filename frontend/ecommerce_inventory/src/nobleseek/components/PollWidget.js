import React, { useEffect, useState } from 'react';
import { Box, Button, LinearProgress, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import { fetchPolls, getPollSession, votePoll } from '../api';

// Homepage sidebar poll: vote once per browser, then live results.
export default function PollWidget() {
  const [polls, setPolls] = useState([]);
  const [voted, setVoted] = useState(() => {
    try { return JSON.parse(localStorage.getItem('ns_voted_polls') || '{}'); } catch { return {}; }
  });

  useEffect(() => { fetchPolls().then(setPolls).catch(() => {}); }, []);
  if (!polls.length) return null;
  const poll = polls[0];
  const hasVoted = !!voted[poll.id];

  const vote = async (optionId) => {
    try {
      const res = await votePoll(poll.id, optionId, getPollSession());
      if (res) {
        setPolls((prev) => prev.map((p) => (p.id === poll.id ? res : p)));
        const next = { ...voted, [poll.id]: true };
        setVoted(next);
        try { localStorage.setItem('ns_voted_polls', JSON.stringify(next)); } catch {}
      }
    } catch { /* 400 already-voted: just show results */ 
      setVoted((v) => ({ ...v, [poll.id]: true }));
    }
  };

  const max = Math.max(1, ...poll.options.map((o) => o.votes));

  return (
    <Box sx={{ border: '1px solid #e8e8e8', borderRadius: 2, bgcolor: '#fffdf5', p: 2 }}>
      <Typography variant="subtitle1" fontWeight={900} className="ns-serif" gutterBottom>
        আজকের জরিপ
      </Typography>
      <Typography variant="body2" fontWeight={700} className="ns-sans" sx={{ mb: 1 }}>
        {poll.question}
      </Typography>
      {hasVoted ? (
        <Box>
          {poll.options.map((o) => (
            <Box key={o.id} sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
              <Typography variant="body2" className="ns-sans" sx={{ minWidth: 90 }}>{o.text}</Typography>
              <LinearProgress variant="determinate" value={(o.votes / max) * 100} sx={{ flex: 1, height: 8, borderRadius: 4 }} />
              <Typography variant="caption" className="ns-sans" sx={{ minWidth: 44, textAlign: 'right' }}>{o.pct}%</Typography>
            </Box>
          ))}
          <Typography variant="caption" color="text.secondary" className="ns-sans">{poll.total} ভোট</Typography>
        </Box>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {poll.options.map((o) => (
            <Button key={o.id} variant="outlined" size="small" onClick={() => vote(o.id)} className="ns-sans" sx={{ justifyContent: 'flex-start' }}>
              {o.text}
            </Button>
          ))}
        </Box>
      )}
    </Box>
  );
}
