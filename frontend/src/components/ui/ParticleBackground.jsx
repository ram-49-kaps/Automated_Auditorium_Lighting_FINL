import { useEffect, useRef } from 'react'

export default function ParticleBackground() {
    const canvasRef = useRef(null)

    useEffect(() => {
        const canvas = canvasRef.current
        const ctx = canvas.getContext('2d')
        let animId

        const resize = () => {
            canvas.width = window.innerWidth
            canvas.height = window.innerHeight
        }
        resize()
        window.addEventListener('resize', resize)

        // Particles: small glowing dots that float and drift
        const particles = Array.from({ length: 60 }, () => ({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            r: Math.random() * 2 + 0.5,
            dx: (Math.random() - 0.5) * 0.3,
            dy: (Math.random() - 0.5) * 0.3 - 0.1,
            opacity: Math.random() * 0.5 + 0.1,
            hue: Math.random() > 0.7 ? 45 : 210, // gold or blue
        }))

        // Spotlight beams
        const beams = Array.from({ length: 3 }, (_, i) => ({
            x: canvas.width * (0.25 + i * 0.25),
            angle: -90 + (Math.random() - 0.5) * 20,
            width: 30 + Math.random() * 20,
            opacity: 0.02 + Math.random() * 0.02,
            speed: (Math.random() - 0.5) * 0.15,
        }))

        function draw() {
            ctx.clearRect(0, 0, canvas.width, canvas.height)

            // Draw spotlight beams
            beams.forEach(beam => {
                beam.angle += beam.speed
                const rad = (beam.angle * Math.PI) / 180
                const length = canvas.height * 1.5

                ctx.save()
                ctx.translate(beam.x, 0)
                ctx.rotate(rad + Math.PI / 2)

                const grad = ctx.createLinearGradient(0, 0, 0, length)
                grad.addColorStop(0, `rgba(255, 215, 0, ${beam.opacity * 2})`)
                grad.addColorStop(0.3, `rgba(255, 215, 0, ${beam.opacity})`)
                grad.addColorStop(1, 'rgba(255, 215, 0, 0)')

                ctx.beginPath()
                ctx.moveTo(-beam.width / 2, 0)
                ctx.lineTo(-beam.width * 2, length)
                ctx.lineTo(beam.width * 2, length)
                ctx.lineTo(beam.width / 2, 0)
                ctx.closePath()
                ctx.fillStyle = grad
                ctx.fill()
                ctx.restore()
            })

            // Draw particles
            particles.forEach(p => {
                p.x += p.dx
                p.y += p.dy

                // Wrap around
                if (p.x < 0) p.x = canvas.width
                if (p.x > canvas.width) p.x = 0
                if (p.y < 0) p.y = canvas.height
                if (p.y > canvas.height) p.y = 0

                // Glow
                const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 4)
                grad.addColorStop(0, `hsla(${p.hue}, 80%, 70%, ${p.opacity})`)
                grad.addColorStop(1, `hsla(${p.hue}, 80%, 70%, 0)`)

                ctx.beginPath()
                ctx.arc(p.x, p.y, p.r * 4, 0, Math.PI * 2)
                ctx.fillStyle = grad
                ctx.fill()

                // Core dot
                ctx.beginPath()
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
                ctx.fillStyle = `hsla(${p.hue}, 90%, 80%, ${p.opacity * 1.5})`
                ctx.fill()
            })

            animId = requestAnimationFrame(draw)
        }

        draw()

        return () => {
            cancelAnimationFrame(animId)
            window.removeEventListener('resize', resize)
        }
    }, [])

    return <canvas ref={canvasRef} className="particle-canvas" />
}
