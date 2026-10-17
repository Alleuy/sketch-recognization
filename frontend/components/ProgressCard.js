"use client";

// 卡3：通关进度（practice 模式隐藏，与原版 display 切换一致）
export default function ProgressCard({ visible, passCount, totalLevel }){
    return (
        <div id="progressPanel" className="panel" style={{display: visible ? "block" : "none"}}>
            <h4>📊 进度信息</h4>
            <div>已通关：<span id="passCount">{passCount}</span> / <span id="totalLevel">{totalLevel}</span></div>
        </div>
    );
}
