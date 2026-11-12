import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { ChartFrame, describeSeries } from '@/components/shared/ChartFrame';

describe('describeSeries', () => {
  it('joins names and values', () => {
    expect(describeSeries([{ name: 'Cepheid', value: 230 }, { name: 'Stable', value: 205 }])).toBe('Cepheid 230, Stable 205');
  });

  it('applies a value format', () => {
    expect(describeSeries([{ name: 'RR Lyrae', value: 0.8123 }], (v) => v.toFixed(2))).toBe('RR Lyrae 0.81');
  });
});

describe('ChartFrame', () => {
  it('exposes the chart as an image with its description', () => {
    const html = renderToStaticMarkup(
      <ChartFrame label="Bar chart of stars per class: Cepheid 230." className="h-full">
        <svg />
      </ChartFrame>,
    );
    expect(html).toBe('<div role="img" aria-label="Bar chart of stars per class: Cepheid 230." class="h-full"><svg></svg></div>');
  });
});
