'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/store/app-store';
import {
    LayoutDashboard,
    Compass,
    Video,
    Image,
    FileText,
    Settings,
    Rocket,
    ChevronLeft,
    ChevronRight,
    TrendingUp,
} from 'lucide-react';

const navigation = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Discover Niches', href: '/discover', icon: Compass },
    { name: 'Video Strategy', href: '/strategy', icon: Video },
    { name: 'Thumbnail Insights', href: '/thumbnails', icon: Image },
    { name: 'Reports', href: '/reports', icon: FileText },
    { name: 'System', href: '/system', icon: Settings },
];

export function Sidebar() {
    const pathname = usePathname();
    const { sidebarOpen, toggleSidebar } = useAppStore();

    return (
        <aside
            className={cn(
                'fixed inset-y-0 left-0 z-50 flex flex-col border-r bg-card transition-all duration-300',
                sidebarOpen ? 'w-64' : 'w-16'
            )}
        >
            {/* Logo */}
            <div className="flex h-16 items-center gap-3 border-b px-4">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary">
                    <TrendingUp className="h-4 w-4 text-primary-foreground" />
                </div>
                {sidebarOpen && (
                    <div className="flex flex-col">
                        <span className="text-sm font-bold tracking-tight">Growth Strategist</span>
                        <span className="text-[10px] text-muted-foreground">YouTube Intelligence</span>
                    </div>
                )}
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-1 px-2 py-4">
                {navigation.map((item) => {
                    const isActive = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={cn(
                                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                                isActive
                                    ? 'bg-primary/10 text-primary'
                                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                            )}
                        >
                            <item.icon className="h-4 w-4 shrink-0" />
                            {sidebarOpen && <span>{item.name}</span>}
                        </Link>
                    );
                })}
            </nav>

            {/* Collapse toggle */}
            <div className="border-t p-2">
                <button
                    onClick={toggleSidebar}
                    className="flex w-full items-center justify-center rounded-lg p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                >
                    {sidebarOpen ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                </button>
            </div>
        </aside>
    );
}
