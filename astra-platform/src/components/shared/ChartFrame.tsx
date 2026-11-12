import type { ReactNode } from 'react';

interface ChartFrameProps {
  /** One sentence a screen reader announces instead of the chart's SVG internals. */
  label: string;
  children: ReactNode;
  className?: string;
}

/** Gives a chart a text alternative (SP-29). Build the label from the same data the chart draws. */
export function ChartFrame({ label, children, className }: ChartFrameProps) {
  return (
    <div role="img" aria-label={label} className={className}>
      {children}
    </div>
  );
}

/** "A 1, B 2" for a chart label. */
export function describeSeries(
  items: readonly { name: string; value: number }[],
  format: (value: number) => string = String,
): string {
  return items.map((item) => `${item.name} ${format(item.value)}`).join(', ');
}
