export default function ProgressBar({ percent = 0, label = '' }) {
    return (
        <div className="w-full">
            {/* Label row */}
            <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-white/50 font-mono uppercase tracking-wider">{label}</span>
                <span className="text-sm font-display font-semibold gradient-text">{Math.round(percent)}%</span>
            </div>

            {/* Bar track */}
            <div className="w-full h-2.5 bg-white/5 rounded-full overflow-hidden">
                <div
                    className="h-full rounded-full shimmer-bar transition-all duration-700 ease-out relative"
                    style={{ width: `${Math.min(100, percent)}%` }}
                >
                    {/* Leading glow */}
                    <div className="absolute right-0 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-amber-400/40 blur-md" />
                </div>
            </div>
        </div>
    )
}
