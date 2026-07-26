import { SliceBoard } from "@/features/slices/slice-board";

export default async function RepoSlicesPage({
  params,
}: {
  params: Promise<{ repoId: string }>;
}) {
  const { repoId } = await params;
  return <SliceBoard repoId={repoId} />;
}
