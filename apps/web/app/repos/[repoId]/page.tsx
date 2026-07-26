import { RepoDetail } from "@/features/repos/repo-detail";

export default async function RepoDetailPage({
  params,
}: {
  params: Promise<{ repoId: string }>;
}) {
  const { repoId } = await params;
  return <RepoDetail repoId={decodeURIComponent(repoId)} />;
}
