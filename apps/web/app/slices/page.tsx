import { Suspense } from "react";

import { SliceIndex, SliceIndexLoading } from "@/features/slices/slice-index";

export const metadata = { title: "Slices — Drake operations" };

export default function SlicesPage() {
  return (
    // This screen reads and writes URL query state, which suspends during
    // static prerendering — the boundary is required, not cosmetic.
    <Suspense fallback={<SliceIndexLoading />}>
      <SliceIndex />
    </Suspense>
  );
}
