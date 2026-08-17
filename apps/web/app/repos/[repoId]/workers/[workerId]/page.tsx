import { WorkerDetail } from "@/features/workers/worker-detail";

export default async function WorkerDetailPage({
  params,
}: {
  params: Promise<{ repoId: string; workerId: string }>;
}) {
  const { repoId, workerId } = await params;
  return (
    <WorkerDetail
      repoId={decodeURIComponent(repoId)}
      workerId={decodeURIComponent(workerId)}
    />
  );
}
