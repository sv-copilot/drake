export function EvidenceResultSummary({
  filtered,
  total,
  noun,
  pluralNoun,
  active,
  onClear,
}: {
  filtered: number;
  total: number;
  noun: string;
  pluralNoun?: string;
  active: boolean;
  onClear?: () => void;
}) {
  const plural = pluralNoun ?? `${noun}s`;
  const word = (count: number) => (count === 1 ? noun : plural);
  const label = active
    ? `Showing ${filtered} of ${total} ${word(total)}`
    : `${total} ${word(total)}`;

  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-600">
      <p>{label}</p>
      {active ? (
        <button
          type="button"
          onClick={onClear}
          className="rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-950 transition-colors hover:bg-stone-50"
        >
          Clear filters
        </button>
      ) : null}
    </div>
  );
}
