let resumeId = null;
let sessionId = null;
let isSending = false;

const byId = (id) => document.getElementById(id);
const sendIconHtml = byId("sendBtn").innerHTML;

/* ---------- Dark Mode ---------- */
(function initDarkMode() {
  const saved = localStorage.getItem("theme");
  if (saved === "dark") document.documentElement.setAttribute("data-theme", "dark");
  const btn = byId("darkToggle");
  function update() {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    btn.textContent = isDark ? "☀️" : "🌙";
    btn.classList.toggle("active", isDark);
  }
  update();
  btn.addEventListener("click", () => {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    if (isDark) {
      document.documentElement.removeAttribute("data-theme");
      localStorage.setItem("theme", "light");
    } else {
      document.documentElement.setAttribute("data-theme", "dark");
      localStorage.setItem("theme", "dark");
    }
    update();
  });
})();

/* ---------- Stealth Mode (sensitive word replacement) ---------- */
const stealthMap = [
  ["InterviewSim", "ChatPal"],
  ["模拟面试平台", "智能对话平台"],
  ["面试对话", "对话"],
  ["面试报告", "总结报告"],
  ["面试设置", "对话设置"],
  ["开始面试", "开始对话"],
  ["结束面试并生成报告", "结束对话并生成总结"],
  ["上传简历", "上传资料"],
  ["完成左侧设置，开始你的模拟面试", "完成左侧设置，开始对话"],
  ["AI 驱动的模拟面试平台", "AI 智能对话助手"],
  ["AI 面试官", "AI 助手"],
];
let stealthOn = false;
(function initStealth() {
  const btn = byId("stealthToggle");
  function applyStealth(on) {
    stealthOn = on;
    btn.classList.toggle("active", on);
    document.querySelectorAll("[data-original]").forEach((el) => {
      const orig = el.getAttribute("data-original");
      el.textContent = on ? replaceWords(orig) : orig;
    });
    document.title = on ? "ChatPal" : "InterviewSim";
  }
  btn.addEventListener("click", () => {
    applyStealth(!stealthOn);
    localStorage.setItem("stealth", stealthOn ? "on" : "off");
  });
  if (localStorage.getItem("stealth") === "on") applyStealth(true);
})();

function replaceWords(text) {
  let out = text;
  for (const [from, to] of stealthMap) out = out.replaceAll(from, to);
  return out;
}

/* ---------- Mission Modal ---------- */
(function initMission() {
  const btn = byId("missionBtn");
  const modal = byId("missionModal");
  const closeBtn = byId("missionCloseBtn");

  async function showMission() {
    try {
      const resp = await fetch("/api/v1/mission");
      const data = await resp.json();
      byId("missionTitle").textContent = stealthOn ? "ChatPal 立意" : (data.title || "InterviewSim 立意");
      byId("missionSubtitle").textContent = data.subtitle || "";
      byId("missionCore").textContent = data.core || "";
      const ul = byId("missionPrinciples");
      ul.innerHTML = "";
      (data.principles || []).forEach((p) => {
        const li = document.createElement("li");
        li.textContent = p;
        ul.appendChild(li);
      });
      byId("missionFull").textContent = data.mission || "";
    } catch (e) {
      byId("missionFull").textContent = "加载失败: " + e.message;
    }
    modal.classList.remove("hidden");
  }

  btn.addEventListener("click", showMission);
  closeBtn.addEventListener("click", () => modal.classList.add("hidden"));
  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.add("hidden");
  });
})();

/* ---------- Sidebar Collapse ---------- */
function collapseSidebar() {
  byId("sidebar").classList.add("collapsed");
}
function expandSidebar() {
  byId("sidebar").classList.remove("collapsed");
}
byId("sidebarToggle").addEventListener("click", () => {
  const sb = byId("sidebar");
  sb.classList.contains("collapsed") ? expandSidebar() : collapseSidebar();
});

function setThinking(isThinking) {
  byId("thinkingHint").classList.toggle("hidden", !isThinking);
}

function autoResizeChatInput() {
  const input = byId("chatInput");
  input.style.height = "auto";
  const nextHeight = Math.min(input.scrollHeight, 360);
  input.style.height = `${nextHeight}px`;
}

function openWorkflowViewer() {
  const sid = sessionId ? `?session_id=${sessionId}` : "";
  window.open(`/web/workflow.html${sid}`, "_blank");
}

async function loadSessionOptions() {
  const select = byId("sessionSelect");
  select.innerHTML = '<option value="">请选择会话</option>';
  try {
    const resp = await fetch("/api/v1/sessions?limit=30");
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "加载会话失败");
    (data.sessions || []).forEach((s) => {
      const option = document.createElement("option");
      option.value = String(s.session_id);
      option.textContent = `#${s.session_id} | ${s.status} | ${s.target_role} | ${s.model}`;
      select.appendChild(option);
    });
    if (sessionId) {
      select.value = String(sessionId);
    }
  } catch (err) {
    byId("workflowOutput").textContent = `加载会话失败: ${err.message}`;
  }
}

async function viewWorkflow(sessionIdToView) {
  if (!sessionIdToView) return;
  const output = byId("workflowOutput");
  output.textContent = "加载中...";
  try {
    const resp = await fetch(`/api/v1/sessions/${sessionIdToView}/workflow`);
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "加载工作流失败");
    output.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    output.textContent = `加载失败: ${err.message}`;
  }
}

async function viewTraceMarkdown(sessionIdToView) {
  if (!sessionIdToView) return;
  const output = byId("workflowOutput");
  output.textContent = "加载中...";
  try {
    const resp = await fetch(`/api/v1/sessions/${sessionIdToView}/trace/markdown`);
    const text = await resp.text();
    if (!resp.ok) throw new Error(text || "加载追踪失败");
    output.textContent = text;
  } catch (err) {
    output.textContent = `加载失败: ${err.message}`;
  }
}

// Update file name display
byId("resumeFile").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) {
    byId("fileName").textContent = file.name;
  } else {
    byId("fileName").textContent = "选择 PDF 或 TXT 文件";
  }
});

function appendMsg(role, text, turnEval) {
  const box = byId("chatBox");
  
  // Remove empty state if it exists
  const emptyState = box.querySelector('.empty-state');
  if (emptyState) {
    emptyState.remove();
  }

  const wrapper = document.createElement("div");
  wrapper.className = `msg-wrapper ${role}`;
  
  const sender = document.createElement("div");
  sender.className = "msg-sender";
  sender.textContent = role === "user" ? "你" : (stealthOn ? "AI 助手" : "AI 面试官");
  
  const bubble = document.createElement("div");
  bubble.className = `msg ${role}`;
  bubble.textContent = text;
  
  wrapper.appendChild(sender);

  // Show evaluation feedback card for assistant messages with turn_eval
  if (role === "assistant" && turnEval && turnEval.topic) {
    const evalCard = buildEvalCard(turnEval);
    wrapper.appendChild(evalCard);
  }

  wrapper.appendChild(bubble);
  box.appendChild(wrapper);
  
  box.scrollTop = box.scrollHeight;
}

function buildEvalCard(turnEval) {
  const card = document.createElement("div");
  card.className = "eval-card";

  // Header row: score badge + topic + toggle
  const header = document.createElement("div");
  header.className = "eval-header";

  const scoreBadge = document.createElement("span");
  const score = turnEval.score || 0;
  const scoreClass = score >= 7 ? "high" : score >= 4 ? "mid" : "low";
  scoreBadge.className = `eval-score ${scoreClass}`;
  scoreBadge.textContent = `${score}/10`;

  const topicLabel = document.createElement("span");
  topicLabel.className = "eval-topic";
  topicLabel.textContent = turnEval.topic;

  const decisionBadge = document.createElement("span");
  const decisionMap = { deepen: "深挖", next_topic: "下一题", next_module: "下一模块", end: "结束" };
  decisionBadge.className = "eval-decision";
  decisionBadge.textContent = decisionMap[turnEval.decision] || turnEval.decision;

  const toggle = document.createElement("span");
  toggle.className = "eval-toggle";
  toggle.textContent = "▸ 详情";

  header.appendChild(scoreBadge);
  header.appendChild(topicLabel);
  header.appendChild(decisionBadge);

  if (turnEval._expected_salary) {
    const salaryBadge = document.createElement("span");
    salaryBadge.className = "eval-salary";
    salaryBadge.textContent = `💰 ${turnEval._expected_salary}`;
    header.appendChild(salaryBadge);
  }

  header.appendChild(toggle);

  // Detail body (collapsed by default)
  const body = document.createElement("div");
  body.className = "eval-body";

  if (turnEval.score_rationale) {
    const rationaleTitle = document.createElement("div");
    rationaleTitle.className = "eval-section-title rationale";
    rationaleTitle.textContent = "📊 评分依据";
    body.appendChild(rationaleTitle);
    const rationaleBlock = document.createElement("div");
    rationaleBlock.className = "eval-rationale-block";
    rationaleBlock.textContent = turnEval.score_rationale;
    body.appendChild(rationaleBlock);
  }

  if (turnEval.evidence && turnEval.evidence.length) {
    const evTitle = document.createElement("div");
    evTitle.className = "eval-section-title good";
    evTitle.textContent = "✓ 回答亮点";
    body.appendChild(evTitle);
    turnEval.evidence.forEach(e => {
      const li = document.createElement("div");
      li.className = "eval-item good";
      li.textContent = e;
      body.appendChild(li);
    });
  }

  if (turnEval.gaps && turnEval.gaps.length) {
    const gapTitle = document.createElement("div");
    gapTitle.className = "eval-section-title warn";
    gapTitle.textContent = "✗ 待改进";
    body.appendChild(gapTitle);
    turnEval.gaps.forEach(g => {
      const li = document.createElement("div");
      li.className = "eval-item warn";
      li.textContent = g;
      body.appendChild(li);
    });
  }

  if (turnEval.reasoning) {
    const reasonTitle = document.createElement("div");
    reasonTitle.className = "eval-section-title reasoning";
    reasonTitle.textContent = "💭 评估思路";
    body.appendChild(reasonTitle);
    const reasonBlock = document.createElement("div");
    reasonBlock.className = "eval-reasoning-block";
    reasonBlock.textContent = turnEval.reasoning;
    body.appendChild(reasonBlock);
  }

  if (turnEval.reference_answer) {
    const refTitle = document.createElement("div");
    refTitle.className = "eval-section-title reference";
    refTitle.textContent = "📖 参考答案";
    body.appendChild(refTitle);
    const refBlock = document.createElement("div");
    refBlock.className = "eval-reference-block";
    refBlock.textContent = turnEval.reference_answer;
    body.appendChild(refBlock);
  }

  card.appendChild(header);
  card.appendChild(body);

  // Toggle expand/collapse
  header.addEventListener("click", () => {
    card.classList.toggle("expanded");
    toggle.textContent = card.classList.contains("expanded") ? "▾ 收起" : "▸ 详情";
  });

  return card;
}

function setLoading(btnId, isLoading, originalText) {
  const btn = byId(btnId);
  if (isLoading) {
    btn.disabled = true;
    btn.innerHTML = `<svg class="animate-spin" style="animation: spin 1s linear infinite; margin-right: 8px; width: 16px; height: 16px; display: inline-block; vertical-align: middle;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" style="opacity: 0.25;"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" style="opacity: 0.75;"></path></svg> 处理中...`;
  } else {
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

// Add keyframes for spinner
const style = document.createElement('style');
style.innerHTML = `
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;
document.head.appendChild(style);

function openStep(stepNum) {
  const idMap = { 1: 'step1', 2: 'step2', 3: 'step4' };
  const prevMap = { 2: 'step1', 3: 'step2' };
  const targetId = idMap[stepNum];
  const target = byId(targetId);
  if (!target) return;
  target.classList.remove('disabled');
  target.classList.add('open');
  const prevId = prevMap[stepNum];
  if (prevId) byId(prevId)?.classList.remove('open');
}

// Accordion: click step headers to collapse/expand
['step1', 'step2', 'step4'].forEach(id => {
  const card = byId(id);
  const header = card.querySelector('.card-header');
  header.addEventListener('click', () => {
    if (card.classList.contains('disabled')) return;
    card.classList.toggle('open');
  });
});

byId("uploadBtn").addEventListener("click", async () => {
  await uploadResume(false);
});

byId("reparseBtn").addEventListener("click", async () => {
  await uploadResume(true);
});

byId("deleteCacheBtn").addEventListener("click", async () => {
  const file = byId("resumeFile").files[0];
  if (!file) return alert("请先选择文件，再删除缓存");
  setLoading("deleteCacheBtn", true, "删除这个文件的缓存");
  try {
    const resp = await fetch(`/api/v1/resumes/cache?filename=${encodeURIComponent(file.name)}`, { method: "DELETE" });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "删除缓存失败");
    alert(`缓存删除完成：${data.deleted} 条`);
  } catch (err) {
    alert(err.message);
  } finally {
    setLoading("deleteCacheBtn", false, "删除这个文件的缓存");
  }
});

async function uploadResume(forceReparse) {
  const file = byId("resumeFile").files[0];
  if (!file) return alert("请选择简历文件");

  const buttonId = forceReparse ? "reparseBtn" : "uploadBtn";
  const buttonText = forceReparse ? "重新解析（不使用缓存）" : "上传并解析";
  setLoading(buttonId, true, buttonText);
  if (forceReparse) {
    byId("uploadBtn").disabled = true;
  } else {
    byId("reparseBtn").disabled = true;
  }

  try {
    const form = new FormData();
    form.append("file", file);
    const url = `/api/v1/resumes${forceReparse ? "?force_reparse=true" : ""}`;
    const resp = await fetch(url, { method: "POST", body: form });
    const data = await resp.json();

    if (!resp.ok) throw new Error(data.detail || "上传失败");

    resumeId = data.resume_id;
    byId("profileOutputWrapper").classList.remove("hidden");
    byId("profileOutput").textContent = JSON.stringify(data, null, 2);

    // Advance to step 2
    openStep(2);

    if (data.cache_hit) {
      alert("命中历史缓存，已复用上次解析结果。若要使用新解析逻辑，请点击“重新解析（忽略缓存）”。");
    } else if (forceReparse) {
      alert("已完成重新解析，并覆盖该文件缓存。");
    }
  } catch (err) {
    alert(err.message);
  } finally {
    byId("uploadBtn").disabled = false;
    byId("reparseBtn").disabled = false;
    setLoading(buttonId, false, buttonText);
  }
}

 

byId("startBtn").addEventListener("click", async () => {
  if (!resumeId) return alert("请先上传简历");
  
  setLoading("startBtn", true, "开始面试");
  
  try {
    const body = {
      resume_id: resumeId,
      target_role: byId("targetRole").value,
      expected_salary: byId("expectedSalary").value,
      city: byId("city").value,
      model: byId("model").value,
    };
    const resp = await fetch("/api/v1/interviews", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await resp.json();
    
    if (!resp.ok) throw new Error(data.detail || "启动失败");
    
    sessionId = data.session_id;
    const sessionIdText = String(sessionId);
    byId("sessionInfo").textContent = `会话 ID: ${sessionIdText.substring(0, 8)}...`;
    
    // Enable chat and advance to step 3
    byId("chatInput").disabled = false;
    byId("sendBtn").disabled = false;
    if (window._micBtn) window._micBtn.disabled = false;
    openStep(3);
    
    // Auto-collapse sidebar for discretion
    collapseSidebar();
    
    // Clear chat box and add first question
    byId("chatBox").innerHTML = '';
    appendMsg("assistant", data.first_question);
    
    // Focus input
    byId("chatInput").focus();
    autoResizeChatInput();
  } catch (err) {
    alert(err.message);
  } finally {
    setLoading("startBtn", false, "开始面试");
  }
});

async function sendMessage() {
  if (!sessionId) return alert("请先启动会话");
  if (isSending) return;
  // Stop speech recognition if active
  if (window._stopListening) window._stopListening();
  const input = byId("chatInput");
  const text = input.value.trim();
  if (!text) return;

  isSending = true;
  appendMsg("user", text);
  input.value = "";
  autoResizeChatInput();
  
  const sendBtn = byId("sendBtn");
  sendBtn.disabled = true;
  input.disabled = true;
  if (window._micBtn) window._micBtn.disabled = true;
  sendBtn.innerHTML = "发送中...";
  setThinking(true);

  try {
    const resp = await fetch(`/api/v1/interviews/${sessionId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_message: text }),
    });
    const data = await resp.json();
    
    if (!resp.ok) throw new Error(data.detail || "发送失败");
    
    if (data.turn_eval && data.expected_salary) {
      data.turn_eval._expected_salary = data.expected_salary;
    }
    appendMsg("assistant", data.assistant_message, data.turn_eval);
  } catch (err) {
    alert(err.message);
  } finally {
    isSending = false;
    setThinking(false);
    sendBtn.innerHTML = sendIconHtml;
    sendBtn.disabled = false;
    input.disabled = false;
    if (window._micBtn) window._micBtn.disabled = false;
    input.focus();
    autoResizeChatInput();
  }
}

byId("sendBtn").addEventListener("click", sendMessage);

byId("chatInput").addEventListener("input", autoResizeChatInput);

byId("chatInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

/* ---------- Speech-to-Text (Whisper backend via MediaRecorder) ---------- */
(function initSTT() {
  const micBtn = byId("micBtn");
  let mediaRecorder = null;
  let audioChunks = [];
  let isListening = false;
  let preExistingText = "";

  /* --- WAV encoding helpers --- */
  function encodeWAV(samples, sampleRate) {
    const buf = new ArrayBuffer(44 + samples.length * 2);
    const v = new DataView(buf);
    const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    w(0, "RIFF");
    v.setUint32(4, 36 + samples.length * 2, true);
    w(8, "WAVE"); w(12, "fmt ");
    v.setUint32(16, 16, true);  // chunk size
    v.setUint16(20, 1, true);   // PCM
    v.setUint16(22, 1, true);   // mono
    v.setUint32(24, sampleRate, true);
    v.setUint32(28, sampleRate * 2, true);
    v.setUint16(32, 2, true);   // block align
    v.setUint16(34, 16, true);  // bits per sample
    w(36, "data");
    v.setUint32(40, samples.length * 2, true);
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    return new Blob([buf], { type: "audio/wav" });
  }

  async function blobToWav16k(blob) {
    const arrayBuf = await blob.arrayBuffer();
    const ctx = new AudioContext();
    const decoded = await ctx.decodeAudioData(arrayBuf);
    const duration = decoded.duration;
    const offCtx = new OfflineAudioContext(1, Math.ceil(duration * 16000), 16000);
    const src = offCtx.createBufferSource();
    src.buffer = decoded;
    src.connect(offCtx.destination);
    src.start();
    const rendered = await offCtx.startRendering();
    ctx.close();
    return encodeWAV(rendered.getChannelData(0), 16000);
  }

  async function startListening() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunks = [];
      preExistingText = byId("chatInput").value;

      mediaRecorder = new MediaRecorder(stream);

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        if (audioChunks.length === 0) return;

        const rawBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });

        micBtn.classList.add("transcribing");
        micBtn.title = "转写中…";

        try {
          const wavBlob = await blobToWav16k(rawBlob);
          const form = new FormData();
          form.append("audio", wavBlob, "recording.wav");
          // Send the last AI question as context for better recognition
          const lastAiMsg = [...document.querySelectorAll(".msg.assistant")].pop();
          if (lastAiMsg) form.append("context", lastAiMsg.textContent);
          const resp = await fetch("/api/v1/stt", { method: "POST", body: form });
          if (!resp.ok) throw new Error(`STT ${resp.status}`);
          const data = await resp.json();
          if (data.text) {
            const input = byId("chatInput");
            input.value = preExistingText + data.text;
            autoResizeChatInput();
            input.focus();
          }
        } catch (err) {
          console.warn("STT transcription failed:", err);
        } finally {
          micBtn.classList.remove("transcribing");
          micBtn.title = "语音输入";
        }
      };

      mediaRecorder.start();
      isListening = true;
      micBtn.classList.add("listening");
      micBtn.title = "点击停止录音";
    } catch (err) {
      console.warn("Microphone access denied:", err);
      isListening = false;
    }
  }

  function stopListening() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
    }
    isListening = false;
    micBtn.classList.remove("listening");
  }

  micBtn.addEventListener("click", () => {
    if (isListening) stopListening();
    else startListening();
  });

  window._stopListening = () => { if (isListening) stopListening(); };
  window._micBtn = micBtn;
})();

byId("workflowBtn").addEventListener("click", async () => {
  byId("workflowPanel").classList.toggle("hidden");
  if (!byId("workflowPanel").classList.contains("hidden")) {
    await loadSessionOptions();
  }
});

byId("openViewerBtn").addEventListener("click", openWorkflowViewer);
byId("openReportViewerBtn").addEventListener("click", openWorkflowViewer);

byId("refreshSessionsBtn").addEventListener("click", loadSessionOptions);

byId("viewCurrentWorkflowBtn").addEventListener("click", async () => {
  if (!sessionId) {
    byId("workflowOutput").textContent = "当前没有激活会话，请先开始面试。";
    return;
  }
  byId("sessionSelect").value = String(sessionId);
  await viewWorkflow(sessionId);
});

byId("viewSelectedWorkflowBtn").addEventListener("click", async () => {
  const selected = byId("sessionSelect").value;
  await viewWorkflow(selected);
});

byId("viewSelectedTraceBtn").addEventListener("click", async () => {
  const selected = byId("sessionSelect").value;
  await viewTraceMarkdown(selected);
});

byId("finishBtn").addEventListener("click", async () => {
  if (!sessionId) return alert("请先启动会话");
  
  setLoading("finishBtn", true, "结束面试并生成报告");
  
  try {
    const resp = await fetch(`/api/v1/interviews/${sessionId}/finish`, { method: "POST" });
    const data = await resp.json();
    
    if (!resp.ok) throw new Error(data.detail || "生成报告失败");
    
    byId("reportOutputWrapper").classList.remove("hidden");
    byId("reportOutput").textContent = JSON.stringify(data.report_payload, null, 2);
    
    // Disable chat
    byId("chatInput").disabled = true;
    byId("sendBtn").disabled = true;
    appendMsg("assistant", "面试已结束，报告已生成在左侧面板。");
  } catch (err) {
    alert(err.message);
  } finally {
    setLoading("finishBtn", false, "结束面试并生成报告");
  }
});
