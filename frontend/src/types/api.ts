/** Hand-maintained DTOs mirroring the FastAPI Pydantic schemas. */

export type Role = "owner" | "approver" | "reviewer" | "readonly";

export type ApprovalState = "draft" | "in_review" | "approved" | "archived";

export type DecompositionMode = "lef" | "tef-vuln" | "full";

export type DistributionType =
  | "pert"
  | "triangular"
  | "uniform"
  | "normal"
  | "lognormal"
  | "beta"
  | "gamma";

export interface DistributionParam {
  type: DistributionType;
  min?: number;
  mode?: number;
  max?: number;
  alpha?: number;
  beta?: number;
  shape?: number;
  lambda?: number;
  notes?: string;
}

export interface ScenarioInputs {
  lef?: DistributionParam;
  tef?: DistributionParam;
  vuln?: DistributionParam;
  tcap?: DistributionParam;
  rs?: DistributionParam;
  plm: DistributionParam;
  slp_prob: DistributionParam;
  slm: DistributionParam;
}

export interface ReferenceLine {
  label: string;
  value: number;
  color: string;
}

export interface ScenarioRead {
  id: string;
  name: string;
  description: string | null;
  business_unit: string | null;
  scenario_type: string | null;
  benchmark_group: string | null;
  tags: string[];
  owner_label: string | null;
  owner_user_id: number | null;
  mode: DecompositionMode;
  inputs: ScenarioInputs;
  tolerance: number;
  reduction_pct: number;
  reference_lines: ReferenceLine[];
  prefs: Record<string, unknown>;
  version_label: string;
  assessment_date: string | null;
  review_date: string | null;
  approval_state: ApprovalState;
  threat_refs: string[];
  control_refs: string[];
  notes: string | null;
  created_at: string;
  updated_at: string;
  latest_simulation_id: string | null;
}

export interface UserPublic {
  id: number;
  email: string;
  display_name: string;
  role: Role;
  is_active: boolean;
  last_login_at: string | null;
}

export interface SessionStatus {
  authenticated: boolean;
  user: UserPublic | null;
  ula_acknowledged: boolean;
  ula_version: string | null;
}

export interface AppSettings {
  iterations: number;
  seed: number;
  theme: string;
  ula_acknowledged_version: string | null;
  ula_acknowledged_at: string | null;
}

export type SimulationStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export interface SimulationStatistics {
  mean: number;
  std: number;
  p5: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
  p95: number;
  p99: number;
  ci_lo: number;
  ci_hi: number;
  tail_mean: number;
  zero_count: number;
  iterations: number;
  seed: number;
  prob_exceed_tolerance: number;
  tolerance: number;
  tolerance_utilisation: number;
  difference_to_tolerance: number;
}

export interface SensitivityEntry {
  name: string;
  label: string;
  corr: number;
}

export interface HistogramPayload {
  lo: number;
  hi: number;
  w: number;
  counts: number[];
  cap: number;
  real_max: number;
  tail_count: number;
  tail_mean: number;
}

export interface SimulationResult {
  id: string;
  scenario_id: string;
  status: SimulationStatus;
  started_at: string | null;
  completed_at: string | null;
  progress: number;
  iterations: number;
  seed: number;
  statistics: SimulationStatistics | null;
  histogram: HistogramPayload | null;
  lec_curve: [number, number][] | null;
  sensitivity: SensitivityEntry[] | null;
  losses_url: string | null;
  driver_samples_url: string | null;
  engine_version: string | null;
  mode_at_run: string | null;
  inputs_at_run: ScenarioInputs | null;
}

export interface SimulationRequest {
  iterations?: number;
  seed?: number;
  persist_artifacts?: boolean;
  snapshot_scenario?: boolean;
  snapshot_note?: string;
}

export interface ScenarioCreate {
  name: string;
  mode: DecompositionMode;
  tolerance?: number;
  inputs: ScenarioInputs;
  business_unit?: string;
  owner_label?: string;
  tags?: string[];
}

export interface LossesResponse {
  losses: number[];
  lefs: number[];
  offset: number;
  limit: number;
  total: number;
}

export interface PortfolioRollup {
  portfolio_id: string | null;
  scenario_count: number;
  simulated_count: number;
  iterations: number;
  total_ale: number;
  total_p50: number;
  total_p90: number;
  total_p95: number;
  total_p99: number;
  total_tail: number;
  ci_lo: number;
  ci_hi: number;
  over_tolerance_count: number;
  appetite: number | null;
  appetite_utilisation: number | null;
  histogram: HistogramPayload;
  lec_curve: [number, number][];
  top_scenarios: TopScenarioEntry[];
}

export interface TopScenarioEntry {
  scenario_id: string;
  name: string;
  ale: number;
  p95: number;
  p99: number;
  tolerance: number;
  utilisation: number;
  over_tolerance: boolean;
  share_of_ale: number;
}

export interface PortfolioSnapshot {
  id: number;
  created_at: string;
  total_ale: number;
  total_p95: number;
  total_p99: number;
  scenario_count: number;
  simulated_count: number;
  reason: string;
}

export interface RegisterRow {
  scenario_id: string;
  name: string;
  business_unit: string | null;
  owner_label: string | null;
  tags: string[];
  mode: string;
  ale: number | null;
  p50: number | null;
  p95: number | null;
  p99: number | null;
  tail_mean: number | null;
  tolerance: number;
  utilisation: number | null;
  prob_exceed_tolerance: number | null;
  over_tolerance: boolean;
  last_simulated_at: string | null;
  version_label: string;
  review_date: string | null;
}
