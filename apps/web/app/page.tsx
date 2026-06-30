import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function HomePage() {
  return (
    <section className="max-w-4xl">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
        Read-only phase
      </p>
      <h2 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
        Software operations guided by repo-native governance.
      </h2>
      <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">
        This shell prepares the hosted UI for portfolio status, slice boards,
        run evidence, worker adapters, and dispatch history without introducing
        write controls or private registry data.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Button asChild>
          <Link href="/portfolio">Open portfolio</Link>
        </Button>
        <Button asChild variant="ghost">
          <Link href="/slices">Review slice board</Link>
        </Button>
      </div>
      <div className="mt-12 border-l border-stone-300 pl-6">
        <p className="text-sm font-medium text-slate-950">Current boundary</p>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          The UI reads through `drake-api` only. GitHub sync, dispatch,
          credentials, auth, database persistence, and production actions land
          in later gated slices.
        </p>
      </div>
    </section>
  );
}
