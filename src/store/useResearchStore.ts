import { create } from 'zustand';

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
  startResearch: (query: string, depth: ResearchDepth) => void;
  updateAgent: (agentId: string, updates: Partial<AgentStep>) => void;
  addReportSection: (section: ReportSection) => void;
  updateReportSection: (id: string, updates: Partial<ReportSection>) => void;
  setSession: (session: Partial<ResearchSession>) => void;
  toggleAgentExpand: (agentId: string) => void;
}

const mockReports: SavedReport[] = [
  {
    id: '1',
    title: 'The Impact of LLMs on Software Engineering Roles 2024',
    query: 'How are large language models changing software engineering jobs?',
    date: new Date('2024-11-15'),
    depth: 'deep',
    confidenceScore: 87,
    tags: ['AI', 'Software Engineering', 'Labor Market'],
    status: 'completed',
  },
  {
    id: '2',
    title: 'Competitive Analysis: Anthropic vs OpenAI vs Google DeepMind',
    query: 'Compare the AI strategies and products of Anthropic, OpenAI, and Google DeepMind',
    date: new Date('2024-11-12'),
    depth: 'deep',
    confidenceScore: 92,
    tags: ['AI Companies', 'Competition', 'Strategy'],
    status: 'completed',
  },
  {
    id: '3',
    title: 'Climate Tech Investment Trends Q3 2024',
    query: 'What are the latest climate tech investment trends?',
    date: new Date('2024-11-08'),
    depth: 'standard',
    confidenceScore: 78,
    tags: ['Climate', 'Investment', 'VC'],
    status: 'completed',
  },
  {
    id: '4',
    title: 'The Rise of AI Agents in Enterprise Workflows',
    query: 'How are AI agents being adopted in enterprise settings?',
    date: new Date('2024-11-01'),
    depth: 'quick',
    confidenceScore: 71,
    tags: ['AI Agents', 'Enterprise', 'Automation'],
    status: 'completed',
  },
  {
    id: '5',
    title: 'Quantum Computing: From Research to Production',
    query: 'What is the current state of quantum computing commercialization?',
    date: new Date('2024-10-28'),
    depth: 'standard',
    confidenceScore: 83,
    tags: ['Quantum', 'Computing', 'Technology'],
    status: 'completed',
  },
];

export const useResearchStore = create<ResearchState>((set) => ({
  currentSession: null,
  savedReports: mockReports,
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
    set({ currentSession: session });
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
}));
