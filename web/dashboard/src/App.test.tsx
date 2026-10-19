import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
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

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function mockFetch(actor: typeof admin | typeof member | null, servers = [server]) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/me") return actor ? Response.json(actor) : Response.json({ detail: "Authentication required" }, { status: 401 });
    if (path === "/api/auth/login") return Response.json(admin);
    if (path === "/api/members") return Response.json([actor ?? admin]);
    if (path === "/api/keys" && !init?.method) return Response.json([]);
    if (path === "/api/keys" && init?.method === "POST") return Response.json(issuedKey, { status: 201 });
    if (path === "/api/invites/accept" && init?.method === "POST") return Response.json(member, { status: 201 });
    if (path === "/api/servers" && !init?.method) return Response.json(servers);
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
});
