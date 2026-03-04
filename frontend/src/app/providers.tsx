'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import { useAppStore } from '@/store/app-store';

export function Providers({ children }: { children: React.ReactNode }) {
    const [queryClient] = useState(
        () =>
            new QueryClient({
                defaultOptions: {
                    queries: {
                        staleTime: 5 * 60 * 1000,   // 5 min — cached data is fresh
                        gcTime: 30 * 60 * 1000,      // 30 min — keep unused cache in memory
                        retry: 1,
                        refetchOnWindowFocus: false,
                    },
                },
            })
    );

    const theme = useAppStore((s) => s.theme);

    useEffect(() => {
        const root = document.documentElement;
        root.classList.remove('light', 'dark');
        root.classList.add(theme);
    }, [theme]);

    return (
        <QueryClientProvider client={queryClient}>
            {children}
        </QueryClientProvider>
    );
}
