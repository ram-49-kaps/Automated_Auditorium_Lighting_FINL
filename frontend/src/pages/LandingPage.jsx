import { useNavigate, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import ParticleBackground from '../components/ui/ParticleBackground'
import Header from '../components/layout/Header'
import { BrainCircuit, Lightbulb, MonitorPlay, FileText, Sparkles, Rocket, ArrowDown, CheckCircle2 } from 'lucide-react'

export default function LandingPage() {
    const navigate = useNavigate()
    const location = useLocation()
    const [showSuccess, setShowSuccess] = useState(false)

    useEffect(() => {
        const params = new URLSearchParams(location.search)
        if (params.get('feedback') === 'success') {
            setShowSuccess(true)
            // Clean up the URL
            window.history.replaceState({}, '', '/')
            // Hide after 5 seconds
            setTimeout(() => setShowSuccess(false), 5000)
        }
    }, [location])

    const features = [
        {
            icon: <BrainCircuit className="w-10 h-10 text-[#00d4ff]" />,
            title: 'AI Emotion Analysis',
            desc: 'DistilRoBERTa ML model detects joy, fear, anger, sadness and more from any script.',
            tag: 'PHASE 2',
        },
        {
            icon: <Lightbulb className="w-10 h-10 text-[#00d4ff]" />,
            title: 'Smart Lighting Design',
            desc: 'RAG + LangChain knowledge base generates professional lighting cues automatically.',
            tag: 'PHASE 3 + 4',
        },
        {
            icon: <MonitorPlay className="w-10 h-10 text-[#00d4ff]" />,
            title: '3D Visualization',
            desc: 'Real-time Three.js WebGL simulation with 40+ fixtures, smoke effects, and smooth transitions.',
            tag: 'PHASE 5',
        },
    ]

    const steps = [
        { num: '01', title: 'Upload Script', desc: 'Drop your PDF, TXT, or DOCX file' },
        { num: '02', title: 'AI Processes', desc: 'Pipeline analyzes emotions & generates cues' },
        { num: '03', title: 'View Simulation', desc: '3D auditorium lights up automatically' },
    ]

    return (
        <div className="min-h-screen relative overflow-hidden font-body">
            <ParticleBackground />
            <Header />

            {/* Hero Section */}
            <section className="relative z-10 flex flex-col items-center justify-center min-h-screen px-6 text-center">

                {/* Success Toast */}
                <div className={`fixed top-24 left-1/2 -translate-x-1/2 z-50 transition-all duration-500 transform ${showSuccess ? 'translate-y-0 opacity-100 visible' : '-translate-y-8 opacity-0 invisible'}`}>
                    <div className="bg-emerald-500/10 border border-emerald-500/30 backdrop-blur-md px-6 py-3 rounded-full flex items-center gap-3 shadow-[0_0_20px_rgba(16,185,129,0.2)]">
                        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                        <span className="font-mono text-xs uppercase tracking-widest text-emerald-100 font-semibold">
                            TELEMETRY RECEIVED & CALIBRATED
                        </span>
                    </div>
                </div>

                {/* Status Badge */}
                <div className="animate-fade-in mb-8">
                    <div className="inline-flex items-center gap-3 px-4 py-1.5 rounded-md
                           bg-black/40 border border-[#00d4ff]/30 text-xs text-[#00d4ff] font-mono uppercase tracking-widest backdrop-blur-md shadow-[0_0_15px_rgba(0,212,255,0.15)]">
                        <span className="w-2 h-2 rounded-full bg-[#00d4ff] animate-pulse shadow-[0_0_8px_#00d4ff]" />
                        SYSTEM ONLINE // AUTO-LIGHTING ENGINE
                    </div>
                </div>

                {/* Main Title */}
                <h1 className="font-display font-black text-6xl md:text-8xl lg:text-9xl leading-none tracking-tighter
                        animate-fade-in-up mb-6 uppercase"
                    style={{ animationDelay: '0.1s' }}>
                    <span className="text-transparent bg-clip-text bg-gradient-to-br from-white via-white to-white/40">
                        Lumina
                    </span>
                    <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00d4ff] to-blue-600 drop-shadow-[0_0_30px_rgba(0,212,255,0.3)]">
                        Intelligence
                    </span>
                </h1>

                {/* Subtitle */}
                <p className="text-base md:text-lg text-white/50 max-w-2xl mx-auto mb-12 font-mono uppercase tracking-widest
                      animate-fade-in-up leading-relaxed"
                    style={{ animationDelay: '0.3s' }}>
                    Enterprise-Grade Stage Lighting Architecture.
                    <br />
                    <span className="text-white/30 text-sm mt-2 block">Upload manuscript to initialize semantic analysis and DMX routing.</span>
                </p>

                {/* CTA */}
                <div className="animate-fade-in-up" style={{ animationDelay: '0.5s' }}>
                    <button
                        onClick={() => navigate('/upload')}
                        className="group relative px-8 py-4 bg-[#00d4ff]/10 hover:bg-[#00d4ff]/20 border border-[#00d4ff]/50 
                        text-[#00d4ff] font-mono text-sm uppercase tracking-[0.2em] transition-all duration-300
                        shadow-[0_0_20px_rgba(0,212,255,0.1)] hover:shadow-[0_0_30px_rgba(0,212,255,0.25)] flex items-center justify-center gap-3 overflow-hidden"
                    >
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out" />
                        <span className="relative z-10 font-bold">Upload Script</span>
                    </button>
                </div>

                {/* Scroll hint */}
                <div className="absolute bottom-8 animate-bounce flex flex-col items-center gap-2 opacity-30 hover:opacity-100 transition-opacity">
                    <span className="font-mono text-[10px] uppercase tracking-widest text-[#00d4ff]">PROCEED</span>
                    <ArrowDown className="w-4 h-4 text-[#00d4ff]" />
                </div>
            </section>

            {/* How It Works */}
            <section className="relative z-10 py-24 px-6">
                <div className="max-w-5xl mx-auto">
                    <div className="text-center mb-16">
                        <span className="text-xs font-mono text-[#00d4ff] uppercase tracking-widest">How It Works</span>
                        <h2 className="text-3xl md:text-5xl font-display font-black text-transparent bg-clip-text bg-gradient-to-r from-white to-white/50 mt-3 uppercase tracking-tight">
                            Three Simple Steps
                        </h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {steps.map((step, i) => (
                            <div
                                key={step.num}
                                className="glass-card p-8 relative group animate-fade-in-up"
                                style={{ animationDelay: `${0.2 * i}s` }}
                            >
                                {/* Step Number */}
                                <span className="text-6xl font-display font-bold text-white/[0.03] absolute top-4 right-6">
                                    {step.num}
                                </span>

                                {/* Arrow connector */}
                                {i < steps.length - 1 && (
                                    <div className="hidden md:block absolute -right-3 top-1/2 -translate-y-1/2 z-10
                                  text-white/20 text-xl">
                                        →
                                    </div>
                                )}

                                <div className="relative z-10">
                                    <div className="w-10 h-10 rounded bg-[#00d4ff]/10
                                  flex items-center justify-center mb-4 border border-[#00d4ff]/30 shadow-[0_0_15px_rgba(0,212,255,0.15)]">
                                        <span className="text-sm font-mono text-[#00d4ff] font-bold">{step.num}</span>
                                    </div>
                                    <h3 className="font-display font-bold text-white/90 mb-2 uppercase tracking-wide text-sm">{step.title}</h3>
                                    <p className="text-xs text-white/40 font-mono tracking-wide">{step.desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Features */}
            <section className="relative z-10 py-24 px-6 bg-gradient-to-b from-transparent to-stage-surface/50">
                <div className="max-w-5xl mx-auto">
                    <div className="text-center mb-16">
                        <span className="text-xs font-mono text-[#00d4ff] uppercase tracking-widest">Technology</span>
                        <h2 className="text-3xl md:text-5xl font-display font-black text-transparent bg-clip-text bg-gradient-to-r from-white to-white/50 mt-3 uppercase tracking-tight">
                            Powered by AI
                        </h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {features.map((f, i) => (
                            <div
                                key={f.title}
                                className="glass-card p-8 group hover:scale-[1.02] animate-fade-in-up"
                                style={{ animationDelay: `${0.15 * i}s` }}
                            >
                                <div className="text-4xl mb-4 group-hover:animate-float">{f.icon}</div>
                                <div className="flex items-center gap-2 mb-3">
                                    <h3 className="font-display font-bold text-white/90 uppercase tracking-wide text-sm">{f.title}</h3>
                                    <span className="text-[10px] font-mono text-[#00d4ff] bg-[#00d4ff]/10 border border-[#00d4ff]/20
                                   px-2 py-0.5 rounded tracking-widest">{f.tag}</span>
                                </div>
                                <p className="text-xs text-white/40 leading-relaxed font-mono">{f.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Supported Formats */}
            <section className="relative z-10 py-20 px-6">
                <div className="max-w-3xl mx-auto text-center">
                    <h2 className="text-2xl font-display font-bold text-white mb-8">Supported Formats</h2>
                    <div className="flex items-center justify-center gap-4 flex-wrap">
                        {[
                            { ext: 'PDF', icon: <FileText className="w-8 h-8 text-red-500" />, color: 'from-red-500/20 to-red-600/10 border-red-500/20' },
                            { ext: 'TXT', icon: <FileText className="w-8 h-8 text-gray-400" />, color: 'from-gray-400/20 to-gray-500/10 border-gray-400/20' },
                            { ext: 'DOCX', icon: <FileText className="w-8 h-8 text-blue-500" />, color: 'from-blue-500/20 to-blue-600/10 border-blue-500/20' },
                        ].map(f => (
                            <div key={f.ext} className={`flex items-center gap-3 px-6 py-3 rounded-xl
                                            bg-gradient-to-r ${f.color} border`}>
                                {f.icon}
                                <span className="font-display font-medium text-white/80">.{f.ext}</span>
                                <span className="text-emerald-400 text-xs">✓</span>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Final CTA */}
            <section className="relative z-10 py-20 px-6 text-center">
                <div className="max-w-2xl mx-auto">
                    <h2 className="text-3xl font-display font-bold text-white mb-4">Ready to Light Up?</h2>
                    <p className="text-white/40 mb-8">Upload your script and see the magic happen.</p>
                    <button onClick={() => navigate('/upload')} className="group relative px-8 py-4 bg-[#00d4ff]/10 hover:bg-[#00d4ff]/20 border border-[#00d4ff]/50 
                        text-[#00d4ff] font-mono text-sm uppercase tracking-[0.2em] transition-all duration-300
                        shadow-[0_0_20px_rgba(0,212,255,0.1)] hover:shadow-[0_0_30px_rgba(0,212,255,0.25)] flex items-center justify-center gap-3 overflow-hidden mx-auto">
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out" />
                        <span className="relative z-10 font-bold flex items-center gap-2">
                            <Rocket className="w-5 h-5" /> INITIALIZE
                        </span>
                    </button>
                </div>
            </section>

            {/* Footer */}
            <footer className="relative z-10 border-t border-white/5 py-8 px-6">
                <div className="max-w-5xl mx-auto flex items-center justify-between text-xs text-white/30">
                    <span>© 2026 Lumina AI - Lighting Automation</span>
                    <span className="font-mono">Built with DistilRoBERTa • RAG • Three.js</span>
                </div>
            </footer>
        </div>
    )
}
