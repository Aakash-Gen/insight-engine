import { motion } from 'framer-motion';
import { Zap, Target, Telescope } from 'lucide-react';
import type { ResearchDepth } from '@/store/useResearchStore';

interface Props {
  value: ResearchDepth;
  onChange: (depth: ResearchDepth) => void;
}

const options: { value: ResearchDepth; label: string; icon: typeof Zap; desc: string; time: string }[] = [
  { value: 'quick', label: 'Quick Scan', icon: Zap, desc: '3-5 sources, fast overview', time: '~30s' },
  { value: 'standard', label: 'Standard', icon: Target, desc: '10-15 sources, balanced', time: '~2min' },
  { value: 'deep', label: 'Deep Dive', icon: Telescope, desc: '25+ sources, comprehensive', time: '~5min' },
];

export const ResearchDepthSelector = ({ value, onChange }: Props) => {
  return (
    <div className="grid grid-cols-3 gap-3">
      {options.map((opt) => {
        const isSelected = value === opt.value;
        const Icon = opt.icon;
        return (
          <motion.button
            key={opt.value}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onChange(opt.value)}
            className={`relative p-3 rounded-lg border text-left transition-all ${
              isSelected
                ? 'border-primary bg-primary/5 glow-primary'
                : 'border-border bg-surface hover:border-muted-foreground/30'
            }`}
          >
            <Icon className={`w-4 h-4 mb-2 ${isSelected ? 'text-primary' : 'text-muted-foreground'}`} />
            <div className={`text-sm font-medium ${isSelected ? 'text-foreground' : 'text-muted-foreground'}`}>
              {opt.label}
            </div>
            <div className="text-xs text-muted-foreground mt-1">{opt.desc}</div>
            <div className="text-xs text-muted-foreground/60 mt-1">{opt.time}</div>
          </motion.button>
        );
      })}
    </div>
  );
};
