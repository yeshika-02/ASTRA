'use client';

import React, { useRef, useEffect } from 'react';
import { useAstraStore } from '@/lib/store';
import { usePathname } from 'next/navigation';

// ── Master Backdrop Component ────────────────────────────────────────
function backgroundVideoFor(pathname: string): string {
  if (pathname === '/') return '/blackhole.mp4';
  if (pathname === '/search') return '/earth.mp4';
  if (pathname === '/analysis') return '/solar-system.mp4';
  if (pathname === '/dataset') return '/star-cluster.mp4';
  if (pathname === '/model') return '/galaxy.mp4';
  if (pathname === '/research') return '/nebula.mp4';
  if (pathname === '/mission-replay') return '/pulsar.mp4';
  if (pathname === '/osint') return '/satellite.mp4';
  if (pathname === '/visualization') return '/space-dust.mp4';
  if (pathname.startsWith('/target/')) return '/space-dust.mp4';
  return '/space-backdrop.mp4';
}

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
