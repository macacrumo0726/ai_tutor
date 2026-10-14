import { getSession } from "./auth";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const session = getSession();
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(session ? { Authorization: `Bearer ${session.token}` } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "No fue posible completar la solicitud");
  }
  return response.json() as Promise<T>;
}

export async function streamChat(
  conversationId: string,
  message: string,
  handlers: { onStatus: (value: string) => void; onToken: (value: string) => void; onDone: (value: unknown) => void },
) {
  const session = getSession();
  const response = await fetch(`${API_URL}/api/conversations/${conversationId}/messages/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session?.token || ""}`,
    },
    body: JSON.stringify({ message }),
  });
  if (!response.ok || !response.body) throw new Error("No fue posible conectar con el tutor");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const packets = buffer.split("\n\n");
    buffer = packets.pop() || "";
    for (const packet of packets) {
      const event = packet.match(/^event: (.+)$/m)?.[1];
      const data = packet.match(/^data: (.+)$/m)?.[1];
      if (!event || !data) continue;
      const parsed = JSON.parse(data);
      if (event === "status") handlers.onStatus(parsed.message);
      if (event === "token") handlers.onToken(parsed.text);
      if (event === "done") handlers.onDone(parsed);
      if (event === "error") throw new Error(parsed.message);
    }
  }
}
