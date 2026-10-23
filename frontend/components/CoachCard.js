"use client";
import { IconBulb } from "./Icons";

// 绘画导师卡片：连续 2 次失败后可主动求助，展示"诊断 + 证据 + 实测对比 + 建议"
export default function CoachCard({ visible, failCount, coach, loading, onAsk }){
    if(!visible) return null;
    const canAsk = failCount >= 2;
    const hasResult = coach && !coach.error;
    if(!canAsk && !hasResult) return null;

    return (
        <div id="coachBox">
            {canAsk && (
                <button id="coachAskBtn" onClick={onAsk} disabled={loading}>
                    {loading ? "导师正在分析你的画…" : "求助：让导师看看哪里不对"}
                </button>
            )}
            {coach && coach.error && (
                <div className="coach-card"><div className="coach-diagnosis">{coach.error}</div></div>
            )}
            {hasResult && (
                <div className="coach-card" id="coachCard">
                    <div className="coach-head"><IconBulb size={15} />绘画导师</div>
                    <div className="coach-diagnosis">{coach.diagnosis}</div>
                    {coach.evidence && coach.evidence.length > 0 && (
                        <ul className="coach-evidence">
                            {coach.evidence.map((text, i) => <li key={i}>{text}</li>)}
                        </ul>
                    )}
                    {coach.probe && (
                        <div className="coach-probe">
                            {coach.probe.changed
                                ? `实测：${coach.probe.label}后，「${coach.target.display_name}」的置信度 ${Math.round(coach.probe.before * 100)}% → ${Math.round(coach.probe.after * 100)}%`
                                : `实测：${coach.probe.label}后模型仍未识别出「${coach.target.display_name}」，问题不在大小或位置`}
                        </div>
                    )}
                    {coach.suggestions && coach.suggestions.length > 0 && (
                        <ul className="coach-suggest">
                            {coach.suggestions.map((text, i) => <li key={i}>{text}</li>)}
                        </ul>
                    )}
                </div>
            )}
        </div>
    );
}
