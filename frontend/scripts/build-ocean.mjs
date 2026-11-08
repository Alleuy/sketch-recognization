// 构建 homepage 字符海洋：ocean-src/app.ts -> public/ocean/ocean.js
// style.css 的字体占位符替换为 /ocean/fonts/*.ttf，字体文件拷贝到 public。
// 用法：cd frontend && node scripts/build-ocean.mjs
import { build } from 'esbuild';
import { readFile, writeFile, mkdir, copyFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = name => join(root, 'ocean-src', name);
const out = name => join(root, 'public', 'ocean', name);

const result = await build({
    entryPoints: [src('app.ts')],
    bundle: true,
    write: false,
    format: 'iife',
    target: 'es2022',
    minify: true,
    legalComments: 'none',
});

let css = await readFile(src('style.css'), 'utf8');
const fonts = ['sans', 'mono', 'light', 'hanzi'];
for (const name of fonts) {
    css = css.replace(`FONT_${name.toUpperCase()}`, `/ocean/fonts/${name}.ttf`);
}

await mkdir(join(root, 'public', 'ocean', 'fonts'), { recursive: true });
for (const name of fonts) {
    await copyFile(src(`${name}.ttf`), out(`fonts/${name}.ttf`));
}
await writeFile(out('ocean.css'), css);
await writeFile(out('ocean.js'), result.outputFiles[0].text);
console.log(`ocean.js ${Math.round(result.outputFiles[0].text.length / 1024)} KB, ocean.css ${Math.round(css.length / 1024)} KB -> public/ocean/`);
