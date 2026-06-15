export default function HomePage() {
  return (
    <main style={{ padding: 'var(--space-8)', maxWidth: 960, margin: '0 auto' }}>
      <h1 style={{ color: 'var(--color-primary)', fontSize: 'var(--text-4xl)', fontWeight: 700, margin: '0 0 var(--space-4)' }}>
        Libertin
      </h1>
      <p style={{ color: 'var(--color-text-muted)', margin: 0 }}>
        Phase 1 — skeleton OK. Storybook: <code>pnpm storybook</code>
      </p>
    </main>
  );
}
