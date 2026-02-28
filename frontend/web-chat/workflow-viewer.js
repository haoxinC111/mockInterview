const byId = (id) => document.getElementById(id);

let currentSessionId = null;
let workflowCache = null;

function querySessionId() {
  const url = new URL(window.location.href);
  const sid = url.searchParams.get("session_id");
  return sid ? Number(sid) : null;
}

async function fetchJson(url) {
  const resp = await fetch(url);
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || `request failed: ${url}`);
  return data;
}

function setActiveTab(name) {
  ["trace", "workflow", "report", "llm"].forEach((tab) => {
    byId(`tab${tab[0].toUpperCase()}${tab.slice(1)}`).classList.toggle("active", tab === name);
    byId(`${tab}View`).classList.toggle("hidden", tab !== name);
  });
}

function renderTrace(workflow) {
  const trace = workflow.decision_traces || [];
  const messages = workflow.messages || [];
  const turns = [];
  let pendingUser = null;
  for (const m of messages) {
    if (m.role === "user") {
      pendingUser = m.content;
      continue;
    }
    if (m.role === "assistant" && pendingUser) {
      turns.push({ user: pendingUser, assistant: m.content });
      pendingUser = null;
    }
  }

  const cards = turns.map((t, idx) => {
    const d = trace[idx] || {};
    return `
      <article class="trace-card">
        <h3>Turn ${idx + 1}</h3>
        <p class="kv"><b>Human</b>: ${t.user}</p>
        <p class="kv"><b>Assistant</b>: ${t.assistant}</p>
        <p class="kv"><b>Topic</b>: ${d.topic || "-"}</p>
        <p class="kv"><b>Score</b>: ${d.score ?? "-"}</p>
        <p class="kv"><b>Decision</b>: ${d.decision || "-"}</p>
        <p class="kv"><b>Reason</b>: ${d.decision_reason || "-"}</p>
        <p class="kv"><b>Feedback</b>: ${d.feedback || "-"}</p>
        <p class="kv"><b>LLM失败</b>: evaluate=${Boolean(d.llm_evaluate_failed)} / followup=${Boolean(d.llm_followup_failed)}</p>
      </article>
    `;
  });
  byId("traceView").innerHTML = cards.join("") || "<p class='muted'>暂无轮次数据</p>";
}

function renderWorkflow(workflow) {
  byId("workflowView").innerHTML = `<pre>${JSON.stringify(workflow, null, 2)}</pre>`;
}

function renderReport(workflow) {
  const report = workflow.latest_report;
  if (!report) {
    byId("reportView").innerHTML = "<p class='muted'>当前会话暂无报告（可能尚未结束面试）。</p>";
    return;
  }
  byId("reportView").innerHTML = `<pre>${JSON.stringify(report, null, 2)}</pre>`;
}

function renderLLM(workflow) {
  const events = workflow.llm_events || [];
  byId("llmView").innerHTML = `<pre>${JSON.stringify(events, null, 2)}</pre>`;
}

async function loadWorkflow(sessionId) {
  currentSessionId = Number(sessionId);
  workflowCache = await fetchJson(`/api/v1/sessions/${sessionId}/workflow`);
  byId("sessionTitle").textContent = `Session #${workflowCache.session_id} - ${workflowCache.target_role}`;
  byId("sessionMeta").textContent = `状态: ${workflowCache.status} | 模型: ${workflowCache.model} | 轮次: ${workflowCache.turn_count ?? 0}`;
  renderTrace(workflowCache);
  renderWorkflow(workflowCache);
  renderReport(workflowCache);
  renderLLM(workflowCache);
}

function renderSessionList(sessions) {
  const container = byId("sessionList");
  container.innerHTML = "";
  sessions.forEach((s) => {
    const div = document.createElement("div");
    div.className = `session-item ${Number(s.session_id) === currentSessionId ? "active" : ""}`;
    div.innerHTML = `
      <div><b>#${s.session_id}</b> ${s.target_role}</div>
      <div class="meta">${s.status} | ${s.model}</div>
      <div class="meta">${s.updated_at}</div>
    `;
    div.addEventListener("click", async () => {
      await loadWorkflow(s.session_id);
      renderSessionList(sessions);
    });
    container.appendChild(div);
  });
}

async function loadSessionsAndInitial() {
  const data = await fetchJson("/api/v1/sessions?limit=50");
  const sessions = data.sessions || [];
  const sid = querySessionId();
  if (sid) currentSessionId = sid;
  else if (!currentSessionId && sessions.length > 0) currentSessionId = sessions[0].session_id;
  renderSessionList(sessions);
  if (currentSessionId) {
    await loadWorkflow(currentSessionId);
    renderSessionList(sessions);
  }
}

byId("refreshBtn").addEventListener("click", loadSessionsAndInitial);
byId("tabTrace").addEventListener("click", () => setActiveTab("trace"));
byId("tabWorkflow").addEventListener("click", () => setActiveTab("workflow"));
byId("tabReport").addEventListener("click", () => setActiveTab("report"));
byId("tabLLM").addEventListener("click", () => setActiveTab("llm"));

loadSessionsAndInitial().catch((err) => {
  byId("traceView").innerHTML = `<p class='muted'>加载失败: ${err.message}</p>`;
});
