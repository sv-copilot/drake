import { Suspense } from "react";

import { WorkerStatus, WorkerStatusLoading } from "@/features/workers/worker-status";

export const metadata = { title: "Workers — Drake operations" };

export default function WorkersPage() {
  return (
    // This screen reads and writes URL query state, which suspends during
    // static prerendering — the boundary is required, not cosmetic.
    <Suspense fallback={<WorkerStatusLoading />}>
      <WorkerStatus />
    </Suspense>
  );
}
