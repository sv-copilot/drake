export default function OperationsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // No extra visual chrome – the sidebar already groups operations.
  return <>{children}</>;
}
