"use client";
import HintBox from "./HintBox";

// 右侧绘画区：画布 + 按钮行 + Ctrl+Z 提示 + 通关提示图
export default function DrawPanel({ canvasRef, onUndo, onClear, onSubmit, hint, hintImgError, onHintError }){
    return (
        <div className="draw-wrap">
            <canvas id="sketchCanvas" width="380" height="380" ref={canvasRef}></canvas>
            <div className="draw-btn-row">
                <button id="undoBtn" onClick={onUndo}>↩ 上一步</button>
                <button id="clearCanvasBtn" onClick={onClear}>清空画布</button>
                <button id="submitBtn" onClick={onSubmit}>提交草图</button>
            </div>
            <div style={{textAlign: "center", marginTop: 8, color: "#7aa89a", fontSize: 12}}>💡 支持 Ctrl+Z 撤销上一步</div>
            <HintBox hint={hint} imgError={hintImgError} onError={onHintError} />
        </div>
    );
}
