import Link from "next/link";

export function ErrorView({ reset }: { reset?: () => void }) {
  return (
    <section className="max-w-3xl rounded-xl border border-rose-200 bg-rose-50 p-8">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-700">
        Something went wrong
      </p>
      <h2 className="mt-3 text-3xl font-semibold text-rose-950">
        The read-only console hit an unexpected error.
      </h2>
      <p className="mt-3 text-rose-800">
        No governance data was changed. Retry the view, or return to the
        portfolio. If this persists, check that `drake-api` is running and the
        read projection is available.
      </p>
      <div className="mt-6 flex flex-wrap gap-2">
        {reset ? (
          <button
            type="button"
            onClick={reset}
            className="rounded-lg border border-rose-300 bg-white px-3 py-2 text-sm font-medium text-rose-950 transition-colors hover:bg-rose-100"
          >
            Try again
          </button>
        ) : null}
        <Link
          href="/portfolio"
          className="rounded-lg border border-rose-300 bg-white px-3 py-2 text-sm font-medium text-rose-950 transition-colors hover:bg-rose-100"
        >
          Back to portfolio
        </Link>
      </div>
    </section>
  );
}
