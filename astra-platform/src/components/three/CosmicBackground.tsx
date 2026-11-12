'use client';

import { useEffect, useRef } from 'react';
import { usePathname } from 'next/navigation';
import { useAstraStore } from '@/lib/store';
import { prefersSavedData, usePageSettled, usePrefersReducedMotion } from '@/lib/hooks/useMotionPreferences';
import { backgroundVideoFor } from './backgroundVideo';

// Decorative backdrop behind every page, hidden from assistive technology. The dark layers
// below double as the poster: they are what every visitor sees until (and unless) the video
// starts.
export function CosmicBackground() {
  const pathname = usePathname();
  const { qualityState } = useAstraStore();
  const reducedMotion = usePrefersReducedMotion();
  const settled = usePageSettled();
  const videoRef = useRef<HTMLVideoElement>(null);

  const videoSrc = backgroundVideoFor(pathname);
  // The video loads only after the page itself has, and never for visitors who asked for
  // reduced motion or less data, or who chose the "low" graphics setting.
  const playVideo = videoSrc !== null && qualityState !== 'low' && settled && !reducedMotion && !prefersSavedData();

  useEffect(() => {
    videoRef.current?.play().catch(() => {
      // Autoplay refused: the static backdrop stays, which is fine.
    });
  }, [playVideo, videoSrc]);

  return (
    <div aria-hidden="true" className="fixed inset-0 z-0 pointer-events-none bg-[#05070B] overflow-hidden">
      {playVideo && videoSrc && (
        <video
          ref={videoRef}
          key={videoSrc}
          autoPlay
          loop
          muted
          playsInline
          preload="auto"
          className="absolute inset-0 w-full h-full object-cover scale-[1.03]"
          style={{ filter: 'brightness(0.30) blur(3px) saturate(0.6)' }}
        >
          <source src={videoSrc} type="video/mp4" />
        </video>
      )}
      {/* 75% Dark overlay & Vignette */}
      <div className="absolute inset-0 bg-[#05070B]/75" />
      <div className="absolute inset-0 bg-gradient-to-t from-[#05070B] via-transparent to-[#05070B]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_30%,#05070B_95%)]" />
    </div>
  );
}
