"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { normalizeSort, type SortKey } from "@/lib/evidence-sort";

export function useSortUrlParam() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const sort = normalizeSort(searchParams.get("sort"));

  function setSort(next: SortKey) {
    const params = new URLSearchParams(searchParams.toString());
    if (next === "newest") {
      params.delete("sort");
    } else {
      params.set("sort", next);
    }
    const search = params.toString();
    router.push(`${pathname}${search ? `?${search}` : ""}`, { scroll: false });
  }

  return [sort, setSort] as const;
}
