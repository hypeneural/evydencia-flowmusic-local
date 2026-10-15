(() => {
  "use strict";
  // Never persist the local API token: no cookies, localStorage or URL params.
  let token = "";
  const byId = (id) => document.getElementById(id);
  const form = byId("access-form");
  const tokenInput = byId("api-token");
  const message = byId("access-message");
  const fmt = (n) => new Intl.NumberFormat("pt-BR").format(n);
  const date = (s) => {
    if (!s) return "Nunca consultado";
    const d = new Date(s);
    return Number.isNaN(d.getTime()) ? "Data indisponível"
      : new Intl.DateTimeFormat("pt-BR", { dateStyle:"short", timeStyle:"short" }).format(d);
  };
  const el = (tag, css, text) => {
    const node = document.createElement(tag);
    if (css) node.className = css;
    if (text !== undefined) node.textContent = text; // No untrusted HTML.
    return node;
  };
  function inform(text, kind = "") {
    message.textContent = text;
    message.className = "message " + kind;
  }
  async function getJson(path) {
    const response = await fetch(path, {
      method: "GET", cache: "no-store", credentials: "omit",
      headers: { "X-Local-Token": token, "Accept": "application/json" }
    });
    if (response.status === 401) throw new Error("Token não autorizado. Confira data/local-token.txt.");
    if (!response.ok) throw new Error("Falha HTTP " + response.status + " ao consultar " + path);
    return response.json();
  }
  const STATE = {
    "not_connected": ["Não conectada", "bad"],
    "invalid_file": ["Sessão inválida", "bad"],
    "access_valid_locally": ["Token no prazo (local)", "ok"],
    "access_expired_refreshable": ["Pode renovar", "warn"],
    "access_expired": ["Token expirado", "bad"],
    "metadata_incomplete": ["Verificar sessão", "warn"]
  };
  function row(profile) {
    const tr = document.createElement("tr");
    tr.appendChild(el("td", "alias", profile.profile || "—"));
    tr.appendChild(el("td", "email", profile.email || "E-mail indisponível"));
    const status = STATE[profile.session_status] || ["Não verificado", "warn"];
    const cell = document.createElement("td");
    cell.appendChild(el("span", "pill " + status[1], status[0]));
    if (profile.recent_account_check) {
      cell.appendChild(el("div", "muted", "Saldo verificado recentemente"));
    }
    tr.appendChild(cell);
    const routing = document.createElement("td");
    routing.appendChild(el("span", "pill " + (profile.eligible === true ? "ok" : "warn"),
      profile.eligible === true ? "Pré-apta" : (profile.enabled === false ? "Desabilitada" : "Indisponível")));
    const explanations = Array.isArray(profile.eligibility_reasons) ? profile.eligibility_reasons : [];
    if (explanations.length) routing.appendChild(
      el("div", "muted", explanations.map(x => ({
        music_live_provider_disabled:"Motor LIVE desligado",
        session_not_present:"Sem sessão salva",
        session_not_locally_current:"Token sem validade local comprovada",
        credit_snapshot_stale:"Saldo antigo",
        insufficient_known_credits:"Sem saldo suficiente",
        account_disabled:"Conta desabilitada",
        auto_selection_not_enabled:"Seleção automática desligada",
        profile_has_pending_or_uncertain_job:"Job pendente ou incerto nesta conta"
      }[x] || x)).join(" · ")));
    tr.appendChild(routing);
    const credits = document.createElement("td");
    credits.className = "number";
    credits.appendChild(el("div", "credits",
      Number.isInteger(profile.credits_remaining) ? fmt(profile.credits_remaining) : "—"));
    credits.appendChild(el("div", "muted",
      profile.credits_remaining === null ? "Não consultado" : (profile.stale ? "Saldo desatualizado" : "Saldo recente")));
    tr.appendChild(credits);
    tr.appendChild(el("td", "", date(profile.checked_at)));
    return tr;
  }
  function show(list, queue) {
    const tbody = byId("accounts-body");
    tbody.replaceChildren();
    const items = Array.isArray(list.profiles) ? list.profiles : [];
    for (const profile of items) tbody.appendChild(row(profile));
    if (!items.length) {
      const tr = el("tr");
      const td = el("td", "", "Nenhum perfil encontrado.");
      td.colSpan = 6; tr.appendChild(td); tbody.appendChild(tr);
    }
    byId("count-profiles").textContent = fmt(items.length);
    byId("count-sessions").textContent = fmt(items.filter(p => p.session_present).length);
    byId("sum-credits").textContent = fmt(items.reduce((sum, p) =>
      sum + ((!p.stale && Number.isInteger(p.credits_remaining)) ? p.credits_remaining : 0), 0));
    const counts = queue?.counts || {};
    const pending = Number(counts.queued || 0);
    const reviewing = Number(counts.needs_review || 0);
    byId("queue-state").textContent = reviewing ? "Revisão" : (pending ? "Pendente" : "Livre");
    byId("queue-detail").textContent = reviewing
      ? reviewing + " tarefa(s) precisam de revisão"
      : pending + " tarefa(s) aguardando";
    byId("music-live-state").textContent = list.live_enabled
      ? "Motor LIVE habilitado. Elegibilidade mostrada é apenas pré-checagem local."
      : "Motor de geração LIVE desligado: nenhuma conta pode ser enviada à fila real.";
    byId("last-update").textContent = "Painel atualizado: " + date(new Date().toISOString());
    byId("metrics").hidden = false;
    byId("account-panel").hidden = false;
  }
  async function refresh() {
    if (!token) return;
    byId("refresh").disabled = true;
    try {
      const [accounts, queue] = await Promise.all([
        getJson("/v1/music/accounts"), getJson("/v1/music/queue")
      ]);
      show(accounts, queue);
      inform("Consulta local concluída. Nenhuma operação Google foi executada.", "success");
    } catch (e) {
      inform(e.message || "Falha de consulta", "error");
      if (String(e.message).includes("não autorizado")) {
        byId("metrics").hidden = true; byId("account-panel").hidden = true;
      }
    } finally {
      byId("refresh").disabled = false;
    }
  }
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    token = tokenInput.value.trim();
    tokenInput.value = "";
    if (!token) { inform("Informe o token local.", "error"); return; }
    byId("disconnect").disabled = false;
    refresh();
  });
  byId("refresh").addEventListener("click", refresh);
  byId("disconnect").addEventListener("click", () => {
    token = "";
    byId("disconnect").disabled = true;
    byId("metrics").hidden = true;
    byId("account-panel").hidden = true;
    byId("accounts-body").replaceChildren();
    inform("Desconectado. O token foi descartado da memória desta página.");
  });
})();