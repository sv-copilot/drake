"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMemo } from "react";

import {
  evidenceFiltersFromSearch,
  evidenceSearchString,
  type EvidenceFilters,
} from "@/lib/evidence-filters";

export function useEvidenceUrlFilters() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const filters = useMemo(
    () => evidenceFiltersFromSearch(searchParams),
    [searchParams],
  );

  function updateFilters(nextFilters: EvidenceFilters) {
    const nextSearch = evidenceSearchString(nextFilters, searchParams.toString());
    router.push(`${pathname}${nextSearch}`, { scroll: false });
  }

  return [filters, updateFilters] as const;
}
