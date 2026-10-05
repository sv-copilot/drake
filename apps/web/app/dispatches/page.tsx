import { Suspense } from "react";

import { DispatchLog, DispatchLogLoading } from "@/features/dispatches/dispatch-log";

export const metadata = { title: "Dispatches — Drake operations" };

export default function DispatchesPage() {
  return (
    // This screen reads and writes URL query state, which suspends during
    // static prerendering — the boundary is required, not cosmetic.
    <Suspense fallback={<DispatchLogLoading />}>
      <DispatchLog />
    </Suspense>
  );
}
