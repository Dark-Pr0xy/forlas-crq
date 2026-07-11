/**
 * TanStack Query hooks for the API. Centralised so query keys stay consistent
 * between hooks and invalidations.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  AnalysisRecord,
  AnalysisUpdate,
  LossesResponse,
  ScenarioCreate,
  ScenarioRead,
  ScenarioTypesResponse,
  SimulationRequest,
  SimulationResult,
} from "@/types/api";

export const keys = {
  scenarios: ["scenarios"] as const,
  scenario: (id: string) => ["scenarios", id] as const,
  latestSimulation: (id: string) => ["scenarios", id, "latest-sim"] as const,
  losses: (runId: string) => ["simulations", runId, "losses"] as const,
  analysis: (id: string) => ["scenarios", id, "analysis"] as const,
  scenarioTypes: ["scenario-types"] as const,
};

export function useScenarios(
  options?: Omit<UseQueryOptions<ScenarioRead[]>, "queryKey" | "queryFn">,
) {
  return useQuery({
    queryKey: keys.scenarios,
    queryFn: () => api.get<ScenarioRead[]>("/api/scenarios"),
    ...options,
  });
}

export function useLatestSimulation(scenarioId: string | null) {
  return useQuery({
    queryKey: scenarioId ? keys.latestSimulation(scenarioId) : ["latest-sim", "none"],
    queryFn: () =>
      api.get<SimulationResult>(`/api/scenarios/${scenarioId}/simulations/latest`),
    enabled: !!scenarioId,
    retry: (failureCount, error: unknown) => {
      // 404 = no run yet — don't retry
      if (
        typeof error === "object" &&
        error !== null &&
        "status" in error &&
        (error as { status: number }).status === 404
      ) {
        return false;
      }
      return failureCount < 1;
    },
  });
}

export function useLosses(runId: string | null, limit = 5000) {
  return useQuery({
    queryKey: runId ? [...keys.losses(runId), limit] : ["losses", "none"],
    queryFn: () =>
      api.get<LossesResponse>(`/api/simulations/${runId}/losses?limit=${limit}`),
    enabled: !!runId,
    staleTime: 5 * 60_000,
  });
}

export function useCreateScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ScenarioCreate) => api.post<ScenarioRead>("/api/scenarios", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.scenarios }),
  });
}

export function useUpdateScenario(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<ScenarioRead> & { snapshot_note?: string }) =>
      api.patch<ScenarioRead>(`/api/scenarios/${id}`, payload),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: keys.scenarios });
      qc.setQueryData(keys.scenario(id), data);
    },
  });
}

export type ApprovalAction =
  | "submit_for_review"
  | "approve"
  | "reject"
  | "archive"
  | "reopen";

export function useTransitionScenario(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { action: ApprovalAction; note?: string }) =>
      api.post<unknown>(`/api/governance/scenarios/${id}/transition`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.scenarios });
      qc.invalidateQueries({ queryKey: keys.scenario(id) });
      qc.invalidateQueries({ queryKey: ["approvals"] });
      qc.invalidateQueries({ queryKey: ["audit"] });
      qc.invalidateQueries({ queryKey: ["reviews"] });
    },
  });
}

// --------------------------------------------------------------- analysis

export function useAnalysis(scenarioId: string | null) {
  return useQuery({
    queryKey: scenarioId ? keys.analysis(scenarioId) : ["analysis", "none"],
    queryFn: () => api.get<AnalysisRecord>(`/api/scenarios/${scenarioId}/analysis`),
    enabled: !!scenarioId,
  });
}

export function useSaveAnalysis(scenarioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AnalysisUpdate) =>
      api.put<AnalysisRecord>(`/api/scenarios/${scenarioId}/analysis`, payload),
    onSuccess: (data) => {
      qc.setQueryData(keys.analysis(scenarioId), data);
      qc.invalidateQueries({ queryKey: ["audit"] });
    },
  });
}

// --------------------------------------------------------- scenario types

export function useScenarioTypes() {
  return useQuery({
    queryKey: keys.scenarioTypes,
    queryFn: () => api.get<ScenarioTypesResponse>("/api/scenario-types"),
  });
}

export function useAddScenarioType() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api.post<ScenarioTypesResponse>("/api/scenario-types", { name }),
    onSuccess: (data) => {
      qc.setQueryData(keys.scenarioTypes, data);
    },
  });
}

export function useDeleteScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/api/scenarios/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.scenarios }),
  });
}

export function useCloneScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<ScenarioRead>(`/api/scenarios/${id}/clone`),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.scenarios }),
  });
}

export function useDeletedScenarios(enabled: boolean) {
  return useQuery({
    queryKey: ["scenarios", "deleted"],
    queryFn: () => api.get<ScenarioRead[]>("/api/scenarios/deleted"),
    enabled,
  });
}

export function useRestoreScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<ScenarioRead>(`/api/scenarios/${id}/restore`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.scenarios });
      qc.invalidateQueries({ queryKey: ["scenarios", "deleted"] });
    },
  });
}

export function useRunSimulation(scenarioId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: SimulationRequest) =>
      api.post<SimulationResult>(`/api/scenarios/${scenarioId}/simulations`, payload),
    onSuccess: (data) => {
      qc.setQueryData(keys.latestSimulation(scenarioId), data);
      qc.invalidateQueries({ queryKey: keys.scenarios });
      qc.invalidateQueries({ queryKey: ["portfolio", "rollup"] });
      qc.invalidateQueries({ queryKey: ["portfolio", "register"] });
    },
  });
}

// --------------------------------------------------------------- portfolio

import type {
  PortfolioRollup,
  PortfolioSnapshot,
  RegisterRow,
} from "@/types/api";

export function usePortfolioRollup(
  appetite?: number | null,
  scenarioIds?: string[] | null,
) {
  const params = new URLSearchParams();
  if (appetite != null) params.set("appetite", String(appetite));
  for (const id of scenarioIds ?? []) params.append("scenario_ids", id);
  const search = params.toString() ? `?${params.toString()}` : "";
  return useQuery({
    queryKey: ["portfolio", "rollup", appetite ?? null, (scenarioIds ?? []).join(",")],
    queryFn: () => api.get<PortfolioRollup>(`/api/portfolio/rollup${search}`),
  });
}

export function usePortfolioSnapshots(limit = 50) {
  return useQuery({
    queryKey: ["portfolio", "snapshots", limit],
    queryFn: () => api.get<PortfolioSnapshot[]>(`/api/portfolio/snapshots?limit=${limit}`),
  });
}

export function useCapturePortfolioSnapshot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { reason: string; appetite?: number | null }) =>
      api.post<PortfolioSnapshot>("/api/portfolio/snapshots", payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio", "snapshots"] }),
  });
}

export function useRegister() {
  return useQuery({
    queryKey: ["portfolio", "register"],
    queryFn: () => api.get<RegisterRow[]>("/api/portfolio/register"),
  });
}
