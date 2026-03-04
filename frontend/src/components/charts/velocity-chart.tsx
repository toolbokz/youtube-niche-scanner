'use client';

import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import type { TopicVelocityResult } from '@/types';
import { Badge } from '@/components/ui/badge';

interface VelocityChartProps {
    data: TopicVelocityResult;
    title?: string;
}

export function VelocityChart({ data, title }: VelocityChartProps) {
    const chartData = (data.weekly_volumes || []).map((wv) => ({
        week: wv.week,
        volume: wv.volume,
    }));

    const trendLabel =
        data.acceleration > 0.2 ? 'Accelerating' : data.acceleration < -0.2 ? 'Decelerating' : 'Stable';
    const trendVariant =
        data.acceleration > 0.2 ? 'success' : data.acceleration < -0.2 ? 'destructive' : 'secondary';

    return (
        <Card>
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium">{title || data.niche}</CardTitle>
                    <Badge variant={trendVariant as 'success' | 'destructive' | 'secondary'}>
                        {trendLabel}
                    </Badge>
                </div>
                <CardDescription>
                    Growth: {data.growth_rate?.toFixed(2)}x · Velocity: {data.velocity_score?.toFixed(0)}/100
                </CardDescription>
            </CardHeader>
            <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                    <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id="velocityGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="hsl(262, 83%, 58%)" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="hsl(262, 83%, 58%)" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="week" className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                        <YAxis className="text-xs" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: 'hsl(var(--card))',
                                border: '1px solid hsl(var(--border))',
                                borderRadius: '8px',
                                color: 'hsl(var(--card-foreground))',
                            }}
                        />
                        <Area
                            type="monotone"
                            dataKey="volume"
                            stroke="hsl(262, 83%, 58%)"
                            fill="url(#velocityGradient)"
                            strokeWidth={2}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
}
