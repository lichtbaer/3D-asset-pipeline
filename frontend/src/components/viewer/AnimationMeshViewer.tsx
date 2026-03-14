import { useRef, useEffect, useState, useCallback } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { GLTF } from "three/examples/jsm/loaders/GLTFLoader.js";
import "./MeshViewer.css";
import "./AnimationMeshViewer.css";

export interface AnimationMeshViewerProps {
  glbUrl: string;
  height?: number;
  className?: string;
}

export function AnimationMeshViewer({
  glbUrl,
  height = 500,
  className = "",
}: AnimationMeshViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mountedRef = useRef(true);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const modelRef = useRef<THREE.Group | null>(null);
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const clockRef = useRef<THREE.Clock | null>(null);
  const actionsRef = useRef<Map<string, THREE.AnimationAction>>(new Map());
  const clipsRef = useRef<THREE.AnimationClip[]>([]);
  const gltfRef = useRef<GLTF | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [clipNames, setClipNames] = useState<string[]>([]);
  const [selectedClip, setSelectedClip] = useState<string>("");
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const playAction = useCallback((clipName: string) => {
    const mixer = mixerRef.current;
    const actions = actionsRef.current;
    if (!mixer) return;

    mixer.stopAllAction();
    const action = actions.get(clipName);
    if (action) {
      action.reset();
      action.setLoop(THREE.LoopRepeat, Infinity);
      action.play();
      setIsPlaying(true);
      const clip = action.getClip();
      setDuration(clip.duration);
      setCurrentTime(0);
    }
  }, []);

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
    controlsRef.current = controls;

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);

    const directional1 = new THREE.DirectionalLight(0xffffff, 1.0);
    directional1.position.set(5, 5, 5);
    scene.add(directional1);

    const directional2 = new THREE.DirectionalLight(0xffffff, 0.3);
    directional2.position.set(-5, -5, -5);
    scene.add(directional2);

    const clock = new THREE.Clock();
    clockRef.current = clock;

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
        gltfRef.current = gltf;
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

        const mixer = new THREE.AnimationMixer(model);
        mixerRef.current = mixer;
        const actions = new Map<string, THREE.AnimationAction>();
        actionsRef.current = actions;

        const clips = gltf.animations ?? [];
        clipsRef.current = clips;
        const names = clips.map((c, i) => c.name || `clip_${i}`);
        setClipNames(names);

        clips.forEach((clip, i) => {
          const key = clip.name || `clip_${i}`;
          const action = mixer.clipAction(clip);
          action.setLoop(THREE.LoopRepeat, Infinity);
          actions.set(key, action);
        });

        if (names.length > 0) {
          setSelectedClip(names[0]);
          setDuration(clips[0].duration);
        }

        if (mountedRef.current) setLoading(false);
      },
      undefined,
      (err) => {
        console.error("AnimationMeshViewer: GLB load error", glbUrl, err);
        if (mountedRef.current) {
          setError("3D-Vorschau nicht verfügbar");
          setLoading(false);
        }
      }
    );

    let frameId: number | null = null;
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const mixer = mixerRef.current;
      if (mixer) {
        mixer.update(delta);
      }
      controls.update();
      renderer.render(scene, camera);
    };
    frameId = requestAnimationFrame(animate);

    const timeInterval = setInterval(() => {
      if (!mountedRef.current) return;
      const actions = actionsRef.current;
      const activeAction = Array.from(actions.values()).find((a) => a.isRunning());
      if (activeAction) {
        const clip = activeAction.getClip();
        const time = activeAction.time % clip.duration;
        setCurrentTime(time);
        setDuration(clip.duration);
      }
    }, 100);

    return () => {
      mountedRef.current = false;
      clearInterval(timeInterval);
      resizeObserver.disconnect();
      if (frameId !== null) {
        cancelAnimationFrame(frameId);
      }
      const mixer = mixerRef.current;
      const gltf = gltfRef.current;
      if (mixer) {
        mixer.stopAllAction();
        if (gltf?.scene) {
          mixer.uncacheRoot(gltf.scene);
        }
        mixerRef.current = null;
      }
      clockRef.current = null;
      actionsRef.current.clear();
      clipsRef.current = [];
      gltfRef.current = null;
      controls.dispose();
      renderer.dispose();
      scene.clear();
      sceneRef.current = null;
      cameraRef.current = null;
      rendererRef.current = null;
      controlsRef.current = null;
      modelRef.current = null;
    };
  }, [glbUrl]);

  useEffect(() => {
    if (selectedClip && clipNames.includes(selectedClip)) {
      playAction(selectedClip);
    }
  }, [selectedClip, clipNames, playAction]);

  const handlePlay = () => {
    const mixer = mixerRef.current;
    const actions = actionsRef.current;
    if (!mixer || !selectedClip) return;
    const action = actions.get(selectedClip);
    if (action) {
      action.play();
      setIsPlaying(true);
    }
  };

  const handlePause = () => {
    const mixer = mixerRef.current;
    if (!mixer) return;
    mixer.stopAllAction();
    setIsPlaying(false);
  };

  const handleReset = () => {
    const mixer = mixerRef.current;
    const actions = actionsRef.current;
    if (!mixer || !selectedClip) return;
    mixer.stopAllAction();
    const action = actions.get(selectedClip);
    if (action) {
      action.reset();
      action.play();
      setIsPlaying(true);
      setCurrentTime(0);
    }
  };

  const handleClipChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedClip(e.target.value);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = Number(e.target.value);
    const mixer = mixerRef.current;
    const actions = actionsRef.current;
    if (!mixer || !selectedClip) return;
    const action = actions.get(selectedClip);
    if (action) {
      action.time = value;
      setCurrentTime(value);
    }
  };

  if (error) {
    return (
      <div
        className={`animation-mesh-viewer animation-mesh-viewer--error ${className}`.trim()}
      >
        <p className="mesh-viewer__error">{error}</p>
      </div>
    );
  }

  return (
    <div
      className={`animation-mesh-viewer mesh-viewer ${className}`.trim()}
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
      <div className="animation-mesh-viewer__controls">
        <div className="animation-mesh-viewer__playback">
          <button
            type="button"
            className="mesh-viewer__btn"
            onClick={handlePlay}
            disabled={!selectedClip || isPlaying}
            title="Play"
          >
            ▶ Play
          </button>
          <button
            type="button"
            className="mesh-viewer__btn"
            onClick={handlePause}
            disabled={!selectedClip || !isPlaying}
            title="Pause"
          >
            ⏸ Pause
          </button>
          <button
            type="button"
            className="mesh-viewer__btn"
            onClick={handleReset}
            disabled={!selectedClip}
            title="Reset"
          >
            ⏮ Reset
          </button>
        </div>
        {clipNames.length > 0 && (
          <div className="animation-mesh-viewer__clip-select">
            <label htmlFor="animation-clip-select" className="animation-mesh-viewer__clip-label">
              Clip:
            </label>
            <select
              id="animation-clip-select"
              value={selectedClip}
              onChange={handleClipChange}
              className="mesh-viewer__select"
            >
              {clipNames.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="animation-mesh-viewer__time">
          <input
            type="range"
            min={0}
            max={duration || 1}
            step={0.01}
            value={currentTime}
            onChange={handleSeek}
            className="animation-mesh-viewer__slider"
            disabled={!selectedClip}
          />
          <span className="animation-mesh-viewer__time-label">
            {currentTime.toFixed(1)}s / {(duration || 0).toFixed(1)}s
          </span>
        </div>
      </div>
    </div>
  );
}
