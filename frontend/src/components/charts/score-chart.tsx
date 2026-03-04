'use client';

import { memo } from 'react';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import type { NicheScore } from '@/types';

const COLORS = [
    'hsl(262, 83%, 58%)', // purple
    'hsl(221, 83%, 53%)', // blue
    'hsl(142, 71%, 45%)', // green
    'hsl(47, 96%, 53%)',  // yellow
    'hsl(0, 84%, 60%)',   // red
    'hsl(199, 89%, 48%)', // cyan
    'hsl(24, 95%, 53%)',  // orange
    'hsl(330, 81%, 60%)', // pink
];

interface ScoreChartProps {
    niches: NicheScore[];
    title?: string;
    dataKey?: keyof NicheScore;
    maxItems?: number;
}

export const ScoreDistributionChart = memo(function ScoreDistributionChart({
    niches,
    title = 'Opportunity Score Distribution',
    dataKey = 'overall_score',
    maxItems = 10,
}: ScoreChartProps) {
    const data = niches.slice(0, maxItems).map((n) => ({
        name: n.niche.length > 20 ? n.niche.substring(0, 20) + '…' : n.niche,
        value: Number(n[dataKey]) || 0,
    }));

    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">{title}</CardTitle>
            </CardHeader>
            <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={data} layout="vertical" margin={{ left: 0, right: 16, top: 5, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis type="number" domain={[0, 100]} className="text-xs" />
                        <YAxis
                            dataKey="name"
                            type="category"
                            width={130}
                            className="text-xs"
                            tick={{ fill: 'hsl(var(--muted-foreground))' }}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: 'hsl(var(--card))',
                                border: '1px solid hsl(var(--border))',
                                borderRadius: '8px',
                                color: 'hsl(var(--card-foreground))',
                            }}
                        />
                        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                            {data.map((_, i) => (
                                <Cell key={i} fill={COLORS[i % COLORS.length]} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
});
