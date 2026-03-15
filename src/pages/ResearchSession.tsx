import { useEffect, useCallback, useState, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft,
  Copy,
  Download,
  Share2,
  BookMarked,
  Send,
  Coins,
  MessageCircle,
  X,
  BookOpen,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { AgentCard } from '@/components/AgentCard';
import { ConfidenceGauge } from '@/components/ConfidenceGauge';
import { toast } from 'sonner';
import { useResearchStore, type AgentStep, type ReportSection } from '@/store/useResearchStore';
import { streamResearch, sendOverride, getReport, exportReport, askReport, type AgentLogEvent, type CompletionEvent } from '@/lib/api';
import { useAuthStore } from '@/store/useAuthStore';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Cell,
} from 'recharts';

// Map backend agent names to valid AgentStep agent type
type ValidAgent = AgentStep['agent'];
const VALID_AGENTS: ValidAgent[] = ['planner', 'researcher', 'critic', 'synthesizer', 'writer'];
function isValidAgent(name: string): name is ValidAgent {
  return VALID_AGENTS.includes(name as ValidAgent);
}

// Derive an agent card title from the log
function logToTitle(agent: string, status: string, message: string): string {
  if (message && message.length < 80) return message;
  const defaults: Record<string, string> = {
    planner: 'Creating research plan...',
    researcher: status === 'retrying' ? 'Re-searching to fill gaps...' : 'Searching sources...',
    critic: 'Reviewing findings for gaps...',
    synthesizer: 'Merging and weighing findings...',
    writer: 'Writing final report...',
  };
  return defaults[agent] ?? `${agent} running...`;
}

const ResearchSession = () => {
  const navigate = useNavigate();
  const { id: routeId } = useParams<{ id: string }>();
  const { user } = useAuthStore();
  const {
    currentSession,
    setSession,
    updateAgent,
    addAgentStep,
    addReportSection,
    initSession,
  } = useResearchStore();

  const [isComplete, setIsComplete] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [override, setOverride] = useState('');
  const [qualityData, setQualityData] = useState<{ name: string; score: number; fill: string }[]>([]);
  const [reportTitle, setReportTitle] = useState<string>('');
  const [qaOpen, setQaOpen] = useState(false);
  const [qaQuestion, setQaQuestion] = useState('');
  const [qaAnswer, setQaAnswer] = useState('');
  const [qaLoading, setQaLoading] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);
  const agentStepMap = useRef<Map<string, string>>(new Map()); // agent key → step id
  const researchIdRef = useRef<string | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);
  const sourcesRef = useRef<{url: string; title: string}[]>([]);

  // The research_id comes from the route param (set by Dashboard after API call)
  const researchId = routeId ?? currentSession?.id ?? null;

  // Fetch final report and populate right panel
  const loadFinalReport = useCallback(async (rid: string) => {
    try {
      const report = await getReport(rid);
      sourcesRef.current = report.sources || [];
      setReportTitle(report.title);

      // Build report sections for right panel
      const sections: ReportSection[] = [];

      if (report.executive_summary) {
        sections.push({
          id: 'exec',
          title: 'Executive Summary',
          content: report.executive_summary,
          isStreaming: false,
        });
      }

      if (report.key_findings?.length) {
        sections.push({
          id: 'findings',
          title: 'Key Findings',
          content: report.key_findings.map((f, i) => `${i + 1}. ${f}`).join('\n\n'),
          isStreaming: false,
        });
      }

      for (const sec of report.sections) {
        sections.push({
          id: sec.title.toLowerCase().replace(/\s+/g, '-'),
          title: sec.title,
          content: sec.content,
          isStreaming: false,
        });
      }

      if (report.conflicting_perspectives) {
        sections.push({
          id: 'conflicts',
          title: 'Conflicting Perspectives',
          content: report.conflicting_perspectives,
          isStreaming: false,
        });
      }

      // Sources are shown in the dedicated Sources panel, not as a report section

      sections.forEach((s) => addReportSection(s));

      const confidence = Math.round(report.overall_confidence * 100);
      setSession({ status: 'completed', overallConfidence: confidence });
      setStreamingText('');

      if (report.quality_breakdown) {
        const qb = report.quality_breakdown;
        setQualityData([
          { name: 'Source Diversity', score: Math.round(qb.source_diversity * 100), fill: 'hsl(239, 84%, 67%)' },
          { name: 'Recency', score: Math.round(qb.recency * 100), fill: 'hsl(187, 94%, 43%)' },
          { name: 'Depth', score: Math.round(qb.depth * 100), fill: 'hsl(142, 71%, 45%)' },
          { name: 'Cross-validation', score: Math.round(qb.cross_validation * 100), fill: 'hsl(45, 93%, 47%)' },
        ]);
      }
    } catch (err) {
      console.error('Failed to load final report:', err);
    }
  }, [addReportSection, setSession]);

  // Handle a single SSE log event
  const handleLog = useCallback((event: AgentLogEvent) => {
    if (!isValidAgent(event.agent)) return;

    const agentKey = `${event.agent}-${event.status === 'retrying' ? 'retry' : 'main'}`;
    const existing = agentStepMap.current.get(agentKey);

    if (existing) {
      // Update the existing card
      updateAgent(existing, {
        status: event.status as AgentStep['status'],
        title: logToTitle(event.agent, event.status, event.message),
        content: [event.message],
      });
    } else {
      // Create a new card
      const stepId = `${event.agent}-${Date.now()}`;
      agentStepMap.current.set(agentKey, stepId);
      addAgentStep({
        id: stepId,
        agent: event.agent,
        status: event.status as AgentStep['status'],
        title: logToTitle(event.agent, event.status, event.message),
        content: [event.message],
        timestamp: new Date(event.timestamp),
        isExpanded: true,
      });
    }
  }, [updateAgent, addAgentStep]);

  // Handle incoming synthesizer token events
  const handleToken = useCallback((agent: string, text: string) => {
    if (agent === 'synthesizer') {
      setStreamingText((prev) => prev + text);
    }
  }, []);

  // Handle the SSE completion event
  const handleComplete = useCallback((event: CompletionEvent) => {
    setIsComplete(true);
    if (event.research_id) {
      loadFinalReport(event.research_id);
    }
  }, [loadFinalReport]);

  // Always reset session state on mount so replayed SSE logs don't duplicate
  // onto stale agents left over from a previous visit to this page.
  useEffect(() => {
    if (researchId) {
      initSession(researchId);
    }
  }, [researchId]);

  // Subscribe to SSE stream
  useEffect(() => {
    if (!researchId) return;
    if (researchIdRef.current === researchId) return;
    researchIdRef.current = researchId;

    let cancelled = false;
    streamResearch(
      researchId,
      handleLog,
      handleComplete,
      (err) => console.error('SSE error:', err),
      handleToken,
    ).then((cleanup) => {
      if (cancelled) {
        cleanup();
      } else {
        cleanupRef.current = cleanup;
      }
    }).catch((err) => console.error('Failed to open SSE stream:', err));

    return () => {
      cancelled = true;
      cleanupRef.current?.();
      cleanupRef.current = null;
    };
  }, [researchId, handleLog, handleComplete, handleToken]);

  // Auto-scroll agent feed
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [currentSession?.agents.length]);

  const handleSendOverride = async () => {
    if (!override.trim() || !researchId) return;
    try {
      await sendOverride(researchId, override.trim());
      setOverride('');
    } catch (err) {
      console.error('Override failed:', err);
    }
  };

  const handleExport = async () => {
    if (!researchId) return;
    try {
      const blob = await exportReport(researchId, 'md');
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(reportTitle || researchId).slice(0, 60).replace(/\s+/g, '_')}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  const handleExportPdf = () => {
    if (!researchId || !currentSession) return;
    const sections = currentSession.report;
    const sources = sourcesRef.current;
    const title = reportTitle || currentSession.query || 'Research Report';

    const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>${title}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Georgia, serif; font-size: 13pt; line-height: 1.7;
           color: #1a1a1a; max-width: 760px; margin: 40px auto; padding: 0 32px; }
    h1 { font-size: 22pt; margin-bottom: 6px; }
    .meta { color: #555; font-size: 10pt; margin-bottom: 32px; }
    h2 { font-size: 14pt; margin: 28px 0 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
    p { margin-bottom: 12px; }
    ol, ul { margin: 8px 0 12px 22px; }
    li { margin-bottom: 6px; }
    .sources { margin-top: 36px; }
    .sources a { color: #2563eb; text-decoration: none; word-break: break-all; }
    sup { color: #2563eb; font-size: 8pt; }
    @media print {
      body { margin: 0; padding: 24px; }
      a { color: #2563eb !important; }
    }
  </style>
</head>
<body>
  <h1>${title}</h1>
  <div class="meta">Generated by ResearchMind · ${new Date().toLocaleDateString()}</div>
  ${sections.map(s => `
    <h2>${s.title}</h2>
    ${s.content.split('\n').filter(Boolean).map(p =>
      p.match(/^\d+\./) ? `<ol><li>${p.replace(/^\d+\.\s*/, '')}</li></ol>` : `<p>${p}</p>`
    ).join('')}
  `).join('')}
  ${sources.length > 0 ? `
    <div class="sources">
      <h2>Sources</h2>
      <ol>${sources.map(s => `<li><a href="${s.url}">${s.title || s.url}</a></li>`).join('')}</ol>
    </div>
  ` : ''}
</body>
</html>`;

    const win = window.open('', '_blank');
    if (!win) return;
    win.document.write(html);
    win.document.close();
    win.focus();
    setTimeout(() => { win.print(); }, 400);
  };

  const handleShare = async () => {
    const url = window.location.href;
    try {
      await navigator.clipboard.writeText(url);
      toast.success('Link copied to clipboard');
    } catch {
      // Fallback for browsers without clipboard API
      const input = document.createElement('input');
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
      toast.success('Link copied to clipboard');
    }
  };

  const handleAsk = async () => {
    if (!qaQuestion.trim() || !researchId || qaLoading) return;
    setQaLoading(true);
    setQaAnswer('');
    setQaQuestion('');
    try {
      const result = await askReport(researchId, qaQuestion.trim());
      setQaAnswer(result.answer);
    } catch (err) {
      setQaAnswer('Failed to get an answer. Please try again.');
      console.error('Q&A failed:', err);
    } finally {
      setQaLoading(false);
    }
  };

  const renderWithCitations = (text: string) => {
    const sources = sourcesRef.current;
    if (!sources.length) return <span>{text}</span>;

    // Split on [SOURCE N] pattern
    const parts = text.split(/(\[SOURCE \d+\])/g);
    return (
      <span>
        {parts.map((part, i) => {
          const match = part.match(/\[SOURCE (\d+)\]/);
          if (match) {
            const idx = parseInt(match[1], 10) - 1;
            const source = sources[idx];
            if (source?.url) {
              return (
                <a
                  key={i}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={source.title || source.url}
                  className="inline-flex items-center align-super text-[10px] font-mono text-primary/70 hover:text-primary bg-primary/10 hover:bg-primary/20 rounded px-1 ml-0.5 transition-colors"
                >
                  {match[1].replace('SOURCE ', '')}
                </a>
              );
            }
          }
          return <span key={i}>{part}</span>;
        })}
      </span>
    );
  };

  const agents = currentSession?.agents ?? [];
  const reportSections = currentSession?.report ?? [];
  const overallConfidence = currentSession?.overallConfidence ?? 0;
  const topic = currentSession?.query ?? 'Research in progress...';
  const title = reportTitle || topic;

  return (
    <div className="min-h-screen bg-background flex flex-col grain-overlay">
      {/* Header */}
      <header className="h-14 border-b border-border flex items-center justify-between px-4 shrink-0 bg-background/80 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/dashboard')}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <div className="text-sm font-medium text-foreground">{topic}</div>
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
          <Button variant="ghost" size="sm" onClick={() => setSourcesOpen(true)} disabled={!isComplete} title="View sources">
            <BookOpen className="w-4 h-4" />
            {sourcesRef.current.length > 0 && (
              <span className="ml-1 text-xs text-muted-foreground">{sourcesRef.current.length}</span>
            )}
          </Button>
          <Button variant="ghost" size="sm" onClick={handleExport} disabled={!isComplete} title="Export as Markdown">
            <Download className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setQaOpen(true)} disabled={!isComplete} title="Ask a question">
            <MessageCircle className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={handleShare} title="Copy link">
            <Share2 className="w-4 h-4" />
          </Button>
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
            {agents.length === 0 && (
              <div className="text-sm text-muted-foreground text-center mt-8">
                Waiting for agents to start...
              </div>
            )}
          </div>

          {/* Override + Stats */}
          <div className="border-t border-border p-4 space-y-3">
            <div className="flex gap-2">
              <Input
                value={override}
                onChange={(e) => setOverride(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendOverride()}
                placeholder="Redirect the research..."
                className="bg-surface border-border text-sm"
                disabled={isComplete}
              />
              <Button
                size="sm"
                className="bg-primary hover:bg-primary/90 shrink-0"
                onClick={handleSendOverride}
                disabled={isComplete || !override.trim()}
              >
                <Send className="w-3 h-3" />
              </Button>
            </div>
            <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
              <div className="flex items-center gap-1">
                <Coins className="w-3 h-3" />
                {(currentSession?.tokenUsage ?? 0).toLocaleString()} tokens
              </div>
              <div>~${((currentSession?.tokenUsage ?? 0) * 0.000002).toFixed(4)} estimated</div>
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
              {title}
            </motion.h1>

            <div className="space-y-8">
              {streamingText && !isComplete && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="mb-8"
                >
                  <h2 className="font-display text-lg font-semibold text-foreground mb-3">
                    Research Synthesis
                    <span className="ml-2 w-1.5 h-1.5 rounded-full bg-green-500 pulse-dot inline-block align-middle" />
                  </h2>
                  <div className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
                    {streamingText}
                  </div>
                </motion.div>
              )}
              {reportSections.map((section) => (
                <AnimatePresence key={section.id}>
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <h2 className="font-display text-lg font-semibold text-foreground">
                        {section.title}
                      </h2>
                      {section.confidenceScore !== undefined && (
                        <span
                          className={`text-xs font-mono px-2 py-0.5 rounded-full ${
                            section.confidenceScore >= 80
                              ? 'bg-green-500/10 text-green-400'
                              : section.confidenceScore >= 60
                              ? 'bg-yellow-500/10 text-yellow-400'
                              : 'bg-red-500/10 text-red-400'
                          }`}
                        >
                          {section.confidenceScore}%
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground leading-relaxed">
                      {section.isStreaming ? (
                        <span className="whitespace-pre-line">{section.content}</span>
                      ) : (
                        <span className="whitespace-pre-line">{renderWithCitations(section.content)}</span>
                      )}
                    </div>
                  </motion.div>
                </AnimatePresence>
              ))}

              {reportSections.length === 0 && !isComplete && (
                <div className="text-sm text-muted-foreground text-center mt-16 opacity-50">
                  Report will appear here as research completes...
                </div>
              )}
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
                        <ConfidenceGauge score={overallConfidence} />
                      </div>
                      {qualityData.length > 0 && (
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
                      )}
                    </div>
                  </div>

                  <div className="flex gap-3 flex-wrap">
                    <Button className="flex-1 bg-primary hover:bg-primary/90" onClick={handleExport}>
                      <Download className="w-4 h-4 mr-2" /> Export Markdown
                    </Button>
                    <Button variant="outline" className="flex-1 border-border hover:bg-surface-hover" onClick={handleExportPdf}>
                      <Download className="w-4 h-4 mr-2" /> Export PDF
                    </Button>
                    <Button variant="outline" className="flex-1 border-border hover:bg-surface-hover" onClick={() => setSourcesOpen(true)}>
                      <BookOpen className="w-4 h-4 mr-2" /> {sourcesRef.current.length} Sources
                    </Button>
                    <Button variant="outline" className="flex-1 border-border hover:bg-surface-hover" onClick={handleShare}>
                      <Share2 className="w-4 h-4 mr-2" /> Share Link
                    </Button>
                    <Button variant="outline" className="flex-1 border-border hover:bg-surface-hover" onClick={() => setQaOpen(true)}>
                      <MessageCircle className="w-4 h-4 mr-2" /> Ask a Question
                    </Button>
                    <Button
                      variant="outline"
                      className="flex-1 border-border hover:bg-surface-hover"
                      onClick={() => navigate('/dashboard')}
                    >
                      New Research
                    </Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Q&A Side Panel */}
      <AnimatePresence>
        {qaOpen && (
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed right-0 top-0 h-full w-[400px] bg-background border-l border-border flex flex-col z-50 shadow-2xl"
          >
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h3 className="font-display text-sm font-semibold text-foreground">Ask About This Report</h3>
              <button onClick={() => setQaOpen(false)} className="text-muted-foreground hover:text-foreground transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {qaAnswer && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="glass-card rounded-lg p-4"
                >
                  <div className="text-xs text-muted-foreground mb-2 uppercase tracking-wide">Answer</div>
                  <p className="text-sm text-foreground leading-relaxed whitespace-pre-line">{qaAnswer}</p>
                </motion.div>
              )}
              {!qaAnswer && !qaLoading && (
                <div className="text-sm text-muted-foreground text-center mt-8">
                  Ask any follow-up question about the report's findings, sources, or conclusions.
                </div>
              )}
              {qaLoading && (
                <div className="text-sm text-muted-foreground text-center mt-8">Thinking...</div>
              )}
            </div>

            <div className="border-t border-border p-4">
              <div className="flex gap-2">
                <Input
                  value={qaQuestion}
                  onChange={(e) => setQaQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
                  placeholder="Ask a follow-up question..."
                  className="bg-surface border-border text-sm"
                  disabled={qaLoading}
                />
                <Button
                  size="sm"
                  className="bg-primary hover:bg-primary/90 shrink-0"
                  onClick={handleAsk}
                  disabled={qaLoading || !qaQuestion.trim()}
                >
                  <Send className="w-3 h-3" />
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sources Side Panel */}
      <AnimatePresence>
        {sourcesOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.4 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black z-40"
              onClick={() => setSourcesOpen(false)}
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="fixed right-0 top-0 h-full w-[420px] bg-background border-l border-border flex flex-col z-50 shadow-2xl"
            >
              <div className="flex items-center justify-between p-4 border-b border-border">
                <div>
                  <h3 className="font-display text-sm font-semibold text-foreground">Sources</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {sourcesRef.current.length} sources consulted
                  </p>
                </div>
                <button onClick={() => setSourcesOpen(false)} className="text-muted-foreground hover:text-foreground transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-2">
                {sourcesRef.current.map((source, i) => {
                  let domain = '';
                  try { domain = new URL(source.url).hostname.replace('www.', ''); } catch {}
                  return (
                    <a
                      key={i}
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-start gap-3 p-3 rounded-lg border border-border bg-surface hover:bg-surface-hover hover:border-muted-foreground/30 transition-all group"
                    >
                      <span className="shrink-0 w-5 h-5 rounded-full bg-primary/10 text-primary text-xs font-mono flex items-center justify-center mt-0.5">
                        {i + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-foreground font-medium leading-snug line-clamp-2 group-hover:text-primary transition-colors">
                          {source.title || domain}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1 truncate">{domain}</div>
                      </div>
                      <ExternalLink className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </a>
                  );
                })}
                {sourcesRef.current.length === 0 && (
                  <div className="text-sm text-muted-foreground text-center mt-8">No sources available.</div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ResearchSession;
