import { SORT_OPTIONS, type SortKey } from "@/lib/evidence-sort";

export function SortControl({
  value,
  onChange,
}: {
  value: SortKey;
  onChange?: (value: SortKey) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="font-medium text-slate-700">Sort</span>
      <select
        value={value}
        onChange={(event) => onChange?.(event.target.value as SortKey)}
        className="rounded-md border border-stone-300 bg-white px-2 py-1.5 text-slate-950"
      >
        {SORT_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
