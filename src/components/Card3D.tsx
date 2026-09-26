import React, { useRef, useState, type ReactNode } from 'react'

interface Card3DProps {
  children: ReactNode
  className?: string
  intensity?: number
  glare?: boolean
  onClick?: () => void
  style?: React.CSSProperties
}

/**
 * Interactive 3D Tilt Card Component.
 * Applies real-time perspective rotations and specular lighting tracking cursor coordinates.
 */
export function Card3D({
  children,
  className = '',
  intensity = 15,
  glare = true,
  onClick,
  style = {},
}: Card3DProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [transform, setTransform] = useState<string>('')
  const [glarePos, setGlarePos] = useState<{ x: number; y: number; opacity: number }>({ x: 50, y: 50, opacity: 0 })
  const [isHovered, setIsHovered] = useState(false)

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return
    const rect = cardRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const centerX = rect.width / 2
    const centerY = rect.height / 2

    const rotateX = ((y - centerY) / centerY) * -intensity
    const rotateY = ((x - centerX) / centerX) * intensity

    setTransform(`perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-4px) scale3d(1.015, 1.015, 1.015)`)
    setGlarePos({
      x: (x / rect.width) * 100,
      y: (y / rect.height) * 100,
      opacity: 0.25,
    })
  }

  const handleMouseEnter = () => {
    setIsHovered(true)
  }

  const handleMouseLeave = () => {
    setIsHovered(false)
    setTransform('perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px) scale3d(1, 1, 1)')
    setGlarePos(prev => ({ ...prev, opacity: 0 }))
  }

  return (
    <div
      ref={cardRef}
      className={`card-3d-wrapper ${className}`}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      style={{
        transform: transform || 'perspective(1000px) rotateX(0deg) rotateY(0deg)',
        transition: isHovered ? 'transform 0.1s ease-out' : 'transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1)',
        transformStyle: 'preserve-3d',
        position: 'relative',
        ...style,
      }}
    >
      {children}
      {glare && (
        <div
          className="card-3d-glare"
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: 'inherit',
            pointerEvents: 'none',
            opacity: glarePos.opacity,
            transition: 'opacity 0.3s ease',
            background: `radial-gradient(circle 220px at ${glarePos.x}% ${glarePos.y}%, rgba(255, 255, 255, 0.18), transparent 70%)`,
            zIndex: 10,
          }}
        />
      )}
    </div>
  )
}
