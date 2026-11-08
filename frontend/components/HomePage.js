"use client";

import { useRef } from "react";

/* 首页：字符海洋背景（ocean-src 构建产物）+ 居中标题/开始面板 + 底部控制坞。
   引擎脚本由 page.js 注入，DOM id（ocean/startBtn/…）是引擎绑定的契约，勿改。 */
export default function HomePage({ homeRef, onStart }){
    const rootRef = useRef(null);
    const setRoot = el => {
        rootRef.current = el;
        if (homeRef) homeRef.current = el;
    };

    return (
        <div className="ocean-root" ref={setRoot}>
            <canvas id="ocean" aria-hidden="true"></canvas>
            <div className="soft-light" aria-hidden="true"></div>

            <main className="hero">
                <h1>一起画画吧。</h1>
                <p className="subtitle">随手画几笔，让 AI 猜猜看</p>

                <section className="center-panel start-panel glass" aria-label="开始游戏">
                    <div className="start-copy">
                        <p className="start-label mono">QUICK DRAW · 100 LEVELS</p>
                        <p className="start-title">CNN 草图识别闯关挑战</p>
                    </div>
                    <button id="startBtn" onClick={onStart}>开始游戏</button>
                </section>

                <p className="thought-status" id="thought-status" role="status"></p>
            </main>

            <footer className="bottom-bar">
                <span className="credit mono">cn sketch game</span>

                <div className="ocean-controls">
                    <span className="interaction-hint mono">draw gently. let the ai guess.</span>
                    <div className="control-dock glass" role="toolbar" aria-label="海洋设置">
                        <button className="mode-button mono" id="style-toggle" title="切换字符风格">ASCII</button>
                        <span className="dock-divider"></span>
                        <button className="icon-button" id="pause" aria-label="暂停动画" aria-pressed="false"></button>
                        <button className="icon-button" id="theme" aria-label="切换深色" aria-pressed="false"></button>
                        <span className="dock-divider"></span>
                        <button className="icon-button" id="settings-toggle" aria-controls="settings-panel" aria-expanded="false" title="设置">
                            <svg viewBox="0 0 24 24"><path d="M5 4v5m0 4v7m7-16v9m0 4v3m7-16v2m0 4v10M2 9h6m1 8h6m1-11h6"/></svg>
                        </button>
                    </div>

                    <section className="popover glass settings-panel" id="settings-panel" hidden>
                        <header className="panel-heading">
                            <span>海洋设置</span>
                            <span className="mono">OCEAN</span>
                        </header>

                        <div className="setting-label"><span>CHAR STYLE</span><span>字符风格</span></div>
                        <select id="render-mode">
                            <option value="ascii">ASCII 原始字符</option>
                            <option value="type">纯字符</option>
                            <option value="braille">盲文点阵</option>
                            <option value="blocks">方块阴影</option>
                            <option value="geometry">几何符号</option>
                            <option value="lines">线条编织</option>
                            <option value="hanzi">汉字艺术</option>
                        </select>
                        <p className="mode-description" id="mode-description"></p>

                        <div className="setting-label"><span>ROSTER</span><span>鱼群主角</span></div>
                        <select id="roster">
                            <option value="mixed">混合巡游</option>
                            <optgroup label="鲨鱼">
                                <option value="thresher">长尾鲨</option>
                                <option value="mako">灰鲭鲨</option>
                                <option value="nurse">护士鲨</option>
                                <option value="greathammer">大锤头鲨</option>
                                <option value="zebra">斑马鲨</option>
                                <option value="tiger">虎鲨</option>
                                <option value="hammerhead">锤头鲨</option>
                            </optgroup>
                            <optgroup label="温和的大型鱼">
                                <option value="whaleshark">鲸鲨</option>
                                <option value="manta">蝠鲼</option>
                                <option value="sunfish">翻车鱼</option>
                            </optgroup>
                        </select>

                        <div className="setting-label"><span>SPEED</span><span>速度</span></div>
                        <input type="range" id="speed" min="0.5" max="2" step="0.05" defaultValue="1" />
                        <output id="speed-value" className="mono">1.00×</output>

                        <div className="ocean-actions">
                            <button id="add-shark">
                                <svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
                                添加一只鱼
                            </button>
                            <button id="ripple">
                                <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="8.5" strokeDasharray="3 4"/></svg>
                                涟漪
                            </button>
                        </div>

                        <p className="panel-footnote">所有变化即刻生效，随时可以切回。</p>
                    </section>
                </div>
            </footer>
        </div>
    );
}
