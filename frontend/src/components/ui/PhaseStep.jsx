export default function PhaseStep({ phase, title, status, duration, stats, detail }) {
    const icons = {
        pending: '⏳',
        running: null, // uses spinner
        complete: '✅',
        error: '❌',
    }

    const statusColors = {
        pending: 'text-white/30',
        running: 'text-amber-400',
        complete: 'text-emerald-400',
        error: 'text-red-400',
    }

    return (
        <div className={`flex items-start gap-4 transition-all duration-500 ${status === 'pending' ? 'opacity-40' : 'opacity-100'
            }`}>
            {/* Step Indicator */}
            <div className="flex flex-col items-center">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${status === 'complete' ? 'border-emerald-500/50 bg-emerald-500/10' :
                        status === 'running' ? 'border-amber-500/50 bg-amber-500/10' :
                            status === 'error' ? 'border-red-500/50 bg-red-500/10' :
                                'border-white/10 bg-white/5'
                    }`}>
                    {status === 'running' ? (
                        <div className="spinner" />
                    ) : (
                        <span className="text-sm">{icons[status]}</span>
                    )}
                </div>
                {/* Connector Line */}
                <div className={`w-0.5 h-8 mt-1 transition-colors duration-500 ${status === 'complete' ? 'bg-emerald-500/30' : 'bg-white/5'
                    }`} />
            </div>

            {/* Content */}
            <div className="flex-1 pb-6">
                <div className="flex items-center justify-between">
                    <div>
                        <span className={`text-xs font-mono uppercase tracking-wider ${statusColors[status]}`}>
                            Phase {phase}
                        </span>
                        <h3 className={`text-sm font-display font-medium mt-0.5 ${status === 'pending' ? 'text-white/40' : 'text-white/90'
                            }`}>
                            {title}
                        </h3>
                    </div>
                    {duration && (
                        <span className="text-xs font-mono text-white/30">{duration.toFixed(1)}s</span>
                    )}
                </div>

                {/* Running detail */}
                {status === 'running' && detail && (
                    <p className="text-xs text-amber-400/70 mt-2 animate-pulse font-mono">{detail}</p>
                )}

                {/* Complete stats */}
                {status === 'complete' && stats && (
                    <div className="flex flex-wrap gap-2 mt-2 animate-fade-in">
                        {Object.entries(stats).map(([key, val]) => (
                            <span
                                key={key}
                                className="text-[11px] bg-white/5 text-white/50 px-2 py-0.5 rounded-md font-mono"
                            >
                                {key}: {val}
                            </span>
                        ))}
                    </div>
                )}

                {/* Error */}
                {status === 'error' && detail && (
                    <p className="text-xs text-red-400/80 mt-2 font-mono">{detail}</p>
                )}
            </div>
        </div>
    )
}
