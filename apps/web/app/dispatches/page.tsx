import { PlaceholderView } from "@/components/placeholder-view";

export default function DispatchesPage() {
  return (
    <PlaceholderView
      eyebrow="Dispatches"
      title="Future dispatch history without write controls."
      description="The first dispatch surface remains a log view. Manual triggers, retries, and production actions stay behind later operator-gated slices."
      source="orchestrator run artifacts + future WebhookDispatch read model"
      next={[
        "Attempt status, worker target, retry count, timestamps, and linked evidence.",
        "Dry-run indicators before any future write-capable dispatch.",
        "Operator gate status for credentials, production actions, and smoke verification.",
      ]}
    />
  );
}
