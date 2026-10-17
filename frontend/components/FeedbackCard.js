"use client";
import Top3List from "./Top3List";

// 卡2：识别反馈（msg 文案与样式类由 useGame 驱动，等价原版 msgEl 赋值）
export default function FeedbackCard({ msg, top3 }){
    return (
        <div className="panel">
            <h4>📌 识别反馈</h4>
            <p id="msg" className={msg.cls || undefined}>{msg.text}</p>
            <Top3List top3={top3} />
        </div>
    );
}
