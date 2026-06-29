import { PlaceholderView } from "@/components/placeholder-view";

export default function RunsPage() {
  return (
    <PlaceholderView
      eyebrow="Runs"
      title="Evidence history for worker activity."
      description="Run history will connect task packets, adapter evidence, validation results, artifacts, logs, and PR links."
      source=".cursor/automation-runs/ + adapters/evidence-contract.schema.json"
      next={[
        "Task packet and orchestrator metadata.",
        "Validation results, timestamps, artifacts, and logs.",
        "Adapter info for Cursor, Cline, SDK runner, and future workers.",
      ]}
    />
  );
}
