import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { ParticleBackground } from '@/components/ParticleBackground';
import {
  ArrowRight,
  Network,
  RefreshCw,
  Activity,
  Sparkles,
  Search,
  ShieldCheck,
  PenTool,
  Check,
  Github,
  Twitter,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const fadeUp = {
  initial: { opacity: 0, y: 30 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true },
  transition: { duration: 0.6 },
};

const stagger = {
  initial: { opacity: 0, y: 20 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true },
};

const Landing = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background grain-overlay">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-40 border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="container mx-auto flex items-center justify-between h-16 px-6">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <span className="font-display text-lg font-bold text-foreground">ResearchMind</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
            <a href="#features" className="hover:text-foreground transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-foreground transition-colors">How It Works</a>
            <a href="#pricing" className="hover:text-foreground transition-colors">Pricing</a>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/login')}>
              Log in
            </Button>
            <Button size="sm" onClick={() => navigate('/signup')} className="bg-primary hover:bg-primary/90">
              Get Started
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
        <ParticleBackground />
        <div className="relative z-10 text-center px-6 max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-primary/20 bg-primary/5 text-primary text-xs font-medium mb-8">
              <Sparkles className="w-3 h-3" />
              Now in Public Beta
            </div>
            <h1 className="font-display text-5xl md:text-7xl font-bold text-foreground leading-tight mb-6">
              Research at the
              <br />
              <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                speed of thought
              </span>
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
              Multi-agent AI that plans, searches, critiques and synthesizes
              intelligence reports — autonomously.
            </p>
            <div className="flex items-center justify-center gap-4">
              <Button
                size="lg"
                onClick={() => navigate('/signup')}
                className="bg-primary hover:bg-primary/90 text-primary-foreground px-8 glow-primary"
              >
                Start Researching Free
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={() => {
                  document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' });
                }}
                className="border-border hover:bg-surface-hover"
              >
                See How It Works
              </Button>
            </div>
          </motion.div>
        </div>

        {/* Gradient fade at bottom */}
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background to-transparent" />
      </section>

      {/* Agent Demo */}
      <section className="py-24 px-6">
        <div className="container mx-auto max-w-5xl">
          <motion.div {...fadeUp} className="glass-card rounded-2xl p-8 border border-border/50">
            <div className="flex items-center gap-2 mb-6">
              <div className="w-2 h-2 rounded-full bg-green-500 pulse-dot" />
              <span className="text-xs font-mono text-green-400">LIVE DEMO</span>
            </div>
            <div className="grid md:grid-cols-2 gap-6">
              <div className="space-y-3">
                {[
                  { label: 'Planner', text: 'Breaking query into 4 sub-questions...', color: 'text-purple-400' },
                  { label: 'Researcher', text: 'Searching 15 sources across arXiv, Scholar...', color: 'text-blue-400' },
                  { label: 'Critic', text: 'Gap found: Missing 2024 data on adoption rates', color: 'text-orange-400' },
                  { label: 'Synthesizer', text: 'Merging findings with confidence weighting...', color: 'text-cyan-400' },
                ].map((agent, i) => (
                  <motion.div
                    key={agent.label}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.2 }}
                    className="flex items-start gap-3 p-3 rounded-lg bg-background/50"
                  >
                    <span className={`text-xs font-mono font-medium ${agent.color} whitespace-nowrap`}>
                      [{agent.label}]
                    </span>
                    <span className="text-sm text-muted-foreground font-mono">{agent.text}</span>
                  </motion.div>
                ))}
              </div>
              <div className="bg-background/50 rounded-lg p-4">
                <div className="text-xs font-mono text-muted-foreground/60 mb-3">OUTPUT</div>
                <div className="space-y-2 text-sm text-foreground/80">
                  <div className="font-medium text-foreground">Executive Summary</div>
                  <p className="text-muted-foreground leading-relaxed">
                    Large language models are fundamentally reshaping software engineering roles.
                    Our analysis of 15 sources reveals a shift toward AI-augmented development,
                    with 73% of engineers reporting daily LLM usage in 2024...
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-6">
        <div className="container mx-auto max-w-5xl">
          <motion.div {...fadeUp} className="text-center mb-16">
            <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground mb-4">
              Intelligence, not just search
            </h2>
            <p className="text-muted-foreground max-w-xl mx-auto">
              A multi-agent system that thinks, critiques, and synthesizes like a research team.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: Network,
                title: 'Multi-Agent Orchestration',
                desc: 'Five specialized agents collaborate in real-time — planning, searching, critiquing, synthesizing, and writing.',
              },
              {
                icon: RefreshCw,
                title: 'Self-Correcting RAG',
                desc: 'A critic agent identifies gaps and sends the researcher back for more data. The loop continues until quality thresholds are met.',
              },
              {
                icon: Activity,
                title: 'Real-time Streaming',
                desc: 'Watch your report materialize in real-time. Every agent step is visible with full transparency.',
              },
            ].map((feature, i) => (
              <motion.div
                key={feature.title}
                {...stagger}
                transition={{ delay: i * 0.15 }}
                className="glass-card rounded-xl p-6 hover:border-primary/30 transition-colors group"
              >
                <div className="p-3 rounded-lg bg-primary/5 w-fit mb-4 group-hover:bg-primary/10 transition-colors">
                  <feature.icon className="w-5 h-5 text-primary" />
                </div>
                <h3 className="font-display text-lg font-semibold text-foreground mb-2">{feature.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{feature.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-24 px-6">
        <div className="container mx-auto max-w-5xl">
          <motion.div {...fadeUp} className="text-center mb-16">
            <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground mb-4">
              How it works
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-4 gap-6">
            {[
              { step: '01', icon: Sparkles, title: 'Plan', desc: 'AI breaks your question into sub-queries and creates a research strategy.' },
              { step: '02', icon: Search, title: 'Research', desc: 'Agents search across academic papers, news, and databases in parallel.' },
              { step: '03', icon: ShieldCheck, title: 'Critique', desc: 'A critic agent reviews findings, identifies gaps, and triggers re-research.' },
              { step: '04', icon: PenTool, title: 'Synthesize', desc: 'Findings are merged into a structured, citation-backed intelligence report.' },
            ].map((item, i) => (
              <motion.div
                key={item.step}
                {...stagger}
                transition={{ delay: i * 0.1 }}
                className="text-center"
              >
                <div className="text-xs font-mono text-primary mb-3">{item.step}</div>
                <div className="mx-auto p-3 rounded-lg bg-surface w-fit mb-4 border border-border">
                  <item.icon className="w-5 h-5 text-foreground" />
                </div>
                <h3 className="font-display font-semibold text-foreground mb-2">{item.title}</h3>
                <p className="text-sm text-muted-foreground">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24 px-6">
        <div className="container mx-auto max-w-5xl">
          <motion.div {...fadeUp} className="text-center mb-16">
            <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground mb-4">
              Simple pricing
            </h2>
            <p className="text-muted-foreground">Start free. Upgrade when you're ready.</p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {[
              {
                name: 'Free',
                price: '$0',
                desc: 'For trying things out',
                features: ['3 reports per day', 'Standard depth', 'Community support'],
                cta: 'Get Started',
                highlight: false,
              },
              {
                name: 'Pro',
                price: '$19',
                desc: 'For serious researchers',
                features: ['Unlimited reports', 'All depth levels', 'Export & sharing', 'Priority support'],
                cta: 'Start Pro Trial',
                highlight: true,
              },
              {
                name: 'Team',
                price: '$49',
                desc: 'For research teams',
                features: ['Everything in Pro', 'Shared workspace', 'API access', 'Custom agents'],
                cta: 'Contact Sales',
                highlight: false,
              },
            ].map((plan, i) => (
              <motion.div
                key={plan.name}
                {...stagger}
                transition={{ delay: i * 0.1 }}
                className={`rounded-xl p-6 border ${
                  plan.highlight
                    ? 'border-primary bg-primary/5 glow-primary'
                    : 'border-border bg-surface'
                }`}
              >
                <div className="mb-4">
                  <h3 className="font-display text-lg font-semibold text-foreground">{plan.name}</h3>
                  <p className="text-sm text-muted-foreground">{plan.desc}</p>
                </div>
                <div className="mb-6">
                  <span className="font-display text-4xl font-bold text-foreground">{plan.price}</span>
                  {plan.price !== '$0' && <span className="text-muted-foreground text-sm">/mo</span>}
                </div>
                <ul className="space-y-2 mb-6">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Check className="w-4 h-4 text-primary" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Button
                  className={`w-full ${
                    plan.highlight
                      ? 'bg-primary hover:bg-primary/90'
                      : 'bg-surface-hover hover:bg-muted border border-border'
                  }`}
                  onClick={() => navigate('/signup')}
                >
                  {plan.cta}
                </Button>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-12 px-6">
        <div className="container mx-auto max-w-5xl flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            <span className="font-display font-bold text-foreground">ResearchMind</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-muted-foreground">
            <a href="#features" className="hover:text-foreground transition-colors">Features</a>
            <a href="#pricing" className="hover:text-foreground transition-colors">Pricing</a>
            <a href="#" className="hover:text-foreground transition-colors">Docs</a>
          </div>
          <div className="flex items-center gap-4">
            <Github className="w-4 h-4 text-muted-foreground hover:text-foreground transition-colors cursor-pointer" />
            <Twitter className="w-4 h-4 text-muted-foreground hover:text-foreground transition-colors cursor-pointer" />
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
