import type { CelebrationType } from "@/lib/types";

type Particle = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  color: string;
  rotation: number;
  spin: number;
};

const colors = ["#111111", "#ffffff", "#d4a72c", "#f7c948", "#2563eb", "#16a34a"];

export function celebrate(type: CelebrationType | null | undefined): void {
  if (!type || typeof window === "undefined" || prefersReducedMotion()) {
    return;
  }

  if (type === "concept_passed") {
    launchConfetti({ particleCount: 90, durationMs: 1200 });
    return;
  }

  launchConfetti({ particleCount: 140, durationMs: 1600 });
  launchBalloons(type === "ariel_examiner_passed" ? "Ariel passed the examiner check!" : "Chapter complete!");
}

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function launchConfetti({ particleCount, durationMs }: { particleCount: number; durationMs: number }): void {
  const canvas = document.createElement("canvas");
  canvas.setAttribute("aria-hidden", "true");
  canvas.className = "pointer-events-none fixed inset-0 z-50";
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  document.body.appendChild(canvas);

  const context = canvas.getContext("2d");
  if (!context) {
    canvas.remove();
    return;
  }
  const canvasContext = context;

  const particles = Array.from({ length: particleCount }, () => createParticle(canvas.width, canvas.height));
  const startedAt = performance.now();

  function draw(now: number) {
    const progress = Math.min((now - startedAt) / durationMs, 1);
    canvasContext.clearRect(0, 0, canvas.width, canvas.height);

    for (const particle of particles) {
      particle.x += particle.vx;
      particle.y += particle.vy;
      particle.vy += 0.08;
      particle.rotation += particle.spin;

      canvasContext.save();
      canvasContext.globalAlpha = 1 - progress;
      canvasContext.translate(particle.x, particle.y);
      canvasContext.rotate(particle.rotation);
      canvasContext.fillStyle = particle.color;
      canvasContext.fillRect(-particle.size / 2, -particle.size / 2, particle.size, particle.size * 0.55);
      canvasContext.restore();
    }

    if (progress < 1) {
      window.requestAnimationFrame(draw);
    } else {
      canvas.remove();
    }
  }

  window.requestAnimationFrame(draw);
}

function createParticle(width: number, height: number): Particle {
  const fromLeft = Math.random() < 0.5;
  return {
    x: fromLeft ? width * 0.2 : width * 0.8,
    y: height * 0.2,
    vx: (fromLeft ? 1 : -1) * (Math.random() * 5 + 2),
    vy: Math.random() * -6 - 2,
    size: Math.random() * 8 + 5,
    color: colors[Math.floor(Math.random() * colors.length)],
    rotation: Math.random() * Math.PI,
    spin: Math.random() * 0.25 - 0.125
  };
}

function launchBalloons(label: string): void {
  const container = document.createElement("div");
  container.className = "pointer-events-none fixed inset-0 z-50 overflow-hidden";
  container.setAttribute("aria-hidden", "true");

  for (let index = 0; index < 7; index += 1) {
    const balloon = document.createElement("span");
    balloon.className = "celebration-balloon";
    balloon.style.left = `${12 + index * 12}%`;
    balloon.style.animationDelay = `${index * 110}ms`;
    balloon.style.background = colors[index % colors.length];
    container.appendChild(balloon);
  }

  const message = document.createElement("div");
  message.className = "celebration-message";
  message.textContent = label;
  container.appendChild(message);
  document.body.appendChild(container);

  window.setTimeout(() => container.remove(), 2200);
}
