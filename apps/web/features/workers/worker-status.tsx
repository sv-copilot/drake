"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo } from "react";

import { fetchRepos, type RepoSummary, type WorkerSummary } from "@/lib/api-client";
import {
  EMPTY_EVIDENCE_FILTERS,
  evidenceSearchString,
} from "@/lib/evidence-filters";
import { useEvidenceUrlFilters } from "@/lib/use-evidence-url-filters";
import { cn } from "@/lib/utils";

export function WorkerStatus() {
  const reposQuery = useQuery({
    queryKey: ["repos"],
    queryFn: fetchRepos,
  });
  const [filters, setFilters] = useEvidenceUrlFilters();

  if (reposQuery.isLoading) {
    return <WorkerStatusLoading />;
  }

  if (reposQuery.isError) {
    return <WorkerStatusError />;
  }

  return (
    <WorkerStatusContent
      repos={reposQuery.data ?? []}
      repoId={filters.repoId}
      onRepoChange={(repoId) =>
        setFilters({ ...EMPTY_EVIDENCE_FILTERS, repoId })
      }
    />
  );
}

export function WorkerStatusContent({
  repos,
  repoId = "",
  onRepoChange,
}: {
  repos: RepoSummary[];
  repoId?: string;
  onRepoChange?: (repoId: string) => void;
}) {
  const allRows = useMemo(() => workerRows(repos), [repos]);
  const repoOptions = useMemo(
    () => [...new Set(repos.map((repo) => repo.id))].sort(),
    [repos],
  );

  if (allRows.length === 0) {
    return <WorkerStatusEmpty />;
  }

  const rows = repoId
    ? allRows.filter((row) => row.repo.id === repoId)
    : allRows;

  return (
    <section>
      <div className="max-w-4xl">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
          Workers
        </p>
        <h2 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
          Adapter status across agent runtimes.
        </h2>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-600">
          Read-only projection of registry worker declarations. Credential refs
          and webhook values are shown as environment variable names only.
        </p>
      </div>

      <div className="mt-10 grid gap-3 rounded-xl border border-stone-200 bg-white p-4 md:max-w-xs">
        <label className="text-sm">
          <span className="font-medium text-slate-950">Repo</span>
          <select
            value={repoId}
            onChange={(event) => onRepoChange?.(event.target.value)}
            className="mt-2 block w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-slate-950"
          >
            <option value="">All</option>
            {repoOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </div>

      {rows.length === 0 ? (
        <WorkerStatusEmpty filtered repoId={repoId} />
      ) : (
        <div className="mt-8 overflow-hidden rounded-xl border border-stone-200 bg-white">
          <div className="grid grid-cols-[1.2fr_1fr_1fr_1fr] gap-4 border-b border-stone-200 px-5 py-3 text-xs font-medium uppercase tracking-wide text-slate-500">
            <span>Worker</span>
            <span>Adapter</span>
            <span>Status</span>
            <span>Env names</span>
          </div>
          <div className="divide-y divide-stone-200">
            {rows.map((row) => (
              <WorkerRow key={`${row.repo.id}:${row.worker.worker_id}`} {...row} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function WorkerRow({
  repo,
  worker,
}: {
  repo: RepoSummary;
  worker: WorkerSummary;
}) {
  const webhookNames = Object.values(worker.webhook_env_names ?? {});
  const credentialRefs = worker.credential_ref_names ?? [];

  return (
    <article className="grid grid-cols-[1.2fr_1fr_1fr_1fr] gap-4 px-5 py-5 text-sm">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium text-slate-950">{worker.worker_id}</p>
          {worker.primary ? (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
              Primary
            </span>
          ) : null}
        </div>
        <p className="mt-1 font-mono text-xs text-slate-500">
          <Link
            href={`/repos/${encodeURIComponent(repo.id)}`}
            className="underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
          >
            {repo.id}
          </Link>{" "}
          · {worker.role}
        </p>
        <Link
          href={`/dispatches${evidenceSearchString({
            repoId: repo.id,
            sliceId: "",
            status: "",
            workerId: worker.worker_id,
          })}`}
          className="mt-2 inline-flex text-xs font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
        >
          View dispatches
        </Link>
      </div>
      <div>
        <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-800">
          {worker.adapter_type}
        </span>
        {worker.model_slug ? (
          <p className="mt-2 text-xs text-slate-500">{worker.model_slug}</p>
        ) : null}
      </div>
      <div>
        <span
          className={cn(
            "rounded-full px-2.5 py-1 text-xs font-medium",
            worker.enabled
              ? "bg-emerald-100 text-emerald-800"
              : "bg-slate-100 text-slate-700",
          )}
        >
          {worker.enabled ? "Enabled" : "Disabled"}
        </span>
      </div>
      <div className="space-y-1">
        {[...webhookNames, ...credentialRefs].map((name) => (
          <p key={name} className="break-words font-mono text-xs text-slate-600">
            {name}
          </p>
        ))}
      </div>
    </article>
  );
}

export function workerRows(repos: RepoSummary[]) {
  return repos.flatMap((repo) =>
    repo.workers.map((worker) => ({
      repo,
      worker,
    })),
  );
}

export function WorkerStatusLoading() {
  return (
    <section aria-label="Loading workers" className="max-w-4xl">
      <div className="h-4 w-28 rounded bg-stone-200" />
      <div className="mt-4 h-10 w-2/3 rounded bg-stone-200" />
      <div className="mt-10 h-64 rounded-xl bg-stone-200" />
    </section>
  );
}

export function WorkerStatusEmpty({
  filtered = false,
  repoId = "",
}: {
  filtered?: boolean;
  repoId?: string;
}) {
  return (
    <section className="mt-8 max-w-3xl rounded-xl border border-stone-200 bg-white p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
        Workers
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-slate-950">
        {filtered
          ? `No workers declared for ${repoId || "this repo"}.`
          : "No workers configured."}
      </h2>
      <p className="mt-3 text-slate-600">
        {filtered
          ? "Clear the repo filter to see workers across all registered repositories."
          : "Add registry worker declarations before this view can report adapter status."}
      </p>
    </section>
  );
}

export function WorkerStatusError() {
  return (
    <section className="max-w-3xl rounded-xl border border-rose-200 bg-rose-50 p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-700">
        Workers unavailable
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-rose-950">
        Could not load worker registry projection.
      </h2>
      <p className="mt-3 text-rose-800">
        Check that `drake-api` is running and the registry read endpoint is
        available.
      </p>
    </section>
  );
}
