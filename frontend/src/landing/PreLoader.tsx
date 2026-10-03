import { useEffect, useState } from 'react';

interface PreLoaderProps {
  onEnter: () => void;
}

const STATUS_MESSAGES = [
  'INITIALIZING KERNEL',
  'COMPILING ATTACK GRAPH',
  'PROVISIONING NAMESPACE',
  'BUILDING SHADERS',
];

export function PreLoader({ onEnter }: PreLoaderProps) {
  const [progress, setProgress] = useState(0);
  const [statusIndex, setStatusIndex] = useState(0);
  const [isReady, setIsReady] = useState(false);
  const [isFading, setIsFading] = useState(false);

  useEffect(() => {
    // Fast simulated boot counter
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsReady(true);
          return 100;
        }
        // Incremental ticks
        const next = prev + Math.floor(Math.random() * 10) + 12;
        const bounded = next > 100 ? 100 : next;

        // Cycle status messages based on quartile
        if (bounded < 25) setStatusIndex(0);
        else if (bounded < 55) setStatusIndex(1);
        else if (bounded < 85) setStatusIndex(2);
        else setStatusIndex(3);

        if (bounded >= 100) {
          clearInterval(interval);
          setIsReady(true);
        }

        return bounded;
      });
    }, 20);

    return () => clearInterval(interval);
  }, []);

  const handleEnterClick = () => {
    setIsFading(true);
    setTimeout(() => {
      onEnter();
    }, 600);
  };

  const formattedCount = String(progress).padStart(3, '0') + '%';

  return (
    <div
      className={`preloader-overlay ${isFading ? 'fade-out' : ''}`}
      data-testid="preloader-overlay"
    >
      <div className="preloader-center">
        <div className="preloader-sysmark font-mono">
          PANTHEON // ADVERSARIAL VALIDATION FRAMEWORK
        </div>

        <div className="preloader-counter" data-testid="preloader-counter">
          {formattedCount}
        </div>

        <div className="preloader-bar-track">
          <div
            className="preloader-bar-fill"
            style={{ width: `${progress}%` }}
            data-testid="preloader-bar"
          />
        </div>

        <div className="preloader-status" data-testid="preloader-status">
          {STATUS_MESSAGES[statusIndex]}
        </div>

        {isReady && (
          <button
            type="button"
            className="preloader-enter-btn"
            onClick={handleEnterClick}
            data-testid="preloader-enter-btn"
          >
            TAP TO ENTER
          </button>
        )}
      </div>
    </div>
  );
}
