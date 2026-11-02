import React, { useState, useEffect } from 'react';
import { Box, Typography } from '@mui/material';

function getTimeLeft(targetDate) {
    const diff = new Date(targetDate) - new Date();
    if (diff <= 0) return null;
    return {
        days: Math.floor(diff / (1000 * 60 * 60 * 24)),
        hours: Math.floor((diff / (1000 * 60 * 60)) % 24),
        minutes: Math.floor((diff / (1000 * 60)) % 60),
        seconds: Math.floor((diff / 1000) % 60),
    };
}

export default function CountdownTimer({ targetDate }) {
    const [timeLeft, setTimeLeft] = useState(() => getTimeLeft(targetDate));

    useEffect(() => {
        const timer = setInterval(() => {
            const tl = getTimeLeft(targetDate);
            if (!tl) clearInterval(timer);
            setTimeLeft(tl);
        }, 1000);
        return () => clearInterval(timer);
    }, [targetDate]);

    if (!timeLeft) return null;

    const units = [
        { label: 'Days', value: timeLeft.days },
        { label: 'Hrs', value: timeLeft.hours },
        { label: 'Min', value: timeLeft.minutes },
        { label: 'Sec', value: timeLeft.seconds },
    ];

    return (
        <Box sx={{ display: 'flex', gap: { xs: 0.5, sm: 1 }, alignItems: 'center' }}>
            {units.map((unit, i) => (
                <Box key={unit.label} sx={{ display: 'flex', alignItems: 'center', gap: { xs: 0.5, sm: 1 } }}>
                    <Box
                        sx={{
                            bgcolor: '#2D2D2D',
                            color: 'white',
                            borderRadius: 1.5,
                            minWidth: { xs: 40, sm: 52 },
                            py: { xs: 0.5, sm: 1 },
                            textAlign: 'center',
                        }}
                    >
                        <Typography variant="h6" sx={{ fontWeight: 800, fontSize: { xs: '1rem', sm: '1.3rem' }, lineHeight: 1.2 }}>
                            {String(unit.value).padStart(2, '0')}
                        </Typography>
                        <Typography variant="caption" sx={{ fontSize: { xs: '0.55rem', sm: '0.65rem' }, opacity: 0.7, textTransform: 'uppercase' }}>
                            {unit.label}
                        </Typography>
                    </Box>
                    {i < units.length - 1 && (
                        <Typography variant="h6" sx={{ fontWeight: 700, color: '#E85D4A', mx: 0 }}>:</Typography>
                    )}
                </Box>
            ))}
        </Box>
    );
}
