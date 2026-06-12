<script setup>
import { useData } from "vitepress";
import { ref, onMounted, onUnmounted, nextTick, watch } from "vue";

const { frontmatter } = useData();

const theme = ref("dark");
const scrolled = ref(false);
let cleanup = [];
let io = null;

const archSvg = ref("");
const ARCH_DEF = `flowchart TD
    subgraph INPUT ["觸發方式"]
        U["CLI User"]
        AI["Claude Code Agent\\n/cdn:cdn-report"]
    end
    U & AI --> P["cdn-traffic-report"]
    P --> AK["Akamai 模組"]
    P --> CF["CloudFront 模組"]
    AK --> OP["1Password op CLI\\n帳密 + TOTP"]
    OP --> BR["agent-browser\\nChromium"]
    BR --> SPA["Akamai Control Center SPA"]
    SPA --> J1["JSON output"]
    CF --> CW["AWS CloudWatch API"]
    CW --> J2["JSON output"]
    J1 & J2 --> OUT["output/"]
    OUT --> CSV["weekly.csv"]`;

let mermaidMod = null;
let archCount = 0;
async function renderArch() {
  if (typeof window === "undefined") return;
  if (!mermaidMod) {
    const m = await import("mermaid");
    mermaidMod = m.default;
  }
  mermaidMod.initialize({ startOnLoad: false, theme: theme.value === "dark" ? "dark" : "default" });
  try {
    archCount++;
    const { svg } = await mermaidMod.render("arch-" + archCount, ARCH_DEF);
    archSvg.value = svg;
  } catch (e) {
    console.error("mermaid:", e);
  }
}

function applyTheme() {
  if (typeof document === "undefined") return;
  document.documentElement.setAttribute("data-theme", theme.value);
}
function toggleTheme() {
  theme.value = theme.value === "dark" ? "light" : "dark";
  try { localStorage.setItem("lab.theme", theme.value); } catch (_) {}
  applyTheme();
}

function reveal() {
  const els = document.querySelectorAll(".lab-content .reveal");
  if (io) io.disconnect();
  io = new IntersectionObserver(
    (entries) => entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } }),
    { threshold: 0.06 }
  );
  els.forEach((el, i) => { el.style.setProperty("--d", (i % 5) * 60 + "ms"); io.observe(el); });
}

onMounted(() => {
  const stored = typeof localStorage !== "undefined" && localStorage.getItem("lab.theme");
  theme.value = stored || document.documentElement.getAttribute("data-theme") || "dark";
  applyTheme();
  nextTick(reveal);
  renderArch();
  const onScroll = () => { scrolled.value = window.scrollY > 8; };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
  cleanup.push(() => window.removeEventListener("scroll", onScroll));
});
onUnmounted(() => { if (io) io.disconnect(); cleanup.forEach((fn) => fn()); cleanup = []; });
watch(theme, renderArch);
</script>

<template>
  <div class="lab-shell">
    <div class="aurora" aria-hidden="true"><div class="aurora-3"></div></div>

    <nav class="toolbar" :class="{ scrolled }">
      <a class="t-brand" href="https://github.com/jimc1682000/cdn-traffic-report" target="_blank" rel="noopener">
        CDN Traffic Report <span class="badge">Claude Code Plugin</span>
      </a>
      <div class="t-ctrls">
        <a href="https://github.com/jimc1682000/cdn-traffic-report" target="_blank" rel="noopener">GitHub</a>
        <a href="https://jimc1682000.github.io" target="_blank" rel="noopener">Resume</a>
        <button class="t-icon" @click="toggleTheme" :aria-label="theme === 'dark' ? 'Light mode' : 'Dark mode'">
          <svg v-if="theme==='dark'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
        </button>
      </div>
    </nav>

    <div class="lab-content">

      <section class="hero reveal">
        <h1>CDN Traffic Report</h1>
        <p class="sub">自動化 CDN 流量報表工具，從 Akamai Control Center 與 AWS CloudFront 擷取數據；同時是 Claude Code Plugin，可直接讓 AI agent 調用</p>
        <div class="hero-badges">
          <a href="https://github.com/jimc1682000/cdn-traffic-report/actions/workflows/test.yml" target="_blank" rel="noopener">
            <img src="https://github.com/jimc1682000/cdn-traffic-report/actions/workflows/test.yml/badge.svg" alt="Tests" />
          </a>
          <a href="https://codecov.io/gh/jimc1682000/cdn-traffic-report" target="_blank" rel="noopener">
            <img src="https://codecov.io/gh/jimc1682000/cdn-traffic-report/graph/badge.svg" alt="Coverage" />
          </a>
        </div>
        <div class="hero-tags">
          <span v-for="t in frontmatter.tech" :key="t">{{ t }}</span>
        </div>
        <div class="hero-links">
          <a class="btn-primary" href="https://github.com/jimc1682000/cdn-traffic-report" target="_blank" rel="noopener">GitHub</a>
          <a class="btn-ghost" href="https://jimc1682000.github.io" target="_blank" rel="noopener">Resume</a>
        </div>
      </section>

      <section class="section reveal">
        <div class="section-title"><span class="ico">🧩</span> 問題 / 為什麼用 Browser Automation</div>
        <div class="card problem-card">
          <p v-for="(line, i) in frontmatter.problem" :key="i">{{ line }}</p>
          <a class="problem-link" href="https://github.com/jimc1682000/cdn-traffic-report/blob/main/COMPARISON.md" target="_blank" rel="noopener">讀 COMPARISON.md →</a>
        </div>
      </section>

      <section class="section reveal">
        <div class="section-title"><span class="ico">🏗</span> 架構 / 資料流</div>
        <div class="card arch-wrap">
          <div v-if="archSvg" class="arch-mermaid" v-html="archSvg"></div>
          <pre v-else class="arch-block">CLI User / Claude Code Agent → cdn-traffic-report
  ├── Akamai: 1Password op → agent-browser (Chromium) → SPA DOM → JSON
  └── CloudFront: AWS CLI → CloudWatch → JSON
→ output/ JSON + weekly.csv</pre>
        </div>
      </section>

      <section class="section reveal">
        <div class="section-title"><span class="ico">💡</span> 核心能力</div>
        <div class="highlight-grid core-grid">
          <div class="highlight-item core-item" v-for="(h, i) in frontmatter.core" :key="h.title">
            <span class="core-num">{{ i + 1 }}</span>
            <h4>{{ h.title }}</h4>
            <p>{{ h.desc }}</p>
          </div>
        </div>
        <div class="extras-row">
          <span class="extras-label">其他亮點</span>
          <div class="extras-list">
            <div class="extra-item" v-for="e in frontmatter.extras" :key="e.title">
              <strong>{{ e.title }}</strong>
              <span>{{ e.desc }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="section reveal">
        <div class="section-title"><span class="ico">🤖</span> Agent Skill 互動流程</div>
        <div class="card-grid">
          <div class="card">
            <div class="code-label">使用者 ↔ Claude Code Agent</div>
            <pre class="code-block"><span class="c"># 使用者只下一句 skill 指令</span>
&gt; /cdn:cdn-report 2026-01-25 2026-01-31

<span class="c"># Agent 自動執行：</span>
  1. 讀 SKILL.md 取得指令模板
  2. 跑 scripts.akamai_report --start … --end …
  3. 讀 output/report_*.json
  4. 依 SKILL.md 規則格式化
  5. 回傳結構化表格</pre>
          </div>
          <div class="card">
            <div class="code-label">Agent 回傳（示意）</div>
            <table class="out-table">
              <thead><tr><th>指標</th><th>流量</th></tr></thead>
              <tbody>
                <tr><td>Edge</td><td>12.34 TB</td></tr>
                <tr><td>Origin</td><td>4.56 TB</td></tr>
                <tr><td>Midgress</td><td>7.89 GB</td></tr>
                <tr><td>Offload</td><td>56.78 %</td></tr>
              </tbody>
            </table>
            <p class="out-note">數字為去識別化示意值，非真實流量。</p>
          </div>
        </div>
      </section>

      <section class="section reveal">
        <div class="section-title"><span class="ico">🛡</span> 測試策略 / 防 UI 改版</div>
        <div class="card-grid">
          <div class="card">
            <div class="code-label">第一層：Contract Check（對真實 UI）</div>
            <p class="defense-desc">contract_check 用 <code>--save</code> 存下 DOM selector baseline，之後用 <code>--diff</code> 比對真實 Akamai UI；selector 失效時在改版當下就抓到，不會靜默產出空值。</p>
            <pre class="code-block">uv run python -m scripts.contract_check --headed --save   <span class="c"># 存 baseline</span>
uv run python -m scripts.contract_check --headed --diff   <span class="c"># 比對偵測改版</span></pre>
          </div>
          <div class="card">
            <div class="code-label">第二層：Mock Integration（CI 離線）</div>
            <p class="defense-desc">tests/mock_site/ 是假的 Akamai SPA（index.html + mock_data.js）。agent-browser 對它跑 integration test，驗證 DOM 擷取邏輯，不需真實帳密、CI 可離線重跑。</p>
            <pre class="code-block">uv run pytest tests/test_mock_integration.py -v   <span class="c"># 離線跑 agent-browser</span></pre>
          </div>
        </div>
      </section>

      <section class="section reveal">
        <div class="section-title"><span class="ico">⚡</span> 使用方式</div>
        <div class="card-grid">
          <div class="card" v-for="cmd in frontmatter.cmds" :key="cmd.label">
            <div class="code-label">{{ cmd.label }}</div>
            <pre class="code-block">{{ cmd.code }}</pre>
          </div>
        </div>
      </section>

      <section class="section reveal">
        <div class="section-title"><span class="ico">📄</span> 輸出格式</div>
        <div class="schema-grid">
          <div class="card">
            <div class="code-label">Akamai / CloudFront JSON</div>
            <pre class="code-block">{
  "date_range": {
    "start": "2026-01-25",
    "end":   "2026-01-31"
  },
  "type":    "summary",
  "traffic": {
    "edge":     12.34,
    "origin":    4.56,
    "offload":  56.78
  },
  "unit": "TB"
}</pre>
          </div>
          <div class="card">
            <div class="code-label">Geography JSON</div>
            <pre class="code-block">{
  "type": "geography",
  "geography": {
    "TW":   9.87,
    "SG":   2.10,
    "ID":   0.05
  },
  "unit": "TB"
}</pre>
          </div>
          <div class="card">
            <div class="code-label">weekly.csv 欄位</div>
            <pre class="code-block">年度 | 週期
edge流量TB | origin流量TB
ID | TW | SG
v1流量TB | v3流量TB
Trailer/EPK | live流量GB
TVA流量GB | home流量GB</pre>
          </div>
        </div>
      </section>

      <section class="section reveal">
        <div class="section-title"><span class="ico">🗂</span> 專案結構</div>
        <div class="card">
          <pre class="code-block">.claude-plugin/plugin.json     <span class="c"># Claude Code Plugin 清單</span>
skills/cdn-report/SKILL.md     <span class="c"># Skill 定義</span>
scripts/
  akamai_report.py             <span class="c"># 主程式 + CLI</span>
  refresh_session.py           <span class="c"># Session + 1Password 登入</span>
  browser_helpers.py           <span class="c"># agent-browser 封裝</span>
  data_extract.py              <span class="c"># DOM 擷取 (KPI + 地理表格)</span>
  contract_check.py            <span class="c"># DOM selector 合約驗證</span>
  cloudfront.py                <span class="c"># AWS CloudWatch 指標</span>
config/settings.yaml.template  <span class="c"># 設定範本</span>
tests/
  mock_site/                   <span class="c"># 本地 mock Akamai SPA</span></pre>
        </div>
      </section>

    </div>

    <footer class="lab-footer">
      <a href="https://github.com/jimc1682000/cdn-traffic-report" target="_blank" rel="noopener">cdn-traffic-report</a>
      <span style="margin:0 .5rem">·</span>
      <a href="https://jimc1682000.github.io" target="_blank" rel="noopener">jimc1682000.github.io</a>
    </footer>
  </div>
</template>
