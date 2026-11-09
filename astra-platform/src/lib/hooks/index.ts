import { useQuery } from '@tanstack/react-query';
import type { Star, StarsResponse, LightCurveData, AstraClass } from '../types';
import type {
  ActiveModel,
  BenchmarkArtifact,
  CalibrationArtifact,
  CheckpointEntry,
  DatasetResponse,
  ResearchResponse,
  SearchResult,
} from '../types/artifacts';

export interface PredictResult {
  tic_id: number;
  predicted_class: AstraClass;
  calibrated_confidence: number;
  entropy: number;
  variance: number;
  probabilities: Record<AstraClass, number>;
  source: 'model';
}

export interface ExplainResult {
  tic_id: number;
  predicted_class: AstraClass;
  calibrated_confidence: number;
  entropy: number;
  probabilities: Record<AstraClass, number>;
  attention_weights: number[][];
  source: 'model';
}

// Robust fetch helper that checks r.ok and parses the JSON error details if present
async function fetchJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) {
    const errorText = await r.text();
    let errorMessage = `HTTP error! status: ${r.status}`;
    try {
      const errJson = JSON.parse(errorText);
      errorMessage = errJson.error || errJson.details || errorMessage;
    } catch {
      // Not JSON
    }
    throw new Error(errorMessage);
  }
  return r.json();
}

// ─── Stars list ────────────────────────────────────────────────────────────────
interface StarsParams {
  q?: string;
  class?: string;
  source?: string;
  split?: string;
  page?: number;
  limit?: number;
}

export function useStars(params: StarsParams = {}) {
  const searchParams = new URLSearchParams();
  if (params.q) searchParams.set('q', params.q);
  if (params.class) searchParams.set('class', params.class);
  if (params.source) searchParams.set('source', params.source);
  if (params.split && params.split !== 'all') searchParams.set('split', params.split);
  if (params.page) searchParams.set('page', String(params.page));
  if (params.limit) searchParams.set('limit', String(params.limit));

  return useQuery<StarsResponse>({
    queryKey: ['stars', params],
    queryFn: () => fetchJson<StarsResponse>(`/api/stars?${searchParams}`),
  });
}

// ─── Single star ───────────────────────────────────────────────────────────────
export function useStar(id: string | number | null) {
  return useQuery<Star>({
    queryKey: ['star', id],
    queryFn: () => fetchJson<Star>(`/api/stars/${id}`),
    enabled: id !== null,
  });
}

// ─── Light curve ───────────────────────────────────────────────────────────────
export function useLightCurve(id: string | number | null) {
  return useQuery<LightCurveData>({
    queryKey: ['lightcurve', id],
    queryFn: () => fetchJson<LightCurveData>(`/api/lightcurve/${id}`),
    enabled: id !== null,
    staleTime: Infinity, // light curves don't change
  });
}

// ─── Search ────────────────────────────────────────────────────────────────────
export function useSearch(query: string) {
  return useQuery({
    queryKey: ['search', query],
    queryFn: () => fetchJson<{ results: SearchResult[] }>(`/api/search?q=${encodeURIComponent(query)}`),
    enabled: query.length >= 2,
    staleTime: 30_000,
  });
}

// ─── Model details ─────────────────────────────────────────────────────────────
export function useModelDetails() {
  return useQuery({
    queryKey: ['model-details'],
    queryFn: () => fetchJson<ActiveModel>('/api/model'),
  });
}

// ─── Checkpoints ───────────────────────────────────────────────────────────────
export function useCheckpoints() {
  return useQuery({
    queryKey: ['checkpoints'],
    queryFn: () => fetchJson<CheckpointEntry[]>('/api/checkpoints'),
  });
}

// ─── Dataset metrics ───────────────────────────────────────────────────────────
export function useDatasetDetails() {
  return useQuery({
    queryKey: ['dataset-details'],
    queryFn: () => fetchJson<DatasetResponse>('/api/dataset'),
  });
}

// ─── Research findings ──────────────────────────────────────────────────────────
export function useResearchFindings() {
  return useQuery({
    queryKey: ['research-findings'],
    queryFn: () => fetchJson<ResearchResponse>('/api/research'),
  });
}

// ─── Benchmark metrics ─────────────────────────────────────────────────────────
export function useBenchmarkMetrics() {
  return useQuery({
    queryKey: ['benchmark-metrics'],
    queryFn: () => fetchJson<BenchmarkArtifact>('/api/benchmark'),
  });
}

// ─── Calibration metrics ───────────────────────────────────────────────────────
export function useCalibrationDetails() {
  return useQuery({
    queryKey: ['calibration-details'],
    queryFn: () => fetchJson<CalibrationArtifact>('/api/calibration'),
  });
}

// ─── Model inference (predict / explain) ──────────────────────────────────────
// A 503 "inference_unavailable" answer is a normal outcome, not an error: the UI must show
// that no model ran instead of inventing output.
export type InferenceResult<T> =
  | { available: true; data: T }
  | { available: false; reasons: string[] };

async function fetchInference<T>(url: string): Promise<InferenceResult<T>> {
  const r = await fetch(url);
  if (r.status === 503) {
    const body = await r.json().catch(() => ({}));
    return { available: false, reasons: Array.isArray(body?.reasons) ? body.reasons : [] };
  }
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body?.error || `HTTP error! status: ${r.status}`);
  }
  return { available: true, data: (await r.json()) as T };
}

export function useExplain(id: string | number | null) {
  return useQuery({
    queryKey: ['explain', id],
    queryFn: () => fetchInference<ExplainResult>(`/api/explain/${id}`),
    enabled: id !== null,
    staleTime: Infinity,
  });
}

export function usePredict(id: string | number | null) {
  return useQuery({
    queryKey: ['predict', id],
    queryFn: () => fetchInference<PredictResult>(`/api/predict/${id}`),
    enabled: id !== null,
    staleTime: Infinity,
  });
}
