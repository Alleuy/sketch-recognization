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
            <body>{children}</body>
        </html>
    );
}
