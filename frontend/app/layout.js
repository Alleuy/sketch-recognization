import "./globals.css";

export const metadata = {
    title: "一起画画吧！",
};

export const viewport = {
    width: "device-width",
    initialScale: 1,
};

export default function RootLayout({ children }){
    return (
        <html lang="zh-CN">
            {/* 字符海洋样式：选择器全部限定在 .ocean-root 内，不影响游戏页 */}
            <link rel="stylesheet" href="/ocean/ocean.css" precedence="default" />
            <body>{children}</body>
        </html>
    );
}
