// Which route plays a background video. Only the landing page does: data pages stay static
// so their first load is the data itself, not tens of megabytes of decorative footage (SP-30).

export const HOME_BACKGROUND_VIDEO = '/blackhole.mp4';

export function backgroundVideoFor(pathname: string): string | null {
  return pathname === '/' ? HOME_BACKGROUND_VIDEO : null;
}
