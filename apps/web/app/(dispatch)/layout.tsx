export default function DispatchLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Visually distinct dispatch area – sidebar already marks it.
  return <>{children}</>;
}
