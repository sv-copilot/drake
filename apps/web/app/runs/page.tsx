import { Suspense } from "react";

import { RunHistory, RunHistoryLoading } from "@/features/runs/run-history";

export const metadata = { title: "Runs — Drake operations" };

export default function RunsPage() {
  return (
    // This screen reads and writes URL query state, which suspends during
    // static prerendering — the boundary is required, not cosmetic.
    <Suspense fallback={<RunHistoryLoading />}>
      <RunHistory />
    </Suspense>
  );
}
