import type { UseQueryResult } from '@tanstack/react-query';

type QueryLike = Pick<UseQueryResult<unknown>, 'isLoading' | 'isError' | 'error' | 'refetch'>;

export interface CombinedQueryState {
  /** True while any query is still loading for the first time. */
  isLoading: boolean;
  /** True when any query failed. */
  isError: boolean;
  /** The first failure, for display. */
  error: unknown;
  /** Re-runs every failed query. */
  retry: () => void;
}

/** One loading/error answer for a view that needs several queries before it can render. */
export function combineQueries(queries: readonly QueryLike[]): CombinedQueryState {
  const failed = queries.filter((q) => q.isError);
  return {
    isLoading: queries.some((q) => q.isLoading),
    isError: failed.length > 0,
    error: failed[0]?.error ?? null,
    retry: () => {
      for (const q of failed) void q.refetch();
    },
  };
}
