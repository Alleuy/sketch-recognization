"use client";
import ModeCard from "./ModeCard";
import FeedbackCard from "./FeedbackCard";
import ProgressCard from "./ProgressCard";
import LevelList from "./LevelList";

// 中间信息卡片栏：闯关模式卡 / 识别反馈卡 / 进度卡 / 关卡列表卡
export default function InfoPanel({ game }){
    const challenge = game.currentMode === "challenge";
    return (
        <div className="info-panel">
            <ModeCard currentMode={game.currentMode} lv={game.lv} />
            <FeedbackCard msg={game.msg} top3={game.top3} />
            <ProgressCard visible={challenge} passCount={game.passCount} totalLevel={game.totalLevel} />
            <LevelList
                visible={challenge}
                levelData={game.levelData}
                progress={game.progress}
                currentLevelId={game.currentLevelId}
                onSelect={game.selectLevel}
            />
        </div>
    );
}
