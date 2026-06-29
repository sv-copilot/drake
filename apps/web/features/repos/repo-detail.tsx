"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { fetchRepo, type RepoSummary, type WorkerSummary } from "@/lib/api-client";
import { evidenceSearchString } from "@/lib/evidence-filters";
import { cn } from "@/lib/utils";

export function RepoDetail({ repoId }: { repoId: string }) {
  const repoQuery = useQuery({
    queryKey: ["repo", repoId],
    queryFn: () => fetchRepo(repoId),
  });

  if (repoQuery.isLoading) {
    return <RepoDetailLoading />;
  }

  if (repoQuery.isError || !repoQuery.data) {
    return <RepoDetailError repoId={repoId} />;
  }

  return <RepoDetailContent repo={repoQuery.data} />;
}

export function RepoDetailContent({ repo }: { repo: RepoSummary }) {
  const readinessEntries = Object.entries(repo.readiness);
  const sourceEntries = Object.entries(repo.repo_native_paths);
  const repoEvidenceSearch = evidenceSearchString({
    repoId: repo.id,
    sliceId: "",
    status: "",
  });

  return (
    <section>
      <div className="max-w-4xl">
        <Link
          href="/portfolio"
          className="text-sm font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
        >
          Back to portfolio
        </Link>
        <p className="mt-8 text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
          Repository
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <h2 className="text-4xl font-semibold tracking-tight text-slate-950">
            {repo.id}
          </h2>
          <AutomationBadge enabled={repo.automation_enabled} />
        </div>
        <p className="mt-4 font-mono text-sm text-slate-600">
          {repo.github_slug} · {repo.integration_branch}
        </p>
      </div>

      <dl className="mt-10 grid gap-px overflow-hidden rounded-xl border border-stone-200 bg-stone-200 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Ready" value={repo.slice_summary.ready_count} />
        <Metric label="Running" value={repo.slice_summary.running_count} />
        <Metric label="Blocked" value={repo.slice_summary.blocked_count} />
        <Metric label="Validated" value={repo.slice_summary.validated_count} />
      </dl>

      <div className="mt-8 grid gap-6 xl:grid-cols-[1fr_22rem]">
        <section className="rounded-xl border border-stone-200 bg-white p-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="font-medium text-slate-950">Readiness signals</h3>
              <p className="mt-1 text-sm text-slate-600">
                Registry-declared gates before unattended automation.
              </p>
            </div>
            <Link
              href={`/repos/${encodeURIComponent(repo.id)}/slices`}
              className="text-sm font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
            >
              Open slice board
            </Link>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            {readinessEntries.map(([key, value]) => (
              <span
                key={key}
                className={cn(
                  "rounded-full border px-2.5 py-1 text-xs",
                  value
                    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                    : "border-amber-200 bg-amber-50 text-amber-900",
                )}
              >
                {key.replaceAll("_", " ")}
              </span>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-stone-200 bg-white p-5">
          <h3 className="font-medium text-slate-950">Evidence links</h3>
          <div className="mt-4 space-y-3 text-sm">
            <DetailLink href={`/runs${repoEvidenceSearch}`} label="Run history" />
            <DetailLink href={`/dispatches${repoEvidenceSearch}`} label="Dispatch log" />
            <DetailLink href={`/workers${repoEvidenceSearch}`} label="Workers" />
            <DetailLink
              href={`/repos/${encodeURIComponent(repo.id)}/slices`}
              label="Slice board"
            />
          </div>
          <p className="mt-5 text-xs uppercase tracking-wide text-slate-500">
            Read-only navigation
          </p>
        </section>
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-2">
        <section className="rounded-xl border border-stone-200 bg-white">
          <div className="border-b border-stone-200 px-5 py-4">
            <h3 className="font-medium text-slate-950">Workers</h3>
            <p className="mt-1 text-sm text-slate-600">
              Credential refs and webhook values remain env names only.
            </p>
          </div>
          <div className="divide-y divide-stone-200">
            {repo.workers.length === 0 ? (
              <p className="px-5 py-5 text-sm text-slate-600">
                No workers declared for this repo.
              </p>
            ) : (
              repo.workers.map((worker) => (
                <WorkerCard key={worker.worker_id} repoId={repo.id} worker={worker} />
              ))
            )}
          </div>
        </section>

        <section className="rounded-xl border border-stone-200 bg-white">
          <div className="border-b border-stone-200 px-5 py-4">
            <h3 className="font-medium text-slate-950">Repo-native sources</h3>
            <p className="mt-1 text-sm text-slate-600">
              Paths are rendered as provenance, not editable configuration.
            </p>
          </div>
          <div className="divide-y divide-stone-200">
            {sourceEntries.map(([key, value]) => (
              <div key={key} className="px-5 py-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">
                  {key.replaceAll("_", " ")}
                </p>
                <p className="mt-1 break-words font-mono text-sm text-slate-700">
                  {value}
                </p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white p-5">
      <dt className="text-sm text-slate-600">{label}</dt>
      <dd className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
        {value}
      </dd>
    </div>
  );
}

function DetailLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="block rounded-lg border border-stone-200 px-3 py-2 font-medium text-slate-950 transition-colors hover:bg-stone-50"
    >
      {label}
    </Link>
  );
}

function WorkerCard({ repoId, worker }: { repoId: string; worker: WorkerSummary }) {
  const webhookNames = Object.values(worker.webhook_env_names ?? {});
  const credentialRefs = worker.credential_ref_names ?? [];
  const envNames = [...webhookNames, ...credentialRefs];

  return (
    <article className="px-5 py-5 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Link
          href={`/repos/${encodeURIComponent(repoId)}/workers/${encodeURIComponent(worker.worker_id)}`}
          className="font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
        >
          {worker.worker_id}
        </Link>
        {worker.primary ? (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
            Primary
          </span>
        ) : null}
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-xs font-medium",
            worker.enabled
              ? "bg-emerald-100 text-emerald-800"
              : "bg-slate-100 text-slate-700",
          )}
        >
          {worker.enabled ? "Enabled" : "Disabled"}
        </span>
      </div>
      <p className="mt-2 text-slate-600">
        {worker.adapter_type} · {worker.role}
        {worker.model_slug ? ` · ${worker.model_slug}` : ""}
      </p>
      <div className="mt-3 space-y-1">
        {envNames.length === 0 ? (
          <p className="text-xs text-slate-500">No env refs declared.</p>
        ) : (
          envNames.map((name) => (
            <p key={name} className="break-words font-mono text-xs text-slate-600">
              {name}
            </p>
          ))
        )}
      </div>
    </article>
  );
}

function AutomationBadge({ enabled }: { enabled: boolean }) {
  return (
    <span
      className={cn(
        "rounded-full px-2.5 py-1 text-xs font-medium",
        enabled ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700",
      )}
    >
      {enabled ? "Automation on" : "Automation off"}
    </span>
  );
}

export function RepoDetailLoading() {
  return (
    <section aria-label="Loading repo detail" className="max-w-4xl">
      <div className="h-4 w-28 rounded bg-stone-200" />
      <div className="mt-4 h-10 w-2/3 rounded bg-stone-200" />
      <div className="mt-10 h-64 rounded-xl bg-stone-200" />
    </section>
  );
}

export function RepoDetailError({ repoId }: { repoId: string }) {
  return (
    <section className="max-w-3xl rounded-xl border border-rose-200 bg-rose-50 p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-700">
        Repo unavailable
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-rose-950">
        Could not load {repoId}.
      </h2>
      <p className="mt-3 text-rose-800">
        Check that `drake-api` is running and the repo exists in the registry
        projection.
      </p>
    </section>
  );
}
