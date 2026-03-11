
import { useState, useEffect, useMemo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useWebSocket } from '../hooks/useWebSocket'
import Header from '../components/layout/Header'
import PhaseStep from '../components/ui/PhaseStep'
import ProgressBar from '../components/ui/ProgressBar'
import { CheckCircle2, Activity, AlertTriangle, Upload, Plus } from 'lucide-react'

// Phases definition for UI mapping
const PHASES = [
    { p: 1, title: 'Script Parsing' },
    { p: 2, title: 'Emotion Analysis' },
    { p: 3, title: 'Knowledge Retrieval' },
    { p: 4, title: 'Lighting Design' },
    { p: 6, title: 'Finalizing Output' },
]

export default function ProcessingPage() {
    const navigate = useNavigate()
    const { jobId } = useParams()

    // Connect to WebSocket
    const { status, messages, latestMessage } = useWebSocket(jobId);

    // State derivation from messages
    const [currentPhase, setCurrentPhase] = useState(1)
    const [progressPercent, setProgressPercent] = useState(0)
    const [phaseDetails, setPhaseDetails] = useState({}) // Store completion stats for each phase
    const [currentDetail, setCurrentDetail] = useState("Initializing...")
    const [isComplete, setIsComplete] = useState(false)
    const [error, setError] = useState(null)

    // Process incoming messages
    useEffect(() => {
        if (!latestMessage) return;

        const msg = latestMessage;

        if (msg.phase === 'error') {
            setError(msg.detail);
            return;
        }

        if (msg.phase === 'done' || msg.redirect) {
            setIsComplete(true);
            setTimeout(() => {
                navigate(msg.redirect || `/results/${jobId}`);
            }, 1000);
            return;
        }

        // Update current state
        setCurrentPhase(msg.phase);
        if (msg.progress) setProgressPercent(msg.progress);
        if (msg.detail) setCurrentDetail(msg.detail);

        // Store stats when complete
        if (msg.status === 'complete' && msg.stats) {
            setPhaseDetails(prev => ({
                ...prev,
                [msg.phase]: msg.stats
            }));
        }

    }, [latestMessage, navigate, jobId]);

    // Emotion Stats Extraction (from Phase 2)
    const emotionStats = useMemo(() => {
        return phaseDetails[2] || null;
    }, [phaseDetails]);

    if (!jobId) {
        return (
            <div className="min-h-screen bg-stage-bg text-white">
                <Header />
                <main className="pt-32 pb-16 px-6 flex flex-col items-center justify-center min-h-[80vh]">
                    <div className="glass-card max-w-lg w-full p-10 text-center animate-fade-in-up border border-[#00d4ff]/20 bg-black/40 backdrop-blur-xl shadow-[0_0_30px_rgba(0,212,255,0.05)]">
                        <div className="w-16 h-16 bg-[#00d4ff]/10 border border-[#00d4ff]/30 rounded flex items-center justify-center mx-auto mb-6 shadow-[0_0_15px_rgba(0,212,255,0.2)]">
                            <Upload className="w-8 h-8 text-[#00d4ff]" />
                        </div>
                        <h2 className="text-2xl font-mono font-bold mb-4 uppercase tracking-widest text-white">No Script Found</h2>
                        <p className="text-white/40 mb-8 leading-relaxed font-mono text-sm uppercase tracking-wide">
                            Pipeline requires text manuscript for semantic lighting analysis. Engage upload protocol to initialize.
                        </p>
                        <button onClick={() => navigate('/upload')} className="group relative px-6 py-3 bg-[#00d4ff]/10 hover:bg-[#00d4ff]/20 border border-[#00d4ff]/50 
                                text-[#00d4ff] font-mono text-xs uppercase tracking-[0.2em] transition-all duration-300
                                shadow-[0_0_15px_rgba(0,212,255,0.1)] hover:shadow-[0_0_25px_rgba(0,212,255,0.2)] flex items-center justify-center gap-3 overflow-hidden mx-auto">
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out" />
                            <span className="relative z-10 font-bold flex items-center gap-2">
                                <Plus className="w-4 h-4 flex-shrink-0" /> RETURN TO UPLOAD
                            </span>
                        </button>
                    </div>
                </main>
            </div>
        )
    }


    return (
        <div className="min-h-screen bg-stage-bg text-white">
            <Header />

            <main className="pt-24 pb-16 px-6">
                <div className="max-w-3xl mx-auto animate-fade-in">

                    {/* Header */}
                    <div className="text-center mb-10">
                        <span className={`inline-flex items-center gap-2 px-3 py-1 bg-black/40 text-[10px] font-mono uppercase tracking-[0.2em] rounded shadow-[0_0_10px_rgba(0,0,0,0.5)] mb-4 border
                                ${status === 'connected' ? 'border-green-500/30 text-green-400 shadow-[0_0_10px_rgba(34,197,94,0.15)]' :
                                status === 'error' ? 'border-red-500/30 text-red-400 shadow-[0_0_10px_rgba(239,68,68,0.15)]' :
                                    'border-yellow-500/30 text-yellow-400 shadow-[0_0_10px_rgba(234,179,8,0.15)]'}`}>
                            {status === 'connected' ? '● LIVE TELEMETRY' : '○ HANDSHAKE IN PROGRESS...'}
                        </span>

                        <h1 className="text-3xl md:text-5xl font-display font-black text-white mt-2 mb-3 uppercase tracking-tight flex items-center justify-center gap-4">
                            {isComplete ? <><CheckCircle2 className="w-8 h-8 text-emerald-400" /> SEQUENCE COMPLETE</> : <><Activity className="w-8 h-8 text-[#00d4ff] animate-pulse" /> COMPILING...</>}
                        </h1>
                        <p className="text-white/40 font-mono text-xs uppercase tracking-widest mt-3">
                            JOB_ID // <span className="text-[#00d4ff]">{jobId?.slice(0, 8)}...</span>
                        </p>
                    </div>

                    {/* Error Banner */}
                    {error && (
                        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl mb-8 text-center flex flex-col items-center">
                            <AlertTriangle className="w-8 h-8 mb-2" />
                            {error}
                            <button onClick={() => navigate('/')} className="block mx-auto mt-4 text-sm underline opacity-60 hover:opacity-100">
                                Return Home
                            </button>
                        </div>
                    )}

                    {/* Overall Progress */}
                    <div className="glass-card p-6 mb-8">
                        <ProgressBar
                            percent={progressPercent}
                            label={error ? "Process Failed" : currentDetail}
                        />
                    </div>

                    {/* Phase Steps Timeline */}
                    <div className="space-y-4">
                        {PHASES.map((p) => {
                            const isPast = currentPhase > p.p || (currentPhase === p.p && phaseDetails[p.p]);
                            const isCurrent = currentPhase === p.p && !phaseDetails[p.p];

                            // Map stats object to string for display
                            let statsStr = "";
                            if (phaseDetails[p.p]) {
                                const s = phaseDetails[p.p];
                                if (p.p === 1) statsStr = `${s.scenes} scenes • ${s.format}`;
                                if (p.p === 2) statsStr = `${Object.keys(s).length} emotions found`;
                                if (p.p === 4) statsStr = `${s.cues_generated} cues generated`;
                            }

                            return (
                                <PhaseStep
                                    key={p.p}
                                    phase={p.p}
                                    title={p.title}
                                    status={isPast ? 'complete' : isCurrent ? 'running' : 'pending'}
                                    detail={isCurrent ? currentDetail : statsStr}
                                />
                            );
                        })}
                    </div>

                    {/* Live Emotion Stats (Phase 2) */}
                    {emotionStats && (
                        <div className="glass-card p-6 mt-8 animate-slide-up">
                            <h3 className="text-xs font-mono text-white/40 uppercase tracking-widest mb-4">
                                Emotion Distribution
                            </h3>
                            <div className="grid grid-cols-3 md:grid-cols-7 gap-3">
                                {Object.entries(emotionStats).slice(0, 7).map(([emo, count]) => (
                                    <div key={emo} className="bg-white/5 border border-white/10 rounded-lg p-3 text-center">
                                        <div className="text-lg font-bold text-white">{count}</div>
                                        <div className="text-[10px] uppercase text-white/40 tracking-wider">{emo}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                </div>
            </main>
        </div>
    )
}
