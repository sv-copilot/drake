"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchRepos, type RepoSummary, type WorkerSummary } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export function WorkerStatus() {
  const reposQuery = useQuery({
    queryKey: ["repos"],
    queryFn: fetchRepos,
  });

  if (reposQuery.isLoading) {
    return <WorkerStatusLoading />;
  }

  if (reposQuery.isError) {
    return <WorkerStatusError />;
  }

  return <WorkerStatusContent repos={reposQuery.data ?? []} />;
}

export function WorkerStatusContent({ repos }: { repos: RepoSummary[] }) {
  const rows = workerRows(repos);

  if (rows.length === 0) {
    return <WorkerStatusEmpty />;
  }

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

      <div className="mt-10 overflow-hidden rounded-xl border border-stone-200 bg-white">
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
          {repo.id} · {worker.role}
        </p>
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

export function WorkerStatusEmpty() {
  return (
    <section className="max-w-3xl rounded-xl border border-stone-200 bg-white p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
        Workers
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-slate-950">
        No workers configured.
      </h2>
      <p className="mt-3 text-slate-600">
        Add registry worker declarations before this view can report adapter
        status.
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
