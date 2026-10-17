"use client";
import { useRef } from "react";
import ParticleBackground from "@/components/ParticleBackground";
import HomePage from "@/components/HomePage";
import GamePage from "@/components/GamePage";
import useDrawing from "@/hooks/useDrawing";
import useGame from "@/hooks/useGame";

// 页面壳：粒子背景 + 首页/游戏页切换编排（原 index.html 整体迁移）
export default function Page(){
    const homeRef = useRef(null);
    const gameRef = useRef(null);
    const drawing = useDrawing();
    const game = useGame({ drawing, homeRef, gameRef });

    return (
        <>
            <ParticleBackground />
            <HomePage homeRef={homeRef} onStart={game.startGame} />
            <GamePage game={game} gameRef={gameRef} />
        </>
    );
}
