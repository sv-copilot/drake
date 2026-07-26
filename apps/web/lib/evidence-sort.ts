import type { DispatchSummary, RunSummary } from "@/lib/api-client";

export type SortKey = "newest" | "oldest" | "status";

export const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
  { value: "status", label: "Status" },
];

export function normalizeSort(value: string | null | undefined): SortKey {
  return value === "oldest" || value === "status" ? value : "newest";
}

function toMs(iso: string): number {
  const parsed = Date.parse(iso);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function sortRecords<T>(
  items: T[],
  getTime: (item: T) => string,
  getStatus: (item: T) => string,
  sort: SortKey,
): T[] {
  const next = [...items];
  if (sort === "oldest") {
    return next.sort((a, b) => toMs(getTime(a)) - toMs(getTime(b)));
  }
  if (sort === "status") {
    return next.sort((a, b) => {
      const byStatus = getStatus(a).localeCompare(getStatus(b));
      return byStatus !== 0 ? byStatus : toMs(getTime(b)) - toMs(getTime(a));
    });
  }
  return next.sort((a, b) => toMs(getTime(b)) - toMs(getTime(a)));
}

export function sortRuns(runs: RunSummary[], sort: SortKey): RunSummary[] {
  return sortRecords(runs, (run) => run.started_at, (run) => run.status, sort);
}

export function sortDispatches(
  dispatches: DispatchSummary[],
  sort: SortKey,
): DispatchSummary[] {
  return sortRecords(
    dispatches,
    (dispatch) => dispatch.dispatched_at,
    (dispatch) => dispatch.status,
    sort,
  );
}
