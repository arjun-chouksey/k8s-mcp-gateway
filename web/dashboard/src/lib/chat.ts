import { ApiError } from "./api";

export type ChatEvent =
  | { type: "tool_call"; conversation_id: string; call_id: string; name: string }
  | { type: "tool_result"; conversation_id: string; call_id: string; name: string; outcome: string; duration_ms: number; preview: string }
  | { type: "text_delta"; conversation_id: string; text: string }
  | { type: "error"; conversation_id: string; message: string }
  | { type: "done"; conversation_id: string };

export async function streamChat(
  prompt: string,
  conversationId: string | null,
  onEvent: (event: ChatEvent) => void,
  signal: AbortSignal,
) {
  const response = await fetch("/api/chat", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, ...(conversationId ? { conversation_id: conversationId } : {}) }),
    signal,
  });
  if (!response.ok) {
    let message = `Chat request failed (${response.status})`;
    try { message = String((await response.json() as { detail?: string }).detail || message); } catch { /* bounded fallback */ }
    throw new ApiError(response.status, message);
  }
  if (!response.body) throw new Error("Chat stream was unavailable");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      const data = block.split(/\r?\n/).find((line) => line.startsWith("data: "));
      if (data) onEvent(JSON.parse(data.slice(6)) as ChatEvent);
    }
    if (done) break;
  }
}
