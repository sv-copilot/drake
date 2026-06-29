"use client";

import { useEffect, useState } from "react";

import {
  EMPTY_EVIDENCE_FILTERS,
  evidenceFiltersFromSearch,
  evidenceSearchString,
  type EvidenceFilters,
} from "@/lib/evidence-filters";

export function useEvidenceUrlFilters() {
  const [filters, setFilters] = useState<EvidenceFilters>(browserFilters);

  useEffect(() => {
    function handlePopState() {
      setFilters(browserFilters());
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function updateFilters(nextFilters: EvidenceFilters) {
    setFilters(nextFilters);
    if (typeof window === "undefined") {
      return;
    }

    const nextSearch = evidenceSearchString(nextFilters, window.location.search);
    window.history.pushState(null, "", `${window.location.pathname}${nextSearch}`);
  }

  return [filters, updateFilters] as const;
}

function browserFilters() {
  if (typeof window === "undefined") {
    return EMPTY_EVIDENCE_FILTERS;
  }

  return evidenceFiltersFromSearch(window.location.search);
}
