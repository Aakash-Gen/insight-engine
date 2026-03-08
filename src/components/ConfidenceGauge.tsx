import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

interface ConfidenceGaugeProps {
  score: number;
  size?: number;
  strokeWidth?: number;
}

export const ConfidenceGauge = ({ score, size = 120, strokeWidth = 8 }: ConfidenceGaugeProps) => {
  const [animatedScore, setAnimatedScore] = useState(0);
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (animatedScore / 100) * circumference;

  const getColor = (s: number) => {
    if (s < 40) return 'hsl(0, 72%, 51%)';
    if (s < 70) return 'hsl(45, 93%, 47%)';
    return 'hsl(142, 71%, 45%)';
  };

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedScore(score), 200);
    return () => clearTimeout(timer);
  }, [score]);

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          stroke="hsl(var(--border))"
          fill="none"
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          stroke={getColor(animatedScore)}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: 'easeOut' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-2xl font-bold text-foreground">{Math.round(animatedScore)}%</span>
        <span className="text-xs text-muted-foreground">confidence</span>
      </div>
    </div>
  );
};
