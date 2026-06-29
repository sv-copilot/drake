"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { fetchRun, type RunSummary } from "@/lib/api-client";

export function RunDetail({ runId }: { runId: string }) {
  const runQuery = useQuery({
    queryKey: ["run", runId],
    queryFn: () => fetchRun(runId),
  });

  if (runQuery.isLoading) {
    return <RunDetailLoading />;
  }

  if (runQuery.isError || !runQuery.data) {
    return <RunDetailError runId={runId} />;
  }

  return <RunDetailContent run={runQuery.data} />;
}

export function RunDetailContent({ run }: { run: RunSummary }) {
  return (
    <section className="max-w-4xl">
      <Link
        href="/runs"
        className="text-sm font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
      >
        Back to runs
      </Link>
      <p className="mt-8 text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
        Run detail
      </p>
      <h2 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
        {run.run_id}
      </h2>
      <p className="mt-4 text-lg leading-8 text-slate-600">
        Evidence and provenance summary for {run.repo_id}
        {run.slice_id ? ` / ${run.slice_id}` : ""}.
      </p>

      <dl className="mt-10 grid gap-px overflow-hidden rounded-xl border border-stone-200 bg-stone-200 sm:grid-cols-2">
        <DetailTerm label="Status" value={run.status} />
        <DetailTerm label="Runtime" value={run.runtime} />
        <DetailTerm label="Model" value={run.model_slug ?? "unknown"} />
        <DetailTerm label="Evidence" value={run.evidence_status ?? "pending"} />
      </dl>

      <div className="mt-8 rounded-xl border border-stone-200 bg-white p-5">
        <h3 className="font-medium text-slate-950">Timeline</h3>
        <div className="mt-4 space-y-3 text-sm text-slate-600">
          <p>Started: {run.started_at}</p>
          {run.completed_at ? <p>Completed: {run.completed_at}</p> : null}
        </div>
      </div>

      <div className="mt-8 rounded-xl border border-stone-200 bg-white p-5">
        <h3 className="font-medium text-slate-950">Provenance</h3>
        <dl className="mt-4 space-y-3 text-sm">
          <DetailLine label="Task packet" value={run.task_id ?? "not declared"} />
          <DetailLine label="Artifact source" value={run.artifact_source ?? "not uploaded"} />
          <DetailLine
            label="Repo artifact path"
            value={run.repo_native_artifact_path ?? "not declared"}
          />
          <DetailLine label="Handoff path" value={run.handoff_path ?? "not declared"} />
        </dl>
        {run.pr_url ? (
          <Link
            href={run.pr_url}
            target="_blank"
            rel="noreferrer"
            className="mt-5 inline-flex text-sm font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
          >
            Open PR
          </Link>
        ) : null}
      </div>
    </section>
  );
}

function DetailTerm({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white p-5">
      <dt className="text-sm text-slate-600">{label}</dt>
      <dd className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        {value}
      </dd>
    </div>
  );
}

function DetailLine({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 break-words font-mono text-slate-700">{value}</dd>
    </div>
  );
}

export function RunDetailLoading() {
  return (
    <section aria-label="Loading run detail" className="max-w-4xl">
      <div className="h-4 w-28 rounded bg-stone-200" />
      <div className="mt-4 h-10 w-2/3 rounded bg-stone-200" />
      <div className="mt-10 h-64 rounded-xl bg-stone-200" />
    </section>
  );
}

export function RunDetailError({ runId }: { runId: string }) {
  return (
    <section className="max-w-3xl rounded-xl border border-rose-200 bg-rose-50 p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-700">
        Run unavailable
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-rose-950">
        Could not load {runId}.
      </h2>
      <p className="mt-3 text-rose-800">
        Check that `drake-api` is running and that the run exists in the read
        projection.
      </p>
    </section>
  );
}
