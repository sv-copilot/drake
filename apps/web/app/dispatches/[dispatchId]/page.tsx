import { DispatchDetail } from "@/features/dispatches/dispatch-detail";

type DispatchDetailPageProps = {
  params: Promise<{
    dispatchId: string;
  }>;
};

export default async function DispatchDetailPage({
  params,
}: DispatchDetailPageProps) {
  const { dispatchId } = await params;
  return <DispatchDetail dispatchId={decodeURIComponent(dispatchId)} />;
}
