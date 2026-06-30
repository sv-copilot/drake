type PlaceholderViewProps = {
  eyebrow: string;
  title: string;
  description: string;
  source: string;
  next: string[];
};

export function PlaceholderView({
  eyebrow,
  title,
  description,
  source,
  next,
}: PlaceholderViewProps) {
  return (
    <section className="max-w-4xl">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
        {eyebrow}
      </p>
      <h2 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
        {title}
      </h2>
      <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-600">
        {description}
      </p>
      <div className="mt-10 border-l border-stone-300 pl-6">
        <p className="text-sm font-medium text-slate-950">Repo-native source</p>
        <p className="mt-1 font-mono text-sm text-slate-600">{source}</p>
      </div>
      <div className="mt-10">
        <p className="text-sm font-medium text-slate-950">
          Planned read model
        </p>
        <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
          {next.map((item) => (
            <li key={item} className="flex gap-3">
              <span aria-hidden="true" className="mt-2 h-1.5 w-1.5 rounded-full bg-slate-400" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
