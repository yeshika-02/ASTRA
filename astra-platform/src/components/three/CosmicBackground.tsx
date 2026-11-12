'use client';

import React, { useRef, useEffect } from 'react';
import { useAstraStore } from '@/lib/store';
import { usePathname } from 'next/navigation';
import { backgroundVideoFor } from './backgroundVideo';

export function CosmicBackground() {
  const pathname = usePathname();
  const { qualityState } = useAstraStore();
  const videoRef = useRef<HTMLVideoElement>(null);

  // Programmatically trigger video playback to guarantee autoplay is active
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.play().catch((err) => {
        console.warn("Autoplay block or video load failure: ", err);
      });
    }
  }, [pathname]);

  // No hooks below this early return: switching quality to 'low' at runtime must not
  // change the number of hooks rendered (React error #300 crashed the page before).
  if (qualityState === 'low') {
    return (
      <div className="fixed inset-0 z-0 bg-[#05070B] pointer-events-none" />
    );
  }

  const opacity = 1.0; // Keep background container opaque to prevent double-dimming
  const videoSrc = backgroundVideoFor(pathname);
  if (videoSrc === null) {
    return <div className="fixed inset-0 z-0 bg-[#05070B] pointer-events-none" />;
  }

  return (
    <div 
      className="fixed inset-0 z-0 pointer-events-none transition-opacity duration-1000 bg-[#05070B] overflow-hidden"
      style={{ opacity }}
    >
      <video
        ref={videoRef}
        key={videoSrc}
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 w-full h-full object-cover scale-[1.03]"
        style={{ filter: 'brightness(0.30) blur(3px) saturate(0.6)' }}
      >
        <source src={videoSrc} type="video/mp4" />
      </video>
      {/* 75% Dark overlay & Vignette */}
      <div className="absolute inset-0 bg-[#05070B]/75 pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-t from-[#05070B] via-transparent to-[#05070B] pointer-events-none" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_30%,#05070B_95%)] pointer-events-none" />
    </div>
  );
}
