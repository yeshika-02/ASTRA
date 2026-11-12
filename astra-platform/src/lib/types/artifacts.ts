// Shapes of the JSON artifacts in data/artifacts/ and of the API responses built from them.
// Derived from the committed artifact files; keep in sync if the artifacts are regenerated.

import type { AstraClass } from './index';

export type PerClass<T> = Record<AstraClass, T>;

export interface SubgroupMetrics {
  bls_accuracy: number;
  bls_macro_f1: number;
  catalog_accuracy: number;
  catalog_macro_f1: number;
}

export interface BenchmarkEntry {
  label: string;
  test_accuracy: number;
  accuracy_ci: string;
  macro_f1: number;
  macro_f1_ci: string;
  weighted_f1: number;
  per_class_f1: PerClass<number>;
  subgroups: SubgroupMetrics;
}

export interface CalibrationSummary {
  brier_raw: number;
  brier_calibrated: number;
  ece_raw: number;
  ece_calibrated: number;
  nll_raw: number;
  nll_calibrated: number;
}

export interface CheckpointEntry {
  filename: string;
  path: string;
  architecture: string;
  exists: boolean;
  sha256: string;
  actual_sha256: string;
  expected_params: number;
  loaded_params: number;
  missing_keys: number;
  unexpected_keys: number;
}

/** data/artifacts/model_registry.json; /api/model returns `active_model`, /api/checkpoints `checkpoints`. */
export interface ModelRegistry {
  generated_at: string;
  active_model: ActiveModel;
  checkpoints: CheckpointEntry[];
}

export interface ActiveModel {
  model: string;
  benchmark: BenchmarkEntry;
  calibration: CalibrationSummary;
  checkpoint: CheckpointEntry;
  temperature: number;
  temperature_hash: string;
  temperature_path: string;
  onnx_path: string;
  onnx_hash: string;
  onnx_data_path: string;
  onnx_data_hash: string;
}

export interface ClassAndSplitCounts {
  class_counts: PerClass<number>;
  period_source_counts: { BLS: number; catalog: number };
  split_counts: { train: number; val: number; test: number };
  total_stars: number;
}

/** data/artifacts/benchmark.json (/api/benchmark). */
export interface BenchmarkArtifact {
  generated_at: string;
  dataset: ClassAndSplitCounts;
  models: Record<string, BenchmarkEntry>;
}

/** data/artifacts/calibration.json (/api/calibration). */
export interface CalibrationArtifact {
  generated_at: string;
  global: Record<string, CalibrationSummary>;
  per_class: PerClass<{
    cnn_raw: number;
    cnn_calibrated: number;
    transformer_raw: number;
    transformer_calibrated: number;
  }>;
  temperatures: Record<string, number>;
}

export interface SelectivePredictionPoint {
  model: string;
  confidence_threshold: number;
  coverage: number;
  accuracy: number;
}

export interface ResearchFindingsArtifact {
  generated_at: string;
  headline: string;
  accuracy_gap_catalog_vs_bls: number;
  findings: { id: string; statement: string; unit: string; value: number }[];
  calibration: CalibrationSummary;
  selective_prediction: SelectivePredictionPoint[];
  shared_transformer: BenchmarkEntry;
}

export interface EntropySummary {
  correct_mean_entropy: number;
  correct_entropy_var: number;
  incorrect_mean_entropy: number;
  incorrect_entropy_var: number;
}

export interface UncertaintyArtifact {
  generated_at: string;
  coverage_sweep: SelectivePredictionPoint[];
  entropy: Record<string, EntropySummary>;
  error_detection_auroc: Record<string, number>;
}

/** /api/research. */
export interface ResearchResponse {
  findings: ResearchFindingsArtifact;
  uncertainty: UncertaintyArtifact;
}

export interface SplitMetadata {
  audit_override_used: boolean;
  calibration_size: number;
  dataset_size: number;
  grouping_key: string;
  minimum_samples_required: number;
  ratios: { calibration: number; test: number; train: number; val: number };
  seed: number;
  split_hash: string;
  test_size: number;
  timestamp: string;
  train_size: number;
  val_size: number;
}

export interface DatasetAuditArtifact extends ClassAndSplitCounts {
  generated_at: string;
  status: string;
  dataset_hash: string;
  expected_dataset_hash: string;
  filesystem_processed_count: number;
  missing_processed_dirs: string[];
  split_metadata: SplitMetadata;
}

export interface LineageArtifact {
  generated_at: string;
  dataset_name: string;
  dataset_version: string;
  freeze_date: string;
  dataset_hash: string;
  expected_dataset_hash: string;
  pipeline: string[];
  counts: {
    classes: PerClass<number>;
    splits: { calibration: number; dataset: number; test: number; train: number; val: number };
    total_stars: number;
  };
  source_files: Record<string, string>;
  split_hashes: Record<string, string>;
  split_metadata: SplitMetadata;
}

/** /api/dataset. */
export interface DatasetResponse {
  audit: DatasetAuditArtifact;
  lineage: LineageArtifact;
  classSplitMatrix: PerClass<{ train: number; val: number; test: number }>;
}

/** One row of the `stars` table in data/astra.sqlite, before JSON columns are parsed. */
export interface StarRow {
  tic_id: number;
  astra_class: AstraClass;
  label: number | null;
  ra: number;
  dec: number;
  period: number;
  period_source: string;
  cadence_type: string | null;
  preprocessing_version: string | null;
  split: string;
  n_sectors: number | null;
  n_points_raw: number | null;
  n_points_clean: number | null;
  bls_period: number | null;
  catalog_period: number | null;
  bls_power: number | null;
  variability_amplitude: number | null;
  snr_estimate: number | null;
  source_catalogs: string | null;
  primary_source: string | null;
  catalog_label: string | null;
  sector_information: string | null;
  source_pipeline: string | null;
  processing_timestamp: string | null;
  preprocessing_hash: string | null;
  has_folded_lc: number | null;
  flux_1000_hash: string | null;
  flux_200_hash: string | null;
  folded_flux_1000_hash: string | null;
  folded_flux_200_hash: string | null;
  metadata_hash: string | null;
}

/** /api/search result item. */
export interface SearchResult {
  tic_id: number;
  astra_class: AstraClass;
  ra: number;
  dec: number;
  period: number;
  period_source: string;
  n_sectors: number | null;
}

/** /api/osint/[id] report. Fields the registry does not hold are null, never invented. */
export interface OsintReport {
  tic_id: number;
  astra_class: string;
  period: number;
  period_source: string;
  ra: number;
  dec: number;
  cross_matches: { catalog: string; identifier: string | null; otype: string | null; distance_arcsec: number | null; notes: string }[];
  observational_history: { observatory: string; instrument: string; filters: string; observations: number | null; first_obs: string | null; last_obs: string | null; cadence: string | null }[];
  related_objects: { identifier: string; class: string; ra: number; dec: number; separation: string; notes: string }[];
  provenance: { step: string; agent: string; detail: string }[];
  scientific_notes: string;
  audit_hash: string;
}
