"use client";

// 卡1：当前模式与目标词（lv 兜底复刻原 HTML 初始文案：1/星星/star）
export default function ModeCard({ currentMode, lv }){
    return (
        <div className="panel">
            <h3 id="modeTitle">{currentMode === "practice" ? "练习模式" : "闯关模式"}</h3>
            {currentMode === "practice"
                ? <div id="modeHint">自由绘图，只看预测结果，不计闯关</div>
                : <div id="modeHint">当前关卡：<span id="lid">{lv.id}</span>｜请画：<span id="targetZh">{lv.display_name}</span>（<span id="targetEn">{lv.class_name}</span>）</div>}
            <div style={{marginTop: 8, color: "#7aa89a", fontSize: 13}}>模式：平衡模式（top1匹配，准确度≥0.5 通过，识别不成功就画大一点）</div>
        </div>
    );
}
