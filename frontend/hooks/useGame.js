"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { FALLBACK_LEVELS, apiFetch, normalizeStrokes } from "@/lib/api";

const DEFAULT_MSG = {text: "绘制草图后点击提交", cls: ""};
// 初始兜底关卡（复刻原 HTML 初始 modeHint 文案：1/星星/star）
const DEFAULT_LV = {id: 1, display_name: "星星", class_name: "star"};

// 游戏状态机：关卡/进度/模式/提交/提示图/页面切换（原 index.html 游戏逻辑迁移）
export default function useGame({ drawing, homeRef, gameRef }){
    const { clear, undo, isBlank, getStrokes } = drawing;
    const [levelData, setLevelData] = useState([]);
    const [progress, setProgress] = useState({});
    const [currentLevelId, setCurrentLevelId] = useState(1);
    const [currentMode, setCurrentMode] = useState("challenge");
    const [msg, setMsg] = useState(DEFAULT_MSG);
    const [top3, setTop3] = useState([]);
    const [hint, setHint] = useState(null);
    const [hintImgError, setHintImgError] = useState(false);
    const failStreakRef = useRef(0);
    const currentLevelIdRef = useRef(1);
    const levelDataRef = useRef([]);

    const updateLevels = useCallback((data) => {
        levelDataRef.current = data;
        setLevelData(data);
    }, []);

    const hideHint = useCallback(() => {
        failStreakRef.current = 0;
        setHint(null);
        setHintImgError(false);
    }, []);

    const loadLevel = useCallback((lid, data) => {
        const levels = data || levelDataRef.current;
        const lv = levels.find(x => x.id === lid);
        if(!lv) return;
        currentLevelIdRef.current = lid;
        setCurrentLevelId(lid);
        clear();
        hideHint();
        setMsg(DEFAULT_MSG);
        setTop3([]);
    }, [clear, hideHint]);

    // ============ 页面切换（原版命令式过渡逐行复刻） ============
    const startGame = useCallback(() => {
        const home = homeRef.current;
        if(!home) return;
        home.style.opacity = "0";
        setTimeout(() => {
            home.style.display = "none";
            if(gameRef.current) gameRef.current.classList.add("active");
        }, 600);
    }, [homeRef, gameRef]);

    const goHome = useCallback(() => {
        if(gameRef.current) gameRef.current.classList.remove("active");
        setTimeout(() => {
            const home = homeRef.current;
            if(!home) return;
            home.style.display = "flex";
            home.style.opacity = "0";
            void home.offsetWidth;  // 强制 reflow，重触发首页渐入动画
            home.style.opacity = "1";
        }, 700);
    }, [homeRef, gameRef]);

    // ============ 模式切换 ============
    const switchMode = useCallback((mode) => {
        setCurrentMode(mode);
        if(mode === "challenge"){
            loadLevel(currentLevelIdRef.current);
        }else if(mode === "practice"){
            clear();
            hideHint();
            setMsg(DEFAULT_MSG);
            setTop3([]);
        }
    }, [clear, hideHint, loadLevel]);

    const selectLevel = useCallback((lid) => {
        loadLevel(lid);
    }, [loadLevel]);

    // ============ 撤销（按钮 + Ctrl+Z 共用，原版无页面守卫） ============
    const handleUndo = useCallback(() => {
        const r = undo();
        if(r === "undone"){
            setMsg({text: "已撤销上一步", cls: ""});
            setTop3([]);
        }else if(r === "empty"){
            setMsg({text: "没有可以撤销的笔画了", cls: "fail"});
        }
    }, [undo]);

    useEffect(() => {
        function onKey(e){
            if(e.ctrlKey || e.metaKey){
                const key = e.key.toLowerCase();
                if(key === "z" && !e.shiftKey && !e.altKey){
                    e.preventDefault();
                    handleUndo();
                }
            }
        }
        document.addEventListener("keydown", onKey);
        return () => document.removeEventListener("keydown", onKey);
    }, [handleUndo]);

    // ============ 提交 ============
    const submit = useCallback(async () => {
        if(isBlank()){
            setMsg({text: "请先在画布上绘制草图", cls: "fail"});
            return;
        }
        const payload = { strokes: normalizeStrokes(getStrokes(), 380) };
        setMsg({text: "识别中...", cls: ""});
        setTop3([]);
        try{
            if(currentMode === "challenge"){
                const lv = levelDataRef.current.find(l => l.id === currentLevelIdRef.current);
                if(!lv) return;
                const r = await apiFetch(`/levels/${lv.id}/submit`, {
                    method: "POST",
                    body: JSON.stringify(payload)
                });
                // 不可变更新（原版原地改对象，React 下必须整体替换）
                setProgress(prev => {
                    const old = prev[lv.id] || {attempts: 0, passed: false, best_confidence: 0};
                    return {...prev, [lv.id]: {
                        attempts: r.attempts,
                        best_confidence: r.best_confidence,
                        passed: r.passed ? true : old.passed
                    }};
                });
                if(r.passed){
                    hideHint();
                    setMsg({text: `识别「${r.display_name}」成功！`, cls: "success"});
                    setTop3(r.top3);
                    setTimeout(() => {
                        if(r.next_level_id) loadLevel(r.next_level_id);
                    }, 1600);
                }else{
                    const names = r.top3.map(x => x.display_name).join("、");
                    setMsg({text: `识别「${r.display_name}」失败，你画的可能是：${names}`, cls: "fail"});
                    setTop3(r.top3);
                    failStreakRef.current++;
                    if(failStreakRef.current >= 5){
                        setHintImgError(false);
                        setHint({name: lv.display_name, className: lv.class_name});
                    }
                }
            }else if(currentMode === "practice"){
                const r = await apiFetch("/predict", {
                    method: "POST",
                    body: JSON.stringify(payload)
                });
                setMsg({text: "预测结果（top3）：", cls: ""});
                setTop3(r.top5.slice(0, 3));
            }
        }catch(e){
            setMsg({text: "无法连接识别服务，请确认后端已启动（uvicorn app.main:app --port 8000）", cls: "fail"});
        }
    }, [currentMode, isBlank, getStrokes, hideHint, loadLevel]);

    const onHintError = useCallback(() => setHintImgError(true), []);

    // ============ 启动：页面加载即拉取关卡与进度（原版如此，不等点开始游戏） ============
    useEffect(() => {
        let cancelled = false;
        apiFetch("/levels").then(data => {
            if(cancelled) return;
            updateLevels(data.levels);
            loadLevel(Math.min(currentLevelIdRef.current, data.levels.length), data.levels);
        }).catch(() => {
            if(cancelled) return;
            updateLevels(FALLBACK_LEVELS);
            setMsg({text: "无法连接识别服务（请启动后端：uvicorn app.main:app --port 8000），当前仅离线浏览", cls: "fail"});
            loadLevel(Math.min(currentLevelIdRef.current, FALLBACK_LEVELS.length), FALLBACK_LEVELS);
        });
        apiFetch("/progress").then(p => {
            if(cancelled) return;
            const map = {};
            p.levels.forEach(x => { map[x.level_id] = x; });
            setProgress(map);
        }).catch(() => {});
        return () => { cancelled = true; };
    }, [loadLevel, updateLevels]);

    // ============ 派生值（渲染期计算，不进 state） ============
    const lv = levelData.find(l => l.id === currentLevelId) || DEFAULT_LV;
    const passCount = Object.values(progress).filter(p => p.passed).length;
    const totalLevel = levelData.length || 10;  // 复刻原 HTML 初始硬编码 10

    return {
        levelData, progress, currentLevelId, currentMode, msg, top3,
        hint, hintImgError, onHintError,
        lv, passCount, totalLevel,
        canvasRef: drawing.canvasRef, handleClear: clear,
        startGame, goHome, switchMode, selectLevel,
        handleUndo, submit,
    };
}
