export type RunMode = "info" | "change";

export type ChangeRecord = {
  action: string;
  target: string;
  backup_path: string;
  timestamp: string;
  details?: string;
};

export type VerifyResult = {
  healthy: boolean;
  reason: string;
};

export type OrchestratorResult = {
  success: boolean;
  message: string;
  mode: RunMode;
  change_record: ChangeRecord | null;
  verify_result: VerifyResult | null;
  plugin_manager_reply?: string;
  verifier_reply?: string;
  rolled_back?: boolean;
};

export type RequestSummary = {
  id: string;
  request: string;
  force_unhealthy: boolean;
  status: "pending" | "running" | "done" | "error";
  created_at: string;
  log_path: string | null;
  result: OrchestratorResult | null;
  error: string | null;
};

export type ServerStatus = {
  alive: boolean;
  pid: number | null;
  server_dir: string;
  process_mode: string;
  ok: boolean;
};

export type PluginsInfo = {
  ok: boolean;
  allowed_sources: string[];
  blocklist: string[];
  loaded: string[];
  jars: string[];
};

export type SseLogEvent = { type: "log"; data: string };
export type SseDoneEvent = {
  type: "done";
  status: string;
  result: OrchestratorResult | null;
  error: string | null;
  log_path: string | null;
};
export type SseEvent = SseLogEvent | SseDoneEvent;
