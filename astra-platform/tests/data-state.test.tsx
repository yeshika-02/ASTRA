import { isValidElement, type ReactElement, type ReactNode } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { LoadError, PageError, PageLoading } from '@/components/shared/DataState';
import { combineQueries } from '@/lib/hooks/queryState';

/** Depth-first search of a rendered element tree for the first element of `type`. */
function findElement(node: ReactNode, type: string): ReactElement<Record<string, unknown>> | null {
  if (Array.isArray(node)) {
    for (const child of node) {
      const hit = findElement(child, type);
      if (hit) return hit;
    }
    return null;
  }
  if (!isValidElement<Record<string, unknown>>(node)) return null;
  if (node.type === type) return node;
  return findElement(node.props.children as ReactNode, type);
}

describe('PageLoading', () => {
  it('announces the page and its loading message', () => {
    const html = renderToStaticMarkup(<PageLoading title="Model Operations" message="Loading model data…" />);
    expect(html).toContain('<h1');
    expect(html).toContain('Model Operations');
    expect(html).toMatch(/role="status"[^>]*>Loading model data…/);
    expect(html).toContain('aria-busy="true"');
  });

  it('hides skeleton blocks from assistive technology', () => {
    const html = renderToStaticMarkup(<PageLoading title="T" message="M" cards={3} panels={2} />);
    expect(html.match(/aria-hidden="true"/g)).toHaveLength(2);
    expect(html.match(/h-24 astra-glass/g)).toHaveLength(3);
    expect(html.match(/h-64 astra-glass/g)).toHaveLength(2);
    expect(html).toContain('md:grid-cols-2');
  });

  it('can omit the card row', () => {
    const html = renderToStaticMarkup(<PageLoading title="T" message="M" cards={0} />);
    expect(html).not.toContain('h-24');
  });
});

describe('LoadError', () => {
  it('renders an alert with the title and the error message', () => {
    const html = renderToStaticMarkup(
      <LoadError title="Could not load dataset details" error={new Error('Dataset files not found.')} />,
    );
    expect(html).toContain('role="alert"');
    expect(html).toContain('Could not load dataset details');
    expect(html).toContain('Dataset files not found.');
    expect(html).toContain('nothing is shown in its place');
  });

  it('ignores thrown values that are not Errors', () => {
    const html = renderToStaticMarkup(<LoadError title="Failed" error={{ secret: 'x' }} />);
    expect(html).not.toContain('secret');
  });

  it('offers a retry button only when a handler is given', () => {
    expect(renderToStaticMarkup(<LoadError title="Failed" />)).not.toContain('<button');

    const onRetry = vi.fn();
    const tree = LoadError({ title: 'Failed', onRetry });
    const button = findElement(tree, 'button');
    expect(button?.props.type).toBe('button');
    (button?.props.onClick as () => void)();
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('has a compact variant without the explanation', () => {
    const html = renderToStaticMarkup(<LoadError title="Failed" compact />);
    expect(html).toContain('p-3');
    expect(html).not.toContain('nothing is shown in its place');
  });
});

describe('PageError', () => {
  it('keeps the page heading above the alert', () => {
    const html = renderToStaticMarkup(
      <PageError heading="Research Findings" title="Could not load research findings" onRetry={() => {}} />,
    );
    expect(html.indexOf('<h1')).toBeLessThan(html.indexOf('role="alert"'));
    expect(html).toContain('Research Findings');
    expect(html).toContain('Retry');
  });
});

describe('combineQueries', () => {
  const query = (state: Partial<{ isLoading: boolean; isError: boolean; error: Error | null }> = {}) => ({
    isLoading: false,
    isError: false,
    error: null as Error | null,
    refetch: vi.fn(() => Promise.resolve({} as never)),
    ...state,
  });

  it('is loading while any query loads', () => {
    expect(combineQueries([query(), query({ isLoading: true })]).isLoading).toBe(true);
    expect(combineQueries([query(), query()]).isLoading).toBe(false);
  });

  it('reports the first failure', () => {
    const first = new Error('first');
    const state = combineQueries([query(), query({ isError: true, error: first }), query({ isError: true, error: new Error('second') })]);
    expect(state.isError).toBe(true);
    expect(state.error).toBe(first);
  });

  it('retries only the failed queries', () => {
    const ok = query();
    const bad = query({ isError: true, error: new Error('x') });
    combineQueries([ok, bad]).retry();
    expect(bad.refetch).toHaveBeenCalledOnce();
    expect(ok.refetch).not.toHaveBeenCalled();
  });

  it('has no error when every query succeeded', () => {
    expect(combineQueries([query(), query()])).toMatchObject({ isError: false, error: null });
  });
});
