export type Role = "admin" | "member";
export type ServerStatus = "connected" | "unreachable" | "disabled" | "checking";
export type AuthType = "none" | "bearer" | "header";

export interface Actor {
  id: string;
  email: string;
  role: Role;
}

export interface ServerRecord {
  id: string;
  slug: string;
  display_name: string;
  url: string;
  auth_type: AuthType;
  auth_header: string | null;
  has_credential: boolean;
  enabled: boolean;
  status: ServerStatus;
  connect_timeout_ms: number;
  call_timeout_ms: number;
  tool_count: number;
  last_checked_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface ServerTool {
  public_alias: string;
  original_name: string;
  description: string | null;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown> | null;
  annotations: Record<string, unknown> | null;
}

export interface ServerCreate {
  slug: string;
  display_name: string;
  url: string;
  auth_type: AuthType;
  auth_header?: string | null;
  credential?: string | null;
  enabled: boolean;
  connect_timeout_ms: number;
  call_timeout_ms: number;
}

export interface ServerUpdate {
  display_name?: string;
  url?: string;
  auth_type?: AuthType;
  auth_header?: string | null;
  credential_action: "keep" | "set" | "clear";
  credential?: string;
  enabled?: boolean;
  connect_timeout_ms?: number;
  call_timeout_ms?: number;
}

export interface MemberRecord {
  id: string;
  email: string;
  role: Role;
  active: boolean;
  created_at: string;
}

export interface InviteRecord {
  id: string;
  email: string;
  role: Role;
  invite_url: string;
  expires_at: string;
}

export interface KeyRecord {
  id: string;
  user_id: string;
  prefix: string;
  name: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface IssuedKey extends KeyRecord {
  key: string;
}

export type AuditOutcome = "ok" | "tool_error" | "upstream_error" | "timeout" | "denied";

export interface AuditEventRecord {
  id: string;
  request_id: string;
  user_id: string | null;
  api_key_id: string | null;
  channel: string;
  server_slug: string;
  public_tool: string;
  original_tool: string;
  started_at: string;
  duration_ms: number;
  outcome: AuditOutcome;
  error_summary: string | null;
}

export interface AuditPageRecord {
  items: AuditEventRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuditFilters {
  user?: string;
  server?: string;
  outcome?: AuditOutcome;
  started_after?: string;
  started_before?: string;
  limit: number;
  offset: number;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationMessage {
  id: string;
  role: "user" | "assistant" | "tool" | "system";
  text: string;
  tool_calls: ToolTrace[] | null;
  created_at: string;
}

export interface ToolTrace {
  call_id: string;
  name: string;
  outcome: string;
  duration_ms?: number;
}

export interface ConversationRecord extends ConversationSummary {
  messages: ConversationMessage[];
}
