import { PlaceholderView } from "@/components/placeholder-view";

export default function WorkersPage() {
  return (
    <PlaceholderView
      eyebrow="Workers"
      title="Adapter status across agent runtimes."
      description="Worker views will compare local/manual work, Cursor bridge work, Cline execution, SDK runners, and future Drake MCP tools."
      source="registry workers[] + adapters/CONTRACT.md"
      next={[
        "Adapter type, role, enabled state, primary flag, and last known run.",
        "Credential reference names only; never secret values.",
        "Conformance and evidence-contract status by worker adapter.",
      ]}
    />
  );
}
