"use client";
import { useCallback, useEffect, useRef } from "react";

// 画布引擎：笔画采集、重绘、撤销、清空（原 index.html 画布模块迁移）
// 笔画数据走 ref：pointermove 高频触发，入 state 会导致全树重渲染且偏离原版行为；
// 画布重绘走命令式 redraw()，与原版 redrawCanvas 等价。
export default function useDrawing(){
    const canvasRef = useRef(null);
    const strokesRef = useRef([]);
    const currentStrokeRef = useRef([]);
    const drawingRef = useRef(false);

    const redraw = useCallback(() => {
        const canvas = canvasRef.current;
        if(!canvas) return;
        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const strokes = strokesRef.current;
        const currentStroke = currentStrokeRef.current;
        const all = currentStroke.length ? strokes.concat([currentStroke]) : strokes;
        all.forEach(stroke => {
            if(!stroke || stroke.length === 0) return;
            ctx.beginPath();
            if(stroke.length === 1){
                ctx.arc(stroke[0][0], stroke[0][1], ctx.lineWidth/2, 0, Math.PI*2);
                ctx.fillStyle = "#fff";
                ctx.fill();
                return;
            }
            ctx.moveTo(stroke[0][0], stroke[0][1]);
            for(let i = 1; i < stroke.length; i++){
                ctx.lineTo(stroke[i][0], stroke[i][1]);
            }
            ctx.stroke();
        });
    }, []);

    const clear = useCallback(() => {
        strokesRef.current = [];
        currentStrokeRef.current = [];
        const canvas = canvasRef.current;
        if(canvas){
            const ctx = canvas.getContext("2d");
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    }, []);

    // 返回 "undone" | "empty" | "drawing"，msg 副作用由调用方（useGame）处理
    const undo = useCallback(() => {
        if(drawingRef.current) return "drawing";
        if(strokesRef.current.length === 0) return "empty";
        strokesRef.current.pop();
        redraw();
        return "undone";
    }, [redraw]);

    // 原版提交前校验：strokes 为空或正绘制中视为空画布
    const isBlank = useCallback(() =>
        strokesRef.current.length === 0 || currentStrokeRef.current.length > 0, []);

    const getStrokes = useCallback(() => strokesRef.current, []);

    useEffect(() => {
        const canvas = canvasRef.current;
        if(!canvas) return;
        const ctx = canvas.getContext("2d");
        ctx.lineWidth = 4;
        ctx.strokeStyle = "#fff";
        ctx.lineCap = "round";
        ctx.lineJoin = "round";

        function getPos(e){
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            return [
                Math.round((e.clientX - rect.left) * scaleX),
                Math.round((e.clientY - rect.top) * scaleY)
            ];
        }
        function onDown(e){
            e.preventDefault();
            if(canvas.setPointerCapture) canvas.setPointerCapture(e.pointerId);
            drawingRef.current = true;
            currentStrokeRef.current = [getPos(e)];
            redraw();
        }
        function onMove(e){
            if(!drawingRef.current) return;
            e.preventDefault();
            const [x, y] = getPos(e);
            const last = currentStrokeRef.current[currentStrokeRef.current.length - 1];
            if(!last || Math.hypot(x - last[0], y - last[1]) > 2){
                currentStrokeRef.current.push([x, y]);
            }
            redraw();
        }
        function endStroke(){
            if(!drawingRef.current) return;
            drawingRef.current = false;
            if(currentStrokeRef.current.length > 0) strokesRef.current.push(currentStrokeRef.current);
            currentStrokeRef.current = [];
            redraw();
        }
        canvas.addEventListener("pointerdown", onDown);
        canvas.addEventListener("pointermove", onMove);
        canvas.addEventListener("pointerup", endStroke);
        canvas.addEventListener("pointercancel", endStroke);
        canvas.addEventListener("pointerleave", endStroke);

        return () => {
            canvas.removeEventListener("pointerdown", onDown);
            canvas.removeEventListener("pointermove", onMove);
            canvas.removeEventListener("pointerup", endStroke);
            canvas.removeEventListener("pointercancel", endStroke);
            canvas.removeEventListener("pointerleave", endStroke);
        };
    }, [redraw]);

    return { canvasRef, redraw, clear, undo, isBlank, getStrokes };
}
