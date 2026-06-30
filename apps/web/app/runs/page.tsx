import { Suspense } from "react";

import { RunHistory, RunHistoryLoading } from "@/features/runs/run-history";

export default function RunsPage() {
  return (
    <Suspense fallback={<RunHistoryLoading />}>
      <RunHistory />
    </Suspense>
  );
}
