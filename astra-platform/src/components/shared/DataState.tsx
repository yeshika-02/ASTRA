// Shared loading and error states for data views. Every page that fetches from the API shows
// the same skeleton while loading and the same alert, with a retry, when the request fails.
// Nothing is ever rendered in place of missing data.

import { cn } from '@/lib/utils';

interface PageLoadingProps {
  title: string;
  message: string;
  /** Metric-card placeholders in the first row. */
  cards?: number;
  /** Wide panel placeholders below the cards; two or more sit side by side on wide screens. */
  panels?: number;
}

export function PageLoading({ title, message, cards = 4, panels = 1 }: PageLoadingProps) {
  return (
    <div className="space-y-6" aria-busy="true">
      <div>
        <h1 className="text-xl font-semibold text-[#D7DEE7]">{title}</h1>
        <p role="status" className="text-[0.8125rem] text-[#8B97A7] mt-0.5 animate-pulse">
          {message}
        </p>
      </div>
      {cards > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse" aria-hidden="true">
          {Array.from({ length: cards }, (_, i) => (
            <div key={i} className="h-24 astra-glass rounded" />
          ))}
        </div>
      )}
      {panels > 0 && (
        <div
          className={cn('grid grid-cols-1 gap-6 animate-pulse', panels > 1 && 'md:grid-cols-2')}
          aria-hidden="true"
        >
          {Array.from({ length: panels }, (_, i) => (
            <div key={i} className="h-64 astra-glass rounded" />
          ))}
        </div>
      )}
    </div>
  );
}

interface LoadErrorProps {
  /** What failed, e.g. "Could not load dataset details". */
  title: string;
  /** The thrown value; its message is shown when it is an Error. API messages are generic. */
  error?: unknown;
  onRetry?: () => void;
  /** Smaller variant for lists and side panels. */
  compact?: boolean;
  className?: string;
}

export function LoadError({ title, error, onRetry, compact = false, className }: LoadErrorProps) {
  const detail = error instanceof Error && error.message ? error.message : null;
  return (
    <div
      role="alert"
      className={cn(
        'rounded border border-[#F85149]/30 bg-[#F85149]/5',
        compact ? 'p-3' : 'p-6',
        className,
      )}
    >
      <p className={cn('font-medium text-[#F85149]', compact ? 'text-[0.75rem]' : 'text-[0.875rem]')}>{title}</p>
      {detail && <p className="mt-1 text-[0.75rem] font-mono text-[#8B97A7] break-words">{detail}</p>}
      {!compact && (
        <p className="mt-1 text-[0.75rem] text-[#8B97A7]">
          The API did not return this data, so nothing is shown in its place.
        </p>
      )}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 px-3 py-1 bg-[#05070B] border border-[#1A2430] text-[#8B97A7] hover:text-[#D7DEE7] rounded text-[11px] transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#6EA8FE]"
        >
          Retry
        </button>
      )}
    </div>
  );
}
