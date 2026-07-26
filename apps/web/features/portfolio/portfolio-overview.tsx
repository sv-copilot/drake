"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import {
  fetchDispatches,
  fetchPortfolio,
  fetchRepos,
  fetchRuns,
  type PortfolioSummary,
  type RepoSummary,
} from "@/lib/api-client";
import {
  countForRepo,
  repoEvidenceCounts,
  type EvidenceCount,
} from "@/lib/evidence-counts";
import { evidenceSearchString } from "@/lib/evidence-filters";
import { cn } from "@/lib/utils";

export function PortfolioOverview() {
  const portfolioQuery = useQuery({
    queryKey: ["portfolio"],
    queryFn: fetchPortfolio,
  });
  const reposQuery = useQuery({
    queryKey: ["repos"],
    queryFn: fetchRepos,
  });
  const runsQuery = useQuery({
    queryKey: ["runs"],
    queryFn: fetchRuns,
  });
  const dispatchesQuery = useQuery({
    queryKey: ["dispatches"],
    queryFn: fetchDispatches,
  });

  if (portfolioQuery.isLoading || reposQuery.isLoading) {
    return <PortfolioLoading />;
  }

  if (portfolioQuery.isError || reposQuery.isError) {
    return <PortfolioError />;
  }

  if (!portfolioQuery.data) {
    return <PortfolioError />;
  }

  return (
    <PortfolioOverviewContent
      portfolio={portfolioQuery.data}
      repos={reposQuery.data ?? []}
      evidenceCounts={repoEvidenceCounts(
        runsQuery.data ?? [],
        dispatchesQuery.data ?? [],
      )}
    />
  );
}

export function PortfolioOverviewContent({
  portfolio,
  repos,
  evidenceCounts = {},
}: {
  portfolio: PortfolioSummary;
  repos: RepoSummary[];
  evidenceCounts?: Record<string, EvidenceCount>;
}) {
  if (repos.length === 0) {
    return <PortfolioEmpty />;
  }

  return (
    <section>
      <div className="max-w-4xl">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
          Portfolio
        </p>
        <h2 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
          Registered repositories and readiness signals.
        </h2>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-600">
          Read-only projection of registry state, worker routing, automation
          flags, and slice readiness. Source paths stay visible so operators can
          trace every fact back to Git.
        </p>
      </div>

      <dl className="mt-10 grid gap-px overflow-hidden rounded-xl border border-stone-200 bg-stone-200 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Repos" value={portfolio.repo_count} />
        <Metric
          label="Automation enabled"
          value={portfolio.automation_enabled_count}
        />
        <Metric label="Ready slices" value={portfolio.ready_slice_count} />
        <Metric label="Running slices" value={portfolio.running_slice_count} />
      </dl>

      <div className="mt-10 overflow-hidden rounded-xl border border-stone-200 bg-white">
        <div className="border-b border-stone-200 px-5 py-4">
          <h3 className="font-medium text-slate-950">Registered repos</h3>
          <p className="mt-1 text-sm text-slate-600">
            Fan-out limit {portfolio.global_fanout_limit}; same-repo idle cap{" "}
            {portfolio.same_repo_max_when_others_idle ?? 1}.
          </p>
        </div>
        <div className="divide-y divide-stone-200">
          {repos.map((repo) => (
            <RepoRow
              key={repo.id}
              repo={repo}
              evidence={countForRepo(evidenceCounts, repo.id)}
            />
          ))}
        </div>
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

function RepoRow({
  repo,
  evidence,
}: {
  repo: RepoSummary;
  evidence: EvidenceCount;
}) {
  const readinessEntries = Object.entries(repo.readiness);
  const primaryWorker = repo.workers.find((worker) => worker.primary) ?? repo.workers[0];
  const repoSearch = evidenceSearchString({
    repoId: repo.id,
    sliceId: "",
    status: "",
  });

  return (
    <article className="px-5 py-5">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href={`/repos/${encodeURIComponent(repo.id)}`}
              className="text-lg font-semibold text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
            >
              {repo.id}
            </Link>
            <StatusPill enabled={repo.automation_enabled} />
          </div>
          <p className="mt-1 font-mono text-sm text-slate-600">
            {repo.github_slug} · {repo.integration_branch}
          </p>
        </div>
        <div className="grid grid-cols-4 gap-4 text-sm">
          <MiniMetric label="Ready" value={repo.slice_summary.ready_count} />
          <MiniMetric label="Running" value={repo.slice_summary.running_count} />
          <MiniMetric label="Blocked" value={repo.slice_summary.blocked_count} />
          <MiniMetric
            label="Validated"
            value={repo.slice_summary.validated_count}
          />
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div>
          <p className="text-sm font-medium text-slate-950">Readiness</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {readinessEntries.map(([key, value]) => (
              <span
                key={key}
                className={cn(
                  "rounded-full border px-2.5 py-1 text-xs",
                  value
                    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                    : "border-amber-200 bg-amber-50 text-amber-800",
                )}
              >
                {key.replaceAll("_", " ")}
              </span>
            ))}
          </div>
        </div>
        <div>
          <p className="text-sm font-medium text-slate-950">Primary worker</p>
          <p className="mt-2 text-sm text-slate-600">
            {primaryWorker
              ? `${primaryWorker.adapter_type} · ${primaryWorker.role} · ${
                  primaryWorker.enabled ? "enabled" : "disabled"
                }`
              : "No worker declared"}
          </p>
          <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">
            Credential refs are names only
          </p>
        </div>
      </div>

      <div className="mt-5 border-l border-stone-300 pl-4">
        <p className="text-sm font-medium text-slate-950">Repo-native source</p>
        <p className="mt-1 font-mono text-sm text-slate-600">
          {repo.repo_native_paths.dependency_tree}
        </p>
      </div>
      <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <Link
          href={`/repos/${repo.id}/slices`}
          className="font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
        >
          Open slice board
        </Link>
        <Link
          href={`/runs${repoSearch}`}
          className="font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
        >
          Runs ({evidence.runs})
        </Link>
        <Link
          href={`/dispatches${repoSearch}`}
          className="font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
        >
          Dispatches ({evidence.dispatches})
        </Link>
      </div>
    </article>
  );
}

function StatusPill({ enabled }: { enabled: boolean }) {
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

function MiniMetric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 font-semibold text-slate-950">{value}</p>
    </div>
  );
}

export function PortfolioLoading() {
  return (
    <section aria-label="Loading portfolio" className="max-w-4xl">
      <div className="h-4 w-28 rounded bg-stone-200" />
      <div className="mt-4 h-10 w-2/3 rounded bg-stone-200" />
      <div className="mt-10 grid gap-4 sm:grid-cols-2">
        {[0, 1, 2, 3].map((item) => (
          <div key={item} className="h-28 rounded-xl bg-stone-200" />
        ))}
      </div>
    </section>
  );
}

export function PortfolioEmpty() {
  return (
    <section className="max-w-3xl rounded-xl border border-stone-200 bg-white p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
        Portfolio
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-slate-950">
        No registered repos yet.
      </h2>
      <p className="mt-3 text-slate-600">
        Run GitHub read sync after configuring a fictional or private registry
        source. The hosted UI will not invent repos without registry data.
      </p>
    </section>
  );
}

export function PortfolioError() {
  return (
    <section className="max-w-3xl rounded-xl border border-rose-200 bg-rose-50 p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-700">
        Portfolio unavailable
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-rose-950">
        Could not load registry projection.
      </h2>
      <p className="mt-3 text-rose-800">
        Check that `drake-api` is running and `NEXT_PUBLIC_API_URL` points at the
        hosted API.
      </p>
    </section>
  );
}
