import type { ReactNode } from "react";

type Tone = "good" | "warning" | "neutral" | "bad";

const colors: Record<Tone, string> = {
  good: "#49e0ac",
  warning: "#f0b85b",
  neutral: "#b8c7c2",
  bad: "#ff7b7b",
};

export function StatusCard({ label, value, detail, tone = "neutral", icon }: {
  label: string; value: string; detail?: string; tone?: Tone; icon?: ReactNode;
}) {
  return (
    <article style={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 18, padding: 20, minHeight: 145, boxShadow: "0 20px 50px rgba(0,0,0,.18)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, color: "var(--muted)", fontSize: 13, letterSpacing: ".05em", textTransform: "uppercase" }}>
        <span>{label}</span><span aria-hidden="true">{icon}</span>
      </div>
      <p style={{ fontSize: 24, fontWeight: 700, margin: "22px 0 8px", color: colors[tone] }}>{value}</p>
      {detail && <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>{detail}</p>}
    </article>
  );
}
