"use client";
import useParticles from "@/hooks/useParticles";

// 全屏粒子背景（气泡上浮 + 脉动）
export default function ParticleBackground(){
    const canvasRef = useParticles();
    return <canvas id="particleCanvas" ref={canvasRef}></canvas>;
}
