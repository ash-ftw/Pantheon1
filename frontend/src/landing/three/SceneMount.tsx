import { Suspense, lazy, useEffect, useState } from 'react';

const PantheonScene = lazy(() => import('./PantheonScene'));

function isWebGLAvailable() {
  if (typeof window === 'undefined') return false;
  try {
    const canvas = document.createElement('canvas');
    return !!(
      window.WebGLRenderingContext &&
      (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
    );
  } catch {
    return false;
  }
}

/** Renders the WebGL scene only in the browser when WebGL is available, after mount. */
export function SceneMount({ className }: { className?: string }) {
  const [mounted, setMounted] = useState(false);
  const [hasWebGL, setHasWebGL] = useState(false);

  useEffect(() => {
    setMounted(true);
    setHasWebGL(isWebGLAvailable());
  }, []);

  if (!mounted || !hasWebGL) {
    return (
      <div className={className} aria-hidden>
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(255,255,255,0.06)_0%,transparent_70%)] pointer-events-none" />
      </div>
    );
  }

  return (
    <div className={className}>
      <Suspense fallback={null}>
        <PantheonScene />
      </Suspense>
    </div>
  );
}
