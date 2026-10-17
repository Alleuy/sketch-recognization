"use client";

// 卡4：关卡列表三态链（渲染期推导，与原版 renderLevelList 逻辑逐行对应）
// 已通关 ✅ 可点｜通关链最前沿 ▶ 可点｜其后 🔒 锁定不可点
export default function LevelList({ visible, levelData, progress, currentLevelId, onSelect }){
    let frontierId = null;
    for(const l of levelData){
        if(!progress[l.id] || !progress[l.id].passed){ frontierId = l.id; break; }
    }
    return (
        <div id="levelListPanel" className="panel" style={{display: visible ? "block" : "none"}}>
            <h4>📖 关卡列表（绿色=已通关）</h4>
            <div id="levelBox">
                {levelData.map(l => {
                    const passed = progress[l.id] && progress[l.id].passed;
                    const isCurrent = l.id === currentLevelId;
                    const locked = !passed && l.id !== frontierId;
                    let cls = "level-tag";
                    if(passed) cls += " passed";
                    else if(isCurrent) cls += " current";
                    if(locked) cls += " locked";
                    const label = `${l.id}.${l.display_name}`;
                    const icon = locked ? "🔒" : (passed ? "✅" : "▶");
                    return locked
                        ? <span key={l.id} className={cls} title="先通过前面的关卡才能解锁">{icon} {label}</span>
                        : <span key={l.id} className={cls} title="点击进入该关卡" onClick={() => onSelect(l.id)}>{icon} {label}</span>;
                })}
            </div>
        </div>
    );
}
