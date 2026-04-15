import { ref } from 'vue';
import { defineStore } from 'pinia';

import type { ConnectionStatus, PendingApproval, WorkflowEvent } from '@/types/research';

const MAX_RECONNECT_DELAY = 15000;
const MAX_RECONNECT_ATTEMPTS = 20;

let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectAttempt = 0;
let activeResearchId: string | null = null;
let intentionalClose = false;

function clearReconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

function getReconnectDelay() {
  const delay = Math.min(1000 * 2 ** reconnectAttempt, MAX_RECONNECT_DELAY);
  reconnectAttempt += 1;
  return delay;
}

export const useWorkflowStore = defineStore('workflow', () => {
  const events = ref<WorkflowEvent[]>([]);
  const currentNode = ref<string | null>(null);
  const isRunning = ref(false);
  const isPaused = ref(false);
  const pendingApproval = ref<PendingApproval | null>(null);
  const socket = ref<WebSocket | null>(null);
  const connectionStatus = ref<ConnectionStatus>('disconnected');

  function addEvent(event: WorkflowEvent) {
    events.value = [...events.value, event];
    currentNode.value = event.node_name || currentNode.value;
  }

  function clearEvents() {
    events.value = [];
    currentNode.value = null;
    isRunning.value = false;
    isPaused.value = false;
    pendingApproval.value = null;
  }

  function setPendingApproval(approval: PendingApproval | null) {
    pendingApproval.value = approval;
  }

  function scheduleReconnect(researchId: string) {
    clearReconnect();

    if (reconnectAttempt >= MAX_RECONNECT_ATTEMPTS) {
      return;
    }

    const delay = getReconnectDelay();
    reconnectTimer = window.setTimeout(() => {
      if (activeResearchId === researchId && !socket.value) {
        connectWebSocket(researchId);
      }
    }, delay);
  }

  function connectWebSocket(researchId: string) {
    const isSameResearch = activeResearchId === researchId;

    if (
      socket.value &&
      (socket.value.readyState === WebSocket.OPEN || socket.value.readyState === WebSocket.CONNECTING) &&
      isSameResearch
    ) {
      return;
    }

    intentionalClose = true;
    if (socket.value && socket.value.readyState !== WebSocket.CLOSED) {
      socket.value.close();
    }
    intentionalClose = false;

    clearReconnect();
    if (!isSameResearch) {
      clearEvents();
    }

    activeResearchId = researchId;
    reconnectAttempt = 0;
    connectionStatus.value = 'connecting';

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/events/ws/${researchId}`;

    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl);
    } catch {
      connectionStatus.value = 'disconnected';
      socket.value = null;
      scheduleReconnect(researchId);
      return;
    }

    ws.onopen = () => {
      reconnectAttempt = 0;
      connectionStatus.value = 'authenticating';
      const token = window.localStorage.getItem('access_token');

      if (!token) {
        ws.close(4001, 'No auth token');
        return;
      }

      ws.send(JSON.stringify({ type: 'auth', token }));
    };

    ws.onmessage = (event) => {
      let message: any;
      try {
        message = JSON.parse(event.data);
      } catch {
        return;
      }

      const type = message.type || message.event_type;

      switch (type) {
        case 'auth_ok':
          connectionStatus.value = 'connected';
          return;
        case 'auth_error':
          intentionalClose = true;
          ws.close();
          intentionalClose = false;
          connectionStatus.value = 'disconnected';
          socket.value = null;
          return;
        case 'connected':
        case 'ping':
          return;
        case 'NODE_STARTED':
          addEvent(message);
          isRunning.value = true;
          isPaused.value = false;
          currentNode.value = message.node_name;
          return;
        case 'NODE_COMPLETED':
        case 'NODE_FAILED':
        case 'ARTIFACT_CREATED':
        case 'LOG_MESSAGE':
          addEvent(message);
          return;
        case 'NODE_WAITING_FOR_APPROVAL':
          addEvent(message);
          isRunning.value = false;
          isPaused.value = true;
          pendingApproval.value = {
            has_pending: true,
            approval_id: message.data?.approval_id ?? null,
            node_execution_id: message.data?.node_execution_id ?? null,
            node_name: message.node_name ?? null,
            step_label: message.step_label ?? null,
            description: message.data?.description || message.message || null,
            approval_type: message.data?.approval_type ?? 'node_approval',
            output_summary: message.data?.output_summary ?? null,
            _source: 'ws',
          };
          return;
        case 'NODE_REVISION_STARTED':
        case 'NODE_RETRY_STARTED':
          addEvent(message);
          isPaused.value = false;
          isRunning.value = true;
          pendingApproval.value = null;
          return;
        case 'WORKFLOW_COMPLETED':
          addEvent(message);
          isRunning.value = false;
          isPaused.value = false;
          currentNode.value = null;
          pendingApproval.value = null;
          return;
        case 'WORKFLOW_FAILED':
          addEvent(message);
          isRunning.value = false;
          isPaused.value = false;
          currentNode.value = null;
          return;
        default:
          if (message.event_type) {
            addEvent(message);
          }
      }
    };

    ws.onclose = () => {
      if (socket.value !== ws) {
        return;
      }

      socket.value = null;
      connectionStatus.value = 'disconnected';

      if (!intentionalClose && activeResearchId === researchId) {
        scheduleReconnect(researchId);
      }
    };

    ws.onerror = () => {
      // reconnect is handled on close
    };

    socket.value = ws;
  }

  function disconnectWebSocket() {
    intentionalClose = true;
    activeResearchId = null;
    clearReconnect();
    reconnectAttempt = 0;

    if (socket.value) {
      try {
        socket.value.close(1000, 'Client disconnect');
      } catch {
        // ignore close failures
      }
    }

    socket.value = null;
    connectionStatus.value = 'disconnected';
    clearEvents();
    intentionalClose = false;
  }

  return {
    events,
    currentNode,
    isRunning,
    isPaused,
    pendingApproval,
    socket,
    connectionStatus,
    addEvent,
    clearEvents,
    setPendingApproval,
    connectWebSocket,
    disconnectWebSocket,
  };
});
