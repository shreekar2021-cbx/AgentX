import { useEffect, useRef } from 'react'
import * as THREE from 'three'

interface ThreeCropVisualProps {
  status?: 'healthy' | 'warning' | 'critical'
  interactive?: boolean
  className?: string
  height?: number | string
}

export function ThreeCropVisual({
  status = 'healthy',
  interactive = true,
  className = '',
  height = '100%',
}: ThreeCropVisualProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // 1. Scene, Camera, Renderer
    const width = container.clientWidth || 340
    const containerHeight = container.clientHeight || 300

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(45, width / containerHeight, 0.1, 1000)
    camera.position.set(0, 1.5, 6)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, containerHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.2
    container.appendChild(renderer.domElement)

    // 2. Palette based on health status
    const colors = {
      healthy: { primary: 0x34d399, secondary: 0x059669, glow: 0x6ee7b7, spore: 0xa7f3d0 },
      warning: { primary: 0xfbbf24, secondary: 0xd97706, glow: 0xfef08a, spore: 0xfde68a },
      critical: { primary: 0xf87171, secondary: 0xdc2626, glow: 0xfca5a5, spore: 0xfecaca },
    }[status]

    // 3. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8)
    scene.add(ambientLight)

    const pointLight = new THREE.PointLight(colors.primary, 3, 20)
    pointLight.position.set(2, 3, 3)
    scene.add(pointLight)

    const rimLight = new THREE.PointLight(0x38bdf8, 2, 15)
    rimLight.position.set(-3, -2, -2)
    scene.add(rimLight)

    // 4. Group for 3D Plant Model
    const plantGroup = new THREE.Group()
    scene.add(plantGroup)

    // Central Stem
    const stemCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, -2, 0),
      new THREE.Vector3(0.1, -1, 0.1),
      new THREE.Vector3(-0.15, 0.2, -0.05),
      new THREE.Vector3(0.1, 1.2, 0.05),
      new THREE.Vector3(0, 2.0, 0),
    ])
    const stemGeo = new THREE.TubeGeometry(stemCurve, 32, 0.07, 12, false)
    const stemMat = new THREE.MeshStandardMaterial({
      color: colors.secondary,
      roughness: 0.35,
      metalness: 0.15,
      emissive: colors.secondary,
      emissiveIntensity: 0.2,
    })
    const stem = new THREE.Mesh(stemGeo, stemMat)
    plantGroup.add(stem)

    // Floating Leaves
    const leafMat = new THREE.MeshStandardMaterial({
      color: colors.primary,
      roughness: 0.2,
      metalness: 0.2,
      side: THREE.DoubleSide,
      emissive: colors.glow,
      emissiveIntensity: 0.25,
    })

    const createLeaf = (x: number, y: number, z: number, rx: number, ry: number, rz: number, scale = 1) => {
      const leafShape = new THREE.Shape()
      leafShape.moveTo(0, 0)
      leafShape.bezierCurveTo(0.3, 0.2, 0.6, 0.8, 0, 1.5)
      leafShape.bezierCurveTo(-0.6, 0.8, -0.3, 0.2, 0, 0)

      const leafGeo = new THREE.ShapeGeometry(leafShape, 16)
      const leafMesh = new THREE.Mesh(leafGeo, leafMat)
      leafMesh.position.set(x, y, z)
      leafMesh.rotation.set(rx, ry, rz)
      leafMesh.scale.set(scale, scale, scale)
      return leafMesh
    }

    const leaves = [
      createLeaf(0.05, -0.6, 0.05, 0.4, 0.3, -0.6, 0.8),
      createLeaf(-0.08, -0.1, -0.02, -0.3, 2.1, 0.7, 0.9),
      createLeaf(0.08, 0.6, 0.04, 0.2, -1.2, -0.5, 0.85),
      createLeaf(-0.06, 1.1, -0.04, -0.4, 1.4, 0.6, 0.75),
      createLeaf(0.02, 1.7, 0.02, 0.1, 0, -0.2, 0.6),
    ]
    leaves.forEach(l => plantGroup.add(l))

    // Interactive Pulsing Bio-Core Orb
    const coreGeo = new THREE.SphereGeometry(0.28, 24, 24)
    const coreMat = new THREE.MeshStandardMaterial({
      color: colors.glow,
      roughness: 0.1,
      metalness: 0.8,
      emissive: colors.primary,
      emissiveIntensity: 0.8,
    })
    const bioCore = new THREE.Mesh(coreGeo, coreMat)
    bioCore.position.set(0, 2.05, 0)
    plantGroup.add(bioCore)

    // Holographic Orbital Rings
    const ringGeo = new THREE.TorusGeometry(1.6, 0.015, 16, 100)
    const ringMat = new THREE.MeshBasicMaterial({
      color: colors.glow,
      transparent: true,
      opacity: 0.45,
    })
    const ring1 = new THREE.Mesh(ringGeo, ringMat)
    ring1.rotation.x = Math.PI / 2.3
    plantGroup.add(ring1)

    const ring2 = new THREE.Mesh(new THREE.TorusGeometry(2.1, 0.012, 16, 100), ringMat)
    ring2.rotation.x = Math.PI / 2.6
    ring2.rotation.y = Math.PI / 6
    plantGroup.add(ring2)

    // Bio-spore particles floating in 3D field
    const particleCount = 70
    const particleGeo = new THREE.BufferGeometry()
    const positions = new Float32Array(particleCount * 3)
    const velocities = new Float32Array(particleCount * 3)

    for (let i = 0; i < particleCount * 3; i += 3) {
      positions[i] = (Math.random() - 0.5) * 5
      positions[i + 1] = (Math.random() - 0.5) * 5
      positions[i + 2] = (Math.random() - 0.5) * 4

      velocities[i] = (Math.random() - 0.5) * 0.005
      velocities[i + 1] = 0.003 + Math.random() * 0.007
      velocities[i + 2] = (Math.random() - 0.5) * 0.005
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const particleMat = new THREE.PointsMaterial({
      color: colors.spore,
      size: 0.07,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
    })
    const particleSystem = new THREE.Points(particleGeo, particleMat)
    plantGroup.add(particleSystem)

    // Mouse Interaction
    let mouseX = 0
    let mouseY = 0
    let targetRotationX = 0
    let targetRotationY = 0

    const handleMouseMove = (e: MouseEvent) => {
      if (!interactive) return
      const rect = container.getBoundingClientRect()
      mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1
      mouseY = -(((e.clientY - rect.top) / rect.height) * 2 - 1)
      targetRotationY = mouseX * 0.6
      targetRotationX = -mouseY * 0.35
    }

    window.addEventListener('mousemove', handleMouseMove)

    // Resize Handler
    const handleResize = () => {
      if (!container) return
      const newWidth = container.clientWidth
      const newHeight = container.clientHeight
      if (newWidth === 0 || newHeight === 0) return
      camera.aspect = newWidth / newHeight
      camera.updateProjectionMatrix()
      renderer.setSize(newWidth, newHeight)
    }

    const resizeObserver = new ResizeObserver(handleResize)
    resizeObserver.observe(container)

    // Animation Loop
    let animationFrameId: number
    let clock = new THREE.Clock()

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate)
      const elapsedTime = clock.getElapsedTime()

      // Smooth camera/plant parallax follow
      plantGroup.rotation.y += (targetRotationY - plantGroup.rotation.y) * 0.05 + 0.004
      plantGroup.rotation.x += (targetRotationX - plantGroup.rotation.x) * 0.05

      // Floating undulation
      plantGroup.position.y = Math.sin(elapsedTime * 1.5) * 0.12

      // Ring rotations
      ring1.rotation.z += 0.008
      ring2.rotation.z -= 0.006

      // Bio core gentle pulse
      const coreScale = 1 + Math.sin(elapsedTime * 3) * 0.09
      bioCore.scale.set(coreScale, coreScale, coreScale)

      // Spore particles drift upward and cycle
      const posAttr = particleGeo.attributes.position as THREE.BufferAttribute
      const posArray = posAttr.array as Float32Array
      for (let i = 0; i < particleCount * 3; i += 3) {
        posArray[i] += velocities[i]
        posArray[i + 1] += velocities[i + 1]
        posArray[i + 2] += velocities[i + 2]

        if (posArray[i + 1] > 2.8) {
          posArray[i + 1] = -2.5
          posArray[i] = (Math.random() - 0.5) * 4
        }
      }
      posAttr.needsUpdate = true

      renderer.render(scene, camera)
    }

    animate()

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      resizeObserver.disconnect()
      cancelAnimationFrame(animationFrameId)
      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [status, interactive])

  return (
    <div
      ref={containerRef}
      className={`three-crop-visual ${className}`}
      style={{
        width: '100%',
        height,
        position: 'relative',
        overflow: 'hidden',
        cursor: interactive ? 'grab' : 'default',
      }}
    />
  )
}
