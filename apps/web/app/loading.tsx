export default function Loading() {
  return (
    <main className="loading-shell" aria-live="polite" aria-busy="true">
      <div className="loading-grid">
        <span />
        <span />
        <span />
      </div>
      <p>Loading tenant-scoped Zulu workspace...</p>
    </main>
  );
}
