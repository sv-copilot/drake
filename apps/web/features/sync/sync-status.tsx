"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchSyncStatus, type SyncStatusSummary } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export function SyncStatus() {
  const syncQuery = useQuery({
    queryKey: ["sync-status"],
    queryFn: fetchSyncStatus,
  });

  if (syncQuery.isLoading) {
    return <SyncStatusLoading />;
  }

  if (syncQuery.isError || !syncQuery.data) {
    return <SyncStatusError />;
  }

  return <SyncStatusContent status={syncQuery.data} />;
}

export function SyncStatusContent({ status }: { status: SyncStatusSummary }) {
  const mode = sourceMode(status);

  return (
    <section>
      <div className="max-w-4xl">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
          Sync
        </p>
        <h2 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
          Registry cache and source file freshness.
        </h2>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-600">
          Read-only sync visibility for the hosted API cache. This page shows
          whether the UI is backed by a synced registry or fixture fallback data.
        </p>
      </div>

      <dl className="mt-10 grid gap-px overflow-hidden rounded-xl border border-stone-200 bg-stone-200 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Status" value={status.status} />
        <Metric label="Source mode" value={mode} />
        <Metric label="Projects" value={String(status.project_count)} />
        <Metric label="Trees" value={String(status.dependency_tree_count)} />
      </dl>

      <div className="mt-8 rounded-xl border border-stone-200 bg-white p-5">
        <div className="flex flex-wrap items-center gap-3">
          <span
            className={cn(
              "rounded-full px-2.5 py-1 text-xs font-medium",
              status.is_stale
                ? "bg-amber-100 text-amber-900"
                : "bg-emerald-100 text-emerald-800",
            )}
          >
            {status.is_stale ? "Stale" : "Fresh"}
          </span>
          <span className="text-sm text-slate-600">
            Stale after {status.stale_after_seconds}s
          </span>
        </div>
        <p className="mt-4 text-sm text-slate-600">
          Last synced: {status.last_synced_at ?? "not synced yet"}
        </p>
      </div>

      <div className="mt-8 overflow-hidden rounded-xl border border-stone-200 bg-white">
        <div className="border-b border-stone-200 px-5 py-4">
          <h3 className="font-medium text-slate-950">Synced files</h3>
          <p className="mt-1 text-sm text-slate-600">
            File provenance only; token values and secret material are not
            displayed.
          </p>
        </div>
        {status.files.length === 0 ? (
          <p className="px-5 py-5 text-sm text-slate-600">
            No files cached yet. Trigger GitHub read sync from the API when a
            staging-scoped read token is available.
          </p>
        ) : (
          <div className="divide-y divide-stone-200">
            {status.files.map((file) => (
              <FileRow key={`${file.repo}:${file.ref}:${file.path}`} file={file} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white p-5">
      <dt className="text-sm text-slate-600">{label}</dt>
      <dd className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        {value}
      </dd>
    </div>
  );
}

function FileRow({ file }: { file: SyncStatusSummary["files"][number] }) {
  return (
    <article className="grid grid-cols-[1fr_1fr_0.8fr] gap-4 px-5 py-5 text-sm">
      <div>
        <p className="font-medium text-slate-950">{file.repo}</p>
        <p className="mt-1 font-mono text-xs text-slate-500">{file.ref}</p>
      </div>
      <p className="break-words font-mono text-xs text-slate-600">{file.path}</p>
      <div>
        <p className="text-slate-950">{file.source}</p>
        <p className="mt-1 break-words font-mono text-xs text-slate-500">
          {file.sha ?? "no sha"}
        </p>
      </div>
    </article>
  );
}

export function sourceMode(status: SyncStatusSummary) {
  if (status.files.length === 0) {
    return "empty";
  }
  if (status.files.every((file) => file.source === "example_fixture")) {
    return "fixture fallback";
  }
  return "synced cache";
}

export function SyncStatusLoading() {
  return (
    <section aria-label="Loading sync status" className="max-w-4xl">
      <div className="h-4 w-28 rounded bg-stone-200" />
      <div className="mt-4 h-10 w-2/3 rounded bg-stone-200" />
      <div className="mt-10 h-64 rounded-xl bg-stone-200" />
    </section>
  );
}

export function SyncStatusError() {
  return (
    <section className="max-w-3xl rounded-xl border border-rose-200 bg-rose-50 p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-700">
        Sync unavailable
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-rose-950">
        Could not load sync status.
      </h2>
      <p className="mt-3 text-rose-800">
        Check that `drake-api` is running and the sync status endpoint is
        available.
      </p>
    </section>
  );
}
