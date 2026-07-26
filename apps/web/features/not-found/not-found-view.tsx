import Link from "next/link";

const SUGGESTIONS = [
  { href: "/portfolio", label: "Portfolio" },
  { href: "/slices", label: "Slices" },
  { href: "/runs", label: "Runs" },
  { href: "/dispatches", label: "Dispatches" },
  { href: "/workers", label: "Workers" },
];

export function NotFoundView() {
  return (
    <section className="max-w-3xl rounded-xl border border-stone-200 bg-white p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
        Not found
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-slate-950">
        This page is not part of the read-only console.
      </h2>
      <p className="mt-3 text-slate-600">
        The hosted UI only renders registry-backed projections. The repo, slice,
        run, or dispatch you requested may not exist in the current read cache,
        or the URL may be mistyped.
      </p>
      <div className="mt-6 flex flex-wrap gap-2">
        {SUGGESTIONS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="rounded-lg border border-stone-200 px-3 py-2 text-sm font-medium text-slate-950 transition-colors hover:bg-stone-50"
          >
            {item.label}
          </Link>
        ))}
      </div>
    </section>
  );
}
