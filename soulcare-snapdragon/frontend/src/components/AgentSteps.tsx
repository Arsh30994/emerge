import type { AgentInfo } from "../types";

interface Props {
  agent: AgentInfo | null;
}

export default function AgentSteps({ agent }: Props) {
  if (!agent?.steps?.length) return null;
  return (
    <div className="animate-rise rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4 shadow-lg backdrop-blur">
      <h2 className="font-display mb-1 text-xl">Agent trail</h2>
      <p className="text-sm text-[var(--muted)]">{agent.tools_used?.join(" → ")}</p>
      <ol className="mt-3 grid list-decimal gap-2 pl-5">
        {agent.steps.map((step, i) => (
          <li key={i} className="animate-rise text-sm text-[var(--muted)]" style={{ animationDelay: `${i * 80}ms` }}>
            <strong className="block capitalize text-[var(--ink)]">{step.tool}</strong>
            <span>{step.thought}</span>
            {step.output?.summary ? (
              <em className="mt-0.5 block not-italic text-gold-400">{step.output.summary}</em>
            ) : null}
          </li>
        ))}
      </ol>
      <p className="mt-3 text-xs text-[var(--muted)]">
        Agent latency {agent.latency_ms}ms · on-device tools
      </p>
    </div>
  );
}
