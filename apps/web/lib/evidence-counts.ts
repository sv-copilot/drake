import type { DispatchSummary, RunSummary } from "@/lib/api-client";

export type EvidenceCount = {
  runs: number;
  dispatches: number;
};

export const EMPTY_EVIDENCE_COUNT: EvidenceCount = { runs: 0, dispatches: 0 };

/**
 * Read-only aggregate of run and dispatch activity per repo. Used to surface
 * evidence volume on portfolio rows without fetching per-repo detail.
 */
export function repoEvidenceCounts(
  runs: RunSummary[],
  dispatches: DispatchSummary[],
): Record<string, EvidenceCount> {
  const counts: Record<string, EvidenceCount> = {};
  const bucket = (repoId: string) => {
    counts[repoId] ??= { runs: 0, dispatches: 0 };
    return counts[repoId];
  };
  for (const run of runs) {
    bucket(run.repo_id).runs += 1;
  }
  for (const dispatch of dispatches) {
    bucket(dispatch.repo_id).dispatches += 1;
  }
  return counts;
}

export function countForRepo(
  counts: Record<string, EvidenceCount>,
  repoId: string,
): EvidenceCount {
  return counts[repoId] ?? EMPTY_EVIDENCE_COUNT;
}
