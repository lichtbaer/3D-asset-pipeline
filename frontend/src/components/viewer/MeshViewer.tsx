import { useRef, useEffect, useState, useCallback } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import "./MeshViewer.css";

export type LightingMode = "studio" | "neutral" | "dark";

export interface MeshViewerProps {
  glbUrl: string;
  height?: number;
  className?: string;
  /** Auto-Rotation standardmäßig aktiv (z.B. für Preview) */
  autoRotateDefault?: boolean;
  /** Nur Viewer ohne Steuerungs-Buttons (Wireframe, Beleuchtung, Fullscreen) */
  readOnly?: boolean;
}

function setWireframeRecursive(
  object: THREE.Object3D,
  wireframe: boolean
): void {
  object.traverse((child) => {
    if (child instanceof THREE.Mesh && child.material) {
      const materials = Array.isArray(child.material)
        ? child.material
        : [child.material];
      materials.forEach((mat) => {
        if ("wireframe" in mat && typeof (mat as { wireframe: boolean }).wireframe === "boolean") {
          (mat as { wireframe: boolean }).wireframe = wireframe;
        }
      });
    }
  });
}

export function MeshViewer({
  glbUrl,
  height = 500,
  className = "",
  autoRotateDefault = false,
  readOnly = false,
}: MeshViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mountedRef = useRef(true);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const modelRef = useRef<THREE.Group | null>(null);
  const lightsRef = useRef<{
    ambient: THREE.AmbientLight;
    directional1: THREE.DirectionalLight;
    directional2: THREE.DirectionalLight;
    directionalTop: THREE.DirectionalLight;
  } | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRotate, setAutoRotate] = useState(autoRotateDefault);
  const [wireframe, setWireframe] = useState(false);
  const [lightingMode, setLightingMode] = useState<LightingMode>("studio");

  const applyLightingMode = useCallback(
    (mode: LightingMode, lights: {
      ambient: THREE.AmbientLight;
      directional1: THREE.DirectionalLight;
      directional2: THREE.DirectionalLight;
      directionalTop: THREE.DirectionalLight;
    }) => {
      lights.ambient.visible = true;
      lights.directional1.visible = mode === "studio";
      lights.directional2.visible = mode === "studio";
      lights.directionalTop.visible = mode === "dark";

      if (mode === "neutral") {
        lights.ambient.intensity = 0.8;
      } else if (mode === "dark") {
        lights.ambient.intensity = 0.1;
        lights.directionalTop.intensity = 1.5;
      } else {
        lights.ambient.intensity = 0.4;
        lights.directionalTop.intensity = 0;
      }
    },
    []
  );

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas || !glbUrl) return;

    mountedRef.current = true;

    if (typeof WebGLRenderingContext === "undefined") {
      queueMicrotask(() => {
        setError("WebGL nicht verfügbar");
        setLoading(false);
      });
      return;
    }

    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
    camera.position.set(0, 1, 3);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    rendererRef.current = renderer;

    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.autoRotate = false;
    controls.autoRotateSpeed = 2;
    controlsRef.current = controls;

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);

    const directional1 = new THREE.DirectionalLight(0xffffff, 1.0);
    directional1.position.set(5, 5, 5);
    scene.add(directional1);

    const directional2 = new THREE.DirectionalLight(0xffffff, 0.3);
    directional2.position.set(-5, -5, -5);
    scene.add(directional2);

    const directionalTop = new THREE.DirectionalLight(0xffffff, 1.5);
    directionalTop.position.set(0, 10, 0);
    directionalTop.visible = false;
    scene.add(directionalTop);

    lightsRef.current = {
      ambient: ambientLight,
      directional1,
      directional2,
      directionalTop,
    };

    const resize = () => {
      if (!container || !camera || !renderer) return;
      const width = container.clientWidth;
      const h = container.clientHeight;
      if (width <= 0 || h <= 0) return;
      camera.aspect = width / h;
      camera.updateProjectionMatrix();
      renderer.setSize(width, h);
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);
    resize();

    const loader = new GLTFLoader();
    loader.load(
      glbUrl,
      (gltf) => {
        const model = gltf.scene;
        modelRef.current = model;

        const box = new THREE.Box3().setFromObject(model);
        const center = box.getCenter(new THREE.Vector3());

        model.position.sub(center);

        const sphere = new THREE.Sphere();
        box.getBoundingSphere(sphere);
        const radius = sphere.radius;
        const camDistance = radius * 3;
        camera.position.set(0, radius * 0.5, camDistance);
        controls.target.set(0, 0, 0);
        controls.update();

        scene.add(model);
        if (mountedRef.current) setLoading(false);
      },
      undefined,
      (err) => {
        console.warn("MeshViewer: GLB load error", glbUrl, err);
        if (mountedRef.current) {
          setError("3D-Vorschau nicht verfügbar");
          setLoading(false);
        }
      }
    );

    let frameId: number | null = null;
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    frameId = requestAnimationFrame(animate);

    return () => {
      mountedRef.current = false;
      resizeObserver.disconnect();
      if (frameId !== null) {
        cancelAnimationFrame(frameId);
      }
      controls.dispose();
      renderer.dispose();
      scene.clear();
      sceneRef.current = null;
      cameraRef.current = null;
      rendererRef.current = null;
      controlsRef.current = null;
      modelRef.current = null;
      lightsRef.current = null;
      animationFrameRef.current = null;
    };
  }, [glbUrl]);

  useEffect(() => {
    const model = modelRef.current;
    if (model) {
      setWireframeRecursive(model, wireframe);
    }
  }, [wireframe]);

  useEffect(() => {
    setAutoRotate(autoRotateDefault);
  }, [autoRotateDefault]);

  useEffect(() => {
    const controls = controlsRef.current;
    if (controls) {
      controls.autoRotate = autoRotate;
    }
  }, [autoRotate]);

  useEffect(() => {
    const lights = lightsRef.current;
    if (lights) {
      applyLightingMode(lightingMode, lights);
    }
  }, [lightingMode, applyLightingMode]);

  const handleFullscreen = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    if (!document.fullscreenElement) {
      canvas.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  };

  if (error) {
    return (
      <div className={`mesh-viewer mesh-viewer--error ${className}`.trim()}>
        <p className="mesh-viewer__error">{error}</p>
      </div>
    );
  }

  return (
    <div
      className={`mesh-viewer ${className}`.trim()}
      style={{ height: `${height}px` }}
    >
      <div ref={containerRef} className="mesh-viewer__canvas-wrap">
        {loading && (
          <div className="mesh-viewer__loading">
            <div className="spinner" aria-hidden />
            <p>3D-Modell wird geladen...</p>
          </div>
        )}
        <canvas ref={canvasRef} className="mesh-viewer__canvas" />
      </div>
      {!readOnly && (
        <div className="mesh-viewer__controls">
          <button
            type="button"
            className={`btn btn--ghost btn--sm ${autoRotate ? "mesh-viewer__btn--active" : ""}`}
            onClick={() => setAutoRotate((v) => !v)}
            title="Auto-Rotation"
          >
            ↺ Auto-Rotation
          </button>
          <button
            type="button"
            className={`btn btn--ghost btn--sm ${wireframe ? "mesh-viewer__btn--active" : ""}`}
            onClick={() => setWireframe((v) => !v)}
            title="Wireframe"
          >
            ⬡ Wireframe
          </button>
          <div className="mesh-viewer__lighting">
            <span className="mesh-viewer__lighting-label">☀ Beleuchtung:</span>
            <select
              value={lightingMode}
              onChange={(e) => setLightingMode(e.target.value as LightingMode)}
              className="mesh-viewer__select"
            >
              <option value="studio">Studio</option>
              <option value="neutral">Neutral</option>
              <option value="dark">Dunkel</option>
            </select>
          </div>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={handleFullscreen}
            title="Vollbild"
          >
            ⤢ Fullscreen
          </button>
        </div>
      )}
    </div>
  );
}
