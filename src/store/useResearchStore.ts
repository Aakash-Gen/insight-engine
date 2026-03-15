import { create } from 'zustand';
import { startResearch as apiStartResearch, listReports, deleteReport, type ReportListItem } from '@/lib/api';

export type AgentStatus = 'waiting' | 'running' | 'done' | 'retrying';
export type ResearchDepth = 'quick' | 'standard' | 'deep';

export interface AgentStep {
  id: string;
  agent: 'planner' | 'researcher' | 'critic' | 'synthesizer' | 'writer';
  status: AgentStatus;
  title: string;
  content: string[];
  timestamp: Date;
  isExpanded: boolean;
}

export interface ReportSection {
  id: string;
  title: string;
  content: string;
  confidenceScore?: number;
  isStreaming: boolean;
}

export interface ResearchSession {
  id: string;
  query: string;
  depth: ResearchDepth;
  status: 'running' | 'completed';
  agents: AgentStep[];
  report: ReportSection[];
  overallConfidence: number;
  tokenUsage: number;
  estimatedCost: number;
  startedAt: Date;
}

export interface SavedReport {
  id: string;
  title: string;
  query: string;
  date: Date;
  depth: ResearchDepth;
  confidenceScore: number;
  tags: string[];
  status: 'completed' | 'running';
}

interface ResearchState {
  currentSession: ResearchSession | null;
  savedReports: SavedReport[];
  isLoading: boolean;
  error: string | null;
  startResearch: (query: string, depth: ResearchDepth) => void;
  startResearchWithAPI: (query: string, depth: ResearchDepth, userId: string) => Promise<string>;
  initSession: (id: string) => void;
  updateAgent: (agentId: string, updates: Partial<AgentStep>) => void;
  addAgentStep: (step: AgentStep) => void;
  addReportSection: (section: ReportSection) => void;
  updateReportSection: (id: string, updates: Partial<ReportSection>) => void;
  setSession: (session: Partial<ResearchSession>) => void;
  toggleAgentExpand: (agentId: string) => void;
  loadUserReports: (userId: string) => Promise<void>;
  removeReport: (researchId: string) => Promise<void>;
}

export const useResearchStore = create<ResearchState>((set, get) => ({
  currentSession: null,
  savedReports: [],
  isLoading: false,
  error: null,

  /**
   * Ensure a session exists for the given id (e.g. after page refresh).
   * No-op if the current session already matches.
   */
  initSession: (id) => {
    set({
      currentSession: {
        id,
        query: '',
        depth: 'standard',
        status: 'running',
        agents: [],
        report: [],
        overallConfidence: 0,
        tokenUsage: 0,
        estimatedCost: 0,
        startedAt: new Date(),
      },
    });
  },

  /** Local-only session start (used by mock/fallback path). */
  startResearch: (query, depth) => {
    const session: ResearchSession = {
      id: Date.now().toString(),
      query,
      depth,
      status: 'running',
      agents: [],
      report: [],
      overallConfidence: 0,
      tokenUsage: 0,
      estimatedCost: 0,
      startedAt: new Date(),
    };
    set({ currentSession: session, error: null });
  },

  /** Call the backend to start research; returns the real research_id. */
  startResearchWithAPI: async (query, depth, userId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await apiStartResearch({ topic: query, depth });
      const session: ResearchSession = {
        id: res.research_id,
        query,
        depth,
        status: 'running',
        agents: [],
        report: [],
        overallConfidence: 0,
        tokenUsage: 0,
        estimatedCost: 0,
        startedAt: new Date(),
      };
      set({ currentSession: session, isLoading: false });
      return res.research_id;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start research';
      set({ isLoading: false, error: message });
      throw err;
    }
  },

  updateAgent: (agentId, updates) => {
    set((state) => {
      if (!state.currentSession) return state;
      return {
        currentSession: {
          ...state.currentSession,
          agents: state.currentSession.agents.map((a) =>
            a.id === agentId ? { ...a, ...updates } : a
          ),
        },
      };
    });
  },

  addAgentStep: (step) => {
    set((state) => {
      if (!state.currentSession) return state;
      return {
        currentSession: {
          ...state.currentSession,
          agents: [...state.currentSession.agents, step],
        },
      };
    });
  },

  addReportSection: (section) => {
    set((state) => {
      if (!state.currentSession) return state;
      return {
        currentSession: {
          ...state.currentSession,
          report: [...state.currentSession.report, section],
        },
      };
    });
  },

  updateReportSection: (id, updates) => {
    set((state) => {
      if (!state.currentSession) return state;
      return {
        currentSession: {
          ...state.currentSession,
          report: state.currentSession.report.map((s) =>
            s.id === id ? { ...s, ...updates } : s
          ),
        },
      };
    });
  },

  setSession: (updates) => {
    set((state) => {
      if (!state.currentSession) return state;
      return {
        currentSession: { ...state.currentSession, ...updates },
      };
    });
  },

  toggleAgentExpand: (agentId) => {
    set((state) => {
      if (!state.currentSession) return state;
      return {
        currentSession: {
          ...state.currentSession,
          agents: state.currentSession.agents.map((a) =>
            a.id === agentId ? { ...a, isExpanded: !a.isExpanded } : a
          ),
        },
      };
    });
  },

  loadUserReports: async (userId) => {
    set({ isLoading: true });
    try {
      const items: ReportListItem[] = await listReports(userId);
      const reports: SavedReport[] = items.map((item) => ({
        id: item.research_id,
        title: item.title,
        query: item.title,
        date: item.created_at ? new Date(item.created_at) : new Date(),
        depth: item.depth as ResearchDepth,
        confidenceScore: Math.round(item.overall_confidence * 100),
        tags: [],
        status: 'completed' as const,
      }));
      set({ savedReports: reports, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load reports';
      set({ isLoading: false, error: message });
    }
  },

  removeReport: async (researchId) => {
    await deleteReport(researchId);
    set((state) => ({
      savedReports: state.savedReports.filter((r) => r.id !== researchId),
    }));
  },
}));
