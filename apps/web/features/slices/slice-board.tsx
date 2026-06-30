"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";

import {
  fetchRepo,
  fetchRepoSlices,
  type RepoSummary,
  type SliceSummary,
} from "@/lib/api-client";
import { evidenceSearchString } from "@/lib/evidence-filters";
import { cn } from "@/lib/utils";

const STATE_ORDER = ["gated", "ready", "running", "blocked", "validated"];

export function SliceBoard({ repoId }: { repoId: string }) {
  const repoQuery = useQuery({
    queryKey: ["repo", repoId],
    queryFn: () => fetchRepo(repoId),
  });
  const slicesQuery = useQuery({
    queryKey: ["repo-slices", repoId],
    queryFn: () => fetchRepoSlices(repoId),
  });

  if (repoQuery.isLoading || slicesQuery.isLoading) {
    return <SliceBoardLoading />;
  }

  if (repoQuery.isError || slicesQuery.isError || !repoQuery.data) {
    return <SliceBoardError repoId={repoId} />;
  }

  return (
    <SliceBoardContent
      repo={repoQuery.data}
      slices={slicesQuery.data ?? []}
    />
  );
}

export function SliceBoardContent({
  repo,
  slices,
}: {
  repo: RepoSummary;
  slices: SliceSummary[];
}) {
  const [selectedId, setSelectedId] = useState<string | null>(
    slices[0]?.slice_id ?? null,
  );
  const selected = slices.find((slice) => slice.slice_id === selectedId) ?? slices[0];
  const grouped = useMemo(() => groupSlices(slices), [slices]);

  if (slices.length === 0) {
    return <SliceBoardEmpty repoId={repo.id} />;
  }

  return (
    <section>
      <div className="max-w-4xl">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
          Slice board
        </p>
        <h2 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
          {repo.id}: dependency states before unattended work.
        </h2>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-600">
          Read-only board grouped by lifecycle state. Gated slices are visually
          distinct so operator approvals stay visible before any dispatch.
        </p>
      </div>

      <div className="mt-10 grid gap-6 xl:grid-cols-[1fr_22rem]">
        <div className="space-y-5">
          {STATE_ORDER.map((state) => (
            <StateLane
              key={state}
              state={state}
              slices={grouped[state] ?? []}
              selectedId={selected?.slice_id}
              onSelect={setSelectedId}
            />
          ))}
        </div>
        {selected ? <SliceDetail repo={repo} slice={selected} /> : null}
      </div>
    </section>
  );
}

function StateLane({
  state,
  slices,
  selectedId,
  onSelect,
}: {
  state: string;
  slices: SliceSummary[];
  selectedId?: string;
  onSelect: (sliceId: string) => void;
}) {
  return (
    <section className="rounded-xl border border-stone-200 bg-white">
      <div className="flex items-center justify-between border-b border-stone-200 px-5 py-3">
        <h3 className="font-medium capitalize text-slate-950">{state}</h3>
        <span className="text-sm text-slate-500">{slices.length}</span>
      </div>
      <div className="divide-y divide-stone-200">
        {slices.length === 0 ? (
          <p className="px-5 py-4 text-sm text-slate-500">No slices in this lane.</p>
        ) : (
          slices.map((slice) => (
            <button
              key={slice.slice_id}
              type="button"
              onClick={() => onSelect(slice.slice_id)}
              className={cn(
                "block w-full px-5 py-4 text-left transition-colors hover:bg-stone-50",
                selectedId === slice.slice_id && "bg-stone-50",
                hasUnresolvedGates(slice) && "border-l-4 border-amber-500",
              )}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-slate-950">{slice.slice_id}</span>
                <StateBadge slice={slice} />
              </div>
              <p className="mt-1 text-sm text-slate-600">{slice.title}</p>
              <p className="mt-2 text-xs uppercase tracking-wide text-slate-500">
                #{slice.slice_number} · dependencies {slice.dependencies.length}
              </p>
            </button>
          ))
        )}
      </div>
    </section>
  );
}

function SliceDetail({ repo, slice }: { repo: RepoSummary; slice: SliceSummary }) {
  const href = `https://github.com/${repo.github_slug}/blob/${repo.integration_branch}/${slice.repo_native_path}`;
  const evidenceSearch = evidenceSearchString({
    repoId: repo.id,
    sliceId: slice.slice_id,
    status: "",
  });

  return (
    <aside className="h-fit rounded-xl border border-stone-200 bg-white p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
        Detail
      </p>
      <h3 className="mt-3 text-xl font-semibold text-slate-950">
        {slice.slice_id}
      </h3>
      <p className="mt-2 text-sm leading-6 text-slate-600">{slice.title}</p>

      <dl className="mt-5 space-y-4 text-sm">
        <DetailTerm label="State" value={slice.state} />
        <DetailTerm
          label="Automation eligible"
          value={slice.automation_eligible ? "yes" : "no"}
        />
        <DetailTerm
          label="Dependencies"
          value={
            slice.dependencies.length > 0 ? slice.dependencies.join(", ") : "none"
          }
        />
      </dl>

      {slice.operator_gates.length > 0 ? (
        <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-medium text-amber-950">Operator gates</p>
          <ul className="mt-2 space-y-1 text-sm text-amber-900">
            {slice.operator_gates.map((gate) => (
              <li key={gate}>{gate}</li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="mt-5 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          No unresolved operator gates.
        </p>
      )}

      <div className="mt-5 border-l border-stone-300 pl-4">
        <p className="text-sm font-medium text-slate-950">Repo-native path</p>
        <p className="mt-1 break-words font-mono text-sm text-slate-600">
          {slice.repo_native_path}
        </p>
        <Link
          href={href}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-flex text-sm font-medium text-slate-950 underline decoration-stone-300 underline-offset-4 hover:decoration-slate-950"
        >
          Open in GitHub
        </Link>
      </div>

      <div className="mt-5">
        <p className="text-sm font-medium text-slate-950">Evidence</p>
        <p className="mt-1 text-xs text-slate-500">
          Read-only history scoped to this repo and slice.
        </p>
        <div className="mt-3 space-y-2 text-sm">
          <Link
            href={`/runs${evidenceSearch}`}
            className="block rounded-lg border border-stone-200 px-3 py-2 font-medium text-slate-950 transition-colors hover:bg-stone-50"
          >
            Runs for this slice
          </Link>
          <Link
            href={`/dispatches${evidenceSearch}`}
            className="block rounded-lg border border-stone-200 px-3 py-2 font-medium text-slate-950 transition-colors hover:bg-stone-50"
          >
            Dispatches for this slice
          </Link>
        </div>
      </div>
    </aside>
  );
}

function DetailTerm({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 text-slate-950">{value}</dd>
    </div>
  );
}

function StateBadge({ slice }: { slice: SliceSummary }) {
  const tone = stateTone(slice);
  return (
    <span
      className={cn(
        "rounded-full px-2 py-0.5 text-xs font-medium capitalize",
        tone === "gate" && "bg-amber-100 text-amber-900",
        tone === "ready" && "bg-emerald-100 text-emerald-800",
        tone === "blocked" && "bg-rose-100 text-rose-800",
        tone === "neutral" && "bg-slate-100 text-slate-700",
      )}
    >
      {slice.state}
    </span>
  );
}

export function hasUnresolvedGates(slice: SliceSummary) {
  return slice.state === "gated" || slice.operator_gates.length > 0;
}

export function stateTone(slice: SliceSummary) {
  if (hasUnresolvedGates(slice)) {
    return "gate";
  }
  if (slice.state === "ready" || slice.state === "validated") {
    return "ready";
  }
  if (slice.state === "blocked") {
    return "blocked";
  }
  return "neutral";
}

export function groupSlices(slices: SliceSummary[]) {
  return slices.reduce<Record<string, SliceSummary[]>>((groups, slice) => {
    const key = STATE_ORDER.includes(slice.state) ? slice.state : "blocked";
    groups[key] = [...(groups[key] ?? []), slice];
    return groups;
  }, {});
}

export function SliceBoardLoading() {
  return (
    <section aria-label="Loading slice board" className="max-w-4xl">
      <div className="h-4 w-28 rounded bg-stone-200" />
      <div className="mt-4 h-10 w-2/3 rounded bg-stone-200" />
      <div className="mt-10 space-y-4">
        {[0, 1, 2].map((item) => (
          <div key={item} className="h-28 rounded-xl bg-stone-200" />
        ))}
      </div>
    </section>
  );
}

export function SliceBoardEmpty({ repoId }: { repoId: string }) {
  return (
    <section className="max-w-3xl rounded-xl border border-stone-200 bg-white p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
        Slice board
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-slate-950">
        No slices for {repoId}.
      </h2>
      <p className="mt-3 text-slate-600">
        Sync a dependency tree before reviewing slice readiness for this repo.
      </p>
    </section>
  );
}

export function SliceBoardError({ repoId }: { repoId: string }) {
  return (
    <section className="max-w-3xl rounded-xl border border-rose-200 bg-rose-50 p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-700">
        Slice board unavailable
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-rose-950">
        Could not load slices for {repoId}.
      </h2>
      <p className="mt-3 text-rose-800">
        Check that `drake-api` is running and the repo exists in the registry
        projection.
      </p>
    </section>
  );
}
