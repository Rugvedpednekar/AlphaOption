export function EmptyState({ title }: { title: string }) {
  return (
    <section style={{ background: "var(--panel)", border: "1px dashed rgba(139,161,153,.3)", borderRadius: 20, minHeight: 350, display: "grid", placeItems: "center", textAlign: "center", padding: 32 }}>
      <div><p style={{ color: "var(--mint)", letterSpacing: ".16em", fontSize: 12, textTransform: "uppercase" }}>Phase 1 shell</p><h2 style={{ margin: "8px 0" }}>{title}</h2><p style={{ color: "var(--muted)" }}>Not implemented yet</p></div>
    </section>
  );
}
