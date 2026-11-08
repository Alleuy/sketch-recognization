/** Animation adapted from https://github.com/stackedlol/ascii-sharks by stackedlol.
 *  Forked for the sketch homepage: ocean engine + control dock only.
 *  Search / music / focus / history demos removed; theme is scoped to .ocean-root. */
import { OceanEngine } from './engine';
import type { SharkKind, SharkSpec } from './world';
import type { RenderMode } from './renderer';

const win = window as unknown as {
  __oceanAPI?: { pause(v: boolean): void; destroy(): void };
};
// The bundle may be injected twice (React StrictMode double effects); init only once.
if (!win.__oceanAPI) {
  init();
}

function init() {
  const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
  const icons = {
    pause: '<svg viewBox="0 0 24 24"><path d="M9 5v14M15 5v14"/></svg>',
    play: '<svg viewBox="0 0 24 24"><path d="m8 5 11 7-11 7Z"/></svg>',
    moon: '<svg viewBox="0 0 24 24"><path d="M20.5 13A8.5 8.5 0 0 1 11 3.5 8.5 8.5 0 1 0 20.5 13Z"/></svg>',
    sun: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3.5"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg>',
  };
  const mixed: SharkSpec[] = [
    { kind: 'whaleshark', size: 1 }, { kind: 'manta', size: .83 },
    { kind: 'hammerhead', size: .86 },
    { kind: 'sunfish', size: .64 }, { kind: 'classic', size: .78 },
  ];
  const kinds: SharkKind[] = ['manta', 'whaleshark', 'sunfish', 'thresher', 'mako', 'nurse', 'greathammer', 'zebra', 'tiger', 'classic', 'hammerhead'];
  const names: Record<SharkKind, string> = { manta: '蝠鲼', whaleshark: '鲸鲨', sunfish: '翻车鱼', thresher: '长尾鲨', mako: '灰鲭鲨', nurse: '护士鲨', greathammer: '大锤头鲨', zebra: '斑马鲨', tiger: '虎鲨', classic: '灰鲨', hammerhead: '锤头鲨' };
  let roster = mixed.map(s => ({ ...s }));
  let paused = false;
  let destroyed = false;
  let dark = false;
  let statusTimer: ReturnType<typeof setTimeout>;
  const storage = {
    get(key: string) { try { return localStorage.getItem(key); } catch { return null; } },
    set(key: string, value: string) { try { localStorage.setItem(key, value); return true; } catch { return false; } },
  };

  // Wait for the React-rendered canvas; next/script may execute before hydration.
  function boot() {
    const root = document.querySelector<HTMLElement>('.ocean-root');
    const canvas = $<HTMLCanvasElement>('ocean');
    if (!root || !canvas) { window.setTimeout(boot, 60); return; }
    start(root, canvas);
  }

  function start(root: HTMLElement, canvas: HTMLCanvasElement) {
    function status(message: string) {
      const el = $('thought-status');
      if (!el) return;
      clearTimeout(statusTimer);
      el.textContent = message;
      el.classList.add('visible');
      statusTimer = setTimeout(() => el.classList.remove('visible'), 3400);
    }

    const pause = $<HTMLButtonElement>('pause');
    const theme = $<HTMLButtonElement>('theme');
    pause.innerHTML = icons.pause;
    theme.innerHTML = icons.moon;

    const engine = new OceanEngine(canvas, roster);
    // Give the initial scene a small head start, so the first frame already feels alive.
    engine.setSharks(roster);

    const renderModes: RenderMode[] = ['ascii', 'type', 'braille', 'blocks', 'geometry', 'lines', 'hanzi'];
    const modeLabels: Record<RenderMode, string> = { ascii: 'ASCII', type: 'TYPE', braille: 'DOTS', blocks: 'BLOCK', geometry: 'GEO', lines: 'LINES', hanzi: 'HANZI' };
    const modeNames: Record<RenderMode, string> = { ascii: 'ASCII 原始字符', type: '纯字符', braille: '盲文点阵', blocks: '方块阴影', geometry: '几何符号', lines: '线条编织', hanzi: '汉字艺术' };
    const modeDescriptions: Record<RenderMode, string> = {
      ascii: '等宽字符与灰色小格，保留最初的质感。',
      type: '用 @ # % R E A T 与标点的疏密，勾勒鱼身与光影。',
      braille: '用细密的点勾勒身体，轻盈、通透。',
      blocks: '用方块和阴影表达明暗，更厚实的像素感。',
      geometry: '圆点、圆环、菱形与方块，组成几何鱼群。',
      lines: '线条沿鱼身方向排列，像游动的编织线稿。',
      hanzi: '一、十、川、水、魚、鯊，以笔画疏密表现层次。',
    };
    let renderMode: RenderMode = 'braille';
    function applyRenderMode(mode: RenderMode) {
      renderMode = mode;
      engine.setRenderMode(mode);
      const select = $<HTMLSelectElement>('render-mode');
      const toggle = $('style-toggle');
      const desc = $('mode-description');
      if (select) select.value = mode;
      if (toggle) {
        toggle.textContent = modeLabels[mode];
        toggle.setAttribute('aria-label', `切换字符风格，当前${modeNames[mode]}`);
        toggle.title = `当前：${modeNames[mode]} · 点击切换下一种`;
      }
      if (desc) desc.textContent = modeDescriptions[mode];
      storage.set('ascii-ocean-render-mode', mode);
    }
    const savedMode = storage.get('ascii-ocean-render-mode') as RenderMode | null;
    applyRenderMode(savedMode && renderModes.includes(savedMode) ? savedMode : 'braille');
    $<HTMLSelectElement>('render-mode').addEventListener('change', e => applyRenderMode((e.target as HTMLSelectElement).value as RenderMode));
    $('style-toggle').addEventListener('click', () => applyRenderMode(renderModes[(renderModes.indexOf(renderMode) + 1) % renderModes.length]));

    pause.addEventListener('click', () => {
      paused = !paused;
      engine.setPaused(paused);
      pause.innerHTML = paused ? icons.play : icons.pause;
      pause.setAttribute('aria-label', paused ? '继续动画' : '暂停动画');
      pause.setAttribute('aria-pressed', String(paused));
      pause.title = paused ? '继续动画' : '暂停动画';
    });

    function applyTheme(value: boolean) {
      dark = value;
      root.dataset.theme = dark ? 'dark' : 'light';
      engine.setTheme(dark);
      theme.innerHTML = dark ? icons.sun : icons.moon;
      theme.setAttribute('aria-label', dark ? '切换浅色' : '切换深色');
      theme.setAttribute('aria-pressed', String(dark));
      theme.title = dark ? '切换浅色' : '切换深色';
    }
    // 默认深色封面风；用户手动切过主题后记住偏好
    applyTheme((storage.get('ascii-ocean-theme') ?? 'dark') === 'dark');
    // Fade only the old water layer; controls remain live while the new palette renders.
    theme.addEventListener('click', () => {
      document.querySelectorAll('.ocean-theme-veil').forEach(el => el.remove());
      let veil: HTMLCanvasElement | null = null;
      if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        const snapshot = document.createElement('canvas');
        snapshot.width = canvas.width;
        snapshot.height = canvas.height;
        const context = snapshot.getContext('2d');
        if (context && 'filter' in context) {
          const appearance = getComputedStyle(canvas);
          context.fillStyle = getComputedStyle(root).backgroundColor;
          context.fillRect(0, 0, snapshot.width, snapshot.height);
          context.filter = appearance.filter;
          context.globalAlpha = Number(appearance.opacity);
          context.drawImage(canvas, 0, 0);
          snapshot.className = 'ocean-theme-veil';
          snapshot.setAttribute('aria-hidden', 'true');
          canvas.after(snapshot);
          veil = snapshot;
        }
      }
      applyTheme(!dark);
      storage.set('ascii-ocean-theme', dark ? 'dark' : 'light');
      if (veil) {
        const snapshot = veil;
        const fade = snapshot.animate([{ opacity: 1 }, { opacity: 0 }], {
          duration: 480, easing: 'cubic-bezier(.2,.7,.2,1)', fill: 'forwards',
        });
        fade.finished.catch(() => {}).finally(() => snapshot.remove());
        // A background tab can suspend animations; do not leave an obsolete layer behind.
        window.setTimeout(() => snapshot.remove(), 650);
      }
    });

    const settingsToggle = $('settings-toggle');
    const settingsPanel = $('settings-panel');
    function closePanels() {
      settingsPanel.hidden = true;
      settingsToggle.setAttribute('aria-expanded', 'false');
    }
    settingsToggle.addEventListener('click', () => {
      const open = settingsPanel.hidden;
      closePanels();
      settingsPanel.hidden = !open;
      settingsToggle.setAttribute('aria-expanded', String(open));
    });
    document.addEventListener('click', e => {
      const target = e.target as Element;
      if (!target.closest('.ocean-controls')) closePanels();
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && !settingsPanel.hidden && settingsPanel.contains(document.activeElement)) settingsToggle.focus();
      if (e.key === 'Escape') closePanels();
    });

    const speed = $<HTMLInputElement>('speed');
    speed.addEventListener('input', () => { engine.setSpeed(Number(speed.value)); $('speed-value').textContent = `${Number(speed.value).toFixed(2)}×`; });
    $<HTMLSelectElement>('roster').addEventListener('change', e => {
      const kind = (e.target as HTMLSelectElement).value;
      roster = kind === 'mixed' ? mixed.map(s => ({ ...s })) : [1, .87, .76, .68].map(size => ({ kind: kind as SharkKind, size }));
      engine.setSharks(roster);
    });
    $('add-shark').addEventListener('click', () => {
      if (roster.length >= 9) { status('海里已经很热闹了，让它们慢慢游吧。'); return; }
      const kind = kinds.find(kind => !roster.some(fish => fish.kind === kind)) ?? kinds[roster.length % kinds.length];
      roster.push({ kind, size: .64 + Math.random() * .15 });
      engine.setSharks(roster);
      status(`${names[kind]}，游进了这片海。`);
    });
    // 涟漪模式开关：开启后按钮高亮，水面周期性泛起涟漪；再点关闭
    const rippleBtn = $('ripple');
    let rippleTimer: number | undefined;
    const rippleOnce = () => engine.ripple(window.innerWidth * (.3 + Math.random() * .4), window.innerHeight * (.5 + Math.random() * .3));
    rippleBtn.addEventListener('click', () => {
      const on = rippleBtn.classList.toggle('active');
      if (on) {
        engine.clickRipple = true;
        rippleOnce();
        rippleTimer = window.setInterval(rippleOnce, 1800);
        status('涟漪模式开启，点击水面查看动效。');
      } else {
        engine.clickRipple = false;
        window.clearInterval(rippleTimer);
        status('涟漪模式关闭。');
      }
    });

    win.__oceanAPI = {
      pause(value: boolean) {
        if (destroyed) return;
        paused = value;
        engine.setPaused(value);
        pause.innerHTML = value ? icons.play : icons.pause;
        pause.setAttribute('aria-pressed', String(value));
        pause.title = value ? '继续动画' : '暂停动画';
      },
      destroy() {
        if (destroyed) return;
        destroyed = true;
        engine.destroy();
      },
    };
    window.addEventListener('pagehide', () => win.__oceanAPI?.destroy(), { once: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
}
