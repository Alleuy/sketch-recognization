"use client";

// 首页卡片（homeRef 供页面切换的命令式过渡使用，保证动画与原版一致）
export default function HomePage({ homeRef, onStart }){
    return (
        <div className="home-wrap" id="homePage" ref={homeRef}>
            <div className="home-card">
                <span className="float-bubble b1"></span>
                <span className="float-bubble b2"></span>
                <span className="deco-dot d1"></span>
                <span className="deco-dot d2"></span>
                <span className="deco-dot d3"></span>
                <h1>一起画画吧！</h1>
                <p className="subtitle">随手画几笔，让 AI 猜猜看</p>
                <button id="startBtn" onClick={onStart}>开始游戏</button>
            </div>
        </div>
    );
}
