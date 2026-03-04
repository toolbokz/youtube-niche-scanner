'use client';

import { memo } from 'react';
import {
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    Radar,
    ResponsiveContainer,
    Tooltip,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import type { NicheScore } from '@/types';

interface NicheRadarProps {
    niche: NicheScore;
}

export const NicheRadar = memo(function NicheRadar({ niche }: NicheRadarProps) {
    const data = [
        { metric: 'Demand', value: niche.demand_score },
        { metric: 'Low Competition', value: niche.competition_score },
        { metric: 'Trend', value: niche.trend_momentum },
        { metric: 'Virality', value: niche.virality_score },
        { metric: 'CTR', value: niche.ctr_potential },
        { metric: 'Velocity', value: niche.topic_velocity_score },
        { metric: 'Viral Opp', value: niche.viral_opportunity_score },
        { metric: 'Faceless', value: niche.faceless_viability },
    ];

    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Score Breakdown</CardTitle>
            </CardHeader>
            <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                    <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
                        <PolarGrid className="stroke-muted" />
                        <PolarAngleAxis
                            dataKey="metric"
                            className="text-xs"
                            tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                        />
                        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} />
                        <Radar
                            name="Score"
                            dataKey="value"
                            stroke="hsl(262, 83%, 58%)"
                            fill="hsl(262, 83%, 58%)"
                            fillOpacity={0.2}
                            strokeWidth={2}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: 'hsl(var(--card))',
                                border: '1px solid hsl(var(--border))',
                                borderRadius: '8px',
                                color: 'hsl(var(--card-foreground))',
                            }}
                        />
                    </RadarChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
});
