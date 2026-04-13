import { create } from 'zustand';

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

interface WorkflowState {
  events: WorkflowEvent[];
  currentNode: string | null;
  isRunning: boolean;
  isPaused: boolean;
  pendingApproval: any | null;
  eventSource: EventSource | null;

  // Actions
  addEvent: (event: WorkflowEvent) => void;
  clearEvents: () => void;
  connectSSE: (researchId: string) => void;
  disconnectSSE: () => void;
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  events: [],
  currentNode: null,
  isRunning: false,
  isPaused: false,
  pendingApproval: null,
  eventSource: null,

  addEvent: (event) => {
    set((state) => ({
      events: [...state.events, event],
      currentNode: event.node_name || state.currentNode,
    }));
  },

  clearEvents: () => {
    set({ events: [], currentNode: null, isRunning: false, isPaused: false, pendingApproval: null });
  },

  connectSSE: (researchId: string) => {
    // Close existing connection
    get().disconnectSSE();

    const token = localStorage.getItem('access_token');
    const url = `/api/v1/events/stream/${researchId}`;
    
    // EventSource doesn't support auth headers, so we use fetch-based SSE
    const es = new EventSource(url);

    es.addEventListener('connected', () => {
      set({ isRunning: true });
    });

    es.addEventListener('NODE_STARTED', (e) => {
      const event = JSON.parse(e.data);
      get().addEvent(event);
      set({ isRunning: true, currentNode: event.node_name });
    });

    es.addEventListener('NODE_COMPLETED', (e) => {
      const event = JSON.parse(e.data);
      get().addEvent(event);
    });

    es.addEventListener('NODE_FAILED', (e) => {
      const event = JSON.parse(e.data);
      get().addEvent(event);
    });

    es.addEventListener('ARTIFACT_CREATED', (e) => {
      const event = JSON.parse(e.data);
      get().addEvent(event);
    });

    es.addEventListener('LOG_MESSAGE', (e) => {
      const event = JSON.parse(e.data);
      get().addEvent(event);
    });

    es.addEventListener('APPROVAL_REQUIRED', (e) => {
      const event = JSON.parse(e.data);
      get().addEvent(event);
      set({ isPaused: true, isRunning: false, pendingApproval: event.data });
    });

    es.addEventListener('WORKFLOW_COMPLETED', (e) => {
      const event = JSON.parse(e.data);
      get().addEvent(event);
      set({ isRunning: false, currentNode: null });
    });

    es.addEventListener('WORKFLOW_FAILED', (e) => {
      const event = JSON.parse(e.data);
      get().addEvent(event);
      set({ isRunning: false, currentNode: null });
    });

    es.addEventListener('ping', () => {
      // keepalive
    });

    es.onerror = () => {
      // Reconnect after delay
      setTimeout(() => {
        if (get().eventSource === es) {
          get().connectSSE(researchId);
        }
      }, 5000);
    };

    set({ eventSource: es });
  },

  disconnectSSE: () => {
    const { eventSource } = get();
    if (eventSource) {
      eventSource.close();
      set({ eventSource: null });
    }
  },
}));
