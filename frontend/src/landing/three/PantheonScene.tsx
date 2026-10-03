import { Canvas, useFrame } from '@react-three/fiber';
import { Environment, Lightformer, useGLTF } from '@react-three/drei';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';

/** Scroll progress 0..1 shared without React re-renders. */
const scrollRef = { current: 0 };
if (typeof window !== 'undefined') {
  const update = () => {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    scrollRef.current = max > 0 ? window.scrollY / max : 0;
  };
  update();
  window.addEventListener('scroll', update, { passive: true });
  window.addEventListener('resize', update);
}

function SuperlaserCannon() {
  const beamCoreRef = useRef<THREE.Mesh>(null);
  const beamGlowRef = useRef<THREE.Mesh>(null);
  const focalOrbRef = useRef<THREE.Mesh>(null);
  const flareFlashRef = useRef<THREE.Mesh>(null);
  const dishSectorRef = useRef<THREE.Mesh>(null);
  const nozzleLightRef = useRef<THREE.PointLight>(null);

  const tributaryMeshes = useRef<THREE.Mesh[]>([]);
  const emitterDotMeshes = useRef<THREE.Mesh[]>([]);
  const energyPulseMeshes = useRef<THREE.Mesh[]>([]);

  // Exact geometry based on Death Star model coordinates and reference image
  const { focalPoint, rimRays, beamCenter, beamQuat, beamLength, pNozzle, dishQuat } =
    useMemo(() => {
      const dir = new THREE.Vector3(-0.915605, 0.402078, 0.0).normalize();
      const u1 = new THREE.Vector3(0.0, 0.0, 1.0);
      const u2 = new THREE.Vector3().crossVectors(dir, u1).normalize();
      const nozzlePos = new THREE.Vector3(-3.584, 1.574, 0.002);

      // Convergence point hovering in space in front of the dish (matches reference image)
      const fPoint = nozzlePos.clone().addScaledVector(dir, 2.2);

      const radius = 1.48;
      const rays: {
        start: THREE.Vector3;
        end: THREE.Vector3;
        position: THREE.Vector3;
        quat: THREE.Quaternion;
        length: number;
      }[] = [];

      for (let i = 0; i < 8; i++) {
        // 8 evenly-spaced emitters around the outer lip of the concave dish
        const th = (i * 2 * Math.PI) / 8 + Math.PI / 8;
        const rim = nozzlePos
          .clone()
          .addScaledVector(dir, 0.4)
          .addScaledVector(u1, Math.cos(th) * radius)
          .addScaledVector(u2, Math.sin(th) * radius);

        const segment = new THREE.Vector3().subVectors(fPoint, rim);
        const len = segment.length();
        const midpoint = rim.clone().addScaledVector(segment, 0.5);
        const q = new THREE.Quaternion().setFromUnitVectors(
          new THREE.Vector3(0, 1, 0),
          segment.clone().normalize(),
        );
        rays.push({ start: rim, end: fPoint, position: midpoint, quat: q, length: len });
      }

      const bLength = 55.0;
      const bCenter = fPoint.clone().addScaledVector(dir, bLength / 2);
      const bQuat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
      const dQuat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir);

      return {
        focalPoint: fPoint,
        rimRays: rays,
        beamCenter: bCenter,
        beamQuat: bQuat,
        beamLength: bLength,
        pNozzle: nozzlePos,
        dishQuat: dQuat,
      };
    }, []);

  useFrame((state) => {
    // Cinematic Slowed-Down 18-second Cycle:
    // 0.0s - 7.0s:  Idle space drift
    // 7.0s - 9.0s:  Emitters awaken & ignite (2.0s)
    // 9.0s - 12.0s: 8 Tributary beams shoot & stream energy pulses (3.0s)
    // 12.0s - 13.5s: Convergence focal orb supercharges to critical mass (1.5s)
    // 13.5s - 15.8s: PRIMARY SUPERLASER BLAST (2.3s sustained cannon firing!)
    // 15.8s - 18.0s: Dissipation & cooling embers afterglow (2.2s)
    const CYCLE = 18.0;
    const t = (state.clock.elapsedTime + 4.0) % CYCLE;
    const et = state.clock.elapsedTime;

    // ----------------------------------------------------
    // Phase 1: IDLE (0.0s - 7.0s)
    // ----------------------------------------------------
    if (t < 7.0) {
      if (beamCoreRef.current) beamCoreRef.current.visible = false;
      if (beamGlowRef.current) beamGlowRef.current.visible = false;
      if (flareFlashRef.current) flareFlashRef.current.visible = false;
      if (dishSectorRef.current) dishSectorRef.current.visible = false;

      // Standby faint pulse at focal point and emitters
      const standbyPulse = 0.05 + Math.sin(et * 2.5) * 0.015;
      if (focalOrbRef.current) {
        focalOrbRef.current.visible = true;
        focalOrbRef.current.scale.setScalar(standbyPulse);
        (focalOrbRef.current.material as THREE.MeshBasicMaterial).opacity = 0.2;
      }
      if (nozzleLightRef.current) {
        nozzleLightRef.current.intensity = 0.5 + Math.sin(et * 2.5) * 0.2;
        nozzleLightRef.current.color.set('#10b981');
      }

      emitterDotMeshes.current.forEach((mesh) => {
        if (mesh) {
          mesh.visible = true;
          mesh.scale.setScalar(0.7 + Math.sin(et * 3) * 0.2);
          (mesh.material as THREE.MeshBasicMaterial).opacity = 0.35;
        }
      });

      tributaryMeshes.current.forEach((mesh) => {
        if (mesh) mesh.visible = false;
      });
      energyPulseMeshes.current.forEach((mesh) => {
        if (mesh) mesh.visible = false;
      });
    }

    // ----------------------------------------------------
    // Phase 2: EMITTERS AWAKEN & IGNITE (7.0s - 9.0s)
    // ----------------------------------------------------
    else if (t >= 7.0 && t < 9.0) {
      const p = (t - 7.0) / 2.0; // 0 -> 1
      if (beamCoreRef.current) beamCoreRef.current.visible = false;
      if (beamGlowRef.current) beamGlowRef.current.visible = false;
      if (flareFlashRef.current) flareFlashRef.current.visible = false;

      // Emitters flare up to high intensity
      emitterDotMeshes.current.forEach((mesh, idx) => {
        if (mesh) {
          mesh.visible = true;
          const stagger = Math.max(0, Math.min(1, (p * 8 - idx * 0.5) * 1.5));
          mesh.scale.setScalar(1.0 + stagger * 1.2 + Math.sin(et * 20 + idx) * 0.2);
          (mesh.material as THREE.MeshBasicMaterial).opacity = 0.4 + stagger * 0.6;
        }
      });

      // Dish interior begins to glow with power conduit fans
      if (dishSectorRef.current) {
        dishSectorRef.current.visible = true;
        (dishSectorRef.current.material as THREE.MeshBasicMaterial).opacity = p * 0.35;
      }

      if (nozzleLightRef.current) {
        nozzleLightRef.current.intensity = 1.0 + p * 3.0;
        nozzleLightRef.current.color.set('#34d399');
      }

      tributaryMeshes.current.forEach((mesh) => {
        if (mesh) mesh.visible = false;
      });
      energyPulseMeshes.current.forEach((mesh) => {
        if (mesh) mesh.visible = false;
      });
    }

    // ----------------------------------------------------
    // Phase 3: CONVERGENCE BEAMS STREAM (9.0s - 12.0s)
    // ----------------------------------------------------
    else if (t >= 9.0 && t < 12.0) {
      const p = (t - 9.0) / 3.0; // 0 -> 1
      if (beamCoreRef.current) beamCoreRef.current.visible = false;
      if (beamGlowRef.current) beamGlowRef.current.visible = false;
      if (flareFlashRef.current) flareFlashRef.current.visible = false;

      // Emitters at peak brilliance
      emitterDotMeshes.current.forEach((mesh) => {
        if (mesh) {
          mesh.visible = true;
          mesh.scale.setScalar(2.0 + Math.sin(et * 25) * 0.3);
          (mesh.material as THREE.MeshBasicMaterial).opacity = 1.0;
        }
      });

      // Dish radial glow
      if (dishSectorRef.current) {
        dishSectorRef.current.visible = true;
        (dishSectorRef.current.material as THREE.MeshBasicMaterial).opacity = 0.35 + p * 0.25;
      }

      // 8 Tributary laser beams shooting from emitters to focal point
      const jitter = 0.9 + Math.random() * 0.2;
      tributaryMeshes.current.forEach((mesh) => {
        if (mesh) {
          mesh.visible = true;
          mesh.scale.set(0.6 + p * 0.5, 1, 0.6 + p * 0.5);
          (mesh.material as THREE.MeshBasicMaterial).opacity = (0.7 + p * 0.3) * jitter;
        }
      });

      // Streaming energy pulses/beads traveling along each of the 8 beams (matching reference image!)
      let pulseIdx = 0;
      rimRays.forEach((ray, rayIdx) => {
        for (let bead = 0; bead < 3; bead++) {
          const pulseMesh = energyPulseMeshes.current[pulseIdx++];
          if (pulseMesh) {
            pulseMesh.visible = true;
            // Travel from rim to focal point
            const travelProgress = (et * 1.8 + bead * 0.33 + rayIdx * 0.125) % 1.0;
            pulseMesh.position.copy(ray.start).lerp(ray.end, travelProgress);
            const beadScale = 0.8 + Math.sin(travelProgress * Math.PI) * 0.5;
            pulseMesh.scale.setScalar(beadScale);
            (pulseMesh.material as THREE.MeshBasicMaterial).opacity = 0.95;
          }
        }
      });

      // Convergence point gathers mass
      if (focalOrbRef.current) {
        focalOrbRef.current.visible = true;
        const orbScale = 0.15 + p * 0.45 + Math.sin(et * 30) * 0.05;
        focalOrbRef.current.scale.setScalar(orbScale);
        (focalOrbRef.current.material as THREE.MeshBasicMaterial).opacity = 0.6 + p * 0.4;
      }

      if (nozzleLightRef.current) {
        nozzleLightRef.current.intensity = 3.0 + p * 7.0 + Math.random() * 1.5;
        nozzleLightRef.current.color.set('#10b981');
      }
    }

    // ----------------------------------------------------
    // Phase 4: FOCAL CRITICAL MASS CHARGE (12.0s - 13.5s)
    // ----------------------------------------------------
    else if (t >= 12.0 && t < 13.5) {
      const p = (t - 12.0) / 1.5; // 0 -> 1
      if (beamCoreRef.current) beamCoreRef.current.visible = false;
      if (beamGlowRef.current) beamGlowRef.current.visible = false;
      if (flareFlashRef.current) flareFlashRef.current.visible = false;

      // Tributary beams reach maximum blinding brightness and vibration
      const vib = 0.85 + Math.random() * 0.3;
      tributaryMeshes.current.forEach((mesh) => {
        if (mesh) {
          mesh.visible = true;
          mesh.scale.set(1.2 * vib, 1, 1.2 * vib);
          (mesh.material as THREE.MeshBasicMaterial).opacity = 1.0;
        }
      });

      // Fast streaming pulses rushing into focal point
      let pulseIdx = 0;
      rimRays.forEach((ray, rayIdx) => {
        for (let bead = 0; bead < 3; bead++) {
          const pulseMesh = energyPulseMeshes.current[pulseIdx++];
          if (pulseMesh) {
            pulseMesh.visible = true;
            const travelProgress = (et * 3.2 + bead * 0.33 + rayIdx * 0.125) % 1.0;
            pulseMesh.position.copy(ray.start).lerp(ray.end, travelProgress);
            pulseMesh.scale.setScalar(1.2);
            (pulseMesh.material as THREE.MeshBasicMaterial).opacity = 1.0;
          }
        }
      });

      // Focal orb pulses violently with blinding white/emerald light
      if (focalOrbRef.current) {
        focalOrbRef.current.visible = true;
        const criticalSwell = 0.6 + p * 0.4 + Math.sin(et * 45) * 0.08;
        focalOrbRef.current.scale.setScalar(criticalSwell);
        (focalOrbRef.current.material as THREE.MeshBasicMaterial).opacity = 1.0;
      }

      if (nozzleLightRef.current) {
        nozzleLightRef.current.intensity = 10.0 + p * 8.0 + Math.random() * 3.0;
        nozzleLightRef.current.color.set('#a7f3d0');
      }
    }

    // ----------------------------------------------------
    // Phase 5: THE PRIMARY SUPERLASER BLAST (13.5s - 15.8s) - Sustained 2.3s!
    // ----------------------------------------------------
    else if (t >= 13.5 && t < 15.8) {
      const bp = (t - 13.5) / 2.3; // 0 -> 1
      const isPeak = bp < 0.75;
      const blastJitter = 0.94 + Math.random() * 0.12;

      // In the first 0.6s, the tributary beams remain connected then fade
      const tribFade = Math.max(0, 1.0 - bp * 2.2);
      tributaryMeshes.current.forEach((mesh) => {
        if (mesh) {
          mesh.visible = tribFade > 0.05;
          (mesh.material as THREE.MeshBasicMaterial).opacity = tribFade;
        }
      });
      energyPulseMeshes.current.forEach((mesh) => {
        if (mesh) mesh.visible = false;
      });

      // Main superlaser blast beam: sustained, thick, and powerful
      const coreScale = isPeak ? 1.0 * blastJitter : Math.max(0.01, (1 - bp) * 3.5 * blastJitter);
      const glowScale = isPeak ? 1.0 * blastJitter : Math.max(0.01, (1 - bp) * 3.5 * blastJitter);

      if (beamCoreRef.current) {
        beamCoreRef.current.visible = true;
        beamCoreRef.current.scale.set(coreScale, 1, coreScale);
      }
      if (beamGlowRef.current) {
        beamGlowRef.current.visible = true;
        beamGlowRef.current.scale.set(glowScale, 1, glowScale);
        (beamGlowRef.current.material as THREE.MeshBasicMaterial).opacity = isPeak
          ? 0.95
          : (1 - bp) * 3.5;
      }

      // Muzzle blast explosion at convergence point
      if (flareFlashRef.current) {
        flareFlashRef.current.visible = true;
        const flashScale = isPeak ? 1.8 + Math.random() * 0.4 : (1 - bp) * 2.0;
        flareFlashRef.current.scale.setScalar(flashScale);
      }

      if (focalOrbRef.current) {
        focalOrbRef.current.visible = true;
        focalOrbRef.current.scale.setScalar(0.9 * blastJitter);
        (focalOrbRef.current.material as THREE.MeshBasicMaterial).opacity = 1.0;
      }

      // Blinding illumination flash across space and Death Star hull
      if (nozzleLightRef.current) {
        nozzleLightRef.current.intensity = isPeak ? 24.0 + Math.random() * 6.0 : (1 - bp) * 20.0;
        nozzleLightRef.current.color.set('#10b981');
      }
    }

    // ----------------------------------------------------
    // Phase 6: DISSIPATION & COOL-DOWN (15.8s - 18.0s)
    // ----------------------------------------------------
    else {
      const cp = (t - 15.8) / 2.2; // 0 -> 1
      if (beamCoreRef.current) beamCoreRef.current.visible = false;
      if (beamGlowRef.current) beamGlowRef.current.visible = false;
      if (flareFlashRef.current) flareFlashRef.current.visible = false;
      if (dishSectorRef.current) dishSectorRef.current.visible = false;

      tributaryMeshes.current.forEach((mesh) => {
        if (mesh) mesh.visible = false;
      });
      energyPulseMeshes.current.forEach((mesh) => {
        if (mesh) mesh.visible = false;
      });

      // Emitters cool down
      emitterDotMeshes.current.forEach((mesh) => {
        if (mesh) {
          mesh.visible = true;
          mesh.scale.setScalar(Math.max(0.7, (1 - cp) * 1.8));
          (mesh.material as THREE.MeshBasicMaterial).opacity = (1 - cp) * 0.7 + 0.3;
        }
      });

      // Focal point cooling embers
      if (focalOrbRef.current) {
        focalOrbRef.current.visible = true;
        const coolScale = Math.max(0.06, (1 - cp) * 0.4);
        focalOrbRef.current.scale.setScalar(coolScale);
        (focalOrbRef.current.material as THREE.MeshBasicMaterial).opacity = (1 - cp) * 0.6;
      }

      if (nozzleLightRef.current) {
        nozzleLightRef.current.intensity = Math.max(0.5, (1 - cp) * 5.0);
        nozzleLightRef.current.color.set('#059669');
      }
    }
  });

  return (
    <group>
      {/* 8 Emitter Nodes on the Outer Lip of the Dish */}
      {rimRays.map((ray, i) => (
        <mesh
          key={`emitter-${i}`}
          ref={(el) => {
            if (el) emitterDotMeshes.current[i] = el;
          }}
          position={ray.start}
        >
          <sphereGeometry args={[0.075, 12, 12]} />
          <meshBasicMaterial
            color="#ecfdf5"
            transparent
            opacity={0.8}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>
      ))}

      {/* Dish Radial Fan Energy Glow */}
      <mesh
        ref={dishSectorRef}
        position={pNozzle.clone().add(new THREE.Vector3(-0.25, 0.1, 0))}
        quaternion={dishQuat}
        visible={false}
      >
        <circleGeometry args={[1.5, 32]} />
        <meshBasicMaterial
          color="#10b981"
          transparent
          opacity={0.3}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* 8 Tributary Laser Beams Connecting Emitters to Focal Point */}
      {rimRays.map((ray, i) => (
        <mesh
          key={`tributary-${i}`}
          ref={(el) => {
            if (el) tributaryMeshes.current[i] = el;
          }}
          position={ray.position}
          quaternion={ray.quat}
          visible={false}
        >
          <cylinderGeometry args={[0.022, 0.022, ray.length, 8]} />
          <meshBasicMaterial
            color="#4ade80"
            transparent
            opacity={0.85}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>
      ))}

      {/* 24 Traveling Energy Pulses / Beads (3 along each of the 8 beams) */}
      {Array.from({ length: 24 }).map((_, idx) => (
        <mesh
          key={`pulse-${idx}`}
          ref={(el) => {
            if (el) energyPulseMeshes.current[idx] = el;
          }}
          visible={false}
        >
          <sphereGeometry args={[0.055, 8, 8]} />
          <meshBasicMaterial
            color="#a7f3d0"
            transparent
            opacity={0.9}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>
      ))}

      {/* Convergence Focal Plasma Orb */}
      <mesh ref={focalOrbRef} position={focalPoint}>
        <sphereGeometry args={[0.4, 16, 16]} />
        <meshBasicMaterial
          color="#ffffff"
          transparent
          opacity={0.9}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Muzzle Blast Flare */}
      <mesh ref={flareFlashRef} position={focalPoint} visible={false}>
        <sphereGeometry args={[0.8, 16, 16]} />
        <meshBasicMaterial
          color="#10b981"
          transparent
          opacity={0.75}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Main Superlaser Blast Beam - Blinding White-Hot Core */}
      <mesh ref={beamCoreRef} position={beamCenter} quaternion={beamQuat} visible={false}>
        <cylinderGeometry args={[0.16, 0.16, beamLength, 16, 1, true]} />
        <meshBasicMaterial
          color="#ffffff"
          transparent
          opacity={1.0}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Main Superlaser Blast Beam - Intense Emerald Plasma Sheath */}
      <mesh ref={beamGlowRef} position={beamCenter} quaternion={beamQuat} visible={false}>
        <cylinderGeometry args={[0.62, 0.62, beamLength, 16, 1, true]} />
        <meshBasicMaterial
          color="#10b981"
          transparent
          opacity={0.88}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Dynamic Nozzle Point Light (illuminates Death Star during charge & blast) */}
      <pointLight
        ref={nozzleLightRef}
        position={focalPoint}
        intensity={0.6}
        color="#10b981"
        distance={14}
      />
    </group>
  );
}

function DeathStarModel() {
  const group = useRef<THREE.Group>(null);
  const { scene } = useGLTF('/models/death-star/death_star.glb');
  const clonedScene = useMemo(() => scene.clone(), [scene]);

  useEffect(() => {
    clonedScene.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh;
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        if (mesh.material) {
          const mat = (mesh.material as THREE.MeshStandardMaterial).clone();
          mat.roughness = 0.82;
          mat.metalness = 0.28;
          // Accentuate panel textures and surface details
          if (mat.name === 'Material.001' && mat.emissiveMap) {
            mat.emissive = new THREE.Color('#34d399');
            mat.emissiveIntensity = 0.45;
          }
          mesh.material = mat;
        }
      }
    });
  }, [clonedScene]);

  useFrame((state, rawDelta) => {
    const delta = Math.min(rawDelta, 0.05);
    const t = state.clock.elapsedTime;
    const s = scrollRef.current;
    const { x, y } = state.pointer;

    if (group.current) {
      // Gentle majestic orbital rotation + responsive pointer parallax + scroll rotation
      // Initial offset brings the iconic superlaser dish into cinematic 3/4 view
      const targetY = Math.PI * 0.42 + t * 0.04 + x * 0.35 + s * Math.PI * 1.6;
      const targetX = -0.12 - y * 0.25 + s * 0.35;

      group.current.rotation.y +=
        (targetY - group.current.rotation.y) * (1 - Math.exp(-2.5 * delta));
      group.current.rotation.x +=
        (targetX - group.current.rotation.x) * (1 - Math.exp(-2.5 * delta));

      // Space station zero-G subtle float
      group.current.position.y = Math.sin(t * 0.45) * 0.08 - s * 0.55;
    }
  });

  return (
    <group ref={group} scale={0.46} position={[0, 0, 0]}>
      <primitive object={clonedScene} />

      {/* Superlaser Cannon Firing System - Attached Directly to Dish Nozzle */}
      <SuperlaserCannon />

      {/* Cyber targeting reticle ring hovering over superlaser dish */}
      <mesh position={[-4.15, 1.67, 0]} rotation={[0, Math.PI / 2, 0]}>
        <ringGeometry args={[0.85, 0.9, 32]} />
        <meshBasicMaterial color="#10b981" transparent opacity={0.3} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

useGLTF.preload('/models/death-star/death_star.glb');

function Nodes({ count = 16 }: { count?: number }) {
  const group = useRef<THREE.Group>(null);
  const seeds = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => {
        const phi = Math.acos(1 - (2 * (i + 0.5)) / count);
        const theta = Math.PI * (1 + Math.sqrt(5)) * i;
        return {
          radius: 3.4 + (i % 4) * 0.35,
          phi,
          theta,
          speed: 0.06 + (i % 5) * 0.02,
          size: 0.06 + (i % 3) * 0.03,
        };
      }),
    [count],
  );

  useFrame((state, rawDelta) => {
    const delta = Math.min(rawDelta, 0.05);
    if (!group.current) return;
    group.current.rotation.y += delta * 0.08;
    group.current.rotation.x = scrollRef.current * 0.8;
    group.current.children.forEach((child, i) => {
      const seed = seeds[i];
      if (!seed) return;
      const t = state.clock.elapsedTime * seed.speed + seed.theta;
      const r = seed.radius;
      child.position.set(
        r * Math.sin(seed.phi) * Math.cos(t),
        r * Math.cos(seed.phi) * 0.75,
        r * Math.sin(seed.phi) * Math.sin(t),
      );
    });
  });

  return (
    <group ref={group}>
      {seeds.map((seed, i) => (
        <mesh key={i}>
          <boxGeometry args={[seed.size, seed.size, seed.size]} />
          <meshStandardMaterial color="#94a3b8" metalness={0.8} roughness={0.3} />
        </mesh>
      ))}
    </group>
  );
}

function getDustPositions(count: number): Float32Array {
  const arr = new Float32Array(count * 3);
  let seed = 42;
  for (let i = 0; i < count; i++) {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    const r1 = seed / 4294967296;
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    const r2 = seed / 4294967296;
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    const r3 = seed / 4294967296;
    arr[i * 3] = (r1 - 0.5) * 26;
    arr[i * 3 + 1] = (r2 - 0.5) * 16;
    arr[i * 3 + 2] = (r3 - 0.5) * 18;
  }
  return arr;
}

function Dust({ count = 500 }: { count?: number }) {
  const points = useRef<THREE.Points>(null);
  const positions = useMemo(() => getDustPositions(count), [count]);

  useFrame((_, rawDelta) => {
    const delta = Math.min(rawDelta, 0.05);
    if (points.current) points.current.rotation.y += delta * 0.015;
  });

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial size={0.035} color="#e2e8f0" transparent opacity={0.45} sizeAttenuation />
    </points>
  );
}

function CameraRig() {
  useFrame((state, rawDelta) => {
    const delta = Math.min(rawDelta, 0.05);
    const k = 1 - Math.exp(-2.2 * delta);
    const cam = state.camera;
    cam.position.x += (state.pointer.x * 1.1 - cam.position.x) * k;
    cam.position.y += (state.pointer.y * 0.7 + 0.3 - cam.position.y) * k;
    cam.lookAt(0, 0, 0);
  });
  return null;
}

export default function PantheonScene() {
  return (
    <Canvas
      dpr={[1, 1.8]}
      camera={{ position: [0, 0.3, 8], fov: 45 }}
      gl={{ antialias: true, alpha: true }}
    >
      {/* Deep Space High-Contrast Lighting */}
      <ambientLight intensity={0.4} />
      <directionalLight position={[7, 6, 6]} intensity={1.9} color="#ffffff" />
      <directionalLight position={[-8, -2, -5]} intensity={0.8} color="#10b981" />
      <directionalLight position={[-4, 5, -3]} intensity={0.4} color="#93c5fd" />

      <Environment>
        <Lightformer intensity={2.0} position={[0, 5, 2]} scale={[10, 10, 1]} />
        <Lightformer
          intensity={1.2}
          color="#10b981"
          position={[-6, 1, -2]}
          rotation-y={Math.PI / 2}
          scale={[20, 2, 1]}
        />
      </Environment>

      <DeathStarModel />
      <Nodes />
      <Dust />
      <CameraRig />
    </Canvas>
  );
}
