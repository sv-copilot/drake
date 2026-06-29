"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { fetchDispatch, type DispatchSummary } from "@/lib/api-client";

export function DispatchDetail({ dispatchId }: { dispatchId: string }) {
  const dispatchQuery = useQuery({
    queryKey: ["dispatch", dispatchId],
    queryFn: () => fetchDispatch(dispatchId),
  });

  if (dispatchQuery.isLoading) {
    return <DispatchDetailLoading />;
  }

  if (dispatchQuery.isError || !dispatchQuery.data) {
    return <DispatchDetailError dispatchId={dispatchId} />;
  }

  return <DispatchDetailContent dispatch={dispatchQuery.data} />;
}

export function DispatchDetailContent({
  dispatch,
}: {
  dispatch: DispatchSummary;
}) {
  return (
    <section className="max-w-4xl">
      <Link
        href="/dispatches"
        className="text-sm font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
      >
        Back to dispatches
      </Link>
      <p className="mt-8 text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
        Dispatch detail
      </p>
      <h2 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
        {dispatch.dispatch_id}
      </h2>
      <p className="mt-4 text-lg leading-8 text-slate-600">
        Read-only dispatch provenance for {dispatch.repo_id} / {dispatch.slice_id}.
      </p>

      <dl className="mt-10 grid gap-px overflow-hidden rounded-xl border border-stone-200 bg-stone-200 sm:grid-cols-2 xl:grid-cols-4">
        <DetailTerm label="Status" value={dispatch.status} />
        <DetailTerm label="Adapter" value={dispatch.adapter_type ?? "unknown"} />
        <DetailTerm label="Retries" value={String(dispatch.retry_count)} />
        <DetailTerm
          label="Chain back"
          value={dispatch.chain_back === undefined ? "not declared" : String(dispatch.chain_back)}
        />
      </dl>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-stone-200 bg-white p-5">
          <h3 className="font-medium text-slate-950">Target</h3>
          <dl className="mt-4 space-y-3 text-sm">
            <DetailLine label="Repository" value={dispatch.repo_id} />
            <DetailLine label="Slice" value={dispatch.slice_id} />
            <DetailLine label="Worker" value={dispatch.worker_id} />
            <DetailLine label="Task packet" value={dispatch.task_packet_id ?? "not declared"} />
          </dl>
        </section>

        <section className="rounded-xl border border-stone-200 bg-white p-5">
          <h3 className="font-medium text-slate-950">Webhook provenance</h3>
          <dl className="mt-4 space-y-3 text-sm">
            <DetailLine
              label="Webhook env"
              value={dispatch.webhook_url_env_name ?? "not declared"}
            />
            <DetailLine label="Dispatched at" value={dispatch.dispatched_at} />
            <DetailLine
              label="Error summary"
              value={dispatch.error_summary ?? "none"}
            />
          </dl>
          <p className="mt-5 rounded-lg border border-stone-200 bg-stone-50 p-3 text-sm text-slate-600">
            Env var names only; webhook values are never rendered in this view.
          </p>
        </section>
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

export function DispatchDetailLoading() {
  return (
    <section aria-label="Loading dispatch detail" className="max-w-4xl">
      <div className="h-4 w-28 rounded bg-stone-200" />
      <div className="mt-4 h-10 w-2/3 rounded bg-stone-200" />
      <div className="mt-10 h-64 rounded-xl bg-stone-200" />
    </section>
  );
}

export function DispatchDetailError({ dispatchId }: { dispatchId: string }) {
  return (
    <section className="max-w-3xl rounded-xl border border-rose-200 bg-rose-50 p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-700">
        Dispatch unavailable
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-rose-950">
        Could not load {dispatchId}.
      </h2>
      <p className="mt-3 text-rose-800">
        Check that `drake-api` is running and the dispatch exists in the read
        projection.
      </p>
    </section>
  );
}
