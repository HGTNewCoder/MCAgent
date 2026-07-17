import type {
  PluginsInfo,
  RequestSummary,
  ServerStatus,
  SseEvent,
} from "./types";

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function createRequest(
  request: string,
  forceUnhealthy = false,
): Promise<{ id: string; status: string }> {
  const res = await fetch("/api/requests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      request,
      force_unhealthy: forceUnhealthy,
    }),
  });
  return parseJson(res);
}

export async function listRequests(): Promise<RequestSummary[]> {
  const data = await parseJson<{ items: RequestSummary[] }>(
    await fetch("/api/requests"),
  );
  return data.items;
}

export async function getRequest(id: string): Promise<RequestSummary> {
  return parseJson(await fetch(`/api/requests/${id}`));
}

export function streamRequestEvents(
  id: string,
  onEvent: (event: SseEvent) => void,
  onError?: (err: Error) => void,
): () => void {
  const source = new EventSource(`/api/requests/${id}/events`);
  source.onmessage = (msg) => {
    try {
      const data = JSON.parse(msg.data) as SseEvent;
      onEvent(data);
      if (data.type === "done") {
        source.close();
      }
    } catch (err) {
      onError?.(err instanceof Error ? err : new Error(String(err)));
      source.close();
    }
  };
  source.onerror = () => {
    onError?.(new Error("SSE connection error"));
    source.close();
  };
  return () => source.close();
}

export async function getServerStatus(): Promise<ServerStatus> {
  return parseJson(await fetch("/api/server/status"));
}

export async function serverAction(
  action: "start" | "stop" | "restart",
): Promise<Record<string, unknown>> {
  return parseJson(
    await fetch(`/api/server/${action}`, { method: "POST" }),
  );
}

export async function getPlugins(): Promise<PluginsInfo> {
  return parseJson(await fetch("/api/plugins"));
}
