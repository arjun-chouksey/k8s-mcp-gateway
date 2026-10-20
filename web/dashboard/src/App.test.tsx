import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const admin = { id: "1", email: "admin@example.test", role: "admin" };
const member = { id: "2", email: "member@example.test", role: "member" };
const server = {
  id: "s1", slug: "woo", display_name: "WooCommerce",
  url: "http://woocommerce-mcp.mcp.svc.cluster.local:8000/mcp",
  auth_type: "bearer", auth_header: null, has_credential: true, enabled: true,
  status: "connected", connect_timeout_ms: 3000, call_timeout_ms: 20000,
  tool_count: 5, last_checked_at: "2026-10-18T12:00:00Z", last_error: null,
  created_at: "2026-10-18T11:00:00Z", updated_at: "2026-10-18T11:00:00Z",
};
const issuedKey = { id: "k1", user_id: "1", prefix: "abc123", name: "Inspector", created_at: "2026-10-18T12:00:00Z", last_used_at: null, revoked_at: null, key: "mcpgw_abc123_one-time-secret" };
const auditEvent = { id: "a1", request_id: "r1", user_id: "2", api_key_id: null, channel: "mcp", server_slug: "woo", public_tool: "woo__list_products", original_tool: "list_products", started_at: "2026-10-18T12:05:00Z", duration_ms: 42, outcome: "ok", error_summary: null };
const conversation = { id: "c1", title: "Store policy", created_at: "2026-10-18T12:00:00Z", updated_at: "2026-10-18T12:06:00Z" };
const conversationDetail = { ...conversation, messages: [
  { id: "m1", role: "user", text: "What is the return policy?", tool_calls: null, created_at: "2026-10-18T12:00:00Z" },
  { id: "m2", role: "assistant", text: "Returns are accepted within the stated window.", tool_calls: [{ call_id: "call-old", name: "policy__get_store_policy", outcome: "ok", duration_ms: 18 }], created_at: "2026-10-18T12:00:01Z" },
] };

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
beforeEach(() => { window.history.pushState({}, "", "/servers"); });

function mockFetch(actor: typeof admin | typeof member | null, servers = [server]) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/me") return actor ? Response.json(actor) : Response.json({ detail: "Authentication required" }, { status: 401 });
    if (path === "/api/auth/login") return Response.json(admin);
    if (path === "/api/members") return Response.json(actor?.role === "admin" ? [admin, member] : [actor ?? member]);
    if (path === "/api/keys" && !init?.method) return Response.json([]);
    if (path === "/api/keys" && init?.method === "POST") return Response.json(issuedKey, { status: 201 });
    if (path === "/api/invites/accept" && init?.method === "POST") return Response.json(member, { status: 201 });
    if (path === "/api/servers" && !init?.method) return Response.json(servers);
    if (path.startsWith("/api/audit?")) return Response.json({ items: [{ ...auditEvent, user_id: actor?.role === "member" ? actor.id : auditEvent.user_id }], total: 1, limit: 20, offset: 0 });
    if (path === "/api/conversations") return Response.json([conversation]);
    if (path === `/api/conversations/${conversation.id}`) return Response.json(conversationDetail);
    if (path === "/api/conversations/c2") return Response.json({ ...conversation, id: "c2", title: "List policies", messages: [
      { id: "m3", role: "user", text: "List our store policies", tool_calls: null, created_at: conversation.created_at },
      { id: "m4", role: "assistant", text: "Available topics include returns and shipping.", tool_calls: [{ call_id: "call-live", name: "policy__list_store_policies", outcome: "ok", duration_ms: 27 }], created_at: conversation.updated_at },
    ] });
    if (path === "/api/chat" && init?.method === "POST") {
      const events = [
        { type: "tool_call", conversation_id: "c2", call_id: "call-live", name: "policy__list_store_policies" },
        { type: "tool_result", conversation_id: "c2", call_id: "call-live", name: "policy__list_store_policies", outcome: "ok", duration_ms: 27, preview: "private@example.test" },
        { type: "text_delta", conversation_id: "c2", text: "Available topics include returns and shipping." },
        { type: "done", conversation_id: "c2" },
      ];
      return new Response(events.map((event) => `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`).join(""), { headers: { "Content-Type": "text/event-stream" } });
    }
    if (path.endsWith("/tools")) return Response.json([{ public_alias: "woo__list_products", original_name: "list_products", description: "List products", input_schema: {}, output_schema: null, annotations: null }]);
    if (init?.method === "PATCH") return Response.json({ ...server, enabled: false, status: "disabled" });
    if (init?.method === "DELETE") return new Response(null, { status: 204 });
    if (init?.method === "POST" && path === "/api/auth/logout") return new Response(null, { status: 204 });
    return Response.json(server, { status: 201 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("dashboard session and server management", () => {
  it("signs in without storing credentials in browser storage", async () => {
    const fetchMock = mockFetch(null);
    const storageSpy = vi.spyOn(Storage.prototype, "setItem");
    render(<App />);
    await screen.findByRole("heading", { name: "Sign in to the gateway" });
    await userEvent.type(screen.getByLabelText("Email address"), "admin@example.test");
    await userEvent.type(screen.getByLabelText("Password"), "private-password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await screen.findByRole("heading", { name: "MCP servers" });
    expect(storageSpy).not.toHaveBeenCalled();
    expect(JSON.parse(String(fetchMock.mock.calls.find((call) => call[0] === "/api/auth/login")?.[1]?.body))).toEqual({ email: "admin@example.test", password: "private-password" });
    storageSpy.mockRestore();
  });

  it("lets admins inspect tools and exposes write-only credential state", async () => {
    mockFetch(admin);
    render(<App />);
    expect(await screen.findByText("WooCommerce")).toBeInTheDocument();
    expect(within(screen.getByLabelText("Registry summary")).getByText("5")).toBeInTheDocument();
    expect(screen.queryByText(/private|credential value/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Tools" }));
    expect(await screen.findByText("woo__list_products")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Register server" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete WooCommerce" })).toBeInTheDocument();
  });

  it("submits a new server credential once through the dedicated API layer", async () => {
    const fetchMock = mockFetch(admin);
    render(<App />);
    await screen.findByText("WooCommerce");
    await userEvent.click(screen.getByRole("button", { name: "Register server" }));
    await userEvent.type(screen.getByLabelText("Display name"), "Inventory MCP");
    await userEvent.type(screen.getByLabelText(/Stable slug/), "inventory");
    await userEvent.type(screen.getByLabelText("Streamable HTTP endpoint"), "https://inventory.example.test/mcp");
    await userEvent.selectOptions(screen.getByLabelText("Authentication"), "bearer");
    await userEvent.type(await screen.findByLabelText(/Credential/), "write-only-secret");
    await userEvent.click(screen.getByRole("button", { name: "Register server" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/servers", expect.objectContaining({ method: "POST" })));
    const request = fetchMock.mock.calls.find((call) => call[0] === "/api/servers" && call[1]?.method === "POST");
    expect(JSON.parse(String(request?.[1]?.body))).toMatchObject({ slug: "inventory", auth_type: "bearer", credential: "write-only-secret" });
    expect(screen.queryByDisplayValue("write-only-secret")).not.toBeInTheDocument();
  });

  it("hides all mutation controls for members", async () => {
    const fetchMock = mockFetch(member);
    render(<App />);
    await screen.findByText("WooCommerce");
    expect(screen.queryByRole("button", { name: "Register server" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit WooCommerce" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Disable" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete WooCommerce" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Team" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "API Keys" })).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/servers", expect.anything()));
  });

  it("shows a newly created personal key once and never stores it", async () => {
    const fetchMock = mockFetch(admin);
    const storageSpy = vi.spyOn(Storage.prototype, "setItem");
    render(<App />);
    await screen.findByText("WooCommerce");
    await userEvent.click(screen.getByRole("link", { name: "API Keys" }));
    await screen.findByRole("heading", { name: "API keys" });
    await userEvent.click(screen.getByRole("button", { name: "Create key" }));
    await userEvent.type(screen.getByLabelText("Key name"), "Inspector");
    await userEvent.click(screen.getByRole("button", { name: "Create key" }));
    expect(await screen.findByText(issuedKey.key)).toBeInTheDocument();
    expect(storageSpy).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledWith("/api/keys", expect.objectContaining({ method: "POST" }));
    await userEvent.click(screen.getByRole("button", { name: "I saved the key" }));
    expect(screen.queryByText(issuedKey.key)).not.toBeInTheDocument();
    storageSpy.mockRestore();
  });

  it("accepts an invitation without requiring an existing session", async () => {
    window.history.pushState({}, "", "/invite?token=valid-invitation-token-that-is-long-enough");
    const fetchMock = mockFetch(null);
    render(<App />);
    await screen.findByRole("heading", { name: "Create your account" });
    await userEvent.type(screen.getByLabelText("Password", { exact: true }), "strong-password-123");
    await userEvent.type(screen.getByLabelText("Confirm password"), "strong-password-123");
    await userEvent.click(screen.getByRole("button", { name: "Accept invitation" }));
    expect(await screen.findByRole("heading", { name: "Account ready" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/invites/accept", expect.objectContaining({ method: "POST" }));
    window.history.pushState({}, "", "/");
  });

  it("shows global audit evidence and user filters to admins", async () => {
    const fetchMock = mockFetch(admin);
    render(<App />);
    await screen.findByText("WooCommerce");
    await userEvent.click(screen.getByRole("link", { name: "Audit Logs" }));
    expect(await screen.findByRole("heading", { name: "Audit logs" })).toBeInTheDocument();
    expect(screen.getByText("woo__list_products")).toBeInTheDocument();
    expect(screen.getAllByText("member@example.test")).toHaveLength(2);
    expect(screen.getByText("connected")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Outcome"), "ok");
    await waitFor(() => expect(fetchMock.mock.calls.some((call) => String(call[0]).includes("outcome=ok"))).toBe(true));
    expect(screen.queryByText(/arguments|payload|credential/i)).not.toBeInTheDocument();
  });

  it("keeps member audit visibility self-scoped and hides the user filter", async () => {
    const fetchMock = mockFetch(member);
    render(<App />);
    await screen.findByRole("heading", { name: "MCP servers" });
    await userEvent.click(screen.getByRole("link", { name: "Audit Logs" }));
    expect(await screen.findByText("woo__list_products")).toBeInTheDocument();
    expect(screen.queryByLabelText("User")).not.toBeInTheDocument();
    const auditCall = fetchMock.mock.calls.find((call) => String(call[0]).startsWith("/api/audit?"));
    expect(String(auditCall?.[0])).not.toContain("user=");
    expect(screen.getAllByText("member@example.test")).toHaveLength(2);
  });

  it("streams real chat tool events without exposing result previews", async () => {
    const fetchMock = mockFetch(admin);
    render(<App />);
    await screen.findByText("WooCommerce");
    await userEvent.click(screen.getByRole("link", { name: "AI Chat" }));
    await screen.findByRole("heading", { name: "Operate the store through one gateway" });
    await userEvent.type(screen.getByLabelText("Message"), "List our store policies");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("policy__list_store_policies")).toBeInTheDocument();
    expect(await screen.findByText("Available topics include returns and shipping.")).toBeInTheDocument();
    expect(screen.getAllByText("Available topics include returns and shipping.")).toHaveLength(1);
    expect(screen.getByText("27 ms")).toBeInTheDocument();
    expect(screen.queryByText("private@example.test")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/chat", expect.objectContaining({ method: "POST", credentials: "same-origin" }));
  });

  it("restores persisted conversation messages and tool traces", async () => {
    mockFetch(member);
    render(<App />);
    await screen.findByText("WooCommerce");
    await userEvent.click(screen.getByRole("link", { name: "AI Chat" }));
    await userEvent.click(await screen.findByRole("button", { name: /Store policy/ }));
    expect(await screen.findByText("What is the return policy?")).toBeInTheDocument();
    expect(screen.getByText("Returns are accepted within the stated window.")).toBeInTheDocument();
    expect(screen.getByText("policy__get_store_policy")).toBeInTheDocument();
    expect(screen.getByText("18 ms")).toBeInTheDocument();
  });
});
