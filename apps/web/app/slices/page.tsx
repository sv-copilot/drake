import { PlaceholderView } from "@/components/placeholder-view";

export default function SlicesPage() {
  return (
    <PlaceholderView
      eyebrow="Slices"
      title="Dependency states before unattended work."
      description="The slice board will project repo-native dependency trees into ready, gated, running, review, and validated lanes."
      source=".docs/slice_dependency_tree.json"
      next={[
        "Slice id, number, title, tier, risk, effort, dependencies, and blocks.",
        "State and operator gate explanations from the committed tree.",
        "PR and validation summaries linked back to repo evidence.",
      ]}
    />
  );
}
