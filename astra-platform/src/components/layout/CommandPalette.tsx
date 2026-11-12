'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Compass, Target, Shield, HelpCircle, Activity, Layout, Volume2, Cpu } from 'lucide-react';
import { useAstraStore } from '@/lib/store';
import { motion, AnimatePresence } from 'framer-motion';
import type { SearchResult as ApiSearchResult } from '@/lib/types/artifacts';

interface SearchResult {
  id: string;
  title: string;
  subtitle: string;
  type: 'navigation' | 'target' | 'action';
  action?: () => void;
  url?: string;
  icon: React.ComponentType<{ className?: string }>;
}

const STATIC_PAGES = [
  { title: 'Mission Control', url: '/', subtitle: 'System narrative, status, and telemetry', icon: Compass },
  { title: '3D Stellar Visualization', url: '/visualization', subtitle: 'Interactive 3D star cluster mapping', icon: Layout },
  { title: 'Target Search', url: '/search', subtitle: 'Query variable star targets', icon: Search },
  { title: 'Dataset Intelligence', url: '/dataset', subtitle: 'Explore dataset splits and audits', icon: Shield },
  { title: 'Model Operations', url: '/model', subtitle: 'PyTorch model weights and checkpoints', icon: Activity },
  { title: 'Research Findings', url: '/research', subtitle: 'Scientific writeups and paper findings', icon: HelpCircle },
  { title: 'Mission Replay', url: '/mission-replay', subtitle: 'Animated step-by-step pipeline progression', icon: Compass },
  { title: 'Space OSINT', url: '/osint', subtitle: 'OSINT target intelligence dossiers', icon: Shield },
];

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const { audioState, setAudioState, qualityState, setQualityState } = useAstraStore();

  // Latest open state for the global key handler, which is registered once.
  const isOpenRef = useRef(isOpen);
  useEffect(() => {
    isOpenRef.current = isOpen;
  }, [isOpen]);

  // Toggle with Command+K / Ctrl+K. Opening always starts from an empty query.
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpenRef.current) {
          setIsOpen(false);
        } else {
          setQuery('');
          setSelectedIndex(0);
          setIsOpen(true);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Autofocus input on open
  useEffect(() => {
    if (!isOpen) return;
    const timer = setTimeout(() => inputRef.current?.focus(), 50);
    return () => clearTimeout(timer);
  }, [isOpen]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Search logic
  useEffect(() => {
    let active = true;
    
    const search = async () => {
      const q = query.trim().toLowerCase();
      
      // Initial state: show static pages & actions
      if (!q) {
        const initialResults: SearchResult[] = [
          ...STATIC_PAGES.map((page) => ({
            id: `nav-${page.url}`,
            title: page.title,
            subtitle: page.subtitle,
            type: 'navigation' as const,
            url: page.url,
            icon: page.icon,
          })),
          {
            id: 'action-audio',
            title: audioState === 'muted' ? 'Enable Ambient Hum' : 'Mute Ambient Hum',
            subtitle: 'Toggle low-frequency space ventilator acoustics',
            type: 'action' as const,
            icon: Volume2,
            action: () => setAudioState(audioState === 'muted' ? 'playing' : 'muted'),
          },
          {
            id: 'action-quality',
            title: qualityState === 'low' ? 'Enable Cinematic Starfield' : 'Use Performance Mode (CSS)',
            subtitle: 'Toggle R3F background quality scaling',
            type: 'action' as const,
            icon: Cpu,
            action: () => setQualityState(qualityState === 'low' ? 'high' : 'low'),
          }
        ];
        setResults(initialResults);
        setSelectedIndex(0);
        return;
      }

      setLoading(true);

      // Filter static pages locally
      const localMatches = STATIC_PAGES.filter(
        (p) => p.title.toLowerCase().includes(q) || p.subtitle.toLowerCase().includes(q)
      ).map((page) => ({
        id: `nav-${page.url}`,
        title: page.title,
        subtitle: page.subtitle,
        type: 'navigation' as const,
        url: page.url,
        icon: page.icon,
      }));

      // Remote query for Targets (TIC IDs)
      let remoteMatches: SearchResult[] = [];
      if (q.length >= 2) {
        try {
          const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
          if (res.ok) {
            const data = await res.json();
            if (active && data.results) {
              remoteMatches = (data.results as ApiSearchResult[]).map((r) => ({
                id: `target-${r.tic_id}`,
                title: `TIC ${r.tic_id}`,
                subtitle: `${r.astra_class} — Period: ${r.period.toFixed(4)} d (${r.period_source})`,
                type: 'target' as const,
                url: `/target/${r.tic_id}`,
                icon: Target,
              }));
            }
          }
        } catch (err) {
          console.error('Command Palette Search Error:', err);
        }
      }

      if (active) {
        setResults([...localMatches, ...remoteMatches]);
        setSelectedIndex(0);
        setLoading(false);
      }
    };

    search();
    
    return () => {
      active = false;
    };
  }, [query, audioState, qualityState, setAudioState, setQualityState]);

  // Keyboard navigation inside the palette
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, results.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + results.length) % Math.max(1, results.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (results[selectedIndex]) {
        triggerItem(results[selectedIndex]);
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setIsOpen(false);
    }
  };

  const triggerItem = (item: SearchResult) => {
    setIsOpen(false);
    if (item.action) {
      item.action();
    } else if (item.url) {
      router.push(item.url);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4 bg-black/70 backdrop-blur-[6px] transition-all">
          <motion.div
            initial={{ opacity: 0, scale: 0.97, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: -8 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            ref={containerRef}
            className="w-full max-w-xl rounded border astra-glass overflow-hidden shadow-2xl flex flex-col max-h-[440px]"
            onKeyDown={handleKeyDown}
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
          >
            {/* Search Input Bar */}
            <div className="flex items-center gap-3 px-4 border-b border-white/5 h-12">
              <Search className="w-4 h-4 text-white/40 shrink-0" aria-hidden="true" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search targets, dashboards, OSINT dossiers..."
                role="combobox"
                aria-label="Search targets and pages"
                aria-expanded={results.length > 0}
                aria-controls="command-palette-results"
                aria-autocomplete="list"
                aria-activedescendant={results[selectedIndex] ? `command-palette-option-${selectedIndex}` : undefined}
                className="w-full h-full bg-transparent border-0 outline-none text-[13px] text-[#D7DEE7] placeholder-white/20 font-mono"
              />
              <span className="text-[10px] px-1.5 py-0.5 rounded border border-white/10 bg-white/5 text-white/40 font-mono select-none">
                ESC
              </span>
            </div>

            {/* List Results */}
            <div
              id="command-palette-results"
              role="listbox"
              aria-label="Results"
              className="flex-1 overflow-y-auto p-1.5 scrollbar-thin"
            >
              {results.length > 0 ? (
                results.map((item, index) => {
                  const Icon = item.icon;
                  const isSelected = index === selectedIndex;
                  return (
                    <div
                      key={item.id}
                      id={`command-palette-option-${index}`}
                      role="option"
                      aria-selected={isSelected}
                      onClick={() => triggerItem(item)}
                      onMouseEnter={() => setSelectedIndex(index)}
                      className={`flex items-center gap-3 px-3 py-2 rounded cursor-pointer transition-colors duration-150 ${
                        isSelected
                          ? 'bg-[#1D3A6B]/30 border border-[#1D3A6B]/50 text-white'
                          : 'border border-transparent text-white/70 hover:text-white'
                      }`}
                    >
                      <Icon aria-hidden="true" className={`w-4 h-4 shrink-0 ${isSelected ? 'text-[#6EA8FE]' : 'text-white/40'}`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-[12px] font-mono font-medium truncate leading-tight">
                          {item.title}
                        </p>
                        <p className="text-[10px] text-white/40 truncate mt-0.5 leading-none">
                          {item.subtitle}
                        </p>
                      </div>
                      {isSelected && (
                        <span className="text-[9px] font-mono text-[#6EA8FE] shrink-0 uppercase tracking-wider">
                          Execute
                        </span>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="py-8 text-center text-white/30 font-mono text-[11px]">
                  {loading ? 'Searching...' : 'No analytical targets matched'}
                </div>
              )}
            </div>

            {/* Footer Status Bar */}
            <div className="h-8 border-t border-white/5 bg-black/20 px-4 flex items-center justify-between text-[9px] text-white/30 font-mono select-none">
              <div className="flex items-center gap-4">
                <span>↑↓ to navigate</span>
                <span>Enter to select</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="border border-white/10 px-1 py-0.5 rounded">⌘</span>
                <span>+</span>
                <span className="border border-white/10 px-1 py-0.5 rounded">K</span>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
