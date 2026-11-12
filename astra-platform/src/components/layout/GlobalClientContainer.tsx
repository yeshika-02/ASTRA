'use client';

import React, { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { CommandPalette } from './CommandPalette';
import { CosmicBackground } from '../three/CosmicBackground';
import { ParticleLayer } from '../shared/ParticleLayer';
import { useAstraStore } from '@/lib/store';
import { spaceHumSynth } from '@/lib/utils/SpaceHum';
import { browserStorage, readPreferences } from '@/lib/store/preferences';
import { motion, AnimatePresence, MotionConfig } from 'framer-motion';
import { usePrefersReducedMotion } from '@/lib/hooks/useMotionPreferences';

export function GlobalClientContainer({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { audioState, audioVolume, setAudioVolume, setQualityState } = useAstraStore();
  const reducedMotion = usePrefersReducedMotion();

  // Restore display preferences on mount. Audio on/off is never restored: sound starts only
  // when the visitor turns it on.
  useEffect(() => {
    const prefs = readPreferences(browserStorage());
    if (prefs.audioVolume !== undefined) setAudioVolume(prefs.audioVolume);
    if (prefs.qualityState !== undefined) setQualityState(prefs.qualityState);
  }, [setAudioVolume, setQualityState]);

  // Manage programmatic deep-space hum synthesis
  useEffect(() => {
    if (audioState === 'playing') {
      spaceHumSynth?.start();
    } else {
      spaceHumSynth?.stop();
    }
  }, [audioState]);

  // Sync volume with synthesizer
  useEffect(() => {
    spaceHumSynth?.setVolume(audioVolume);
  }, [audioVolume]);

  // Clean up audio on unmount
  useEffect(() => {
    return () => {
      spaceHumSynth?.stop();
    };
  }, []);

  return (
    // reducedMotion="user": framer-motion drops transform animations when the OS asks for less motion.
    <MotionConfig reducedMotion="user">
    <div className="flex h-screen overflow-hidden text-[#D7DEE7]">
      {/* 3D Cosmic Starfield Layer (behind everything) */}
      <CosmicBackground />
      <ParticleLayer />

      {/* Global Navigation Sidebar */}
      <Sidebar />

      {/* Main Workspace Column */}
      <div className="flex flex-col flex-1 overflow-hidden relative z-10">
        {/* Telemetry and Global Action Top Bar */}
        <TopBar />

        {/* Dynamic Transition Area */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 relative select-text">
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={reducedMotion ? false : { opacity: 0, y: 6, filter: 'blur(4px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              exit={reducedMotion ? undefined : { opacity: 0, y: -6, filter: 'blur(4px)' }}
              transition={{ duration: reducedMotion ? 0 : 0.35, ease: 'easeInOut' }}
              className="h-full w-full"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Global Shortcut Palette (Cmd+K / Ctrl+K) */}
      <CommandPalette />
    </div>
    </MotionConfig>
  );
}
