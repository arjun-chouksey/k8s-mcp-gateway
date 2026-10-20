import type { Actor, AuditFilters, AuditPageRecord, ConversationRecord, ConversationSummary, InviteRecord, IssuedKey, KeyRecord, MemberRecord, Role, ServerCreate, ServerRecord, ServerTool, ServerUpdate } from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...init,
    headers: init?.body ? { "Content-Type": "application/json", ...init.headers } : init?.headers,
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json() as { detail?: string | Array<{ msg?: string }> };
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((item) => item.msg).filter(Boolean).join(". ") || message;
    } catch {
      // Non-JSON failures retain the bounded status message.
    }
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  me: () => request<Actor>("/api/me"),
  login: (email: string, password: string) => request<Actor>("/api/auth/login", {
    method: "POST", body: JSON.stringify({ email, password }),
  }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  servers: () => request<ServerRecord[]>("/api/servers"),
  serverTools: (id: string) => request<ServerTool[]>(`/api/servers/${id}/tools`),
  createServer: (payload: ServerCreate) => request<ServerRecord>("/api/servers", {
    method: "POST", body: JSON.stringify(payload),
  }),
  updateServer: (id: string, payload: ServerUpdate) => request<ServerRecord>(`/api/servers/${id}`, {
    method: "PATCH", body: JSON.stringify(payload),
  }),
  deleteServer: (id: string) => request<void>(`/api/servers/${id}`, { method: "DELETE" }),
  members: () => request<MemberRecord[]>("/api/members"),
  invite: (email: string, role: Role) => request<InviteRecord>("/api/invites", { method: "POST", body: JSON.stringify({ email, role }) }),
  acceptInvite: (token: string, password: string) => request<MemberRecord>("/api/invites/accept", { method: "POST", body: JSON.stringify({ token, password }) }),
  updateMember: (id: string, payload: { role?: Role; active?: boolean }) => request<MemberRecord>(`/api/members/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  keys: () => request<KeyRecord[]>("/api/keys"),
  createKey: (name: string) => request<IssuedKey>("/api/keys", { method: "POST", body: JSON.stringify({ name }) }),
  revokeKey: (id: string) => request<void>(`/api/keys/${id}`, { method: "DELETE" }),
  createMemberKey: (memberId: string, name: string) => request<IssuedKey>(`/api/members/${memberId}/keys`, { method: "POST", body: JSON.stringify({ name }) }),
  revokeMemberKey: (memberId: string, keyId: string) => request<void>(`/api/members/${memberId}/keys/${keyId}`, { method: "DELETE" }),
  audit: (filters: AuditFilters) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => { if (value !== undefined && value !== "") params.set(key, String(value)); });
    return request<AuditPageRecord>(`/api/audit?${params.toString()}`);
  },
  conversations: () => request<ConversationSummary[]>("/api/conversations"),
  conversation: (id: string) => request<ConversationRecord>(`/api/conversations/${id}`),
};
