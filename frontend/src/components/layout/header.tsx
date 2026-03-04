'use client';

import { Moon, Sun, Search, Activity } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAppStore } from '@/store/app-store';
import { useHealth } from '@/hooks/use-api';
import { cn } from '@/lib/utils';

export function Header() {
    const { theme, toggleTheme, sidebarOpen } = useAppStore();
    const { data: health } = useHealth();

    return (
        <header
            className={cn(
                'sticky top-0 z-40 flex h-16 items-center gap-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-6 transition-all duration-300',
                sidebarOpen ? 'ml-64' : 'ml-16'
            )}
        >
            {/* Search */}
            <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input placeholder="Search niches, reports..." className="pl-9 bg-muted/50" />
            </div>

            <div className="flex items-center gap-3 ml-auto">
                {/* Backend status */}
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Activity className="h-3 w-3" />
                    <span
                        className={cn(
                            'h-2 w-2 rounded-full',
                            health?.status === 'ok' ? 'bg-emerald-500' : 'bg-red-500'
                        )}
                    />
                    <span>{health?.status === 'ok' ? 'API Connected' : 'API Offline'}</span>
                    {health?.version && <span className="text-[10px]">v{health.version}</span>}
                </div>

                {/* Theme toggle */}
                <Button variant="ghost" size="icon" onClick={toggleTheme}>
                    {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                </Button>
            </div>
        </header>
    );
}
