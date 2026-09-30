export default function AgentSteps({ agent }) {
  if (!agent?.steps?.length) return null;
  return (
    <div className="panel agent-panel animate-in">
      <h2>Agent trail</h2>
      <p className="risk-conf">{agent.tools_used?.join(" → ")}</p>
      <ol className="agent-steps">
        {agent.steps.map((step, i) => (
          <li key={i} style={{ animationDelay: `${i * 80}ms` }}>
            <strong>{step.tool}</strong>
            <span>{step.thought}</span>
            {step.output?.summary ? <em>{step.output.summary}</em> : null}
          </li>
        ))}
      </ol>
      <p className="fineprint">Agent latency {agent.latency_ms}ms · on-device tools</p>
    </div>
  );
}
