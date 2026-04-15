import { create } from 'zustand';
import type { PendingApproval } from '../api/research';

export interface WorkflowEvent {
  event_type: string;
  research_id: string;
  run_id?: string;
  node_name?: string;
  step_label?: string;
  message?: string;
  data?: Record<string, any>;
  timestamp?: string;
}

type ConnectionStatus = 'disconnected' | 'connecting' | 'authenticating' | 'connected';

interface WorkflowState {
  events: WorkflowEvent[];
  currentNode: string | null;
  isRunning: boolean;
  isPaused: boolean;
  pendingApproval: PendingApproval | null;
  socket: WebSocket | null;
  connectionStatus: ConnectionStatus;

  // Actions
  addEvent: (event: WorkflowEvent) => void;
  clearEvents: () => void;
  setPendingApproval: (approval: PendingApproval | null) => void;
  connectWebSocket: (researchId: string) => void;
  disconnectWebSocket: () => void;
}

// ── Private reconnection state (outside store to avoid re-renders) ──
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let _reconnectAttempt = 0;
let _activeResearchId: string | null = null;
let _intentionalClose = false;

const MAX_RECONNECT_DELAY = 15000; // 15 seconds max
const MAX_RECONNECT_ATTEMPTS = 20;

function _clearReconnect() {
  if (_reconnectTimer) {
    clearTimeout(_reconnectTimer);
    _reconnectTimer = null;
  }
}

function _getReconnectDelay(): number {
  const delay = Math.min(1000 * Math.pow(2, _reconnectAttempt), MAX_RECONNECT_DELAY);
  _reconnectAttempt++;
  return delay;
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  events: [],
  currentNode: null,
  isRunning: false,
  isPaused: false,
  pendingApproval: null,
  socket: null,
  connectionStatus: 'disconnected',

  addEvent: (event) => {
    set((state) => ({
      events: [...state.events, event],
      currentNode: event.node_name || state.currentNode,
    }));
  },

  clearEvents: () => {
    set({
      events: [],
      currentNode: null,
      isRunning: false,
      isPaused: false,
      pendingApproval: null,
    });
  },

  setPendingApproval: (approval) => {
    set({ pendingApproval: approval });
  },

  connectWebSocket: (researchId: string) => {
    const state = get();
    const isSameResearch = _activeResearchId === researchId;

    // Idempotent: don't reconnect if already connected to the same research
    if (
      state.socket &&
      (state.socket.readyState === WebSocket.OPEN || state.socket.readyState === WebSocket.CONNECTING) &&
      isSameResearch
    ) {
      return;
    }

    // Close existing connection (but don't trigger reconnect)
    _intentionalClose = true;
    if (state.socket && state.socket.readyState !== WebSocket.CLOSED) {
      state.socket.close();
    }
    _intentionalClose = false;

    _clearReconnect();
    if (!isSameResearch) {
      set({
        events: [],
        currentNode: null,
        isRunning: false,
        isPaused: false,
        pendingApproval: null,
      });
    }
    _activeResearchId = researchId;
    _reconnectAttempt = 0;

    set({ connectionStatus: 'connecting' });

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/events/ws/${researchId}`;

    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl);
    } catch (e) {
      console.error('[WS] Failed to create WebSocket:', e);
      set({ connectionStatus: 'disconnected', socket: null });
      _scheduleReconnect(researchId, get);
      return;
    }

    ws.onopen = () => {
      _reconnectAttempt = 0;
      set({ connectionStatus: 'authenticating' });

      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          ws.send(JSON.stringify({ type: 'auth', token }));
        } catch {
          ws.close();
        }
      } else {
        console.error('[WS] No auth token available');
        ws.close(4001, 'No auth token');
      }
    };

    ws.onmessage = (e) => {
      let msg: any;
      try {
        msg = JSON.parse(e.data);
      } catch {
        return;
      }

      const type = msg.type || msg.event_type;

      switch (type) {
        // ── Connection Lifecycle ─────────────────────────
        case 'auth_ok':
          set({ connectionStatus: 'connected' });
          console.log('[WS] Connected and authenticated');
          break;

        case 'auth_error':
          console.error('[WS] Auth failed:', msg.message);
          _intentionalClose = true;
          ws.close();
          _intentionalClose = false;
          set({ connectionStatus: 'disconnected', socket: null });
          break;

        case 'connected':
          // Server confirmed subscription — no UI action needed
          break;

        case 'ping':
          // Keepalive — no action needed
          break;

        // ── Pipeline Events ─────────────────────────────
        case 'NODE_STARTED':
          get().addEvent(msg);
          set({ isRunning: true, isPaused: false, currentNode: msg.node_name });
          break;

        case 'NODE_COMPLETED':
          get().addEvent(msg);
          break;

        case 'NODE_FAILED':
          get().addEvent(msg);
          break;

        case 'ARTIFACT_CREATED':
          get().addEvent(msg);
          break;

        case 'LOG_MESSAGE':
          get().addEvent(msg);
          break;

        // ── Per-Node Approval Events ────────────────────
        case 'NODE_WAITING_FOR_APPROVAL':
          get().addEvent(msg);
          set({
            isPaused: true,
            isRunning: false,
            pendingApproval: {
              has_pending: true,
              node_name: msg.node_name,
              step_label: msg.step_label,
              description: msg.data?.description || msg.message,
              approval_id: msg.data?.approval_id,
              node_execution_id: msg.data?.node_execution_id ?? null,
              approval_type: msg.data?.approval_type ?? 'node_approval',
              output_summary: msg.data?.output_summary ?? null,
              _source: 'ws',
            },
          });
          break;

        case 'NODE_REVISION_STARTED':
          get().addEvent(msg);
          set({ isPaused: false, isRunning: true, pendingApproval: null });
          break;

        case 'NODE_RETRY_STARTED':
          get().addEvent(msg);
          set({ isPaused: false, isRunning: true, pendingApproval: null });
          break;

        // ── Legacy Events ───────────────────────────────
        case 'APPROVAL_REQUIRED':
          get().addEvent(msg);
          set({ isPaused: true, isRunning: false, pendingApproval: msg.data });
          break;

        case 'WORKFLOW_COMPLETED':
          get().addEvent(msg);
          set({ isRunning: false, isPaused: false, currentNode: null, pendingApproval: null });
          break;

        case 'WORKFLOW_FAILED':
          get().addEvent(msg);
          set({ isRunning: false, isPaused: false, currentNode: null });
          break;

        default:
          if (msg.event_type) {
            get().addEvent(msg);
          }
          break;
      }
    };

    ws.onclose = (e) => {
      // Only process if this is still our active socket
      if (get().socket !== ws) return;
      set({ socket: null, connectionStatus: 'disconnected' });

      if (!_intentionalClose && _activeResearchId === researchId) {
        console.log(`[WS] Connection closed (code=${e.code}). Scheduling reconnect...`);
        _scheduleReconnect(researchId, get);
      }
    };

    ws.onerror = () => {
      // onerror always fires before onclose — reconnection handled in onclose
    };

    set({ socket: ws });
  },

  disconnectWebSocket: () => {
    _intentionalClose = true;
    _activeResearchId = null;
    _clearReconnect();
    _reconnectAttempt = 0;

    const { socket } = get();
    if (socket) {
      try {
        socket.close(1000, 'Client disconnect');
      } catch { /* ignore */ }
      set({
        socket: null,
        connectionStatus: 'disconnected',
        events: [],
        currentNode: null,
        isRunning: false,
        isPaused: false,
        pendingApproval: null,
      });
    }
    _intentionalClose = false;
  },
}));


function _scheduleReconnect(researchId: string, get: () => WorkflowState) {
  _clearReconnect();

  if (_reconnectAttempt >= MAX_RECONNECT_ATTEMPTS) {
    console.warn('[WS] Max reconnect attempts reached. Stopping.');
    return;
  }

  const delay = _getReconnectDelay();
  console.log(`[WS] Reconnecting in ${delay}ms (attempt ${_reconnectAttempt})...`);

  _reconnectTimer = setTimeout(() => {
    // Only reconnect if no other socket has taken over
    if (_activeResearchId === researchId && !get().socket) {
      get().connectWebSocket(researchId);
    }
  }, delay);
}
