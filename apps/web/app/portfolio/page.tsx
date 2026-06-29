import { PlaceholderView } from "@/components/placeholder-view";

export default function PortfolioPage() {
  return (
    <PlaceholderView
      eyebrow="Portfolio"
      title="Registered repositories and readiness signals."
      description="A future read model will summarize registered repos, branch policy, automation readiness, open gates, and stale validations."
      source=".docs/projects-registry.json"
      next={[
        "Repo identity, GitHub slug, integration branch, and readiness.",
        "Worker summaries from registry entries without exposing credential values.",
        "Operator gates surfaced before any automation dispatch.",
      ]}
    />
  );
}
