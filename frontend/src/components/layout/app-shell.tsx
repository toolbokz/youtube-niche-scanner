'use client';

import { Sidebar } from './sidebar';
import { Header } from './header';
import { useAppStore } from '@/store/app-store';
import { cn } from '@/lib/utils';

export function AppShell({ children }: { children: React.ReactNode }) {
    const sidebarOpen = useAppStore((s) => s.sidebarOpen);

    return (
        <div className="min-h-screen bg-background text-foreground">
            <Sidebar />
            <div
                className={cn(
                    'flex flex-col transition-all duration-300',
                    sidebarOpen ? 'ml-64' : 'ml-16'
                )}
            >
                <Header />
                <main className="flex-1 p-6">{children}</main>
            </div>
        </div>
    );
}
