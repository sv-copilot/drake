import { Suspense } from "react";

import { WorkerStatus, WorkerStatusLoading } from "@/features/workers/worker-status";

export default function WorkersPage() {
  return (
    <Suspense fallback={<WorkerStatusLoading />}>
      <WorkerStatus />
    </Suspense>
  );
}
