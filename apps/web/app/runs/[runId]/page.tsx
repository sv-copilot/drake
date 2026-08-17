import { RunDetail } from "@/features/runs/run-detail";

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return <RunDetail runId={decodeURIComponent(runId)} />;
}
