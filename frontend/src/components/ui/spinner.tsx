import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

interface SpinnerProps {
    className?: string;
    size?: number;
}

export function Spinner({ className, size = 24 }: SpinnerProps) {
    return <Loader2 className={cn('animate-spin text-muted-foreground', className)} size={size} />;
}

export function LoadingScreen({ message = 'Loading...' }: { message?: string }) {
    return (
        <div className="flex h-64 flex-col items-center justify-center gap-3">
            <Spinner size={32} />
            <p className="text-sm text-muted-foreground">{message}</p>
        </div>
    );
}

export function EmptyState({
    icon: Icon,
    title,
    description,
    children,
}: {
    icon?: React.ComponentType<{ className?: string; size?: number }>;
    title: string;
    description?: string;
    children?: React.ReactNode;
}) {
    return (
        <div className="flex h-64 flex-col items-center justify-center gap-3 text-center">
            {Icon && <Icon className="text-muted-foreground" size={48} />}
            <h3 className="text-lg font-semibold">{title}</h3>
            {description && <p className="max-w-md text-sm text-muted-foreground">{description}</p>}
            {children}
        </div>
    );
}
