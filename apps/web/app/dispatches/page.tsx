import { Suspense } from "react";

import { DispatchLog, DispatchLogLoading } from "@/features/dispatches/dispatch-log";

export default function DispatchesPage() {
  return (
    <Suspense fallback={<DispatchLogLoading />}>
      <DispatchLog />
    </Suspense>
  );
}
