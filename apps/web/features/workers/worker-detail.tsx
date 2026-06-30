"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import {
  fetchDispatches,
  fetchRepo,
  type DispatchSummary,
  type RepoSummary,
  type WorkerSummary,
} from "@/lib/api-client";
import { evidenceSearchString } from "@/lib/evidence-filters";
import { cn } from "@/lib/utils";

export function WorkerDetail({
  repoId,
  workerId,
}: {
  repoId: string;
  workerId: string;
}) {
  const repoQuery = useQuery({
    queryKey: ["repo", repoId],
    queryFn: () => fetchRepo(repoId),
  });
  const dispatchesQuery = useQuery({
    queryKey: ["dispatches"],
    queryFn: fetchDispatches,
  });

  if (repoQuery.isLoading) {
    return <WorkerDetailLoading />;
  }

  if (repoQuery.isError || !repoQuery.data) {
    return <WorkerDetailError repoId={repoId} workerId={workerId} />;
  }

  const worker = repoQuery.data.workers.find((item) => item.worker_id === workerId);

  if (!worker) {
    return <WorkerDetailNotFound repoId={repoId} workerId={workerId} />;
  }

  const dispatches = (dispatchesQuery.data ?? []).filter(
    (dispatch) =>
      dispatch.repo_id === repoId && dispatch.worker_id === workerId,
  );

  return (
    <WorkerDetailContent
      repo={repoQuery.data}
      worker={worker}
      dispatches={dispatches}
    />
  );
}

export function WorkerDetailContent({
  repo,
  worker,
  dispatches = [],
}: {
  repo: RepoSummary;
  worker: WorkerSummary;
  dispatches?: DispatchSummary[];
}) {
  const webhookNames = Object.values(worker.webhook_env_names ?? {});
  const credentialRefs = worker.credential_ref_names ?? [];
  const envNames = [...webhookNames, ...credentialRefs];
  const dispatchesHref = `/dispatches${evidenceSearchString({
    repoId: repo.id,
    sliceId: "",
    status: "",
    workerId: worker.worker_id,
  })}`;

  return (
    <section className="max-w-4xl">
      <Link
        href={`/repos/${encodeURIComponent(repo.id)}`}
        className="text-sm font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
      >
        Back to {repo.id}
      </Link>
      <p className="mt-8 text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
        Worker
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <h2 className="text-4xl font-semibold tracking-tight text-slate-950">
          {worker.worker_id}
        </h2>
        {worker.primary ? (
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-700">
            Primary
          </span>
        ) : null}
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
      <p className="mt-4 font-mono text-sm text-slate-600">
        {repo.github_slug} · {worker.role}
      </p>

      <dl className="mt-10 grid gap-px overflow-hidden rounded-xl border border-stone-200 bg-stone-200 sm:grid-cols-2 xl:grid-cols-3">
        <DetailTerm label="Adapter" value={worker.adapter_type} />
        <DetailTerm label="Role" value={worker.role} />
        <DetailTerm label="Model" value={worker.model_slug ?? "not declared"} />
      </dl>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-stone-200 bg-white p-5">
          <h3 className="font-medium text-slate-950">Environment references</h3>
          <p className="mt-1 text-sm text-slate-600">
            Credential and webhook references are environment variable names
            only; values are never rendered.
          </p>
          <div className="mt-4 space-y-1">
            {envNames.length === 0 ? (
              <p className="text-sm text-slate-500">No env refs declared.</p>
            ) : (
              envNames.map((name) => (
                <p
                  key={name}
                  className="break-words font-mono text-xs text-slate-600"
                >
                  {name}
                </p>
              ))
            )}
          </div>
        </section>

        <section className="rounded-xl border border-stone-200 bg-white p-5">
          <div className="flex items-center justify-between gap-4">
            <h3 className="font-medium text-slate-950">Dispatch history</h3>
            <Link
              href={dispatchesHref}
              className="text-sm font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
            >
              Open dispatch log
            </Link>
          </div>
          <div className="mt-4 space-y-2 text-sm">
            {dispatches.length === 0 ? (
              <p className="text-slate-500">
                No dispatches recorded for this worker.
              </p>
            ) : (
              dispatches.map((dispatch) => (
                <Link
                  key={dispatch.dispatch_id}
                  href={`/dispatches/${encodeURIComponent(dispatch.dispatch_id)}`}
                  className="block break-words rounded-lg border border-stone-200 px-3 py-2 font-medium text-slate-950 transition-colors hover:bg-stone-50"
                >
                  {dispatch.dispatch_id} · {dispatch.slice_id} · {dispatch.status}
                </Link>
              ))
            )}
          </div>
        </section>
      </div>
    </section>
  );
}

function DetailTerm({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white p-5">
      <dt className="text-sm text-slate-600">{label}</dt>
      <dd className="mt-2 break-words text-xl font-semibold leading-7 tracking-tight text-slate-950">
        {value}
      </dd>
    </div>
  );
}

export function WorkerDetailLoading() {
  return (
    <section aria-label="Loading worker detail" className="max-w-4xl">
      <div className="h-4 w-28 rounded bg-stone-200" />
      <div className="mt-4 h-10 w-2/3 rounded bg-stone-200" />
      <div className="mt-10 h-64 rounded-xl bg-stone-200" />
    </section>
  );
}

export function WorkerDetailNotFound({
  repoId,
  workerId,
}: {
  repoId: string;
  workerId: string;
}) {
  return (
    <section className="max-w-3xl rounded-xl border border-stone-200 bg-white p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
        Worker
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-slate-950">
        No worker {workerId} on {repoId}.
      </h2>
      <p className="mt-3 text-slate-600">
        This worker is not declared in the registry projection for {repoId}.
      </p>
      <Link
        href={`/repos/${encodeURIComponent(repoId)}`}
        className="mt-5 inline-flex text-sm font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
      >
        Back to {repoId}
      </Link>
    </section>
  );
}

export function WorkerDetailError({
  repoId,
  workerId,
}: {
  repoId: string;
  workerId: string;
}) {
  return (
    <section className="max-w-3xl rounded-xl border border-rose-200 bg-rose-50 p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-700">
        Worker unavailable
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-rose-950">
        Could not load {workerId} on {repoId}.
      </h2>
      <p className="mt-3 text-rose-800">
        Check that `drake-api` is running and the repo exists in the registry
        projection.
      </p>
    </section>
  );
}
