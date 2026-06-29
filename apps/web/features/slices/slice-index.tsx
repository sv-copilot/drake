"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { fetchRepos, type RepoSummary } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export function SliceIndex() {
  const reposQuery = useQuery({
    queryKey: ["repos"],
    queryFn: fetchRepos,
  });

  if (reposQuery.isLoading) {
    return <SliceIndexLoading />;
  }

  if (reposQuery.isError) {
    return <SliceIndexError />;
  }

  return <SliceIndexContent repos={reposQuery.data ?? []} />;
}

export function SliceIndexContent({ repos }: { repos: RepoSummary[] }) {
  if (repos.length === 0) {
    return <SliceIndexEmpty />;
  }

  const totals = sliceTotals(repos);

  return (
    <section>
      <div className="max-w-4xl">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
          Slices
        </p>
        <h2 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
          Dependency states before unattended work.
        </h2>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-600">
          Repo-aware index of slice boards. Use this page to find ready work,
          gated work, and the Git source of each dependency tree.
        </p>
      </div>

      <dl className="mt-10 grid gap-px overflow-hidden rounded-xl border border-stone-200 bg-stone-200 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Ready" value={totals.ready_count} />
        <Metric label="Running" value={totals.running_count} />
        <Metric label="Blocked" value={totals.blocked_count} />
        <Metric label="Validated" value={totals.validated_count} />
      </dl>

      <div className="mt-10 overflow-hidden rounded-xl border border-stone-200 bg-white">
        <div className="grid grid-cols-[1.3fr_1fr_1fr] gap-4 border-b border-stone-200 px-5 py-3 text-xs font-medium uppercase tracking-wide text-slate-500">
          <span>Repository</span>
          <span>Slice state</span>
          <span>Source</span>
        </div>
        <div className="divide-y divide-stone-200">
          {repos.map((repo) => (
            <SliceRepoRow key={repo.id} repo={repo} />
          ))}
        </div>
      </div>
    </section>
  );
}

function SliceRepoRow({ repo }: { repo: RepoSummary }) {
  const hasBlocked = repo.slice_summary.blocked_count > 0;

  return (
    <article className="grid grid-cols-[1.3fr_1fr_1fr] gap-4 px-5 py-5 text-sm">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href={`/repos/${encodeURIComponent(repo.id)}/slices`}
            className="font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
          >
            {repo.id}
          </Link>
          <span
            className={cn(
              "rounded-full px-2.5 py-1 text-xs font-medium",
              hasBlocked
                ? "bg-amber-100 text-amber-900"
                : "bg-emerald-100 text-emerald-800",
            )}
          >
            {hasBlocked ? "Needs review" : "No blockers"}
          </span>
        </div>
        <p className="mt-1 font-mono text-xs text-slate-500">
          {repo.github_slug} · {repo.integration_branch}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3 text-xs">
        <MiniMetric label="Ready" value={repo.slice_summary.ready_count} />
        <MiniMetric label="Running" value={repo.slice_summary.running_count} />
        <MiniMetric label="Blocked" value={repo.slice_summary.blocked_count} />
        <MiniMetric label="Validated" value={repo.slice_summary.validated_count} />
      </div>
      <div>
        <p className="break-words font-mono text-xs text-slate-600">
          {repo.repo_native_paths.dependency_tree}
        </p>
        <Link
          href={`/repos/${encodeURIComponent(repo.id)}/slices`}
          className="mt-3 inline-flex text-sm font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
        >
          Open slice board
        </Link>
      </div>
    </article>
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

function MiniMetric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 font-semibold text-slate-950">{value}</p>
    </div>
  );
}

export function sliceTotals(repos: RepoSummary[]) {
  return repos.reduce(
    (totals, repo) => ({
      ready_count: totals.ready_count + repo.slice_summary.ready_count,
      running_count: totals.running_count + repo.slice_summary.running_count,
      blocked_count: totals.blocked_count + repo.slice_summary.blocked_count,
      validated_count: totals.validated_count + repo.slice_summary.validated_count,
    }),
    {
      ready_count: 0,
      running_count: 0,
      blocked_count: 0,
      validated_count: 0,
    },
  );
}

export function SliceIndexLoading() {
  return (
    <section aria-label="Loading slice index" className="max-w-4xl">
      <div className="h-4 w-28 rounded bg-stone-200" />
      <div className="mt-4 h-10 w-2/3 rounded bg-stone-200" />
      <div className="mt-10 h-64 rounded-xl bg-stone-200" />
    </section>
  );
}

export function SliceIndexEmpty() {
  return (
    <section className="max-w-3xl rounded-xl border border-stone-200 bg-white p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
        Slices
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-slate-950">
        No repo slice boards yet.
      </h2>
      <p className="mt-3 text-slate-600">
        Run GitHub read sync after configuring a registry and dependency tree.
      </p>
    </section>
  );
}

export function SliceIndexError() {
  return (
    <section className="max-w-3xl rounded-xl border border-rose-200 bg-rose-50 p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-700">
        Slices unavailable
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-rose-950">
        Could not load repo slice index.
      </h2>
      <p className="mt-3 text-rose-800">
        Check that `drake-api` is running and the repos read endpoint is
        available.
      </p>
    </section>
  );
}
