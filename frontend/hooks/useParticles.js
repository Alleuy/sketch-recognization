"use client";
import { useEffect, useRef } from "react";

// 粒子背景引擎（从原 index.html 粒子模块原样迁移：90 个气泡、5 色调色板、上浮循环）
const PALETTE = [
    "rgba(168, 230, 207, 0.75)",
    "rgba(190, 227, 248, 0.70)",
    "rgba(255, 218, 185, 0.68)",
    "rgba(255, 209, 220, 0.68)",
    "rgba(220, 237, 200, 0.70)"
];

export default function useParticles(){
    const canvasRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if(!canvas) return;
        const ctx = canvas.getContext("2d");
        let w, h;

        function resize(){
            w = canvas.width = window.innerWidth;
            h = canvas.height = window.innerHeight;
        }
        resize();
        window.addEventListener("resize", resize);

        class Particle{
            constructor(){
                this.reset(true);
            }
            reset(init){
                this.x = Math.random() * w;
                this.y = init ? Math.random() * h : h + 10;
                this.r = Math.random() * 3.2 + 1.2;
                this.speedX = (Math.random() - 0.5) * 0.28;
                this.speedY = (Math.random() - 0.5) * 0.28;
                this.color = PALETTE[Math.floor(Math.random() * PALETTE.length)];
                this.pulse = Math.random() * Math.PI * 2;
                this.pulseSpeed = 0.006 + Math.random() * 0.008;
            }
            update(){
                this.x += this.speedX;
                this.y += this.speedY;
                if(this.x < -20) this.x = w + 20;
                if(this.x > w + 20) this.x = -20;
                if(this.y < -20) this.y = h + 20;
                if(this.y > h + 20) this.y = -20;
                this.pulse += this.pulseSpeed;
            }
            draw(){
                const r = this.r + Math.sin(this.pulse) * 0.6;
                ctx.beginPath();
                ctx.arc(this.x, this.y, Math.max(0.5, r), 0, Math.PI * 2);
                ctx.fillStyle = this.color;
                ctx.fill();
            }
        }

        const particles = [];
        for(let i = 0; i < 90; i++) particles.push(new Particle());

        let raf;
        function animate(){
            ctx.clearRect(0, 0, w, h);
            particles.forEach(p => { p.update(); p.draw(); });
            raf = requestAnimationFrame(animate);
        }
        animate();

        // StrictMode 双执行防护：清理监听与动画帧
        return () => {
            window.removeEventListener("resize", resize);
            cancelAnimationFrame(raf);
        };
    }, []);

    return canvasRef;
}
