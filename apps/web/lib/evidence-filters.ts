export type EvidenceFilters = {
  repoId: string;
  sliceId: string;
  status: string;
};

export const EMPTY_EVIDENCE_FILTERS: EvidenceFilters = {
  repoId: "",
  sliceId: "",
  status: "",
};

export function evidenceFiltersFromSearch(
  search: string | URLSearchParams,
): EvidenceFilters {
  const params = typeof search === "string" ? new URLSearchParams(search) : search;

  return {
    repoId: params.get("repo") ?? "",
    sliceId: params.get("slice") ?? "",
    status: params.get("status") ?? "",
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
