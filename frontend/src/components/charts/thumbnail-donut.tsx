'use client';

import { memo } from 'react';
import {
    PieChart,
    Pie,
    Cell,
    ResponsiveContainer,
    Tooltip,
    Legend,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

const COLORS = [
    'hsl(262, 83%, 58%)',
    'hsl(221, 83%, 53%)',
    'hsl(142, 71%, 45%)',
    'hsl(47, 96%, 53%)',
    'hsl(0, 84%, 60%)',
    'hsl(199, 89%, 48%)',
    'hsl(24, 95%, 53%)',
    'hsl(330, 81%, 60%)',
];

interface ThumbnailDonutProps {
    title: string;
    data: { name: string; value: number }[];
}

export const ThumbnailDonut = memo(function ThumbnailDonut({ title, data }: ThumbnailDonutProps) {
    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">{title}</CardTitle>
            </CardHeader>
            <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                        <Pie
                            data={data}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={90}
                            paddingAngle={3}
                            dataKey="value"
                        >
                            {data.map((_, i) => (
                                <Cell key={i} fill={COLORS[i % COLORS.length]} />
                            ))}
                        </Pie>
                        <Tooltip
                            contentStyle={{
                                backgroundColor: 'hsl(var(--card))',
                                border: '1px solid hsl(var(--border))',
                                borderRadius: '8px',
                                color: 'hsl(var(--card-foreground))',
                            }}
                        />
                        <Legend
                            formatter={(value) => (
                                <span style={{ color: 'hsl(var(--card-foreground))' }}>{value}</span>
                            )}
                        />
                    </PieChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
});
