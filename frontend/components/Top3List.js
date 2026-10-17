"use client";

// top3/top5 识别结果列表（原 renderTop3 的 innerHTML → JSX，内联样式原样）
export default function Top3List({ top3 }){
    return (
        <div id="top3Box">
            {top3.map((x, i) => (
                <div key={`${i}-${x.class_name}`} style={{marginTop: 6, overflow: "hidden"}}>
                    {x.display_name}（{x.class_name}）
                    <span style={{float: "right", color: "#3a9e7f"}}>{(x.confidence * 100).toFixed(1)}%</span>
                </div>
            ))}
        </div>
    );
}
