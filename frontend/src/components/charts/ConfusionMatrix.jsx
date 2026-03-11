
import { useState } from 'react'
import { Smile, Ghost, Angry, Frown, Meh, AlertCircle } from 'lucide-react'

export default function ConfusionMatrix({
    data,
    title = "Confusion Matrix",
    rowLabel = "Actual",
    colLabel = "Predicted",
    mode = "classification"
}) {
    const [hoveredCell, setHoveredCell] = useState(null)

    // Default demo data if none provided
    const matrix = data || {
        labels: ['Joy', 'Fear', 'Anger', 'Sadness', 'Neutral'],
        values: [
            [12, 1, 0, 0, 2],
            [0, 15, 1, 2, 1],
            [0, 1, 10, 1, 0],
            [1, 1, 0, 8, 1],
            [2, 0, 0, 1, 28],
        ],
    }

    const { labels, values } = matrix

    // Calculate totals
    const total = values.reduce((s, row) => s + row.reduce((a, b) => a + b, 0), 0)

    // Metrics only for classification mode
    const correct = mode === 'classification' ? values.reduce((s, row, i) => s + row[i], 0) : 0
    const accuracy = mode === 'classification' ? ((correct / total) * 100).toFixed(1) : 0

    // Find max value for color scaling
    const maxVal = Math.max(...values.flat()) || 1

    // Per-class metrics (only meaningful for classification)
    const classMetrics = labels.map((label, i) => {
        if (mode !== 'classification') return {}

        const tp = values[i][i]
        const rowSum = values[i].reduce((a, b) => a + b, 0)
        const colSum = values.reduce((s, row) => s + row[i], 0)
        const precision = colSum > 0 ? ((tp / colSum) * 100).toFixed(0) : '0'
        const recall = rowSum > 0 ? ((tp / rowSum) * 100).toFixed(0) : '0'
        const f1 = precision > 0 && recall > 0
            ? ((2 * precision * recall) / (Number(precision) + Number(recall))).toFixed(0)
            : '0'
        return { label, tp, rowSum, colSum, precision, recall, f1 }
    })

    const getCellOpacity = (val) => {
        if (val === 0) return 0.05
        return Math.max(0.15, (val / maxVal) * 0.85)
    }

    const emotionEmojis = {
        'Joy': <Smile className="w-5 h-5 text-amber-500" />,
        'Fear': <Ghost className="w-5 h-5 text-purple-500" />,
        'Anger': <Angry className="w-5 h-5 text-red-500" />,
        'Sadness': <Frown className="w-5 h-5 text-blue-500" />,
        'Neutral': <Meh className="w-5 h-5 text-gray-400" />,
        'Surprise': <AlertCircle className="w-5 h-5 text-cyan-500" />,
        'Disgust': <Frown className="w-5 h-5 text-green-500" />
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-xs font-mono text-white/40 uppercase tracking-widest">
                        {title}
                    </h2>
                    <p className="text-[11px] text-white/25 mt-1">
                        Rows = {rowLabel} • Columns = {colLabel}
                    </p>
                </div>

                {mode === 'classification' && (
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 px-4 py-2 rounded-xl
                              bg-emerald-500/10 border border-emerald-500/20">
                            <span className="text-xs text-emerald-400/70">Accuracy</span>
                            <span className="text-lg font-display font-bold text-emerald-400">{accuracy}%</span>
                        </div>
                        <div className="text-right">
                            <span className="text-[11px] text-white/30 block">{correct}/{total} correct</span>
                            <span className="text-[11px] text-white/20">{total - correct} errors</span>
                        </div>
                    </div>
                )}
            </div>

            {/* Matrix Grid */}
            <div className="overflow-x-auto">
                <div className="min-w-[400px]">
                    {/* Column Headers */}
                    <div className="flex mb-1">
                        <div className="w-20 flex-shrink-0" />
                        {labels.map((label) => (
                            <div key={`col-${label}`} className="flex-1 text-center">
                                <span className="text-lg">{emotionEmojis[label] || '•'}</span>
                                <span className="block text-[10px] text-white/40 mt-0.5 font-mono">{label}</span>
                            </div>
                        ))}
                        {mode === 'classification' && (
                            <div className="w-14 flex-shrink-0 text-center">
                                <span className="text-[10px] text-white/20 font-mono">Recall</span>
                            </div>
                        )}
                    </div>

                    {/* Axis Label */}
                    <div className="flex items-center mb-1">
                        <div className="w-20 flex-shrink-0" />
                        <div className="flex-1 text-center">
                            <span className="text-[9px] text-stage-gold/40 font-mono uppercase tracking-widest">
                                ← {colLabel} →
                            </span>
                        </div>
                        {mode === 'classification' && <div className="w-14 flex-shrink-0" />}
                    </div>

                    {/* Matrix Rows */}
                    {values.map((row, rowIdx) => (
                        <div key={`row-${rowIdx}`} className="flex items-center mb-1">
                            {/* Row Label */}
                            <div className="w-20 flex-shrink-0 flex items-center gap-1.5 justify-end pr-3">
                                <span className="text-[10px] text-white/40 font-mono">{labels[rowIdx]}</span>
                                <span className="text-sm">{emotionEmojis[labels[rowIdx]] || '•'}</span>
                            </div>

                            {/* Cells */}
                            {row.map((val, colIdx) => {
                                const isHovered = hoveredCell?.row === rowIdx && hoveredCell?.col === colIdx
                                const isDiagonal = rowIdx === colIdx

                                // Color Logic
                                let bgColor = 'bg-white/[0.02]'
                                if (val > 0) {
                                    if (mode === 'classification') {
                                        // Green/Red logic
                                        bgColor = isDiagonal
                                            ? `rgba(16, 185, 129, ${getCellOpacity(val)})`
                                            : `rgba(239, 68, 68, ${getCellOpacity(val)})`
                                    } else {
                                        // Heatmap logic (Blue/Amber)
                                        // Using amber-500 rgb(245, 158, 11)
                                        const opacity = getCellOpacity(val)
                                        bgColor = `rgba(245, 158, 11, ${opacity})`
                                    }
                                }

                                return (
                                    <div
                                        key={`cell-${rowIdx}-${colIdx}`}
                                        className="flex-1 aspect-square mx-0.5 rounded-lg flex items-center justify-center
                                relative cursor-default transition-all duration-200 group"
                                        style={{
                                            backgroundColor: bgColor,
                                            transform: isHovered ? 'scale(1.1)' : 'scale(1)',
                                            zIndex: isHovered ? 10 : 1,
                                            boxShadow: isHovered && val > 0 ? '0 0 15px rgba(255,255,255,0.1)' : 'none'
                                        }}
                                        onMouseEnter={() => setHoveredCell({ row: rowIdx, col: colIdx })}
                                        onMouseLeave={() => setHoveredCell(null)}
                                    >
                                        <span className={`text-sm font-mono font-semibold transition-all duration-200 ${val === 0 ? 'text-white/5' : 'text-white/90'
                                            } ${isHovered ? 'scale-125' : ''}`}>
                                            {val}
                                        </span>

                                        {/* Hover Tooltip */}
                                        {isHovered && val > 0 && (
                                            <div className="absolute -top-16 left-1/2 -translate-x-1/2 
                                      bg-stage-bg border border-white/10 rounded-lg px-3 py-2
                                      shadow-xl whitespace-nowrap z-20 animate-fade-in pointer-events-none">
                                                <p className="text-[10px] text-white/50">
                                                    {rowLabel}: <span className="text-white/80">{labels[rowIdx]}</span>
                                                </p>
                                                <p className="text-[10px] text-white/50">
                                                    {colLabel}: <span className="text-white/80">{labels[colIdx]}</span>
                                                </p>
                                                <p className="text-[10px] font-semibold mt-0.5 text-stage-gold">
                                                    Count: {val}
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                )
                            })}

                            {/* Recall per row (only classification) */}
                            {mode === 'classification' && (
                                <div className="w-14 flex-shrink-0 flex items-center justify-center">
                                    <span className={`text-[11px] font-mono ${Number(classMetrics[rowIdx].recall) >= 80 ? 'text-emerald-400' :
                                        Number(classMetrics[rowIdx].recall) >= 60 ? 'text-amber-400' : 'text-red-400'
                                        }`}>
                                        {classMetrics[rowIdx].recall}%
                                    </span>
                                </div>
                            )}
                        </div>
                    ))}

                    {/* Precision Row (only classification) */}
                    {mode === 'classification' && (
                        <div className="flex items-center mt-2">
                            <div className="w-20 flex-shrink-0 text-right pr-3">
                                <span className="text-[10px] text-white/20 font-mono">Precision</span>
                            </div>
                            {classMetrics.map((m) => (
                                <div key={`prec-${m.label}`} className="flex-1 text-center">
                                    <span className={`text-[11px] font-mono ${Number(m.precision) >= 80 ? 'text-emerald-400' :
                                        Number(m.precision) >= 60 ? 'text-amber-400' : 'text-red-400'
                                        }`}>
                                        {m.precision}%
                                    </span>
                                </div>
                            ))}
                            <div className="w-14 flex-shrink-0" />
                        </div>
                    )}
                </div>
            </div>

            {/* Legend - Simplified for Transition Mode */}
            <div className="flex items-center justify-center gap-6 pt-2">
                {mode === 'classification' ? (
                    <>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded bg-emerald-500/40" />
                            <span className="text-[11px] text-white/40">Correct</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded bg-red-500/30" />
                            <span className="text-[11px] text-white/40">Misclassification</span>
                        </div>
                    </>
                ) : (
                    <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded bg-amber-500/40" />
                        <span className="text-[11px] text-white/40">Frequency Heatmap</span>
                    </div>
                )}
                <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded bg-white/[0.03] border border-white/5" />
                    <span className="text-[11px] text-white/40">No Samples</span>
                </div>
            </div>

        </div>
    )
}
