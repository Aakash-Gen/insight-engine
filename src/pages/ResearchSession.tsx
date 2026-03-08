import { useEffect, useCallback, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft,
  Copy,
  Download,
  Share2,
  BookMarked,
  Send,
  Coins,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { AgentCard } from '@/components/AgentCard';
import { ConfidenceGauge } from '@/components/ConfidenceGauge';
import { useResearchStore, type AgentStep, type ReportSection } from '@/store/useResearchStore';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Cell,
} from 'recharts';

const mockPlan = [
  '1. What are the key capabilities of current multi-agent AI systems?',
  '2. How do they compare to single-agent approaches in research tasks?',
  '3. What are the main challenges and limitations?',
  '4. What does the competitive landscape look like?',
];

const mockSearchQueries = [
  'Searching: "multi-agent AI systems 2024 survey"',
  'Found: arxiv.org/abs/2401.xxxxx — Multi-Agent Systems Survey',
  'Searching: "agent orchestration frameworks comparison"',
  'Found: github.com/langchain-ai/langgraph — Agent Orchestration',
  'Searching: "RAG self-correction techniques"',
  'Found: research.google — Self-RAG: Learning to Retrieve',
];

const mockCritique = [
  '⚠ Gap: No data on production deployment metrics',
  '⚠ Gap: Missing comparison with human researcher performance',
  '✓ Adequate coverage of technical architecture',
  '→ Recommending: Re-search for deployment case studies',
];

const mockResearchRetry = [
  'Searching: "multi-agent AI production deployment metrics 2024"',
  'Found: Scale AI blog — Enterprise Agent Deployment Report',
  'Searching: "human vs AI research quality comparison"',
  'Found: Nature — Comparative Study on AI-Assisted Research',
];

const reportSections: { id: string; title: string; content: string; confidence: number }[] = [
  {
    id: 'exec',
    title: 'Executive Summary',
    confidence: 89,
    content:
      'Multi-agent AI systems represent a paradigm shift in automated research, enabling coordinated intelligence gathering that surpasses single-agent approaches by 40-60% in comprehensiveness [1]. Our analysis of 23 sources reveals rapid adoption in enterprise settings, with 67% of Fortune 500 companies exploring agent-based workflows [2]. The technology is maturing from research prototypes to production systems, though significant challenges remain in reliability and cost optimization.',
  },
  {
    id: 'findings',
    title: 'Key Findings',
    confidence: 85,
    content:
      '1. **Agent Specialization Outperforms Generalization**: Systems with dedicated planning, research, and critique agents produce 43% higher quality outputs than monolithic agents [3].\n\n2. **Self-Correction Loops are Critical**: Iterative critique-and-retry cycles improve factual accuracy by 28% compared to single-pass generation [4].\n\n3. **Cost Efficiency**: Multi-agent systems use 2-3x more tokens but deliver significantly more comprehensive results, with a net cost-per-insight ratio that favors the multi-agent approach [5].\n\n4. **Human-in-the-Loop Remains Important**: The most effective deployments maintain human oversight at strategic decision points, reducing hallucination rates by 60% [6].',
  },
  {
    id: 'analysis',
    title: 'Detailed Analysis',
    confidence: 82,
    content:
      'The multi-agent research landscape is dominated by three architectural patterns: hierarchical orchestration (used by AutoGPT, BabyAGI), peer-to-peer collaboration (CrewAI, MetaGPT), and hybrid approaches (LangGraph, Microsoft Autogen) [7].\n\nHierarchical systems excel at complex, multi-step research tasks where a central planner can decompose queries effectively. Peer-to-peer systems show advantages in creative and exploratory research where emergent behavior is beneficial [8].\n\nThe critic agent pattern — where one agent reviews and challenges another\'s outputs — has emerged as perhaps the single most impactful architectural decision, correlating with a 35% improvement in output quality across all benchmarks [9].',
  },
  {
    id: 'perspectives',
    title: 'Conflicting Perspectives',
    confidence: 74,
    content:
      'There is significant debate on whether multi-agent systems represent genuine architectural innovation or merely "prompt engineering with extra steps." Critics argue that similar results can be achieved with well-crafted single prompts [10]. Proponents counter that the modularity and observability of multi-agent systems provide crucial benefits for enterprise adoption and debugging [11].\n\nCost remains contentious: while multi-agent systems consume more compute, advocates argue the cost-per-quality-unit is actually lower when measuring actionable insights rather than raw token output [12].',
  },
  {
    id: 'sources',
    title: 'Sources & Citations',
    confidence: 95,
    content:
      '[1] Wang et al., "A Survey on Multi-Agent Systems," arXiv 2024\n[2] McKinsey, "Enterprise AI Adoption Report Q3 2024"\n[3] AutoGen Team, "Specialization vs Generalization in Agent Systems," Microsoft Research\n[4] Asai et al., "Self-RAG: Learning to Retrieve, Generate, and Critique," NeurIPS 2023\n[5] LangChain, "Cost Analysis of Multi-Agent Architectures," 2024\n[6] Anthropic, "Human-in-the-Loop Patterns for AI Agents," 2024\n[7] Liu et al., "Agent Architecture Comparison Study," Stanford HAI\n[8] CrewAI, "Peer-to-Peer Agent Collaboration Whitepaper," 2024\n[9] Google DeepMind, "The Critic Agent Pattern," 2024\n[10] Karpathy, "Against Multi-Agent Complexity," Blog Post\n[11] Harrison Chase, "Why Agents Need Structure," LangChain Blog\n[12] Scale AI, "Enterprise Agent Deployment Report," 2024',
  },
];

const qualityData = [
  { name: 'Source Diversity', score: 85, fill: 'hsl(239, 84%, 67%)' },
  { name: 'Recency', score: 78, fill: 'hsl(187, 94%, 43%)' },
  { name: 'Depth', score: 92, fill: 'hsl(142, 71%, 45%)' },
  { name: 'Cross-validation', score: 71, fill: 'hsl(45, 93%, 47%)' },
];

const ResearchSession = () => {
  const navigate = useNavigate();
  const {
    currentSession,
    setSession,
    updateAgent,
  } = useResearchStore();

  const [visibleSections, setVisibleSections] = useState<string[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [tokenCount, setTokenCount] = useState(0);
  const [override, setOverride] = useState('');
  const feedRef = useRef<HTMLDivElement>(null);
  const hasStarted = useRef(false);

  const addAgent = useCallback(
    (agent: AgentStep) => {
      useResearchStore.setState((state) => {
        if (!state.currentSession) return state;
        return {
          currentSession: {
            ...state.currentSession,
            agents: [...state.currentSession.agents, agent],
          },
        };
      });
    },
    []
  );

  useEffect(() => {
    if (hasStarted.current) return;
    hasStarted.current = true;

    // If no session, create one
    if (!currentSession) {
      useResearchStore.getState().startResearch('Multi-agent AI systems: current state and future potential', 'deep');
    }

    const timers: ReturnType<typeof setTimeout>[] = [];

    // Planner at 0.5s
    timers.push(
      setTimeout(() => {
        addAgent({
          id: 'planner-1',
          agent: 'planner',
          status: 'running',
          title: 'Creating research plan...',
          content: mockPlan,
          timestamp: new Date(),
          isExpanded: true,
        });
        setTokenCount(1240);
      }, 500)
    );

    timers.push(
      setTimeout(() => {
        updateAgent('planner-1', { status: 'done', title: 'Research plan created' });
      }, 2500)
    );

    // Researcher at 3s
    timers.push(
      setTimeout(() => {
        addAgent({
          id: 'researcher-1',
          agent: 'researcher',
          status: 'running',
          title: 'Searching 15 sources...',
          content: mockSearchQueries,
          timestamp: new Date(),
          isExpanded: true,
        });
        setTokenCount(3890);
        setVisibleSections(['exec']);
      }, 3000)
    );

    timers.push(
      setTimeout(() => {
        updateAgent('researcher-1', { status: 'done', title: 'Found 15 relevant sources' });
        setVisibleSections(['exec', 'findings']);
        setTokenCount(6420);
      }, 5500)
    );

    // Critic at 6s
    timers.push(
      setTimeout(() => {
        addAgent({
          id: 'critic-1',
          agent: 'critic',
          status: 'running',
          title: 'Reviewing findings for gaps...',
          content: mockCritique,
          timestamp: new Date(),
          isExpanded: true,
        });
        setTokenCount(7850);
      }, 6000)
    );

    timers.push(
      setTimeout(() => {
        updateAgent('critic-1', { status: 'done', title: '2 gaps identified, triggering re-research' });
      }, 7500)
    );

    // Researcher retry at 8s
    timers.push(
      setTimeout(() => {
        addAgent({
          id: 'researcher-2',
          agent: 'researcher',
          status: 'retrying',
          title: 'Re-searching to fill gaps...',
          content: mockResearchRetry,
          timestamp: new Date(),
          isExpanded: true,
        });
        setTokenCount(9200);
        setVisibleSections(['exec', 'findings', 'analysis']);
      }, 8000)
    );

    timers.push(
      setTimeout(() => {
        updateAgent('researcher-2', { status: 'done', title: 'Gaps filled with 4 additional sources' });
        setTokenCount(11340);
      }, 9500)
    );

    // Synthesizer + Writer at 10s
    timers.push(
      setTimeout(() => {
        addAgent({
          id: 'synth-1',
          agent: 'synthesizer',
          status: 'running',
          title: 'Merging and weighting findings...',
          content: ['Applying confidence weighting...', 'Cross-referencing 19 sources...', 'Resolving conflicting claims...'],
          timestamp: new Date(),
          isExpanded: true,
        });
        setVisibleSections(['exec', 'findings', 'analysis', 'perspectives']);
        setTokenCount(13560);
      }, 10000)
    );

    timers.push(
      setTimeout(() => {
        updateAgent('synth-1', { status: 'done', title: 'Synthesis complete' });
        addAgent({
          id: 'writer-1',
          agent: 'writer',
          status: 'running',
          title: 'Structuring final report...',
          content: ['Writing executive summary...', 'Formatting citations...', 'Generating confidence scores...'],
          timestamp: new Date(),
          isExpanded: true,
        });
        setTokenCount(15890);
      }, 11500)
    );

    // Complete at 13s
    timers.push(
      setTimeout(() => {
        updateAgent('writer-1', { status: 'done', title: 'Report complete' });
        setVisibleSections(['exec', 'findings', 'analysis', 'perspectives', 'sources']);
        setTokenCount(18420);
        setIsComplete(true);
        setSession({ status: 'completed', overallConfidence: 84, tokenUsage: 18420, estimatedCost: 0.037 });
      }, 13000)
    );

    return () => timers.forEach(clearTimeout);
  }, []);

  // Auto-scroll agent feed
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [currentSession?.agents.length]);

  const agents = currentSession?.agents || [];

  return (
    <div className="min-h-screen bg-background flex flex-col grain-overlay">
      {/* Header */}
      <header className="h-14 border-b border-border flex items-center justify-between px-4 shrink-0 bg-background/80 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/dashboard')}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <div className="text-sm font-medium text-foreground">
              {currentSession?.query || 'Multi-agent AI systems: current state and future potential'}
            </div>
            <div className="flex items-center gap-2">
              {!isComplete && (
                <span className="flex items-center gap-1.5 text-xs">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 pulse-dot" />
                  <span className="text-green-400 font-mono">LIVE</span>
                </span>
              )}
              {isComplete && (
                <span className="text-xs text-muted-foreground font-mono">COMPLETED</span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm"><Copy className="w-4 h-4" /></Button>
          <Button variant="ghost" size="sm"><Download className="w-4 h-4" /></Button>
          <Button variant="ghost" size="sm"><BookMarked className="w-4 h-4" /></Button>
          <Button variant="ghost" size="sm"><Share2 className="w-4 h-4" /></Button>
        </div>
      </header>

      {/* Panels */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel — Agent Feed */}
        <div className="w-[40%] border-r border-border flex flex-col">
          <div className="p-4 border-b border-border">
            <h2 className="text-sm font-display font-semibold text-foreground">Agent Workflow</h2>
          </div>

          <div ref={feedRef} className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-3">
            <AnimatePresence>
              {agents.map((step) => (
                <AgentCard key={step.id} step={step} />
              ))}
            </AnimatePresence>
          </div>

          {/* Override + Stats */}
          <div className="border-t border-border p-4 space-y-3">
            <div className="flex gap-2">
              <Input
                value={override}
                onChange={(e) => setOverride(e.target.value)}
                placeholder="Redirect the research..."
                className="bg-surface border-border text-sm"
              />
              <Button size="sm" className="bg-primary hover:bg-primary/90 shrink-0">
                <Send className="w-3 h-3" />
              </Button>
            </div>
            <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
              <div className="flex items-center gap-1">
                <Coins className="w-3 h-3" />
                {tokenCount.toLocaleString()} tokens
              </div>
              <div>~${(tokenCount * 0.000002).toFixed(4)} estimated</div>
            </div>
          </div>
        </div>

        {/* Right Panel — Report */}
        <div className="w-[60%] overflow-y-auto scrollbar-thin">
          <div className="max-w-3xl mx-auto p-8">
            <motion.h1
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="font-display text-2xl font-bold text-foreground mb-8"
            >
              Multi-Agent AI Systems: Current State & Future Potential
            </motion.h1>

            <div className="space-y-8">
              {reportSections.map((section) => {
                const isVisible = visibleSections.includes(section.id);
                return (
                  <AnimatePresence key={section.id}>
                    {isVisible && (
                      <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6 }}
                      >
                        <div className="flex items-center gap-3 mb-3">
                          <h2 className="font-display text-lg font-semibold text-foreground">
                            {section.title}
                          </h2>
                          {section.confidence && (
                            <span
                              className={`text-xs font-mono px-2 py-0.5 rounded-full ${
                                section.confidence >= 80
                                  ? 'bg-green-500/10 text-green-400'
                                  : section.confidence >= 60
                                  ? 'bg-yellow-500/10 text-yellow-400'
                                  : 'bg-red-500/10 text-red-400'
                              }`}
                            >
                              {section.confidence}%
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
                          {section.content}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                );
              })}
            </div>

            {/* Completion stats */}
            <AnimatePresence>
              {isComplete && (
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8, delay: 0.3 }}
                  className="mt-12 space-y-8"
                >
                  <div className="glass-card rounded-xl p-6">
                    <div className="flex items-center gap-8">
                      <div>
                        <div className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">
                          Overall Confidence
                        </div>
                        <ConfidenceGauge score={84} />
                      </div>
                      <div className="flex-1">
                        <div className="text-xs text-muted-foreground mb-3 uppercase tracking-wide">
                          Research Quality
                        </div>
                        <ResponsiveContainer width="100%" height={120}>
                          <BarChart data={qualityData} layout="vertical">
                            <XAxis type="number" domain={[0, 100]} hide />
                            <YAxis
                              type="category"
                              dataKey="name"
                              width={110}
                              tick={{ fontSize: 11, fill: 'hsl(240, 8%, 55%)' }}
                              axisLine={false}
                              tickLine={false}
                            />
                            <Bar dataKey="score" radius={[0, 4, 4, 0]} barSize={16}>
                              {qualityData.map((entry, i) => (
                                <Cell key={i} fill={entry.fill} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <Button className="flex-1 bg-primary hover:bg-primary/90">
                      <Download className="w-4 h-4 mr-2" /> Export as PDF
                    </Button>
                    <Button variant="outline" className="flex-1 border-border hover:bg-surface-hover">
                      Ask Follow-up Question
                    </Button>
                    <Button variant="outline" className="flex-1 border-border hover:bg-surface-hover">
                      Re-run Deep Dive
                    </Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResearchSession;
