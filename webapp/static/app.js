const state = {
  catalog: null,
  assets: null,
  textureScale: 2,
  jokers: [],
  cards: [],
  selectedJokerIndex: null,
  selectedCardIndex: null,
  backups: [],
};

const el = (id) => document.getElementById(id);

function showToast(message, type = "info", duration = 4000) {
  let container = el("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.setAttribute("aria-live", "polite");
    container.setAttribute("aria-atomic", "false");
    document.body.appendChild(container);
  }

  const allowedTypes = new Set(["success", "error", "warning", "info"]);
  const normalizedType = allowedTypes.has(type) ? type : "info";
  const iconByType = {
    success: "✅",
    error: "❌",
    warning: "⚠️",
    info: "ℹ️",
  };

  const toastNode = document.createElement("div");
  toastNode.className = `toast-item toast-${normalizedType}`;

  const iconNode = document.createElement("span");
  iconNode.className = "toast-icon";
  iconNode.textContent = iconByType[normalizedType];

  const messageNode = document.createElement("span");
  messageNode.className = "toast-message";
  messageNode.textContent = String(message);

  toastNode.appendChild(iconNode);
  toastNode.appendChild(messageNode);
  container.appendChild(toastNode);

  const maxVisibleToasts = 5;
  while (container.children.length > maxVisibleToasts) {
    const oldest = container.firstElementChild;
    if (oldest) {
      oldest.remove();
    } else {
      break;
    }
  }

  const dismiss = () => {
    toastNode.classList.add("toast-leave");
    setTimeout(() => {
      toastNode.remove();
    }, 240);
  };

  setTimeout(dismiss, duration);
}

function toast(message, level = "info") {
  if (typeof level === "boolean") {
    showToast(message, level ? "error" : "success");
    return;
  }
  showToast(message, level || "info");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    const details = payload.details ? `\n${payload.details}` : "";
    throw new Error((payload.error || "Request failed") + details);
  }
  return payload;
}

function setActiveView(viewId) {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === viewId);
  });
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active", view.id === viewId);
  });
}

function fillSelect(node, options, includeNone = true) {
  node.innerHTML = "";
  if (includeNone) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "none";
    node.appendChild(opt);
  }
  options.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item.value;
    opt.textContent = item.label;
    node.appendChild(opt);
  });
}

function renderStickerChecks(container, stickers, values = {}) {
  container.innerHTML = "";
  stickers.forEach((sticker) => {
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.dataset.sticker = sticker;
    checkbox.checked = !!values[sticker];
    label.appendChild(checkbox);
    label.appendChild(document.createTextNode(sticker));
    container.appendChild(label);
  });
}

function readStickerChecks(container) {
  const stickers = {};
  container.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
    stickers[checkbox.dataset.sticker] = checkbox.checked;
  });
  return stickers;
}

function getSelectedItemForArea(area, cardIndex) {
  const source = area === "jokers" ? state.jokers : state.cards;
  return source.find((entry) => entry.index === cardIndex) || null;
}

function changedStickerValues(previous = {}, current = {}) {
  const changed = {};
  Object.keys(current || {}).forEach((key) => {
    if (!!previous[key] !== !!current[key]) {
      changed[key] = !!current[key];
    }
  });
  return changed;
}

function buildModifierPayload(area, cardIndex, prefix) {
  const selected = getSelectedItemForArea(area, cardIndex) || {};
  const payload = {
    area,
    card_index: cardIndex,
    apply_scope:
      prefix === "joker"
        ? el("jokerApplyScope").value
        : el("cardApplyScope").value,
  };

  const uiEdition = el(`${prefix}Edition`).value || "";
  const currentEdition = selected.edition || "";
  if (uiEdition !== currentEdition) {
    payload.edition = uiEdition || null;
  }

  const uiSeal = el(`${prefix}Seal`).value || "";
  const currentSeal = selected.seal || "";
  if (uiSeal !== currentSeal) {
    payload.seal = uiSeal || null;
  }

  const stickerDelta = changedStickerValues(
    selected.stickers || {},
    readStickerChecks(el(`${prefix}Stickers`)),
  );
  if (Object.keys(stickerDelta).length) {
    payload.stickers = stickerDelta;
  }

  return payload;
}

function buildTransformPayload(area, cardIndex) {
  const selected = getSelectedItemForArea(area, cardIndex) || {};
  const payload = {
    area,
    card_index: cardIndex,
    apply_scope: el("cardApplyScope").value,
  };

  const uiSuit = el("cardTransformSuit").value || "";
  const currentSuit = selected.base_suit || "";
  if (uiSuit !== currentSuit) {
    payload.suit = uiSuit || null;
  }

  const uiRank = el("cardTransformRank").value || "";
  const currentRank = selected.base_value || "";
  if (uiRank !== currentRank) {
    payload.rank = uiRank || null;
  }

  const uiEnhancement = el("cardTransformEnhancement").value || "";
  const currentEnhancement = selected.center_id || "";
  if (uiEnhancement !== currentEnhancement) {
    payload.enhancement = uiEnhancement || null;
  }

  return payload;
}

function hasModifierChanges(payload) {
  return (
    Object.prototype.hasOwnProperty.call(payload, "edition") ||
    Object.prototype.hasOwnProperty.call(payload, "seal") ||
    (payload.stickers && Object.keys(payload.stickers).length > 0)
  );
}

function hasTransformChanges(payload) {
  return (
    Object.prototype.hasOwnProperty.call(payload, "suit") ||
    Object.prototype.hasOwnProperty.call(payload, "rank") ||
    Object.prototype.hasOwnProperty.call(payload, "enhancement")
  );
}

function syncEditorControls(prefix, card) {
  if (!state.catalog || !card) {
    return;
  }
  el(`${prefix}Edition`).value = card.edition || "";
  el(`${prefix}Seal`).value = card.seal || "";
  renderStickerChecks(
    el(`${prefix}Stickers`),
    state.catalog.stickers,
    card.stickers || {},
  );
}

function renderCardList(listId, items, selectedIndex, onSelect) {
  const list = el(listId);
  list.innerHTML = "";

  const overlays =
    (state.catalog && state.catalog.assets) ||
    (state.assets && state.assets.overlays) ||
    {};

  const spriteBoxStyle = (sprite, ratio = 0.48) => {
    if (!sprite || !sprite.atlas) {
      return "width:88px;height:120px;background:linear-gradient(145deg,#2b2538,#1a1622);";
    }
    const atlas = sprite.atlas;
    const sheetScale = state.textureScale || 2;
    const frameW = atlas.px * sheetScale;
    const frameH = atlas.py * sheetScale;
    const width = Math.round(frameW * ratio);
    const height = Math.round(frameH * ratio);
    return [`width:${width}px`, `height:${height}px`].join(";");
  };

  const spriteFrameStyle = (sprite, ratio = 0.48) => {
    if (!sprite || !sprite.atlas) {
      return "";
    }
    const atlas = sprite.atlas;
    const sheetScale = state.textureScale || 2;
    const frameW = atlas.px * sheetScale;
    const frameH = atlas.py * sheetScale;
    return [
      `width:${frameW}px`,
      `height:${frameH}px`,
      `background-image:url(/core-assets/${atlas.path})`,
      `background-position:${-sprite.x * frameW}px ${-sprite.y * frameH}px`,
      "background-repeat:no-repeat",
      "image-rendering:auto",
      `transform:scale(${ratio})`,
      "transform-origin:top left",
    ].join(";");
  };

  const badgeFrameStyle = (sprite) => {
    if (!sprite || !sprite.atlas) {
      return "";
    }
    const atlas = sprite.atlas;
    const sheetScale = state.textureScale || 2;
    const frameW = atlas.px * sheetScale;
    const frameH = atlas.py * sheetScale;
    const ratio = Math.min(16 / Math.max(frameW, 1), 16 / Math.max(frameH, 1));
    return [
      `width:${frameW}px`,
      `height:${frameH}px`,
      `background-image:url(/core-assets/${atlas.path})`,
      `background-position:${-sprite.x * frameW}px ${-sprite.y * frameH}px`,
      "background-repeat:no-repeat",
      `transform:scale(${ratio})`,
      "transform-origin:top left",
    ].join(";");
  };

  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = `visual-card ${item.index === selectedIndex ? "selected" : ""}`;
    row.onclick = () => onSelect(item.index);

    const sprite = document.createElement("div");
    sprite.className = "visual-sprite";
    sprite.setAttribute("style", spriteBoxStyle(item.render));

    if (item.render && item.render.atlas) {
      const spriteFrame = document.createElement("div");
      spriteFrame.className = "visual-sprite-frame";
      spriteFrame.setAttribute("style", spriteFrameStyle(item.render));
      sprite.appendChild(spriteFrame);
    }

    const badges = document.createElement("div");
    badges.className = "visual-overlay-badges";

    const editionSprite =
      item.edition && overlays.editions
        ? overlays.editions[item.edition]
        : null;
    if (editionSprite) {
      const badge = document.createElement("div");
      badge.className = "visual-badge";
      badge.title = `Edition: ${item.edition}`;
      const frame = document.createElement("div");
      frame.className = "visual-badge-frame";
      frame.setAttribute("style", badgeFrameStyle(editionSprite));
      badge.appendChild(frame);
      badges.appendChild(badge);
    }

    const sealSprite =
      item.seal && overlays.seals ? overlays.seals[item.seal] : null;
    if (sealSprite) {
      const badge = document.createElement("div");
      badge.className = "visual-badge";
      badge.title = `Seal: ${item.seal}`;
      const frame = document.createElement("div");
      frame.className = "visual-badge-frame";
      frame.setAttribute("style", badgeFrameStyle(sealSprite));
      badge.appendChild(frame);
      badges.appendChild(badge);
    }

    Object.entries(item.stickers || {})
      .filter(([, enabled]) => !!enabled)
      .forEach(([stickerName]) => {
        const stickerSprite =
          overlays.stickers && overlays.stickers[stickerName];
        const badge = document.createElement("div");
        badge.className = "visual-badge";
        badge.title = `Sticker: ${stickerName}`;
        if (stickerSprite) {
          const frame = document.createElement("div");
          frame.className = "visual-badge-frame";
          frame.setAttribute("style", badgeFrameStyle(stickerSprite));
          badge.appendChild(frame);
        } else {
          badge.textContent = "•";
        }
        badges.appendChild(badge);
      });

    sprite.appendChild(badges);

    const title = document.createElement("div");
    title.className = "visual-title";
    title.textContent = `${item.center_name || item.name || item.id || item.key}`;

    row.appendChild(sprite);
    row.appendChild(title);
    list.appendChild(row);
  });
}

async function loadCatalog() {
  const payload = await api("/api/catalog");
  state.catalog = payload.catalog;
  if (state.catalog && state.catalog.assets) {
    state.assets = { overlays: state.catalog.assets };
  }

  const editions = state.catalog.editions.map((entry) => ({
    value: entry.type,
    label: entry.extra ? `${entry.name} (extra: ${entry.extra})` : entry.name,
  }));
  const seals = state.catalog.seals.map((seal) => ({
    value: seal,
    label: seal,
  }));

  fillSelect(el("jokerEdition"), editions, true);
  fillSelect(el("jokerSeal"), seals, true);
  fillSelect(el("cardEdition"), editions, true);
  fillSelect(el("cardSeal"), seals, true);
  fillSelect(el("addJokerEdition"), editions, true);
  fillSelect(el("addJokerSeal"), seals, true);

  renderStickerChecks(el("jokerStickers"), state.catalog.stickers, {});
  renderStickerChecks(el("cardStickers"), state.catalog.stickers, {});
  renderStickerChecks(el("addJokerStickers"), state.catalog.stickers, {});

  fillSelect(
    el("cardTransformSuit"),
    (state.catalog.suits || []).map((value) => ({ value, label: value })),
    true,
  );
  fillSelect(
    el("cardTransformRank"),
    (state.catalog.ranks || []).map((value) => ({ value, label: value })),
    true,
  );
  fillSelect(
    el("cardTransformEnhancement"),
    (state.catalog.enhancements || []).map((entry) => ({
      value: entry.id,
      label: `${entry.name} (${entry.id})`,
    })),
    true,
  );

  const addJokerSelect = el("addJokerSelect");
  addJokerSelect.innerHTML = "";
  state.catalog.jokers.forEach((joker) => {
    const opt = document.createElement("option");
    opt.value = joker.id;
    opt.textContent = `${joker.name} (${joker.id})`;
    addJokerSelect.appendChild(opt);
  });
}

async function loadAssetManifest() {
  const payload = await api("/api/assets");
  state.assets = payload.assets;
  state.textureScale = payload.assets.texture_scale || 2;
}

async function refreshDashboard() {
  const [dashboardPayload, statsPayload] = await Promise.all([
    api("/api/dashboard"),
    api("/api/stats"),
  ]);
  const dashboard = dashboardPayload.dashboard;
  const stats = statsPayload.stats;

  el("dashMoney").textContent = dashboard.money;
  el("dashChips").textContent = dashboard.chips;
  el("dashHands").textContent = dashboard.current_round.hands_left;

  el("moneyInput").value = stats.money;
  el("chipsInput").value = stats.chips;
  el("interestInput").value = stats.interest_cap;
  el("rerollInput").value = stats.reroll_cost;
  el("handsLeftInput").value = stats.hands_left;
  el("discardsLeftInput").value = stats.discards_left;
  el("handSizeInput").value = stats.hand_size;
  el("jokerSlotsInput").value = stats.joker_slots;
  el("consumableSlotsInput").value = stats.consumable_slots;
}

async function refreshJokers() {
  const payload = await api("/api/jokers");
  state.jokers = payload.items;
  if (!state.selectedJokerIndex && state.jokers.length) {
    state.selectedJokerIndex = state.jokers[0].index;
  }
  const onSelectJoker = (index) => {
    state.selectedJokerIndex = index;
    const selected = state.jokers.find((entry) => entry.index === index);
    syncEditorControls("joker", selected);
    renderCardList(
      "jokerList",
      state.jokers,
      state.selectedJokerIndex,
      onSelectJoker,
    );
  };
  renderCardList(
    "jokerList",
    state.jokers,
    state.selectedJokerIndex,
    onSelectJoker,
  );

  const selected = state.jokers.find(
    (entry) => entry.index === state.selectedJokerIndex,
  );
  syncEditorControls("joker", selected);
}

async function refreshCards() {
  const area = el("cardAreaSelect").value;
  const payload = await api(`/api/cards?area=${encodeURIComponent(area)}`);
  state.cards = payload.items;
  if (!state.selectedCardIndex && state.cards.length) {
    state.selectedCardIndex = state.cards[0].index;
  }
  const onSelectCard = (index) => {
    state.selectedCardIndex = index;
    const selected = state.cards.find((entry) => entry.index === index);
    syncEditorControls("card", selected);
    renderCardList(
      "cardList",
      state.cards,
      state.selectedCardIndex,
      onSelectCard,
    );
  };
  renderCardList(
    "cardList",
    state.cards,
    state.selectedCardIndex,
    onSelectCard,
  );

  const selected = state.cards.find(
    (entry) => entry.index === state.selectedCardIndex,
  );
  syncEditorControls("card", selected);
}

async function preview(area, cardIndex, prefix, outputId) {
  if (!cardIndex) {
    toast("Select a card first", true);
    return;
  }
  const payload = buildModifierPayload(area, cardIndex, prefix);
  if (!hasModifierChanges(payload)) {
    el(outputId).textContent = "No property changes selected.";
    return;
  }
  const data = await api("/api/card/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  el(outputId).textContent =
    JSON.stringify(data.preview, null, 2) +
    (data.validation_errors.length
      ? `\n\nValidation Errors:\n- ${data.validation_errors.join("\n- ")}`
      : "\n\nValidation: OK");
}

async function apply(area, cardIndex, prefix) {
  if (!cardIndex) {
    toast("Select a card first", true);
    return;
  }
  const payload = buildModifierPayload(area, cardIndex, prefix);
  if (!hasModifierChanges(payload)) {
    toast("No property changes selected", "warning");
    return;
  }
  const previewData = await api("/api/card/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  const targetCount = previewData.preview?.target_count || 1;
  const ok = window.confirm(
    `Apply changes to ${targetCount} card(s)?\n\n` +
      JSON.stringify(previewData.preview, null, 2),
  );
  if (!ok) {
    return;
  }
  await api("/api/card/apply", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  toast("Changes applied");
}

function compactModifierPreview(modifierPreview) {
  if (!modifierPreview || !modifierPreview.samples) {
    return modifierPreview;
  }

  const compactSamples = modifierPreview.samples.map((sample) => {
    const oldState = (sample.preview && sample.preview.old) || {};
    const newState = (sample.preview && sample.preview.new) || {};

    const changed = {};
    if (oldState.edition !== newState.edition) {
      changed.edition = { from: oldState.edition, to: newState.edition };
    }
    if (oldState.seal !== newState.seal) {
      changed.seal = { from: oldState.seal, to: newState.seal };
    }

    const oldStickers = oldState.stickers || {};
    const newStickers = newState.stickers || {};
    const stickerChanges = {};
    Object.keys(newStickers).forEach((key) => {
      if (oldStickers[key] !== newStickers[key]) {
        stickerChanges[key] = { from: oldStickers[key], to: newStickers[key] };
      }
    });
    if (Object.keys(stickerChanges).length) {
      changed.flags = stickerChanges;
    }

    return {
      index: sample.index,
      changed,
    };
  });

  return {
    scope: modifierPreview.scope,
    target_count: modifierPreview.target_count,
    samples: compactSamples,
  };
}

function compactTransformPreview(transformPreview) {
  if (!transformPreview || !transformPreview.samples) {
    return transformPreview;
  }

  const compactSamples = transformPreview.samples.map((sample) => {
    const current = sample.current || {};
    const next = sample.next || {};
    const changed = {};

    if (current.suit !== next.suit) {
      changed.suit = { from: current.suit, to: next.suit };
    }
    if (current.rank !== next.rank) {
      changed.rank = { from: current.rank, to: next.rank };
    }
    if (current.center_id !== next.center_id) {
      changed.enhancement = {
        from: current.center_id,
        to: next.center_id,
      };
    }

    return {
      index: sample.index,
      changed,
    };
  });

  return {
    scope: transformPreview.scope,
    target_count: transformPreview.target_count,
    samples: compactSamples,
  };
}

async function previewCardEditor(area, cardIndex) {
  if (!cardIndex) {
    toast("Select a card first", true);
    return null;
  }

  const modifierPayload = buildModifierPayload(area, cardIndex, "card");
  const transformPayload = buildTransformPayload(area, cardIndex);

  let modifierResponse = { preview: null, validation_errors: [] };
  if (hasModifierChanges(modifierPayload)) {
    modifierResponse = await api("/api/card/preview", {
      method: "POST",
      body: JSON.stringify(modifierPayload),
    });
  }

  let transformPreview = null;
  if (hasTransformChanges(transformPayload)) {
    const transformResponse = await api("/api/card/transform/preview", {
      method: "POST",
      body: JSON.stringify(transformPayload),
    });
    transformPreview = transformResponse.preview;
  }

  const combined = {
    card_properties: compactModifierPreview(modifierResponse.preview),
    identity_and_enhancement: compactTransformPreview(transformPreview),
    validation_errors: modifierResponse.validation_errors || [],
  };
  el("cardPreview").textContent = JSON.stringify(combined, null, 2);
  return combined;
}

async function applyCardEditor(area, cardIndex) {
  const combinedPreview = await previewCardEditor(area, cardIndex);
  if (!combinedPreview) {
    return;
  }

  const modifierPayload = buildModifierPayload(area, cardIndex, "card");
  const transformPayload = buildTransformPayload(area, cardIndex);
  const hasModifier = hasModifierChanges(modifierPayload);
  const hasTransform = hasTransformChanges(transformPayload);

  if (!hasModifier && !hasTransform) {
    toast("No changes selected", "warning");
    return;
  }

  const modifierTargets = combinedPreview.card_properties?.target_count || 1;
  const transformTargets =
    combinedPreview.identity_and_enhancement?.target_count || 0;
  const ok = window.confirm(
    `Apply changes?\n- Modifiers: ${modifierTargets} card(s)\n- Transform: ${transformTargets} card(s)\n\n` +
      JSON.stringify(combinedPreview, null, 2),
  );
  if (!ok) {
    return;
  }

  if (hasModifier) {
    await api("/api/card/apply", {
      method: "POST",
      body: JSON.stringify(modifierPayload),
    });
  }

  if (hasTransform) {
    await api("/api/card/transform/apply", {
      method: "POST",
      body: JSON.stringify(transformPayload),
    });
  }

  toast("Changes applied");
}

async function saveChanges() {
  const res = await fetch("/api/download-save");
  if (!res.ok) {
    let msg = "Failed to download save.";
    try {
      const js = await res.json();
      msg = js.error || msg;
    } catch (e) {}
    throw new Error(msg);
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.style.display = "none";
  a.href = url;
  a.download = "save.jkr";
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  a.remove();
  toast("Save changes downloaded successfully!");
}

async function refreshBackupHistory() {
  const payload = await api("/api/backups");
  state.backups = payload.items || [];

  const select = el("backupHistorySelect");
  select.innerHTML = "";

  const noneOption = document.createElement("option");
  noneOption.value = "";
  noneOption.textContent = "Latest backup";
  select.appendChild(noneOption);

  state.backups.forEach((entry) => {
    const opt = document.createElement("option");
    opt.value = entry.path;
    const timestamp = entry.created_at || "unknown time";
    opt.textContent = `${entry.name} (${timestamp})`;
    select.appendChild(opt);
  });
}

function numberValue(id) {
  return Number.parseInt(el(id).value || "0", 10);
}

function bindEvents() {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => setActiveView(btn.dataset.view));
  });

  el("uploadSaveBtn").addEventListener("click", () => {
    el("fileUploadInput").click();
  });

  el("fileUploadInput").addEventListener("change", async (e) => {
    if (!e.target.files.length) return;
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
      el("savePath").textContent = "Uploading...";
      const res = await fetch("/api/upload-save", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || "Failed to upload.");
      }
      toast("Save file uploaded and loaded!");
      el("savePath").textContent = file.name;
      await refreshAll();
    } catch (err) {
      toast(err.message, true);
      el("savePath").textContent = "Upload failed";
    }
    el("fileUploadInput").value = "";
  });

  el("saveChangesBtn").addEventListener("click", async () => {
    try {
      await saveChanges();
    } catch (err) {
      toast(err.message, true);
    }
  });

  el("undoLastChangeBtn").addEventListener("click", async () => {
    try {
      await api("/api/undo-last-change", { method: "POST", body: "{}" });
      await refreshDashboard();
      await refreshJokers();
      await refreshCards();
      toast("Last change undone");
    } catch (err) {
      toast(err.message, true);
    }
  });

  el("viewBackupHistoryBtn").addEventListener("click", async () => {
    try {
      await refreshBackupHistory();
      toast(`Backups: ${state.backups.length}`);
    } catch (err) {
      toast(err.message, true);
    }
  });

  el("restoreBackupBtn").addEventListener("click", async () => {
    try {
      const selectedBackupPath = el("backupHistorySelect").value || null;
      const targetLabel =
        selectedBackupPath ||
        (state.backups[0] && state.backups[0].name) ||
        "latest backup";
      const ok = window.confirm(
        `Are you sure you want to restore backup?\n\nTarget: ${targetLabel}\n\nThis will replace current save content.`,
      );
      if (!ok) {
        return;
      }

      await api("/api/restore-backup", {
        method: "POST",
        body: JSON.stringify({ backup_path: selectedBackupPath }),
      });

      await refreshDashboard();
      await refreshJokers();
      await refreshCards();
      await refreshBackupHistory();
      toast("Backup restored");
    } catch (err) {
      toast(err.message, true);
    }
  });

  el("applyResourcesBtn").addEventListener("click", async () => {
    try {
      await api("/api/stats/resources", {
        method: "POST",
        body: JSON.stringify({
          money: numberValue("moneyInput"),
          chips: numberValue("chipsInput"),
          interest_cap: numberValue("interestInput"),
          reroll_cost: numberValue("rerollInput"),
          hands_left: numberValue("handsLeftInput"),
          discards_left: numberValue("discardsLeftInput"),
        }),
      });
      await refreshDashboard();
      toast("Resources updated");
    } catch (err) {
      toast(err.message, true);
    }
  });

  el("applyCapacitiesBtn").addEventListener("click", async () => {
    try {
      await api("/api/stats/capacities", {
        method: "POST",
        body: JSON.stringify({
          hand_size: numberValue("handSizeInput"),
          joker_slots: numberValue("jokerSlotsInput"),
          consumable_slots: numberValue("consumableSlotsInput"),
        }),
      });
      await refreshDashboard();
      toast("Capacities updated");
    } catch (err) {
      toast(err.message, true);
    }
  });

  el("refreshJokersBtn").addEventListener("click", async () => {
    try {
      await refreshJokers();
    } catch (err) {
      toast(err.message, true);
    }
  });

  el("previewJokerBtn").addEventListener("click", async () => {
    try {
      await preview(
        "jokers",
        state.selectedJokerIndex,
        "joker",
        "jokerPreview",
      );
    } catch (err) {
      toast(err.message, true);
    }
  });

  el("applyJokerBtn").addEventListener("click", async () => {
    try {
      await apply("jokers", state.selectedJokerIndex, "joker");
      await refreshJokers();
    } catch (err) {
      toast(err.message, true);
    }
  });

  el("removeJokerBtn").addEventListener("click", async () => {
    if (!state.selectedJokerIndex) {
      return toast("Select a joker first", true);
    }
    try {
      await api("/api/remove-joker", {
        method: "POST",
        body: JSON.stringify({ card_index: state.selectedJokerIndex }),
      });
      state.selectedJokerIndex = null;
      await refreshJokers();
      toast("Joker removed");
    } catch (err) {
      toast(err.message, true);
    }
  });

  el("addJokerBtn").addEventListener("click", async () => {
    try {
      const centerId = el("addJokerSelect").value;
      if (!centerId) {
        toast("Select a Joker ID first", true);
        return;
      }

      const data = await api("/api/add-joker", {
        method: "POST",
        body: JSON.stringify({
          center_id: centerId,
          edition: el("addJokerEdition").value || null,
          seal: el("addJokerSeal").value || null,
          stickers: readStickerChecks(el("addJokerStickers")),
        }),
      });
      if (data.new_item && data.new_item.index) {
        state.selectedJokerIndex = data.new_item.index;
      }
      await refreshJokers();
      toast("Joker added");
    } catch (err) {
      toast(err.message, true);
    }
  });

  el("refreshCardsBtn").addEventListener("click", async () => {
    try {
      await refreshCards();
    } catch (err) {
      toast(err.message, true);
    }
  });

  el("cardAreaSelect").addEventListener("change", async () => {
    state.selectedCardIndex = null;
    try {
      await refreshCards();
    } catch (err) {
      toast(err.message, true);
    }
  });

  el("previewCardBtn").addEventListener("click", async () => {
    try {
      await previewCardEditor(
        el("cardAreaSelect").value,
        state.selectedCardIndex,
      );
    } catch (err) {
      toast(err.message, true);
    }
  });

  el("applyCardBtn").addEventListener("click", async () => {
    try {
      await applyCardEditor(
        el("cardAreaSelect").value,
        state.selectedCardIndex,
      );
      await refreshCards();
    } catch (err) {
      toast(err.message, true);
    }
  });

  el("removeCardBtn").addEventListener("click", async () => {
    if (!state.selectedCardIndex) {
      return toast("Select a card first", true);
    }
    try {
      await api("/api/remove-card", {
        method: "POST",
        body: JSON.stringify({
          area: el("cardAreaSelect").value,
          card_index: state.selectedCardIndex,
        }),
      });
      state.selectedCardIndex = null;
      await refreshCards();
      toast("Card removed");
    } catch (err) {
      toast(err.message, true);
    }
  });

  document.querySelectorAll(".cheat-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        const data = await api("/api/god-mode", {
          method: "POST",
          body: JSON.stringify({ action: button.dataset.action }),
        });
        await refreshDashboard();
        await refreshJokers();
        await refreshCards();
        toast(data.message || "Action applied");
      } catch (err) {
        toast(err.message, true);
      }
    });
  });
}

async function bootstrap() {
  bindEvents();
  try {
    const health = await api("/api/health");
    await loadAssetManifest();
    await loadCatalog();
    if (health.save_path) {
      el("savePath").textContent = health.save_path;
      await refreshDashboard();
      await refreshJokers();
      await refreshCards();
      await refreshBackupHistory();
    } else {
      el("savePath").textContent = "No save file loaded";
    }
  } catch (err) {
    toast(err.message, true);
  }
}

bootstrap();
