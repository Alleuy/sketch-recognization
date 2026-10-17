"use client";
import { HINT_BASE } from "@/lib/api";

// 通关提示图（同一关卡连续 5 次未通关后展示；图片 404 时走兜底文案）
export default function HintBox({ hint, imgError, onError }){
    return (
        <div id="hintBox" style={{display: hint ? "block" : "none", marginTop: 14, textAlign: "center"}}>
            <div style={{fontSize: 13, color: "#a97b1a", fontWeight: "bold"}}>
                连续 5 次未通关，参考一下「<span id="hintName">{hint ? hint.name : ""}</span>」可以这样画：
            </div>
            <img
                id="hintImg"
                alt="参考图"
                src={hint ? HINT_BASE + hint.className + ".png" : undefined}
                onError={onError}
                style={{
                    width: 170, height: 170, marginTop: 8, borderRadius: 14,
                    background: "#0b1222", boxShadow: "0 6px 16px rgba(0,0,0,0.18)",
                    display: imgError ? "none" : undefined
                }}
            />
            <div id="hintFallback" style={{display: imgError ? "block" : "none", fontSize: 12, color: "#c0605a", marginTop: 4}}>
                参考图加载失败
            </div>
        </div>
    );
}
