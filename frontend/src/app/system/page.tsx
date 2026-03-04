'use client';

import { useHealth, useCacheStats } from '@/hooks/use-api';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { LoadingScreen } from '@/components/ui/spinner';
import { Activity, Database, HardDrive, Clock, Server, Cpu } from 'lucide-react';

export default function SystemPage() {
    const { data: health, isLoading: healthLoading } = useHealth();
    const { data: cacheStats, isLoading: cacheLoading, refetch: refetchCache } = useCacheStats();

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">System</h1>
                <p className="text-muted-foreground">Backend health, cache statistics, and configuration.</p>
            </div>

            {/* Health check */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                        <Server className="h-4 w-4" />
                        API Health
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {healthLoading ? (
                        <LoadingScreen message="Checking API..." />
                    ) : (
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2">
                                <div
                                    className={`h-3 w-3 rounded-full ${health?.status === 'ok' ? 'bg-emerald-500' : 'bg-red-500'
                                        }`}
                                />
                                <span className="text-sm font-medium">
                                    {health?.status === 'ok' ? 'Connected' : 'Unavailable'}
                                </span>
                            </div>
                            {health?.version && (
                                <Badge variant="outline">v{health.version}</Badge>
                            )}
                            <Badge
                                variant={health?.status === 'ok' ? 'success' : 'destructive'}
                            >
                                {health?.status || 'unknown'}
                            </Badge>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Cache stats */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-base flex items-center gap-2">
                            <Database className="h-4 w-4" />
                            Cache Statistics
                        </CardTitle>
                        <button
                            onClick={() => refetchCache()}
                            className="text-xs text-muted-foreground hover:text-foreground"
                        >
                            Refresh
                        </button>
                    </div>
                </CardHeader>
                <CardContent>
                    {cacheLoading ? (
                        <LoadingScreen message="Loading cache stats..." />
                    ) : cacheStats ? (
                        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                            {Object.entries(cacheStats).map(([key, value]) => (
                                <div key={key} className="rounded-lg border p-3">
                                    <p className="text-xs text-muted-foreground">{key.replace(/_/g, ' ')}</p>
                                    <p className="text-lg font-bold">
                                        {typeof value === 'number' ? value.toLocaleString() : String(value)}
                                    </p>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm text-muted-foreground">No cache data available.</p>
                    )}
                </CardContent>
            </Card>

            {/* Info */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                        <Cpu className="h-4 w-4" />
                        Configuration
                    </CardTitle>
                    <CardDescription>Connection details for this instance.</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-3 sm:grid-cols-2">
                        <div className="rounded-lg border p-3">
                            <p className="text-xs text-muted-foreground">Backend URL</p>
                            <p className="text-sm font-mono">
                                {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
                            </p>
                        </div>
                        <div className="rounded-lg border p-3">
                            <p className="text-xs text-muted-foreground">Frontend</p>
                            <p className="text-sm font-mono">http://localhost:3000</p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
