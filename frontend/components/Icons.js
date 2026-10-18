"use client";

// 统一 SVG 图标库：描边风格（24×24 viewBox，跟随 currentColor 自动变色）
// 默认 15px、基线下移 0.15em、右距 5px，与原 emoji 的排版占位基本一致

function Svg({ size = 15, filled = false, style, children }){
    return (
        <svg
            viewBox="0 0 24 24"
            width={size}
            height={size}
            fill={filled ? "currentColor" : "none"}
            stroke="currentColor"
            strokeWidth={filled ? 1.5 : 2}
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ verticalAlign: "-0.15em", marginRight: 5, ...style }}
            aria-hidden="true"
        >
            {children}
        </svg>
    );
}

// 左箭头：返回
export function IconArrowLeft(props){
    return (
        <Svg {...props}>
            <path d="M19 12H5" />
            <path d="m12 19-7-7 7-7" />
        </Svg>
    );
}

// 拐弯箭头：撤销上一步
export function IconUndo(props){
    return (
        <Svg {...props}>
            <polyline points="9 14 4 9 9 4" />
            <path d="M20 20v-7a4 4 0 0 0-4-4H4" />
        </Svg>
    );
}

// 灯泡：提示
export function IconBulb(props){
    return (
        <Svg {...props}>
            <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1.3.5 2.6 1.5 3.5.8.8 1.3 1.5 1.5 2.5" />
            <path d="M9 18h6" />
            <path d="M10 22h4" />
        </Svg>
    );
}

// 图钉：识别反馈
export function IconPin(props){
    return (
        <Svg {...props}>
            <path d="M12 17v5" />
            <path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z" />
        </Svg>
    );
}

// 柱状图：进度信息
export function IconChart(props){
    return (
        <Svg {...props}>
            <path d="M3 3v18h18" />
            <path d="M18 17V9" />
            <path d="M13 17V5" />
            <path d="M8 17v-3" />
        </Svg>
    );
}

// 书本：关卡列表
export function IconBook(props){
    return (
        <Svg {...props}>
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
        </Svg>
    );
}

// 锁：锁定关卡
export function IconLock(props){
    return (
        <Svg {...props}>
            <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </Svg>
    );
}

// 对勾圆圈：已通关
export function IconCheck(props){
    return (
        <Svg {...props}>
            <circle cx="12" cy="12" r="10" />
            <path d="m9 12 2 2 4-4" />
        </Svg>
    );
}

// 实心三角：当前最前沿未通关关卡
export function IconPlay(props){
    return (
        <Svg {...props} filled>
            <polygon points="6 3 20 12 6 21 6 3" />
        </Svg>
    );
}
