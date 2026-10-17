"use client";

// 左侧模式按钮组（词语接龙 MVP 未开放，保持禁用态）
export default function ModePanel({ currentMode, onModeChange }){
    const modes = [
        {mode: "challenge", label: "闯关模式"},
        {mode: "chain", label: "词语接龙", disabled: true},
        {mode: "practice", label: "练习模式"},
    ];
    return (
        <div className="mode-panel">
            {modes.map(m => (
                <button
                    key={m.mode}
                    className={"mode-btn" + (currentMode === m.mode ? " active" : "")}
                    data-mode={m.mode}
                    disabled={m.disabled}
                    title={m.disabled ? "MVP 暂未开放，敬请期待" : undefined}
                    onClick={() => onModeChange(m.mode)}
                >
                    {m.label}
                </button>
            ))}
        </div>
    );
}
