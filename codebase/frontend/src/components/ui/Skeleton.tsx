import type { HTMLAttributes } from "react";

/**
 * Base pulsing placeholder block. Compose with width/height utility
 * classes to approximate the shape of the content being loaded.
 */
export function Skeleton({ className = "", ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse rounded-md bg-ink/[0.08] ${className}`}
      {...rest}
    />
  );
}

/**
 * Row-based skeleton matching the card + divided-list pattern used
 * throughout the app (see AdminUsersPage, OrdersPage, etc.). This is
 * the default loading placeholder for list/table-style screens.
 */
export function SkeletonList({ rows = 5 }: { rows?: number }) {
  return (
    <div
      role="status"
      aria-label="Loading content"
      className="rounded-lg border border-line bg-paper-raised divide-y divide-line"
    >
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center justify-between gap-3 px-5 py-3.5">
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3.5 w-1/3" />
            <Skeleton className="h-3 w-1/4" />
          </div>
          <Skeleton className="h-5 w-16 shrink-0 rounded-full" />
        </div>
      ))}
    </div>
  );
}

/**
 * Generic rectangular content placeholder for non-list screens such
 * as stat panels, charts, wallets and form-heavy detail pages.
 */
export function SkeletonBlock({ className = "h-40" }: { className?: string }) {
  return (
    <div
      role="status"
      aria-label="Loading content"
      className={`rounded-lg border border-line bg-paper-raised p-5 ${className}`}
    >
      <Skeleton className="h-full w-full" />
    </div>
  );
}
