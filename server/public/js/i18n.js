/* ==========================================================================
   Samanvay i18n + accessibility controls (English / मराठी, text size).
   Loaded with `defer` on every page, after js/i18n-strings.js.

   Two translation paths:
   1. Static markup:  <el data-i18n="key">English</el>  (also
      data-i18n-placeholder / -title / -aria-label). Keys live in
      SAMANVAY_STRINGS.keys = { key: { en, mr } }.
   2. Runtime text written by page scripts (status badges, alerts, backend
      messages). Page scripts keep writing their original English; this file
      maps it to plain-language English or Marathi when it lands in the DOM.
      Table: SAMANVAY_STRINGS.dynamic (exact) + .patterns (regex).
   This means no existing page script has to change to be translated.

   Language and text size persist across pages in localStorage.
   ========================================================================== */
(function () {
  'use strict';

  var S = window.SAMANVAY_STRINGS || { keys: {}, dynamic: {}, patterns: [] };
  var LANG_KEY = 'samanvay.lang';
  var SIZE_KEY = 'samanvay.textSize';
  var LANGS = ['en', 'mr'];
  var SIZES = ['small', 'normal', 'large'];

  function store(key, value) {
    try { if (value === undefined) return localStorage.getItem(key); localStorage.setItem(key, value); } catch (e) { return null; }
    return value;
  }

  var current = LANGS.indexOf(store(LANG_KEY)) >= 0 ? store(LANG_KEY) : 'en';

  // ---------- lookup helpers ------------------------------------------------
  function norm(s) { return String(s).replace(/\s+/g, ' ').trim(); }

  function t(key, lang) {
    var e = S.keys[key];
    if (!e) return null;
    return e[lang || current] || e.en;
  }

  // Build a normalised lookup for the runtime table once.
  var DYN = {};
  Object.keys(S.dynamic).forEach(function (src) { DYN[norm(src)] = S.dynamic[src]; });

  function resolveEntry(entry, lang) {
    if (typeof entry === 'string') return t(entry, lang);   // points at a key
    return entry[lang] || entry.en;
  }

  // Translate one runtime string. Returns null when it is unknown (left as is).
  function translateString(src, lang, depth) {
    lang = lang || current;
    depth = depth || 0;
    var n = norm(src);
    if (!n || depth > 4) return null;
    if (Object.prototype.hasOwnProperty.call(DYN, n)) return resolveEntry(DYN[n], lang);

    for (var i = 0; i < S.patterns.length; i++) {
      var p = S.patterns[i];
      var m = n.match(p.re);
      if (!m) continue;
      // `need`: groups that must themselves be known strings, else skip this pattern.
      if (p.need && p.need.some(function (g) { return translateString(m[g] || '', lang, depth + 1) === null; })) continue;
      var tpl = p[lang] || p.en;
      return tpl.replace(/\$(\d)/g, function (_, d) {
        var part = m[+d] || '';
        if (p.tr && p.tr.indexOf(+d) >= 0) {
          var sub = translateString(part, lang, depth + 1);
          return sub === null ? part : sub;
        }
        return part;
      });
    }

    // Backend joins several sentences with "; " — translate each if all known.
    if (n.indexOf('; ') > 0) {
      var parts = n.split('; ').map(function (x) { return translateString(x, lang, depth + 1); });
      if (parts.every(function (x) { return x !== null; })) return parts.join('; ');
    }
    return null;
  }

  // ---------- static [data-i18n] elements -----------------------------------
  // Remember what we last wrote so we never overwrite text a page script has
  // since replaced (e.g. a badge that changed from "Locked" to "Completed").
  var lastWritten = new WeakMap();

  function applyStatic(root) {
    root = root || document;
    var els = Array.prototype.slice.call(root.querySelectorAll('[data-i18n]'));
    if (root.nodeType === 1 && root.hasAttribute('data-i18n')) els.unshift(root);
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      var key = el.getAttribute('data-i18n');
      var val = t(key);
      if (val === null) continue;
      var now = norm(el.textContent);
      // Only replace text we own: our last write, or this key's text in any
      // language. Anything else was written by a page script since — leave it
      // (runtime text is handled by the dynamic table below).
      var owned = (lastWritten.has(el) && now === lastWritten.get(el)) ||
        LANGS.some(function (l) { return now === norm(t(key, l)); });
      if (!owned) continue;
      if (el.tagName === 'TITLE') document.title = val;
      else el.textContent = val;
      lastWritten.set(el, norm(val));
    }
    ['placeholder', 'title', 'aria-label'].forEach(function (attr) {
      var list = (root || document).querySelectorAll('[data-i18n-' + attr + ']');
      for (var j = 0; j < list.length; j++) {
        var v = t(list[j].getAttribute('data-i18n-' + attr));
        if (v !== null) list[j].setAttribute(attr, v);
      }
    });
  }

  // ---------- runtime text nodes --------------------------------------------
  var managed = new Map();   // Text node -> { src, shown }

  function skipNode(node) {
    var p = node.parentElement;
    if (!p) return true;
    if (p.closest('script, style, textarea, [translate="no"]')) return true;
    // Static text still owned by a data-i18n element is handled by applyStatic.
    var owner = p.closest('[data-i18n]');
    if (owner && lastWritten.has(owner) && norm(owner.textContent) === lastWritten.get(owner)) return true;
    return false;
  }

  function renderNode(node, rec) {
    var shown = translateString(rec.src);
    var out = shown === null ? rec.src : rec.src.replace(norm(rec.src), shown);
    rec.shown = out;                       // set first: the observer compares against it
    if (node.nodeValue !== out) node.nodeValue = out;
  }

  function considerTextNode(node) {
    if (!node.nodeValue || !node.nodeValue.trim()) return;
    var rec = managed.get(node);
    if (rec && node.nodeValue === rec.shown) return;      // our own write
    if (skipNode(node)) return;
    var src = node.nodeValue;
    if (translateString(src, 'en') === null) return;      // unknown string
    rec = { src: src, shown: null };
    managed.set(node, rec);
    renderNode(node, rec);
  }

  function scan(root) {
    if (!root) return;
    if (root.nodeType === 3) { considerTextNode(root); return; }
    if (root.nodeType !== 1 && root.nodeType !== 9 && root.nodeType !== 11) return;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var n;
    while ((n = walker.nextNode())) considerTextNode(n);
  }

  function rerenderManaged() {
    managed.forEach(function (rec, node) {
      if (!node.isConnected) { managed.delete(node); return; }
      renderNode(node, rec);
    });
  }

  // Runtime placeholders set by page scripts (login identifier field).
  function applyDynamicAttrs() {
    var inputs = document.querySelectorAll('input[placeholder], textarea[placeholder]');
    for (var i = 0; i < inputs.length; i++) {
      var el = inputs[i];
      if (el.hasAttribute('data-i18n-placeholder')) continue;
      var now = el.getAttribute('placeholder');
      // A page script wrote a new placeholder since our last write -> new source.
      var src = (now === el.getAttribute('data-i18n-shown-placeholder'))
        ? el.getAttribute('data-i18n-src-placeholder') : now;
      var tr = translateString(src);
      if (tr === null) continue;
      el.setAttribute('data-i18n-src-placeholder', src);
      el.setAttribute('data-i18n-shown-placeholder', tr);
      if (now !== tr) el.setAttribute('placeholder', tr);   // no-op writes would loop the observer
    }
  }

  // ---------- public apply ---------------------------------------------------
  function setLang(lang, persist) {
    if (LANGS.indexOf(lang) < 0) lang = 'en';
    current = lang;
    if (persist !== false) store(LANG_KEY, lang);
    document.documentElement.setAttribute('lang', lang);
    applyStatic(document);
    rerenderManaged();
    scan(document.body);
    applyDynamicAttrs();
    var btns = document.querySelectorAll('[data-lang]');
    for (var i = 0; i < btns.length; i++) {
      btns[i].setAttribute('aria-pressed', String(btns[i].getAttribute('data-lang') === lang));
    }
  }

  function setTextSize(size, persist) {
    if (SIZES.indexOf(size) < 0) size = 'normal';
    if (size === 'normal') document.documentElement.removeAttribute('data-text-size');
    else document.documentElement.setAttribute('data-text-size', size);
    if (persist !== false) store(SIZE_KEY, size);
    var btns = document.querySelectorAll('[data-text-size]');
    for (var i = 0; i < btns.length; i++) {
      btns[i].setAttribute('aria-pressed', String(btns[i].getAttribute('data-text-size') === size));
    }
  }

  // ---------- window.alert: translate known runtime messages ----------------
  var nativeAlert = window.alert ? window.alert.bind(window) : null;
  if (nativeAlert) {
    window.alert = function (msg) {
      var s = String(msg);
      var tr = translateString(s);
      return nativeAlert(tr === null ? s : tr);
    };
  }

  // ---------- init -----------------------------------------------------------
  function init() {
    document.addEventListener('click', function (e) {
      var l = e.target.closest && e.target.closest('[data-lang]');
      if (l) { setLang(l.getAttribute('data-lang')); return; }
      var z = e.target.closest && e.target.closest('[data-text-size]');
      if (z) setTextSize(z.getAttribute('data-text-size'));
    });

    setTextSize(store(SIZE_KEY) || 'normal', false);
    setLang(current, false);

    var mo = new MutationObserver(function (records) {
      for (var i = 0; i < records.length; i++) {
        var r = records[i];
        if (r.type === 'characterData') considerTextNode(r.target);
        else if (r.type === 'attributes') applyDynamicAttrs();
        else for (var j = 0; j < r.addedNodes.length; j++) {
          var added = r.addedNodes[j];
          // Markup inserted later by a page script may carry its own data-i18n keys.
          if (added.nodeType === 1) applyStatic(added);
          scan(added);
        }
      }
    });
    mo.observe(document.body, {
      childList: true, subtree: true, characterData: true,
      attributes: true, attributeFilter: ['placeholder']
    });
  }

  window.I18N = {
    t: function (key, lang) { var v = t(key, lang); return v === null ? key : v; },
    translate: function (src, lang) { return translateString(src, lang); },
    // True when a runtime text node is being translated by this file (used by QA checks).
    isRuntimeTranslated: function (node) { var r = managed.get(node); return !!r && translateString(r.src) !== null; },
    lang: function () { return current; },
    setLang: setLang,
    setTextSize: setTextSize
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
