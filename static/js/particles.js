class UltimateParticleSystem {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.numParticles = 100;
        this.connectionDistance = 110;
        this.mouseDist = 150;
        this.mouse = { x: -1000, y: -1000 };
        this.accentColor = 'rgba(168, 85, 247, 1)'; // Vibrant Purple
        this.glowColor = 'rgba(168, 85, 247, 0.6)';
        this.lineColor = 'rgba(168, 85, 247, 0.15)';

        this.init();
        window.addEventListener('resize', () => this.resize());
        window.addEventListener('mousemove', (e) => {
            this.mouse.x = e.clientX;
            this.mouse.y = e.clientY;
        });
    }

    init() {
        this.resize();
        for (let i = 0; i < this.numParticles; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                vx: (Math.random() - 0.5) * 1.2,
                vy: (Math.random() - 0.5) * 1.2,
                size: Math.random() * 2 + 1,
                alpha: Math.random() * 0.5 + 0.3
            });
        }
        this.animate();
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        for (let i = 0; i < this.particles.length; i++) {
            let p = this.particles[i];

            // Mouse Interaction (Repel)
            let dxm = p.x - this.mouse.x;
            let dym = p.y - this.mouse.y;
            let distm = Math.sqrt(dxm * dxm + dym * dym);
            if (distm < this.mouseDist) {
                let force = (this.mouseDist - distm) / this.mouseDist;
                p.x += (dxm / distm) * force * 5;
                p.y += (dym / distm) * force * 5;
            }

            // Move
            p.x += p.vx;
            p.y += p.vy;

            // Bounce
            if (p.x < 0 || p.x > this.canvas.width) p.vx *= -1;
            if (p.y < 0 || p.y > this.canvas.height) p.vy *= -1;

            // Draw VINON Glow
            this.ctx.save();
            this.ctx.shadowBlur = 12;
            this.ctx.shadowColor = this.glowColor;
            this.ctx.globalAlpha = p.alpha;
            this.ctx.fillStyle = '#fff';
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            this.ctx.fill();
            this.ctx.restore();

            // Draw Line Connections (from user's C# request)
            for (let j = i + 1; j < this.particles.length; j++) {
                let p2 = this.particles[j];
                let dx = p.x - p2.x;
                let dy = p.y - p2.y;
                let dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < this.connectionDistance) {
                    let alpha = (1 - (dist / this.connectionDistance)) * 0.4;
                    this.ctx.strokeStyle = `rgba(168, 85, 247, ${alpha})`;
                    this.ctx.lineWidth = 0.8;
                    this.ctx.beginPath();
                    this.ctx.moveTo(p.x, p.y);
                    this.ctx.lineTo(p2.x, p2.y);
                    this.ctx.stroke();
                }
            }
        }

        requestAnimationFrame(() => this.animate());
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('particle-canvas')) {
        const canvas = document.createElement('canvas');
        canvas.id = 'particle-canvas';
        canvas.style.position = 'fixed';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100vw';
        canvas.style.height = '100vh';
        canvas.style.zIndex = '0';
        canvas.style.pointerEvents = 'none';
        document.body.prepend(canvas);
    }
    new UltimateParticleSystem('particle-canvas');
});
