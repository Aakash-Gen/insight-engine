import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Brain, Search, ShieldCheck, Layers, PenTool } from 'lucide-react';
import type { AgentStep, AgentStatus } from '@/store/useResearchStore';
import { useResearchStore } from '@/store/useResearchStore';

const agentConfig = {
  planner: { icon: Brain, color: 'text-purple-400', bg: 'bg-purple-400/10', label: 'Planner Agent' },
  researcher: { icon: Search, color: 'text-blue-400', bg: 'bg-blue-400/10', label: 'Researcher Agent' },
  critic: { icon: ShieldCheck, color: 'text-orange-400', bg: 'bg-orange-400/10', label: 'Critic Agent' },
  synthesizer: { icon: Layers, color: 'text-cyan-400', bg: 'bg-cyan-400/10', label: 'Synthesizer Agent' },
  writer: { icon: PenTool, color: 'text-green-400', bg: 'bg-green-400/10', label: 'Writer Agent' },
};

const statusConfig: Record<AgentStatus, { label: string; dotClass: string }> = {
  waiting: { label: 'Waiting', dotClass: 'bg-muted-foreground' },
  running: { label: 'Running', dotClass: 'bg-primary pulse-dot' },
  done: { label: 'Done', dotClass: 'bg-green-500' },
  retrying: { label: 'Retrying', dotClass: 'bg-orange-500 pulse-dot' },
};

export const AgentCard = ({ step }: { step: AgentStep }) => {
  const toggleAgentExpand = useResearchStore((s) => s.toggleAgentExpand);
  const config = agentConfig[step.agent];
  const status = statusConfig[step.status];
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="glass-card rounded-lg overflow-hidden"
    >
      <button
        onClick={() => toggleAgentExpand(step.id)}
        className="w-full flex items-center gap-3 p-3 hover:bg-surface-hover transition-colors"
      >
        <div className={`p-2 rounded-md ${config.bg}`}>
          <Icon className={`w-4 h-4 ${config.color}`} />
        </div>
        <div className="flex-1 text-left">
          <div className="text-sm font-medium text-foreground">{config.label}</div>
          <div className="text-xs text-muted-foreground">{step.title}</div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${status.dotClass}`} />
            <span className="text-xs text-muted-foreground">{status.label}</span>
          </div>
          <ChevronDown
            className={`w-4 h-4 text-muted-foreground transition-transform ${
              step.isExpanded ? 'rotate-180' : ''
            }`}
          />
        </div>
      </button>

      <AnimatePresence>
        {step.isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 pt-1 border-t border-border">
              <div className="space-y-1 font-mono text-xs text-muted-foreground">
                {step.content.map((line, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.05 }}
                    className="leading-relaxed"
                  >
                    {line}
                  </motion.div>
                ))}
              </div>
              <div className="mt-2 text-xs text-muted-foreground/50">
                {step.timestamp.toLocaleTimeString()}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
