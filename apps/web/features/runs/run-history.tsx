"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo } from "react";

import { EvidenceResultSummary } from "@/components/evidence-result-summary";
import { RelativeTime } from "@/components/relative-time";
import { fetchRuns, type RunSummary } from "@/lib/api-client";
import {
  EMPTY_EVIDENCE_FILTERS,
  hasActiveEvidenceFilters,
  type EvidenceFilters as Filters,
} from "@/lib/evidence-filters";
import { useEvidenceUrlFilters } from "@/lib/use-evidence-url-filters";
import { cn } from "@/lib/utils";

export function RunHistory() {
  const runsQuery = useQuery({
    queryKey: ["runs"],
    queryFn: fetchRuns,
  });
  const [filters, setFilters] = useEvidenceUrlFilters();

  if (runsQuery.isLoading) {
    return <RunHistoryLoading />;
  }

  if (runsQuery.isError) {
    return <RunHistoryError />;
  }

  return (
    <RunHistoryContent
      runs={runsQuery.data ?? []}
      filters={filters}
      onFiltersChange={setFilters}
    />
  );
}

export function RunHistoryContent({
  runs,
  filters,
  onFiltersChange,
}: {
  runs: RunSummary[];
  filters?: Filters;
  onFiltersChange?: (filters: Filters) => void;
}) {
  const currentFilters = filters ?? EMPTY_EVIDENCE_FILTERS;
  const filteredRuns = useMemo(
    () => filterRuns(runs, currentFilters),
    [runs, currentFilters],
  );
  const options = useMemo(() => runFilterOptions(runs), [runs]);

  return (
    <section>
      <div className="max-w-4xl">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
          Runs
        </p>
        <h2 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
          Evidence history for worker activity.
        </h2>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-600">
          Searchable read-only view of run artifacts, evidence status, model,
          runtime, and PR provenance.
        </p>
      </div>

      <RunFilters
        filters={currentFilters}
        options={options}
        onChange={onFiltersChange}
      />

      {runs.length > 0 ? (
        <EvidenceResultSummary
          filtered={filteredRuns.length}
          total={runs.length}
          noun="run"
          active={hasActiveEvidenceFilters(currentFilters)}
          onClear={() => onFiltersChange?.(EMPTY_EVIDENCE_FILTERS)}
        />
      ) : null}

      {filteredRuns.length === 0 ? (
        <RunHistoryEmpty filtered={runs.length > 0} />
      ) : (
        <div className="mt-8 overflow-hidden rounded-xl border border-stone-200 bg-white">
          <div className="grid grid-cols-[1.4fr_1fr_1fr_1fr] gap-4 border-b border-stone-200 px-5 py-3 text-xs font-medium uppercase tracking-wide text-slate-500">
            <span>Run</span>
            <span>Target</span>
            <span>Status</span>
            <span>Evidence</span>
          </div>
          <div className="divide-y divide-stone-200">
            {filteredRuns.map((run) => (
              <RunRow key={run.run_id} run={run} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function RunFilters({
  filters,
  options,
  onChange,
}: {
  filters: Filters;
  options: ReturnType<typeof runFilterOptions>;
  onChange?: (filters: Filters) => void;
}) {
  return (
    <div className="mt-10 grid gap-3 rounded-xl border border-stone-200 bg-white p-4 md:grid-cols-3">
      <FilterSelect
        label="Repo"
        value={filters.repoId}
        options={options.repoIds}
        onChange={(value) => onChange?.({ ...filters, repoId: value })}
      />
      <FilterSelect
        label="Slice"
        value={filters.sliceId}
        options={options.sliceIds}
        onChange={(value) => onChange?.({ ...filters, sliceId: value })}
      />
      <FilterSelect
        label="Status"
        value={filters.status}
        options={options.statuses}
        onChange={(value) => onChange?.({ ...filters, status: value })}
      />
    </div>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-sm">
      <span className="font-medium text-slate-950">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 block w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-slate-950"
      >
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function RunRow({ run }: { run: RunSummary }) {
  return (
    <article className="grid grid-cols-[1.4fr_1fr_1fr_1fr] gap-4 px-5 py-5 text-sm">
      <div>
        <Link
          href={`/runs/${encodeURIComponent(run.run_id)}`}
          className="font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
        >
          {run.run_id}
        </Link>
        <p className="mt-1 font-mono text-xs text-slate-500">{run.task_id}</p>
        <p className="mt-1 text-xs text-slate-500">
          <RelativeTime iso={run.started_at} />
        </p>
      </div>
      <div>
        <Link
          href={`/repos/${encodeURIComponent(run.repo_id)}`}
          className="font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
        >
          {run.repo_id}
        </Link>
        <p className="mt-1 text-slate-600">{run.slice_id ?? "no slice"}</p>
      </div>
      <div>
        <StatusBadge status={run.status} />
        <p className="mt-2 text-xs text-slate-500">
          {run.runtime} · {run.model_slug ?? "unknown model"}
        </p>
      </div>
      <div>
        <p className="text-slate-950">{run.evidence_status ?? "pending"}</p>
        <p className="mt-1 text-xs text-slate-500">
          {run.artifact_source ?? "not uploaded"}
        </p>
      </div>
    </article>
  );
}

function StatusBadge({ status }: { status: string }) {
  const tone = statusTone(status);
  return (
    <span
      className={cn(
        "rounded-full px-2.5 py-1 text-xs font-medium capitalize",
        tone === "success" && "bg-emerald-100 text-emerald-800",
        tone === "running" && "bg-sky-100 text-sky-800",
        tone === "failed" && "bg-rose-100 text-rose-800",
        tone === "neutral" && "bg-slate-100 text-slate-700",
      )}
    >
      {status}
    </span>
  );
}

export function filterRuns(runs: RunSummary[], filters: Filters) {
  return runs.filter((run) => {
    if (filters.repoId && run.repo_id !== filters.repoId) {
      return false;
    }
    if (filters.sliceId && run.slice_id !== filters.sliceId) {
      return false;
    }
    if (filters.status && run.status !== filters.status) {
      return false;
    }
    return true;
  });
}

export function runFilterOptions(runs: RunSummary[]) {
  return {
    repoIds: sortedUnique(runs.map((run) => run.repo_id)),
    sliceIds: sortedUnique(runs.map((run) => run.slice_id).filter(Boolean)),
    statuses: sortedUnique(runs.map((run) => run.status)),
  };
}

function sortedUnique(values: Array<string | undefined>) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort();
}

export function statusTone(status: string) {
  if (status === "success") {
    return "success";
  }
  if (status === "running" || status === "pending") {
    return "running";
  }
  if (["failure", "partial", "blocked", "cancelled"].includes(status)) {
    return "failed";
  }
  return "neutral";
}

export function RunHistoryLoading() {
  return (
    <section aria-label="Loading runs" className="max-w-4xl">
      <div className="h-4 w-28 rounded bg-stone-200" />
      <div className="mt-4 h-10 w-2/3 rounded bg-stone-200" />
      <div className="mt-10 h-64 rounded-xl bg-stone-200" />
    </section>
  );
}

export function RunHistoryEmpty({ filtered = false }: { filtered?: boolean }) {
  return (
    <section className="mt-8 max-w-3xl rounded-xl border border-stone-200 bg-white p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
        Runs
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-slate-950">
        {filtered ? "No runs match these filters." : "No run artifacts yet."}
      </h2>
      <p className="mt-3 text-slate-600">
        Run history remains read-only; upload and ingestion pipelines are future
        slices.
      </p>
    </section>
  );
}

export function RunHistoryError() {
  return (
    <section className="max-w-3xl rounded-xl border border-rose-200 bg-rose-50 p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-700">
        Runs unavailable
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-rose-950">
        Could not load run history.
      </h2>
      <p className="mt-3 text-rose-800">
        Check that `drake-api` is running and the run read endpoint is available.
      </p>
    </section>
  );
}
