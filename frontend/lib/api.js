// API 层：常量、会话、请求封装（从原 index.html 迁移，逻辑原样）
export const API_BASE = "http://127.0.0.1:8000/api";

// 关卡参考提示图（后端 /static 挂载，generate_hint_images.py 产出）
export const HINT_BASE = API_BASE.replace(/\/api$/, "") + "/static/hints/";

// 离线兜底关卡（后端不可用时仅可浏览）
export const FALLBACK_LEVELS = [
    {id:1, class_name:"star", display_name:"星星", difficulty:1, pass_threshold:0.5},
    {id:2, class_name:"hand", display_name:"手", difficulty:1, pass_threshold:0.5},
    {id:3, class_name:"apple", display_name:"苹果", difficulty:2, pass_threshold:0.5},
];

export function getUserId(){
    let id = localStorage.getItem("qd_user_id");
    if(!id){
        id = "u-" + (crypto.randomUUID ? crypto.randomUUID()
                                       : Date.now() + "-" + Math.random().toString(36).slice(2));
        localStorage.setItem("qd_user_id", id);
    }
    return id;
}

export async function apiFetch(path, options = {}){
    const headers = Object.assign(
        {"Content-Type": "application/json", "X-User-ID": getUserId()},
        options.headers || {}
    );
    const resp = await fetch(API_BASE + path, Object.assign({}, options, {headers}));
    if(!resp.ok){
        let detail = "";
        try { detail = (await resp.json()).detail || ""; } catch(e){}
        throw new Error(`请求失败(${resp.status}) ${detail}`);
    }
    return resp.json();
}

// 画布坐标(0~380) -> 训练坐标空间(0~255)
export function normalizeStrokes(rawStrokes, canvasWidth){
    const k = 255 / canvasWidth;
    return rawStrokes.map(s => s.map(p => [Math.round(p[0] * k), Math.round(p[1] * k)]));
}
