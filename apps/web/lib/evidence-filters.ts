export type EvidenceFilters = {
  repoId: string;
  sliceId: string;
  status: string;
  workerId?: string;
};

export const EMPTY_EVIDENCE_FILTERS: EvidenceFilters = {
  repoId: "",
  sliceId: "",
  status: "",
  workerId: "",
};

type SearchParamsLike = Pick<URLSearchParams, "get">;

export function evidenceFiltersFromSearch(
  search: string | SearchParamsLike,
): EvidenceFilters {
  const params = typeof search === "string" ? new URLSearchParams(search) : search;

  return {
    repoId: params.get("repo") ?? "",
    sliceId: params.get("slice") ?? "",
    status: params.get("status") ?? "",
    workerId: params.get("worker") ?? "",
  };
}

export function evidenceSearchString(
  filters: EvidenceFilters,
  currentSearch = "",
) {
  const params = new URLSearchParams(currentSearch);
  setOptionalParam(params, "repo", filters.repoId);
  setOptionalParam(params, "slice", filters.sliceId);
  setOptionalParam(params, "status", filters.status);
  setOptionalParam(params, "worker", filters.workerId ?? "");
  const search = params.toString();
  return search ? `?${search}` : "";
}

function setOptionalParam(params: URLSearchParams, key: string, value: string) {
  if (value) {
    params.set(key, value);
  } else {
    params.delete(key);
  }
}
