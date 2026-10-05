import { Suspense } from "react";

import { PortfolioLoading, PortfolioOverview } from "@/features/portfolio/portfolio-overview";

export const metadata = { title: "Portfolio — Drake operations" };

export default function PortfolioPage() {
  return (
    <Suspense fallback={<PortfolioLoading />}>
      <PortfolioOverview />
    </Suspense>
  );
}
