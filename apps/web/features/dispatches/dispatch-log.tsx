"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo } from "react";

import { fetchDispatches, type DispatchSummary } from "@/lib/api-client";
import {
  EMPTY_EVIDENCE_FILTERS,
  type EvidenceFilters as Filters,
} from "@/lib/evidence-filters";
import { useEvidenceUrlFilters } from "@/lib/use-evidence-url-filters";
import { cn } from "@/lib/utils";

export function DispatchLog() {
  const dispatchesQuery = useQuery({
    queryKey: ["dispatches"],
    queryFn: fetchDispatches,
  });
  const [filters, setFilters] = useEvidenceUrlFilters();

  if (dispatchesQuery.isLoading) {
    return <DispatchLogLoading />;
  }

  if (dispatchesQuery.isError) {
    return <DispatchLogError />;
  }

  return (
    <DispatchLogContent
      dispatches={dispatchesQuery.data ?? []}
      filters={filters}
      onFiltersChange={setFilters}
    />
  );
}

export function DispatchLogContent({
  dispatches,
  filters,
  onFiltersChange,
}: {
  dispatches: DispatchSummary[];
  filters?: Filters;
  onFiltersChange?: (filters: Filters) => void;
}) {
  const currentFilters = filters ?? EMPTY_EVIDENCE_FILTERS;
  const filteredDispatches = useMemo(
    () => filterDispatches(dispatches, currentFilters),
    [dispatches, currentFilters],
  );
  const options = useMemo(() => dispatchFilterOptions(dispatches), [dispatches]);

  if (dispatches.length === 0) {
    return <DispatchLogEmpty />;
  }

  return (
    <section>
      <div className="max-w-4xl">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
          Dispatches
        </p>
        <h2 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
          Read-only orchestrator to worker dispatch log.
        </h2>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-600">
          Phase 1 shows dispatch attempts and retry state only. Manual dispatch,
          retry, and production actions stay out of this screen.
        </p>
      </div>

      <DispatchFilters
        filters={currentFilters}
        options={options}
        onChange={onFiltersChange}
      />

      {filteredDispatches.length === 0 ? (
        <DispatchLogEmpty filtered />
      ) : (
        <div className="mt-8 overflow-hidden rounded-xl border border-stone-200 bg-white">
          <div className="grid grid-cols-[1.2fr_1fr_1fr_1fr] gap-4 border-b border-stone-200 px-5 py-3 text-xs font-medium uppercase tracking-wide text-slate-500">
            <span>Dispatch</span>
            <span>Target</span>
            <span>Status</span>
            <span>Webhook env</span>
          </div>
          <div className="divide-y divide-stone-200">
            {filteredDispatches.map((dispatch) => (
              <DispatchRow key={dispatch.dispatch_id} dispatch={dispatch} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function DispatchFilters({
  filters,
  options,
  onChange,
}: {
  filters: Filters;
  options: ReturnType<typeof dispatchFilterOptions>;
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

function DispatchRow({ dispatch }: { dispatch: DispatchSummary }) {
  return (
    <article className="grid grid-cols-[1.2fr_1fr_1fr_1fr] gap-4 px-5 py-5 text-sm">
      <div>
        <Link
          href={`/dispatches/${encodeURIComponent(dispatch.dispatch_id)}`}
          className="font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
        >
          {dispatch.dispatch_id}
        </Link>
        <p className="mt-1 font-mono text-xs text-slate-500">
          {dispatch.orchestrator_run_id}
        </p>
        <p className="mt-2 text-xs uppercase tracking-wide text-slate-500">
          {dispatch.dispatched_at}
        </p>
      </div>
      <div>
        <p className="font-medium text-slate-950">{dispatch.repo_id}</p>
        <p className="mt-1 text-sm text-slate-600">{dispatch.slice_id}</p>
        <p className="mt-1 text-xs text-slate-500">{dispatch.worker_id}</p>
      </div>
      <div>
        <StatusBadge status={dispatch.status} />
        <p className="mt-2 text-xs text-slate-500">
          retries {dispatch.retry_count}
        </p>
        {dispatch.error_summary ? (
          <p className="mt-2 rounded-md bg-rose-50 p-2 text-xs text-rose-800">
            {dispatch.error_summary}
          </p>
        ) : null}
      </div>
      <div>
        <p className="break-words font-mono text-xs text-slate-600">
          {dispatch.webhook_url_env_name ?? "not declared"}
        </p>
        <p className="mt-2 text-xs uppercase tracking-wide text-slate-500">
          Env var name only
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
        tone === "pending" && "bg-sky-100 text-sky-800",
        tone === "failed" && "bg-rose-100 text-rose-800",
        tone === "neutral" && "bg-slate-100 text-slate-700",
      )}
    >
      {status}
    </span>
  );
}

export function statusTone(status: string) {
  if (["completed", "accepted"].includes(status)) {
    return "success";
  }
  if (["queued", "dispatched", "retrying"].includes(status)) {
    return "pending";
  }
  if (["failed", "cancelled"].includes(status)) {
    return "failed";
  }
  return "neutral";
}

export function filterDispatches(
  dispatches: DispatchSummary[],
  filters: Filters,
) {
  return dispatches.filter((dispatch) => {
    if (filters.repoId && dispatch.repo_id !== filters.repoId) {
      return false;
    }
    if (filters.sliceId && dispatch.slice_id !== filters.sliceId) {
      return false;
    }
    if (filters.status && dispatch.status !== filters.status) {
      return false;
    }
    return true;
  });
}

export function dispatchFilterOptions(dispatches: DispatchSummary[]) {
  return {
    repoIds: sortedUnique(dispatches.map((dispatch) => dispatch.repo_id)),
    sliceIds: sortedUnique(dispatches.map((dispatch) => dispatch.slice_id)),
    statuses: sortedUnique(dispatches.map((dispatch) => dispatch.status)),
  };
}

function sortedUnique(values: Array<string | undefined>) {
  return [...new Set(values.filter((value): value is string => Boolean(value)))].sort();
}

export function DispatchLogLoading() {
  return (
    <section aria-label="Loading dispatches" className="max-w-4xl">
      <div className="h-4 w-28 rounded bg-stone-200" />
      <div className="mt-4 h-10 w-2/3 rounded bg-stone-200" />
      <div className="mt-10 h-64 rounded-xl bg-stone-200" />
    </section>
  );
}

export function DispatchLogEmpty({ filtered = false }: { filtered?: boolean }) {
  return (
    <section className="max-w-3xl rounded-xl border border-stone-200 bg-white p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
        Dispatches
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-slate-950">
        {filtered ? "No dispatches match these filters." : "No dispatch attempts yet."}
      </h2>
      <p className="mt-3 text-slate-600">
        {filtered
          ? "Adjust repo, slice, or status filters to widen the dispatch log."
          : "OSS equivalent: inspect orchestrator run artifacts and manual webhook POST logs until hosted dispatch is enabled."}
      </p>
    </section>
  );
}

export function DispatchLogError() {
  return (
    <section className="max-w-3xl rounded-xl border border-rose-200 bg-rose-50 p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-700">
        Dispatch log unavailable
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-rose-950">
        Could not load dispatch projection.
      </h2>
      <p className="mt-3 text-rose-800">
        Check that `drake-api` is running and the dispatch read endpoint is
        available.
      </p>
    </section>
  );
}
