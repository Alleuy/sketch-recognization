"use client";

// 游戏页组装（gameRef 供页面切换的命令式过渡使用）
import ModePanel from "./ModePanel";
import InfoPanel from "./InfoPanel";
import DrawPanel from "./DrawPanel";

export default function GamePage({ game, gameRef }){
    return (
        <div className="game-wrap" id="gamePage" ref={gameRef}>
            <button className="back-btn" id="backBtn" onClick={game.goHome}>← 返回首页</button>
            <h1>一起画画吧！</h1>
            <div className="main-wrap">
                <ModePanel currentMode={game.currentMode} onModeChange={game.switchMode} />
                <InfoPanel game={game} />
                <DrawPanel
                    canvasRef={game.canvasRef}
                    onUndo={game.handleUndo}
                    onClear={game.handleClear}
                    onSubmit={game.submit}
                    hint={game.hint}
                    hintImgError={game.hintImgError}
                    onHintError={game.onHintError}
                />
            </div>
        </div>
    );
}
