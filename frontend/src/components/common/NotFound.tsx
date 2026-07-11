export function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-center">
      <div className="text-3xl font-semibold text-ink">404</div>
      <p className="text-sm text-muted">This page doesn&apos;t exist.</p>
      <a href="/dashboard" className="text-sm text-accent hover:underline">
        Back to dashboard
      </a>
    </div>
  );
}
