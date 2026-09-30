export type RiskLevel = "low" | "medium" | "high" | "critical" | string;

export interface RiskResult {
  label?: string;
  risk_level: RiskLevel;
  risk_score: number;
  confidence?: number;
  probabilities?: Record<string, number>;
  needs_helpline?: boolean;
  backend?: string;
  model?: string;
  demo?: boolean;
}

export interface ToneResult {
  tone: string;
  demo?: boolean;
  features?: Record<string, number>;
}

export interface VadResult {
  has_speech: boolean;
  speech_ratio: number;
  waveform_preview?: number[];
  backend?: string;
  demo?: boolean;
}

export interface Helpline {
  us: string;
  intl: string;
  disclaimer: string;
}

export interface ChatResponse {
  reply: string;
  backend?: string;
  model?: string;
  helpline?: Helpline | null;
  risk_level?: RiskLevel;
  demo?: boolean;
}

export interface AgentStep {
  thought: string;
  tool: string;
  output?: { summary?: string; suggestion?: string };
  latency_ms?: number;
}

export interface AgentInfo {
  steps: AgentStep[];
  tools_used?: string[];
  latency_ms?: number;
}

export interface Message {
  role: "user" | "assistant";
  text: string;
  via?: "voice" | "text";
  risk?: RiskResult | null;
  helpline?: Helpline | null;
  agent?: AgentInfo | null;
  model?: string;
  tone?: ToneResult;
}

export interface AuthUser {
  username: string;
  display_name?: string;
  guest?: boolean;
}

export interface SystemStatus {
  status: string;
  version?: string;
  demo_mode?: boolean;
  cloud_fallback?: boolean;
  models?: Record<string, string>;
  snapdragon?: {
    preferred_accelerator?: string;
  };
  performance_targets_ms?: Record<string, number | string>;
}
