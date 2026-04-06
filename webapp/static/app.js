const state = {
  catalog: null,
  assets: null,
  textureScale: 2,
  jokers: [],
  cards: [],
  voucherCatalog: [],
  voucherOwned: [],
  selectedVoucherCatalogIndex: null,
  consumeableCatalog: [],
  consumeableOwned: [],
  selectedConsumeableCatalogIndex: null,
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

const APPLY_SCOPE_LABELS = {
  selected: "Selected only",
  same_id: "Same ID",
  all: "All",
};

function formatApplyScope(scope) {
  return APPLY_SCOPE_LABELS[scope] || scope || APPLY_SCOPE_LABELS.selected;
}

function showConfirmDialog(options = {}) {
  const {
    title = "Confirm Action",
    message = "Are you sure you want to continue?",
    details = [],
    confirmText = "Confirm",
    cancelText = "Cancel",
    tone = "warning",
  } = options;

  return new Promise((resolve) => {
    const existing = document.querySelector(".confirm-overlay");
    if (existing) {
      existing.remove();
    }

    const overlay = document.createElement("div");
    overlay.className = "confirm-overlay";

    const dialog = document.createElement("div");
    dialog.className = `confirm-dialog confirm-${tone}`;
    dialog.setAttribute("role", "alertdialog");
    dialog.setAttribute("aria-modal", "true");

    const head = document.createElement("div");
    head.className = "confirm-head";

    const icon = document.createElement("span");
    icon.className = "confirm-icon";
    icon.textContent = tone === "danger" ? "!" : "?";

    const titleNode = document.createElement("h4");
    titleNode.className = "confirm-title";
    titleNode.textContent = title;

    head.appendChild(icon);
    head.appendChild(titleNode);

    const messageNode = document.createElement("p");
    messageNode.className = "confirm-message";
    messageNode.textContent = message;

    dialog.appendChild(head);
    dialog.appendChild(messageNode);

    const cleanedDetails = details
      .map((line) => String(line || "").trim())
      .filter(Boolean);

    if (cleanedDetails.length) {
      const detailList = document.createElement("ul");
      detailList.className = "confirm-details";

      cleanedDetails.forEach((line) => {
        const li = document.createElement("li");
        li.textContent = line;
        detailList.appendChild(li);
      });

      dialog.appendChild(detailList);
    }

    const actions = document.createElement("div");
    actions.className = "confirm-actions";

    const cancelBtn = document.createElement("button");
    cancelBtn.type = "button";
    cancelBtn.className = "confirm-btn cancel";
    cancelBtn.textContent = cancelText;

    const confirmBtn = document.createElement("button");
    confirmBtn.type = "button";
    confirmBtn.className = "confirm-btn confirm";
    confirmBtn.textContent = confirmText;

    actions.appendChild(cancelBtn);
    actions.appendChild(confirmBtn);
    dialog.appendChild(actions);
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    let settled = false;

    const finish = (result) => {
      if (settled) {
        return;
      }
      settled = true;
      document.removeEventListener("keydown", onKeydown);
      overlay.classList.add("is-closing");
      setTimeout(() => {
        overlay.remove();
        resolve(result);
      }, 140);
    };

    const onKeydown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        finish(false);
      } else if (event.key === "Enter") {
        event.preventDefault();
        finish(true);
      }
    };

    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) {
        finish(false);
      }
    });

    cancelBtn.addEventListener("click", () => finish(false));
    confirmBtn.addEventListener("click", () => finish(true));
    document.addEventListener("keydown", onKeydown);
    confirmBtn.focus();
  });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function api(path, options = {}) {
  let response = null;
  const maxAttempts = 4;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    response = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });

    if (response.status !== 503 || attempt === maxAttempts) {
      break;
    }

    await sleep(700 * attempt);
  }

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
    payload.edition = uiEdition;
  }

  const sealSelect = el(`${prefix}Seal`);
  if (prefix !== "joker" && sealSelect) {
    const uiSeal = sealSelect.value || "";
    const currentSeal = selected.seal || "";
    if (uiSeal !== currentSeal) {
      payload.seal = uiSeal;
    }
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
  const enhancementIds = new Set(
    (state.catalog?.enhancements || []).map((entry) => entry.id),
  );
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
  const currentEnhancement = enhancementIds.has(selected.center_id)
    ? selected.center_id
    : "";
  if (uiEnhancement !== currentEnhancement) {
    payload.enhancement = uiEnhancement;
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
  if (!state.catalog) {
    return;
  }
  const selected = card || {};
  el(`${prefix}Edition`).value = selected.edition || "";
  const sealSelect = el(`${prefix}Seal`);
  if (sealSelect) {
    sealSelect.value = selected.seal || "";
  }
  renderStickerChecks(
    el(`${prefix}Stickers`),
    state.catalog.stickers,
    selected.stickers || {},
  );

  if (prefix === "card") {
    el("cardTransformSuit").value = selected.base_suit || "";
    el("cardTransformRank").value = selected.base_value || "";

    const enhancementIds = new Set(
      (state.catalog?.enhancements || []).map((entry) => entry.id),
    );
    el("cardTransformEnhancement").value = enhancementIds.has(
      selected.center_id,
    )
      ? selected.center_id
      : "";
  }
}

function renderCardList(listId, items, selectedIndex, onSelect) {
  const list = el(listId);
  list.innerHTML = "";

  const overlays =
    (state.catalog && state.catalog.assets) ||
    (state.assets && state.assets.overlays) ||
    {};

  const atlasScale = (atlas) => {
    if (atlas && atlas.path) {
      const match = String(atlas.path).match(/\/(\d+)x\//);
      if (match) {
        const parsed = Number.parseInt(match[1], 10);
        if (Number.isFinite(parsed) && parsed > 0) {
          return parsed;
        }
      }
    }
    return state.textureScale || 2;
  };

  const spriteBoxStyle = (sprite, ratio = 0.56) => {
    if (!sprite || !sprite.atlas) {
      return "width:96px;height:132px;background:linear-gradient(145deg,#233246,#151f2d);";
    }
    const atlas = sprite.atlas;
    const sheetScale = atlasScale(atlas);
    const frameW = atlas.px * sheetScale;
    const frameH = atlas.py * sheetScale;
    const width = Math.round(frameW * ratio);
    const height = Math.round(frameH * ratio);
    return [`width:${width}px`, `height:${height}px`].join(";");
  };

  const spriteFrameStyle = (sprite, ratio = 0.56) => {
    if (!sprite || !sprite.atlas) {
      return "";
    }
    const atlas = sprite.atlas;
    const sheetScale = atlasScale(atlas);
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

  const badgeFrameStyle = (sprite, boxSize = 20) => {
    if (!sprite || !sprite.atlas) {
      return "";
    }
    const atlas = sprite.atlas;
    const sheetScale = atlasScale(atlas);
    const frameW = atlas.px * sheetScale;
    const frameH = atlas.py * sheetScale;
    const ratio = Math.min(
      boxSize / Math.max(frameW, 1),
      boxSize / Math.max(frameH, 1),
    );
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

  const editionClassFor = (editionType) => {
    const normalized = String(editionType || "").toLowerCase();
    if (normalized === "foil") return "edition-foil";
    if (normalized === "holo") return "edition-holo";
    if (normalized === "polychrome") return "edition-polychrome";
    if (normalized === "negative") return "edition-negative";
    return "";
  };

  const collectionSets = new Set([
    "Joker",
    "Voucher",
    "Tarot",
    "Planet",
    "Spectral",
    "Booster",
  ]);

  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = `visual-card ${item.index === selectedIndex ? "selected" : ""}`;
    row.onclick = () => onSelect(item.index);

    const sprite = document.createElement("div");
    sprite.className = "visual-sprite";
    sprite.setAttribute("style", spriteBoxStyle(item.render));

    const enhancementSprite =
      item.center_set === "Enhanced" && item.center_id && overlays.enhancements
        ? overlays.enhancements[item.center_id]
        : null;
    if (enhancementSprite) {
      const enhancementFrame = document.createElement("div");
      enhancementFrame.className =
        "visual-sprite-frame visual-enhancement-overlay";
      enhancementFrame.title = `Enhancement: ${item.center_name || item.center_id}`;
      enhancementFrame.setAttribute(
        "style",
        spriteFrameStyle(enhancementSprite),
      );
      sprite.appendChild(enhancementFrame);
    }

    if (item.render && item.render.atlas) {
      const spriteFrame = document.createElement("div");
      spriteFrame.className = "visual-sprite-frame visual-sprite-base";
      spriteFrame.setAttribute("style", spriteFrameStyle(item.render));
      sprite.appendChild(spriteFrame);
    }

    const editionClass = editionClassFor(item.edition);
    if (editionClass) {
      sprite.classList.add(editionClass);
      const editionOverlay = document.createElement("div");
      editionOverlay.className = `visual-edition-overlay ${editionClass}`;
      sprite.appendChild(editionOverlay);
    }

    const sealSprite =
      item.seal && overlays.seals ? overlays.seals[item.seal] : null;
    if (sealSprite) {
      const sealFrame = document.createElement("div");
      sealFrame.className = "visual-sprite-frame visual-seal-overlay";
      sealFrame.title = `Seal: ${item.seal}`;
      sealFrame.setAttribute("style", spriteFrameStyle(sealSprite));
      sprite.appendChild(sealFrame);
    }

    const badges = document.createElement("div");
    badges.className = "visual-overlay-badges";

    Object.entries(item.stickers || {})
      .filter(([, enabled]) => !!enabled)
      .forEach(([stickerName]) => {
        const stickerSprite =
          overlays.stickers && overlays.stickers[stickerName];
        const badge = document.createElement("div");
        badge.className = "visual-badge badge-sticker";
        badge.title = `Sticker: ${stickerName}`;
        if (stickerSprite) {
          const frame = document.createElement("div");
          frame.className = "visual-badge-frame";
          frame.setAttribute("style", badgeFrameStyle(stickerSprite, 18));
          badge.appendChild(frame);
        } else {
          badge.textContent = "•";
        }
        badges.appendChild(badge);
      });

    if (badges.children.length) {
      sprite.appendChild(badges);
    }

    const cardFaceName =
      item.base_value && item.base_suit
        ? `${item.base_value} ${item.base_suit}`
        : "";
    const preferCenterName = collectionSets.has(String(item.center_set || ""));
    const titleText = preferCenterName
      ? item.center_name || item.name || item.id || item.key || cardFaceName
      : cardFaceName || item.center_name || item.name || item.id || item.key;

    const title = document.createElement("div");
    title.className = "visual-title";
    title.textContent = titleText;

    const chipRow = document.createElement("div");
    chipRow.className = "visual-chip-row";
    if (item.center_set === "Enhanced") {
      const chip = document.createElement("span");
      chip.className = "visual-chip enhancement";
      chip.textContent = `Enhancement: ${item.center_name || item.center_id}`;
      chipRow.appendChild(chip);
    }
    if (item.edition) {
      const chip = document.createElement("span");
      chip.className = "visual-chip edition";
      chip.textContent = `Edition: ${item.edition}`;
      chipRow.appendChild(chip);
    }
    if (item.seal) {
      const chip = document.createElement("span");
      chip.className = "visual-chip seal";
      chip.textContent = `Seal: ${item.seal}`;
      chipRow.appendChild(chip);
    }

    row.title = title.textContent;

    row.appendChild(sprite);
    row.appendChild(title);
    if (chipRow.children.length) {
      row.appendChild(chipRow);
    }
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
  fillSelect(el("cardEdition"), editions, true);
  fillSelect(el("cardSeal"), seals, true);
  fillSelect(el("addJokerEdition"), editions, true);

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

function consumeableCatalogToVisualItems(items) {
  return (items || []).map((entry, index) => ({
    index: index + 1,
    key: entry.id,
    id: entry.id,
    center_id: entry.id,
    center_name: entry.name,
    center_set: entry.set,
    render: entry.render || null,
    stickers: {},
  }));
}

function voucherCatalogToVisualItems(items) {
  return (items || []).map((entry, index) => ({
    index: index + 1,
    key: entry.id,
    id: entry.id,
    center_id: entry.id,
    center_name: entry.name,
    center_set: "Voucher",
    render: entry.render || null,
    enabled: !!entry.enabled,
    stickers: {},
  }));
}

function normalizeConsumeableSetKey(raw) {
  const value = String(raw || "")
    .trim()
    .toLowerCase();

  if (value === "tarot" || value === "tarots") {
    return "tarot";
  }
  if (value === "planet" || value === "planets") {
    return "planet";
  }
  if (value === "spectral" || value === "spectrals") {
    return "spectral";
  }
  return "tarot";
}

function consumeableSetLabel(setKey) {
  if (setKey === "planet") {
    return "Planet Cards";
  }
  if (setKey === "spectral") {
    return "Spectral Cards";
  }
  return "Tarot Cards";
}

async function refreshVoucherCatalog() {
  const listNode = el("voucherCatalogList");
  const ownedNode = el("voucherOwnedList");
  if (!listNode || !ownedNode) {
    return;
  }

  const selectedVoucher = state.voucherCatalog.find(
    (entry) => entry.index === state.selectedVoucherCatalogIndex,
  );
  const previousVoucherId = selectedVoucher ? selectedVoucher.center_id : "";

  const payload = await api("/api/vouchers");
  state.voucherCatalog = voucherCatalogToVisualItems(payload.items || []);
  state.voucherOwned = state.voucherCatalog.filter((entry) => !!entry.enabled);

  if (!state.voucherCatalog.length) {
    state.selectedVoucherCatalogIndex = null;
    listNode.innerHTML =
      '<div class="muted">No vouchers found in catalog.</div>';
  } else {
    if (previousVoucherId) {
      const kept = state.voucherCatalog.find(
        (entry) => entry.center_id === previousVoucherId,
      );
      state.selectedVoucherCatalogIndex = kept ? kept.index : null;
    }

    if (
      !state.selectedVoucherCatalogIndex ||
      !state.voucherCatalog.some(
        (entry) => entry.index === state.selectedVoucherCatalogIndex,
      )
    ) {
      state.selectedVoucherCatalogIndex = state.voucherCatalog[0].index;
    }

    const onSelect = (index) => {
      state.selectedVoucherCatalogIndex = index;
      renderCardList(
        "voucherCatalogList",
        state.voucherCatalog,
        state.selectedVoucherCatalogIndex,
        onSelect,
      );
    };

    renderCardList(
      "voucherCatalogList",
      state.voucherCatalog,
      state.selectedVoucherCatalogIndex,
      onSelect,
    );
  }

  if (!state.voucherOwned.length) {
    ownedNode.innerHTML =
      '<div class="muted">No vouchers unlocked in this save.</div>';
  } else {
    renderCardList("voucherOwnedList", state.voucherOwned, null, () => {});
  }

  const catalogStatsNode = el("voucherCatalogStats");
  if (catalogStatsNode) {
    catalogStatsNode.textContent = `Voucher pool: ${state.voucherCatalog.length} total`;
  }

  const ownedStatsNode = el("voucherOwnedStats");
  if (ownedStatsNode) {
    ownedStatsNode.textContent = `Unlocked: ${state.voucherOwned.length}/${state.voucherCatalog.length}`;
  }
}

async function refreshConsumeableCatalog() {
  const groupSelect = el("consumeableSetSelect");
  const listNode = el("consumeableCatalogList");
  if (!groupSelect || !listNode) {
    return;
  }

  const setKey = normalizeConsumeableSetKey(groupSelect.value || "tarot");
  const payload = await api(
    `/api/consumeables/catalog?set=${encodeURIComponent(setKey)}`,
  );
  state.consumeableCatalog = consumeableCatalogToVisualItems(
    payload.items || [],
  );

  if (!state.consumeableCatalog.length) {
    state.selectedConsumeableCatalogIndex = null;
    listNode.innerHTML =
      '<div class="muted">No cards available in this pool.</div>';
  } else {
    if (
      !state.selectedConsumeableCatalogIndex ||
      !state.consumeableCatalog.some(
        (entry) => entry.index === state.selectedConsumeableCatalogIndex,
      )
    ) {
      state.selectedConsumeableCatalogIndex = state.consumeableCatalog[0].index;
    }

    const onSelect = (index) => {
      state.selectedConsumeableCatalogIndex = index;
      renderCardList(
        "consumeableCatalogList",
        state.consumeableCatalog,
        state.selectedConsumeableCatalogIndex,
        onSelect,
      );
    };

    renderCardList(
      "consumeableCatalogList",
      state.consumeableCatalog,
      state.selectedConsumeableCatalogIndex,
      onSelect,
    );
  }

  const statNode = el("consumeablePoolStats");
  if (statNode) {
    statNode.textContent = `Showing ${state.consumeableCatalog.length} ${consumeableSetLabel(setKey)}`;
  }
}

async function refreshOwnedConsumeables() {
  const listNode = el("consumeableOwnedList");
  if (!listNode) {
    return;
  }

  const payload = await api("/api/cards?area=consumeables");
  state.consumeableOwned = payload.items || [];

  if (!state.consumeableOwned.length) {
    listNode.innerHTML =
      '<div class="muted">No consumables in this save.</div>';
  } else {
    renderCardList(
      "consumeableOwnedList",
      state.consumeableOwned,
      null,
      () => {},
    );
  }

  const statNode = el("consumeableOwnedStats");
  if (statNode) {
    statNode.textContent = `Current consumables: ${state.consumeableOwned.length}`;
  }
}

async function refreshAll() {
  await loadAssetManifest();
  await loadCatalog();
  await refreshDashboard();
  await refreshJokers();
  await refreshCards();
  await refreshBackupHistory();
  await refreshVoucherCatalog();
  await refreshConsumeableCatalog();
  await refreshOwnedConsumeables();
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
  const ok = await showConfirmDialog({
    title: "Apply Changes",
    message: "Are you sure you want to apply these updates?",
    details: [
      `Target cards: ${targetCount}`,
      `Scope: ${formatApplyScope(payload.apply_scope)}`,
    ],
    confirmText: "Apply",
    cancelText: "Cancel",
    tone: "warning",
  });
  if (!ok) {
    return;
  }
  await api("/api/card/apply", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  toast(`Applied successfully to ${targetCount} card(s)`);
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
  const ok = await showConfirmDialog({
    title: "Apply Card Changes",
    message: "Confirm to apply selected card updates.",
    details: [
      `Card properties: ${hasModifier ? `${modifierTargets} card(s)` : "No changes"}`,
      `Identity/Enhancement: ${hasTransform ? `${transformTargets} card(s)` : "No changes"}`,
      `Scope: ${formatApplyScope(modifierPayload.apply_scope)}`,
    ],
    confirmText: "Apply",
    cancelText: "Cancel",
    tone: "warning",
  });
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

  const modifierSummary = hasModifier
    ? `${modifierTargets} properties`
    : "0 properties";
  const transformSummary = hasTransform
    ? `${transformTargets} transforms`
    : "0 transforms";
  toast(`Applied: ${modifierSummary}, ${transformSummary}`);
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
  document.querySelectorAll(".nav-btn[data-view]").forEach((btn) => {
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
        const details = data.details ? `\n${data.details}` : "";
        throw new Error((data.error || "Failed to upload.") + details);
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

  const consumeableSetSelect = el("consumeableSetSelect");
  if (consumeableSetSelect) {
    consumeableSetSelect.addEventListener("change", async () => {
      state.selectedConsumeableCatalogIndex = null;
      try {
        await refreshConsumeableCatalog();
      } catch (err) {
        toast(err.message, true);
      }
    });
  }

  const refreshConsumeablePoolBtn = el("refreshConsumeablePoolBtn");
  if (refreshConsumeablePoolBtn) {
    refreshConsumeablePoolBtn.addEventListener("click", async () => {
      try {
        await refreshConsumeableCatalog();
      } catch (err) {
        toast(err.message, true);
      }
    });
  }

  const refreshVoucherBtn = el("refreshVoucherBtn");
  if (refreshVoucherBtn) {
    refreshVoucherBtn.addEventListener("click", async () => {
      try {
        await refreshVoucherCatalog();
      } catch (err) {
        toast(err.message, true);
      }
    });
  }

  const refreshConsumeablesBtn = el("refreshConsumeablesBtn");
  if (refreshConsumeablesBtn) {
    refreshConsumeablesBtn.addEventListener("click", async () => {
      try {
        await refreshOwnedConsumeables();
      } catch (err) {
        toast(err.message, true);
      }
    });
  }

  const addConsumeableBtn = el("addConsumeableBtn");
  if (addConsumeableBtn) {
    addConsumeableBtn.addEventListener("click", async () => {
      try {
        const selected = state.consumeableCatalog.find(
          (entry) => entry.index === state.selectedConsumeableCatalogIndex,
        );
        if (!selected) {
          toast("Select a consumable card first", "warning");
          return;
        }

        const data = await api("/api/consumeables/add", {
          method: "POST",
          body: JSON.stringify({ center_id: selected.center_id }),
        });

        await refreshOwnedConsumeables();
        if (
          el("cardAreaSelect") &&
          el("cardAreaSelect").value === "consumeables"
        ) {
          await refreshCards();
        }
        toast(data.message || `Added consumable: ${selected.center_name}`);
      } catch (err) {
        toast(err.message, true);
      }
    });
  }

  const unlockVoucherBtn = el("unlockVoucherBtn");
  if (unlockVoucherBtn) {
    unlockVoucherBtn.addEventListener("click", async () => {
      try {
        const selectedVoucher = state.voucherCatalog.find(
          (entry) => entry.index === state.selectedVoucherCatalogIndex,
        );
        if (!selectedVoucher) {
          toast("Select a voucher first", "warning");
          return;
        }

        const data = await api("/api/voucher/set", {
          method: "POST",
          body: JSON.stringify({
            voucher_key: selectedVoucher.center_id,
            enabled: true,
          }),
        });

        await refreshVoucherCatalog();
        toast(data.message || "Voucher updated");
      } catch (err) {
        toast(err.message, true);
      }
    });
  }

  const unlockAllVouchersBtn = el("unlockAllVouchersBtn");
  if (unlockAllVouchersBtn) {
    unlockAllVouchersBtn.addEventListener("click", async () => {
      try {
        const data = await api("/api/god-mode", {
          method: "POST",
          body: JSON.stringify({ action: "unlock_vouchers" }),
        });
        await refreshVoucherCatalog();
        toast(data.message || "Unlocked all vouchers");
      } catch (err) {
        toast(err.message, true);
      }
    });
  }

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
    if (health.save_path) {
      el("savePath").textContent = health.save_path;
      await refreshAll();
    } else {
      el("savePath").textContent = "No save file loaded";
    }
  } catch (err) {
    toast(err.message, true);
  }
}

bootstrap();
