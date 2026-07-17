#!/usr/bin/env python3
"""Browser QA for local HTML decks.

Checks the runtime contract, routing, staged reveals, source modals, media
loading, console errors, screenshots, and visible content bounds. Requires Playwright:
  python -m pip install playwright
  python -m playwright install chromium
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CONTROLLED_STEP_CONTRACT = "fragment-v1"
CONTROLLED_STEP_SELECTOR = ".fragment"
TEXT_COLLISION_GAP_PX = 1.0
TEXT_COLLISION_FONT_METRIC_SLACK_PX = 0.25
ANCESTOR_CLIP_TOLERANCE_PX = 0.5
DESIGN_CANVAS_WIDTH = 1600
DESIGN_CANVAS_HEIGHT = 900
CANVAS_TOLERANCE_RATIO = 0.005


CONTROLLED_STEP_CHECK = f"""() => {{
  const deck = document.querySelector('.deck');
  const declared = deck?.getAttribute('data-taohtml-step-contract');
  const contract = declared || '{CONTROLLED_STEP_CONTRACT}';
  const pages = [...document.querySelectorAll('.slide')].map((slide, index) => {{
    const nodes = [...slide.querySelectorAll('{CONTROLLED_STEP_SELECTOR}')];
    const steps = nodes.reduce((maximum, node) => {{
      const normalized = Number.parseInt(node.dataset.taohtmlStep || '', 10);
      const authored = Number.parseInt(node.dataset.step || '', 10);
      return Math.max(maximum, Number.isInteger(normalized) ? normalized : authored || 0);
    }}, 0);
    return {{ page: index + 1, controlled_nodes: nodes.length, controlled_steps: steps }};
  }});
  return {{
    contract,
    declared: Boolean(declared),
    supported: contract === '{CONTROLLED_STEP_CONTRACT}',
    initial_mode: deck?.dataset.mode === 'reading' ? 'reading' : 'presentation',
    controlled_nodes: pages.reduce((total, item) => total + item.controlled_nodes, 0),
    controlled_steps: pages.reduce((total, item) => total + item.controlled_steps, 0),
    pages,
  }};
}}"""


CANVAS_COVERAGE_CHECK = f"""() => {{
  const deck = document.querySelector('.deck');
  const slide = document.querySelector('.slide.active');
  if (!deck || !slide) return {{ valid: false, error: 'missing deck or active slide' }};
  const d = deck.getBoundingClientRect();
  const s = slide.getBoundingClientRect();
  const toleranceX = Math.max(2, d.width * {CANVAS_TOLERANCE_RATIO});
  const toleranceY = Math.max(2, d.height * {CANVAS_TOLERANCE_RATIO});
  const deltas = {{
    left: s.left - d.left,
    top: s.top - d.top,
    width: s.width - d.width,
    height: s.height - d.height,
  }};
  const round = value => Math.round(value * 100) / 100;
  return {{
    valid: Math.abs(deltas.left) <= toleranceX &&
      Math.abs(deltas.top) <= toleranceY &&
      Math.abs(deltas.width) <= toleranceX &&
      Math.abs(deltas.height) <= toleranceY,
    tolerance: {{ x: round(toleranceX), y: round(toleranceY) }},
    deck: {{ left: round(d.left), top: round(d.top), width: round(d.width), height: round(d.height) }},
    slide: {{ left: round(s.left), top: round(s.top), width: round(s.width), height: round(s.height) }},
    deltas: Object.fromEntries(Object.entries(deltas).map(([key, value]) => [key, round(value)])),
    coverage: {{
      width_ratio: d.width ? round(s.width / d.width) : 0,
      height_ratio: d.height ? round(s.height / d.height) : 0,
    }},
  }};
}}"""


TEXT_COLLISION_CHECK = rf"""() => {{
  const root = document.querySelector('.slide.active');
  if (!root) return {{ collisions: [], opt_outs: [], invalid_opt_outs: [], normal_flow_metric_exclusions: [] }};
  const safetyGap = {TEXT_COLLISION_GAP_PX};
  const fontMetricSlack = {TEXT_COLLISION_FONT_METRIC_SLACK_PX};
  const blockSelector = 'p,h1,h2,h3,h4,h5,h6,li,button,label,figcaption,td,th,caption,dt,dd,summary,legend,[data-qa-text-label]';
  const round = value => Math.round(value * 100) / 100;

  function visible(element) {{
    if (!(element instanceof Element)) return false;
    if (typeof element.checkVisibility === 'function' &&
        !element.checkVisibility({{ checkOpacity: true, checkVisibilityCSS: true }})) return false;
    const style = getComputedStyle(element);
    if (style.display === 'none' || style.visibility === 'hidden' ||
        style.visibility === 'collapse' || Number.parseFloat(style.opacity || '1') <= 0) return false;
    return true;
  }}

  function selectorFor(element) {{
    if (element.id) return `#${{CSS.escape(element.id)}}`;
    const parts = [];
    let current = element;
    while (current && current !== root && parts.length < 5) {{
      let part = current.localName || current.tagName.toLowerCase();
      if (current.classList?.length) {{
        part += '.' + [...current.classList].slice(0, 2).map(value => CSS.escape(value)).join('.');
      }}
      const parent = current.parentElement;
      if (parent) {{
        const siblings = [...parent.children].filter(item => item.localName === current.localName);
        if (siblings.length > 1) part += `:nth-of-type(${{siblings.indexOf(current) + 1}})`;
      }}
      parts.unshift(part);
      current = parent;
    }}
    return '.slide.active > ' + parts.join(' > ');
  }}

  function localOptOut(owner) {{
    if (!owner.hasAttribute('data-qa-ignore-text-collision')) return null;
    const reason = owner.getAttribute('data-qa-ignore-text-collision')?.trim() || '';
    return reason ? reason : '__invalid_empty_reason__';
  }}

  const labels = new Map();
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let textNode;
  while ((textNode = walker.nextNode())) {{
    const text = textNode.textContent?.replace(/\s+/g, ' ').trim();
    const parent = textNode.parentElement;
    if (!text || !parent || parent.closest('svg text') || !visible(parent)) continue;
    const semantic = parent.closest(blockSelector);
    const owner = semantic && root.contains(semantic) ? semantic : parent;
    if (!visible(owner)) continue;
    if (!labels.has(owner)) labels.set(owner, {{ owner, text: [], rects: [], kind: 'html' }});
    const range = document.createRange();
    range.selectNodeContents(textNode);
    const rects = [...range.getClientRects()]
      .filter(rect => rect.width > 0 && rect.height > 0)
      .map(rect => ({{ left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom,
        width: rect.width, height: rect.height }}));
    labels.get(owner).text.push(text);
    labels.get(owner).rects.push(...rects);
  }}

  for (const owner of root.querySelectorAll('svg text')) {{
    const text = owner.textContent?.replace(/\s+/g, ' ').trim();
    const rect = owner.getBoundingClientRect();
    if (!text || !visible(owner) || rect.width <= 0 || rect.height <= 0) continue;
    labels.set(owner, {{
      owner,
      text: [text],
      rects: [{{ left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom,
        width: rect.width, height: rect.height }}],
      kind: 'svg-text',
    }});
  }}

  const optOuts = [];
  const invalidOptOuts = [];
  const active = [];
  for (const label of labels.values()) {{
    const reason = localOptOut(label.owner);
    const normalized = {{
      owner: label.owner,
      text: label.text.join(' ').replace(/\s+/g, ' ').trim().slice(0, 120),
      selector: selectorFor(label.owner),
      kind: label.kind,
      rects: label.rects,
      layoutRect: (() => {{
        const rect = label.owner.getBoundingClientRect();
        return {{ left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom,
          width: rect.width, height: rect.height }};
      }})(),
    }};
    if (reason === '__invalid_empty_reason__') {{
      invalidOptOuts.push({{ text: normalized.text, selector: normalized.selector }});
      active.push(normalized);
    }} else if (reason) {{
      optOuts.push({{ text: normalized.text, selector: normalized.selector, reason }});
    }} else {{
      active.push(normalized);
    }}
  }}

  function sameInlineFlow(first, second) {{
    const a = first.owner;
    const b = second.owner;
    const sa = getComputedStyle(a);
    const sb = getComputedStyle(b);
    return a.parentElement === b.parentElement && sa.position === 'static' && sb.position === 'static' &&
      sa.display.startsWith('inline') && sb.display.startsWith('inline');
  }}

  function isStaticUntransformedHtml(label) {{
    if (label.kind !== 'html') return false;
    const style = getComputedStyle(label.owner);
    const noIndependentTransform = style.transform === 'none' &&
      (!style.translate || style.translate === 'none') &&
      (!style.scale || style.scale === 'none') &&
      (!style.rotate || style.rotate === 'none');
    return style.position === 'static' && style.float === 'none' && noIndependentTransform;
  }}

  function normalFlowMetricExclusion(
    first, second, overlapX, overlapY, horizontalGap, verticalGap
  ) {{
    if (!isStaticUntransformedHtml(first) || !isStaticUntransformedHtml(second)) return null;
    const a = first.layoutRect;
    const b = second.layoutRect;
    const layoutOverlapX = Math.min(a.right, b.right) - Math.max(a.left, b.left);
    const layoutOverlapY = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    if (layoutOverlapX > 0 && layoutOverlapY > 0) return null;
    const intersects = overlapX > 0 && overlapY > 0;
    const gapDepths = [];
    if (overlapY > 0 && horizontalGap < safetyGap) gapDepths.push(safetyGap - horizontalGap);
    if (overlapX > 0 && verticalGap < safetyGap) gapDepths.push(safetyGap - verticalGap);
    const metricDepth = intersects
      ? Math.min(overlapX, overlapY)
      : (gapDepths.length ? Math.min(...gapDepths) : 0);
    if (metricDepth > safetyGap + fontMetricSlack) return null;
    return {{
      layout_clearance: {{
        x: round(Math.max(b.left - a.right, a.left - b.right, 0)),
        y: round(Math.max(b.top - a.bottom, a.top - b.bottom, 0)),
      }},
      metric_overlap_depth: round(metricDepth),
      metric_overlap_limit: round(safetyGap + fontMetricSlack),
      reason: 'static-untransformed HTML layout boxes are separate; shallow Range overlap is font metrics',
    }};
  }}

  const collisions = [];
  const normalFlowMetricExclusions = [];
  for (let i = 0; i < active.length; i += 1) {{
    for (let j = i + 1; j < active.length; j += 1) {{
      const first = active[i];
      const second = active[j];
      if (first.owner.contains(second.owner) || second.owner.contains(first.owner)) continue;
      let pairHandled = false;
      for (const a of first.rects) {{
        for (const b of second.rects) {{
          const overlapX = Math.min(a.right, b.right) - Math.max(a.left, b.left);
          const overlapY = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
          const horizontalGap = Math.max(b.left - a.right, a.left - b.right, 0);
          const verticalGap = Math.max(b.top - a.bottom, a.top - b.bottom, 0);
          const intersects = overlapX > 0 && overlapY > 0;
          const closeHorizontal = overlapY > 0 && horizontalGap < safetyGap;
          const closeVertical = overlapX > 0 && verticalGap < safetyGap;
          const unsafeGap = !sameInlineFlow(first, second) && (closeHorizontal || closeVertical);
          if (!intersects && !unsafeGap) continue;
          const metricExclusion = normalFlowMetricExclusion(
            first, second, overlapX, overlapY, horizontalGap, verticalGap
          );
          if (metricExclusion) {{
            normalFlowMetricExclusions.push({{
              first: {{ text: first.text, selector: first.selector, kind: first.kind }},
              second: {{ text: second.text, selector: second.selector, kind: second.kind }},
              range_overlap: {{ x: round(Math.max(overlapX, 0)), y: round(Math.max(overlapY, 0)) }},
              ...metricExclusion,
            }});
            pairHandled = true;
            break;
          }}
          collisions.push({{
            first: {{ text: first.text, selector: first.selector, kind: first.kind }},
            second: {{ text: second.text, selector: second.selector, kind: second.kind }},
            overlap: {{ x: round(Math.max(overlapX, 0)), y: round(Math.max(overlapY, 0)) }},
            clearance: {{ x: round(horizontalGap), y: round(verticalGap) }},
            safety_gap: safetyGap,
          }});
          pairHandled = true;
          break;
        }}
        if (pairHandled) break;
      }}
    }}
  }}
  return {{ collisions, opt_outs: optOuts, invalid_opt_outs: invalidOptOuts,
    normal_flow_metric_exclusions: normalFlowMetricExclusions }};
}}"""


ANCESTOR_CLIPPING_CHECK = rf"""() => {{
  const root = document.querySelector('.slide.active');
  if (!root) return {{
    candidate_count: 0,
    text_rect_count: 0,
    clipping_ancestor_checks: 0,
    editable_region_capacity_checks: 0,
    duration_ms: 0,
    clips: [],
  }};
  const started = performance.now();
  const tolerance = {ANCESTOR_CLIP_TOLERANCE_PX};
  const clippingValues = new Set(['hidden', 'clip', 'auto', 'scroll']);
  const contentOwnerSelector = [
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'button', 'label',
    'figcaption', 'td', 'th', 'caption', 'dt', 'dd', 'summary', 'legend',
    '[data-qa-text-label]', '[data-qa-readable-content]',
  ].join(',');
  const round = value => Math.round(value * 100) / 100;

  function selectorFor(element) {{
    if (element === root) return '.slide.active';
    if (element.id) return `#${{CSS.escape(element.id)}}`;
    const insideSlide = root.contains(element);
    const boundary = insideSlide ? root : document.documentElement;
    const parts = [];
    let current = element;
    while (current && current !== boundary && parts.length < 6) {{
      let part = current.localName || current.tagName.toLowerCase();
      if (current.classList?.length) {{
        part += '.' + [...current.classList].slice(0, 2)
          .map(value => CSS.escape(value)).join('.');
      }}
      const parent = current.parentElement;
      if (parent) {{
        const siblings = [...parent.children]
          .filter(item => item.localName === current.localName);
        if (siblings.length > 1) {{
          part += `:nth-of-type(${{siblings.indexOf(current) + 1}})`;
        }}
      }}
      parts.unshift(part);
      current = parent;
    }}
    return (insideSlide ? '.slide.active' : 'html') +
      (parts.length ? ' > ' + parts.join(' > ') : '');
  }}

  function rendered(element) {{
    if (!(element instanceof Element) || !element.isConnected) return false;
    if (element.closest('script,style,noscript,template,[hidden],[aria-hidden="true"]')) return false;
    if (typeof element.checkVisibility === 'function' &&
        !element.checkVisibility({{ checkOpacity: true, checkVisibilityCSS: true }})) return false;
    let current = element;
    while (current) {{
      const style = getComputedStyle(current);
      if (style.display === 'none' || style.visibility === 'hidden' ||
          style.visibility === 'collapse' || Number.parseFloat(style.opacity || '1') <= 0) {{
        return false;
      }}
      current = current.parentElement;
    }}
    return true;
  }}

  function normalizeRect(rect) {{
    return {{
      left: rect.left,
      top: rect.top,
      right: rect.right,
      bottom: rect.bottom,
      width: rect.width,
      height: rect.height,
    }};
  }}

  function roundedRect(rect) {{
    if (!rect) return null;
    return Object.fromEntries(
      Object.entries(rect).map(([key, value]) => [key, round(value)])
    );
  }}

  function unionRect(rects) {{
    if (!rects.length) return null;
    const left = Math.min(...rects.map(rect => rect.left));
    const top = Math.min(...rects.map(rect => rect.top));
    const right = Math.max(...rects.map(rect => rect.right));
    const bottom = Math.max(...rects.map(rect => rect.bottom));
    return {{ left, top, right, bottom, width: right - left, height: bottom - top }};
  }}

  function clippingAxes(element) {{
    const style = getComputedStyle(element);
    return {{
      x: clippingValues.has(style.overflowX),
      y: clippingValues.has(style.overflowY),
      overflowX: style.overflowX,
      overflowY: style.overflowY,
    }};
  }}

  function clippingBox(element) {{
    const rect = element.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return null;
    const offsetWidth = Number(element.offsetWidth) || rect.width;
    const offsetHeight = Number(element.offsetHeight) || rect.height;
    const scaleX = offsetWidth ? rect.width / offsetWidth : 1;
    const scaleY = offsetHeight ? rect.height / offsetHeight : 1;
    const clientLeft = Number(element.clientLeft) || 0;
    const clientTop = Number(element.clientTop) || 0;
    const clientWidth = Number(element.clientWidth) || offsetWidth;
    const clientHeight = Number(element.clientHeight) || offsetHeight;
    const left = rect.left + clientLeft * scaleX;
    const top = rect.top + clientTop * scaleY;
    const right = left + clientWidth * scaleX;
    const bottom = top + clientHeight * scaleY;
    return {{ left, top, right, bottom, width: right - left, height: bottom - top }};
  }}

  function clipRect(rect, box, axes) {{
    const pixels = {{
      left: axes.x ? Math.min(rect.width, Math.max(0, box.left - rect.left)) : 0,
      right: axes.x ? Math.min(rect.width, Math.max(0, rect.right - box.right)) : 0,
      top: axes.y ? Math.min(rect.height, Math.max(0, box.top - rect.top)) : 0,
      bottom: axes.y ? Math.min(rect.height, Math.max(0, rect.bottom - box.bottom)) : 0,
    }};
    let left = axes.x ? Math.max(rect.left, box.left) : rect.left;
    let right = axes.x ? Math.min(rect.right, box.right) : rect.right;
    let top = axes.y ? Math.max(rect.top, box.top) : rect.top;
    let bottom = axes.y ? Math.min(rect.bottom, box.bottom) : rect.bottom;
    if (right <= left || bottom <= top) {{
      return {{ pixels, visible: null }};
    }}
    return {{
      pixels,
      visible: {{ left, top, right, bottom, width: right - left, height: bottom - top }},
    }};
  }}

  const candidates = new Map();
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let textNode;
  while ((textNode = walker.nextNode())) {{
    const text = textNode.textContent?.replace(/\s+/g, ' ').trim();
    const parent = textNode.parentElement;
    if (!text || !parent || parent.closest('svg text') || !rendered(parent)) continue;
    const semantic = parent.closest(contentOwnerSelector);
    const owner = semantic && root.contains(semantic) ? semantic : parent;
    if (!rendered(owner)) continue;
    const range = document.createRange();
    range.selectNodeContents(textNode);
    const rects = [...range.getClientRects()]
      .filter(rect => rect.width > 0 && rect.height > 0)
      .map(normalizeRect);
    if (!rects.length) continue;
    if (!candidates.has(owner)) {{
      candidates.set(owner, {{ owner, text: [], rects: [], kind: 'html' }});
    }}
    candidates.get(owner).text.push(text);
    candidates.get(owner).rects.push(...rects);
  }}

  for (const owner of root.querySelectorAll('svg text')) {{
    const text = owner.textContent?.replace(/\s+/g, ' ').trim();
    const rect = owner.getBoundingClientRect();
    if (!text || !rendered(owner) || rect.width <= 0 || rect.height <= 0) continue;
    candidates.set(owner, {{
      owner,
      text: [text],
      rects: [normalizeRect(rect)],
      kind: 'svg-text',
    }});
  }}

  let clippingAncestorChecks = 0;
  const clips = [];
  for (const candidate of candidates.values()) {{
    const contentRect = unionRect(candidate.rects);
    const editableRegion = candidate.owner.closest('[data-editable-region]');
    let visibleRects = candidate.rects.map(rect => ({{ ...rect }}));
    let ancestor = candidate.owner;
    while (ancestor && visibleRects.length) {{
      const axes = clippingAxes(ancestor);
      if (axes.x || axes.y) {{
        const box = clippingBox(ancestor);
        if (box) {{
          clippingAncestorChecks += 1;
          const clippedPixels = {{ left: 0, right: 0, top: 0, bottom: 0 }};
          const nextRects = [];
          let affectedRects = 0;
          for (const rect of visibleRects) {{
            const result = clipRect(rect, box, axes);
            const affected = Object.values(result.pixels).some(value => value > tolerance);
            if (affected) affectedRects += 1;
            for (const direction of Object.keys(clippedPixels)) {{
              clippedPixels[direction] = Math.max(
                clippedPixels[direction], result.pixels[direction]
              );
            }}
            if (result.visible) nextRects.push(result.visible);
          }}
          const directions = Object.entries(clippedPixels)
            .filter(([, value]) => value > tolerance)
            .map(([direction]) => direction);
          if (directions.length) {{
            clips.push({{
              content: {{
                selector: selectorFor(candidate.owner),
                text: candidate.text.join(' ').replace(/\s+/g, ' ').trim().slice(0, 120),
                kind: candidate.kind,
                rect: roundedRect(contentRect),
              }},
              editable_region_context: editableRegion ? {{
                id: editableRegion.getAttribute('data-editable-region') || '',
                selector: selectorFor(editableRegion),
                content_box: roundedRect(clippingBox(editableRegion)),
              }} : null,
              clipping_ancestor: {{
                selector: selectorFor(ancestor),
                overflow_x: axes.overflowX,
                overflow_y: axes.overflowY,
                content_box: roundedRect(box),
              }},
              directions,
              clipped_pixels: Object.fromEntries(
                Object.entries(clippedPixels).map(([key, value]) => [key, round(value)])
              ),
              visible_content_rect: roundedRect(unionRect(nextRects)),
              affected_text_rects: affectedRects,
              fully_clipped: nextRects.length === 0,
              tolerance_px: tolerance,
            }});
          }}
          visibleRects = nextRects;
        }}
      }}
      ancestor = ancestor.parentElement;
    }}
  }}
  const editableRegionCapacityChecks = [
    ...(root.matches('[data-editable-region]') ? [root] : []),
    ...root.querySelectorAll('[data-editable-region]'),
  ].filter(rendered).length;
  return {{
    candidate_count: candidates.size,
    text_rect_count: [...candidates.values()]
      .reduce((total, candidate) => total + candidate.rects.length, 0),
    clipping_ancestor_checks: clippingAncestorChecks,
    editable_region_capacity_checks: editableRegionCapacityChecks,
    duration_ms: round(performance.now() - started),
    clips,
  }};
}}"""


OVERFLOW_CHECK = """() => {
  const root = document.querySelector('.slide.active');
  if (!root) return [];
  const bounds = root.getBoundingClientRect();
  const selector = 'h1,h2,h3,h4,p,li,button,img,video,table,svg,[data-qa-bounds]';
  return [...root.querySelectorAll(selector)]
    .filter(el => {
      if (el.closest('[data-qa-ignore-overflow]')) return false;
      const r = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
      if (r.width === 0 || r.height === 0) return false;
      return r.left < bounds.left - 2 || r.top < bounds.top - 2 ||
        r.right > bounds.right + 2 || r.bottom > bounds.bottom + 2;
    })
    .slice(0, 20)
    .map(el => {
      const r = el.getBoundingClientRect();
      return {
        tag: el.tagName,
        cls: typeof el.className === 'string' ? el.className : '',
        text: (el.textContent || '').trim().slice(0, 80),
        rect: { left: r.left, top: r.top, right: r.right, bottom: r.bottom },
      };
    });
}"""

RHYTHM_CHECK = """() => {
  const root = document.querySelector('.slide.active');
  if (!root) return [];
  return [...root.querySelectorAll('[data-rhythm-check]')]
    .map(container => {
      const token = container.getAttribute('data-rhythm-check') || '';
      const axis = container.getAttribute('data-rhythm-axis') || 'block';
      const from = container.querySelector(':scope > [data-rhythm-from]');
      const to = container.querySelector(':scope > [data-rhythm-to]');
      const expected = Number.parseFloat(getComputedStyle(container).getPropertyValue(token));
      if (!from || !to || !Number.isFinite(expected) || !['block', 'inline'].includes(axis)) {
        return { token, axis, error: 'invalid rhythm contract' };
      }
      const fromRect = from.getBoundingClientRect();
      const toRect = to.getBoundingClientRect();
      const actual = axis === 'inline'
        ? toRect.left - fromRect.right
        : toRect.top - fromRect.bottom;
      if (Math.abs(actual - expected) <= 1.25) return null;
      return {
        token,
        axis,
        expected,
        actual: Math.round(actual * 100) / 100,
        container: typeof container.className === 'string' ? container.className : '',
        from: (from.textContent || '').trim().slice(0, 60),
        to: (to.textContent || '').trim().slice(0, 60),
      };
    })
    .filter(Boolean)
    .slice(0, 20);
}"""


def aggregate_editable_region_capacity_failures(
    page_number: int,
    states: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Aggregate canonical-canvas clips into auditable editable-region failures."""
    failures: list[dict[str, object]] = []
    for state in states:
        groups: dict[str, list[dict[str, object]]] = {}
        for clip in state["clips"]:
            region = clip.get("editable_region_context")
            if not region:
                continue
            groups.setdefault(region["selector"], []).append(clip)
        for clips in groups.values():
            region = clips[0]["editable_region_context"]
            directions = sorted(
                {
                    direction
                    for clip in clips
                    for direction in clip["directions"]
                }
            )
            clipped_pixels = {
                direction: max(
                    clip["clipped_pixels"][direction]
                    for clip in clips
                    if direction in clip["clipped_pixels"]
                )
                for direction in directions
            }
            axes = []
            if any(direction in {"left", "right"} for direction in directions):
                axes.append("horizontal")
            if any(direction in {"top", "bottom"} for direction in directions):
                axes.append("vertical")
            samples = []
            seen_samples: set[tuple[str, str]] = set()
            for clip in clips:
                key = (clip["content"]["selector"], clip["content"]["text"])
                if key in seen_samples:
                    continue
                seen_samples.add(key)
                samples.append(clip["content"])
            failures.append(
                {
                    "page": page_number,
                    "state": state["state"],
                    "basis": "canonical_design_canvas_render",
                    "probe_viewport": {
                        "width": DESIGN_CANVAS_WIDTH,
                        "height": DESIGN_CANVAS_HEIGHT,
                    },
                    "editable_region": region,
                    "clipping_ancestors": [
                        clip["clipping_ancestor"] for clip in clips
                    ],
                    "directions": directions,
                    "axes": axes,
                    "clipped_pixels": clipped_pixels,
                    "clipped_content": {
                        "candidate_count": len(samples),
                        "samples": samples[:4],
                    },
                    "tolerance_px": ANCESTOR_CLIP_TOLERANCE_PX,
                }
            )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Run browser QA for an HTML deck.")
    parser.add_argument("html", type=Path, help="HTML file to test.")
    parser.add_argument("output_dir", type=Path, help="Directory for screenshots and report.")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--max-pages", type=int, default=0, help="Limit slide count. 0 means all.")
    parser.add_argument(
        "--executable-path",
        type=Path,
        help="Optional Chromium executable path for environments without Playwright's headless shell.",
    )
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("Playwright is required. Install with: python -m pip install playwright") from exc

    args.output_dir.mkdir(parents=True, exist_ok=True)
    url = args.html.resolve().as_uri()
    results: dict[str, object] = {
        "url": url,
        "viewport": {"width": args.width, "height": args.height},
        "pages": [],
    }
    failures: list[str] = []

    with sync_playwright() as pw:
        launch_options = {}
        if args.executable_path:
            if not args.executable_path.is_file():
                raise SystemExit(f"Chromium executable not found: {args.executable_path}")
            launch_options["executable_path"] = str(args.executable_path)
        browser = pw.chromium.launch(**launch_options)
        page = browser.new_page(viewport={"width": args.width, "height": args.height})
        console_errors: list[str] = []
        page_errors: list[str] = []
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        page.goto(url, wait_until="load")
        controlled_steps = page.evaluate(CONTROLLED_STEP_CHECK)
        results["controlled_step_contract"] = controlled_steps
        if not controlled_steps["supported"]:
            failures.append(
                "Unsupported controlled-step contract: "
                f"{controlled_steps['contract']}."
            )
        elif (
            controlled_steps["initial_mode"] == "presentation"
            and controlled_steps["controlled_steps"] == 0
        ):
            failures.append(
                "Presentation mode has zero controlled presentation steps under "
                f"{controlled_steps['contract']}."
            )
        slide_count = page.locator(".slide").count()
        if args.max_pages:
            slide_count = min(slide_count, args.max_pages)
        if slide_count == 0:
            failures.append("No .slide elements found.")

        runtime_methods = [
            "getState",
            "setMode",
            "showPage",
            "nextStep",
            "previousStep",
            "nextPage",
            "previousPage",
            "toggleFullscreen",
        ]
        runtime_contract = page.evaluate(
            """methods => {
              const runtime = window.TaoHtmlRuntime;
              return {
                available: Boolean(runtime),
                missing: runtime ? methods.filter(name => typeof runtime[name] !== 'function') : methods,
              };
            }""",
            runtime_methods,
        )
        results["runtime_contract"] = runtime_contract
        if not runtime_contract["available"] or runtime_contract["missing"]:
            failures.append(f"Runtime contract is incomplete: {runtime_contract}")

        runtime_behavior: dict[str, object] = {"tested": False}
        if runtime_contract["available"] and slide_count >= 2:
            page.goto(f"{url}#1")
            page.evaluate("() => window.TaoHtmlRuntime.setMode('presentation')")
            first_fragment_count = page.locator(
                f".slide.active {CONTROLLED_STEP_SELECTOR}"
            ).count()
            before = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            if first_fragment_count:
                page.keyboard.press("ArrowRight")
            after_step = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.keyboard.press("PageDown")
            after_page_down = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.keyboard.press("PageUp")
            after_return = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.evaluate("() => window.TaoHtmlRuntime.setMode('reading')")
            reading_visible = page.evaluate(
                """selector => [...document.querySelectorAll(`.slide.active ${selector}`)]
                .every(el => getComputedStyle(el).opacity === '1')""",
                CONTROLLED_STEP_SELECTOR,
            )
            reading_state = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.evaluate("() => window.TaoHtmlRuntime.showPage(1)")
            page.keyboard.press("ArrowLeft")
            reading_after_left = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.evaluate("() => window.TaoHtmlRuntime.showPage(1)")
            page.evaluate("() => window.TaoHtmlRuntime.setMode('presentation')")
            presentation_state = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.keyboard.press("ArrowLeft")
            after_left_at_zero = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.evaluate("() => window.TaoHtmlRuntime.setMode('reading')")
            page.evaluate("() => window.TaoHtmlRuntime.showPage(0)")
            page.evaluate("() => window.TaoHtmlRuntime.setMode('presentation')")
            page.keyboard.press("ArrowLeft")
            after_left_at_first_page = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            control_before = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            page.locator("#moreToggle").focus()
            page.keyboard.press("Space")
            control_after = page.evaluate("() => window.TaoHtmlRuntime.getState()")
            control_menu_open = page.locator("#moreMenu:not([hidden])").count() == 1
            page.wait_for_timeout(3200)
            menu_stays_open = page.locator("#moreMenu:not([hidden])").count() == 1
            page.locator("#fullscreenToggle").click()
            page.wait_for_function("() => Boolean(document.fullscreenElement)")
            fullscreen_entered = page.evaluate(
                """() => ({
                  menuHidden: document.querySelector('#moreMenu').hidden,
                  expanded: document.querySelector('#moreToggle').getAttribute('aria-expanded'),
                  controlsHidden: document.querySelector('#deck').classList.contains('controls-hidden'),
                })"""
            )
            page.wait_for_timeout(3200)
            fullscreen_idle_hidden = page.locator("#deck.controls-hidden").count() == 1
            page.mouse.move(args.width // 2, args.height // 2)
            fullscreen_pointer_revealed = page.locator("#deck:not(.controls-hidden)").count() == 1
            page.evaluate("() => document.exitFullscreen()")
            page.wait_for_function("() => !document.fullscreenElement")
            fullscreen_exited = page.evaluate(
                """() => ({
                  menuHidden: document.querySelector('#moreMenu').hidden,
                  expanded: document.querySelector('#moreToggle').getAttribute('aria-expanded'),
                })"""
            )
            grouped_step = page.evaluate(
                """selector => {
                  const targetIndex = [...document.querySelectorAll('.slide')]
                    .findIndex(slide => slide.querySelectorAll(selector).length >= 2);
                  if (targetIndex < 0) return { tested: false };
                  const runtime = window.TaoHtmlRuntime;
                  runtime.showPage(targetIndex);
                  runtime.setMode('reading');
                  document.querySelectorAll(`.slide.active ${selector}`)
                    .forEach(el => { el.dataset.taohtmlStep = '1'; });
                  runtime.setMode('presentation');
                  runtime.nextStep();
                  return {
                    tested: true,
                    state: runtime.getState(),
                    total: document.querySelectorAll(`.slide.active ${selector}`).length,
                    visible: document.querySelectorAll(`.slide.active ${selector}.visible`).length,
                  };
                }""",
                CONTROLLED_STEP_SELECTOR,
            )

            expected_stage = 1 if first_fragment_count else 0
            runtime_behavior = {
                "tested": True,
                "before": before,
                "after_step": after_step,
                "after_page_down": after_page_down,
                "after_return": after_return,
                "reading_state": reading_state,
                "reading_visible": reading_visible,
                "reading_after_left": reading_after_left,
                "presentation_state": presentation_state,
                "after_left_at_zero": after_left_at_zero,
                "after_left_at_first_page": after_left_at_first_page,
                "control_keyboard": {
                    "before": control_before,
                    "after": control_after,
                    "menu_open": control_menu_open,
                    "menu_stays_open": menu_stays_open,
                },
                "fullscreen": {
                    "entered": fullscreen_entered,
                    "idle_hidden": fullscreen_idle_hidden,
                    "pointer_revealed": fullscreen_pointer_revealed,
                    "exited": fullscreen_exited,
                },
                "grouped_step": grouped_step,
            }
            if after_step["stages"][0] != expected_stage:
                failures.append("ArrowRight did not advance exactly one presentation step.")
            if after_page_down["index"] != 1:
                failures.append("PageDown did not jump directly to the next page.")
            if after_return["index"] != 0 or after_return["stages"][0] != expected_stage:
                failures.append("Returning to a page did not restore its presentation stage.")
            if reading_state["mode"] != "reading" or not reading_visible:
                failures.append("Reading mode did not expose all current-page fragments.")
            if reading_after_left["mode"] != "reading" or reading_after_left["index"] != 0:
                failures.append("ArrowLeft did not move to the previous page in reading mode.")
            if presentation_state["mode"] != "presentation" or presentation_state["stages"][1] != 0:
                failures.append("Switching from reading to presentation did not reset the current page.")
            if after_left_at_zero["index"] != 0 or after_left_at_zero["stages"][0] != expected_stage:
                failures.append("ArrowLeft at step zero did not return to the previous page and preserve its stage.")
            if after_left_at_first_page["index"] != 0 or after_left_at_first_page["stages"][0] != 0:
                failures.append("ArrowLeft at the first page underflowed the deck boundary.")
            if control_after != control_before or not control_menu_open or not menu_stays_open:
                failures.append("Focused controls did not consume Space without advancing the report.")
            if fullscreen_entered != {"menuHidden": True, "expanded": "false", "controlsHidden": False}:
                failures.append("Entering fullscreen did not close the more menu and expose controls cleanly.")
            if not fullscreen_idle_hidden or not fullscreen_pointer_revealed:
                failures.append("Fullscreen controls did not auto-hide on idle and reappear on pointer movement.")
            if fullscreen_exited != {"menuHidden": True, "expanded": "false"}:
                failures.append("Exiting fullscreen left stale more-menu state behind.")
            if grouped_step["tested"] and grouped_step["visible"] != grouped_step["total"]:
                failures.append("Elements sharing one data-step did not reveal together.")
        results["runtime_behavior"] = runtime_behavior
        page.reload(wait_until="load")
        page.add_style_tag(
            content="""
              *, *::before, *::after {
                transition-duration: 0s !important;
                transition-delay: 0s !important;
                animation-duration: 0s !important;
                animation-delay: 0s !important;
              }
            """
        )

        for i in range(slide_count):
            console_start = 0 if i == 0 else len(console_errors)
            page_error_start = 0 if i == 0 else len(page_errors)
            page.goto(f"{url}#{i + 1}")
            page.wait_for_timeout(150)

            active = page.locator(".slide.active")
            active_count = active.count()
            active_index = page.evaluate(
                "() => [...document.querySelectorAll('.slide')].indexOf(document.querySelector('.slide.active'))"
            )
            route_ok = active_count == 1 and active_index == i

            fragment_count = (
                active.locator(CONTROLLED_STEP_SELECTOR).count()
                if active_count == 1
                else 0
            )
            step_count = (
                active.locator(CONTROLLED_STEP_SELECTOR).evaluate_all(
                    "els => Math.max(0, ...els.map(el => Number.parseInt(el.dataset.taohtmlStep || '0', 10)))"
                )
                if active_count == 1
                else 0
            )
            initial_mode = page.evaluate(
                "() => window.TaoHtmlRuntime?.getState().mode || "
                "(document.querySelector('.deck')?.dataset.mode === 'reading' ? 'reading' : 'presentation')"
            )
            text_collision_states: list[dict[str, object]] = []
            ancestor_clipping_states: list[dict[str, object]] = []

            def capture_layout_state(label: str) -> None:
                text_state_result = page.evaluate(TEXT_COLLISION_CHECK)
                clipping_state_result = page.evaluate(ANCESTOR_CLIPPING_CHECK)
                text_collision_states.append({"state": label, **text_state_result})
                ancestor_clipping_states.append(
                    {"state": label, **clipping_state_result}
                )

            capture_layout_state(f"{initial_mode}-initial")
            if initial_mode == "reading" and fragment_count and runtime_contract["available"]:
                page.evaluate("() => window.TaoHtmlRuntime.setMode('presentation')")
                page.wait_for_timeout(40)
                capture_layout_state("presentation-step-0")

            for step_index in range(step_count):
                page.keyboard.press("ArrowRight")
                page.wait_for_timeout(40)
                capture_layout_state(f"presentation-step-{step_index + 1}")
            visible_fragments = (
                active.locator(f"{CONTROLLED_STEP_SELECTOR}.visible").count()
                if active_count == 1
                else 0
            )
            for _ in range(step_count):
                page.keyboard.press("ArrowLeft")
                page.wait_for_timeout(40)
            rewound_fragments = (
                active.locator(f"{CONTROLLED_STEP_SELECTOR}.visible").count()
                if active_count == 1
                else 0
            )
            for _ in range(step_count):
                page.keyboard.press("ArrowRight")
                page.wait_for_timeout(40)
            if initial_mode == "reading" and runtime_contract["available"]:
                page.evaluate("() => window.TaoHtmlRuntime.setMode('reading')")
                page.wait_for_timeout(40)

            source_failures: list[str] = []
            source_buttons = active.locator(".source-btn") if active_count == 1 else page.locator(".never-match")
            for source_index in range(source_buttons.count()):
                button = source_buttons.nth(source_index)
                source = button.get_attribute("data-source") or "<missing data-source>"
                button.click()
                page.wait_for_timeout(200)
                modal_open = page.locator("#modal.open").count() == 1
                if not modal_open:
                    source_failures.append(f"{source}: modal did not open")
                media_error = page.locator("#modalBody").get_attribute("data-media-error")
                if media_error:
                    source_failures.append(f"{source}: failed to load")
                source_media_failed = page.evaluate(
                    """() => {
                      const media = document.querySelector('#modalBody img, #modalBody video');
                      if (!media) return Boolean(document.querySelector('#modalBody [data-media-error], #modalBody .source-error'));
                      if (media.tagName === 'IMG') return !media.complete || media.naturalWidth === 0;
                      return Boolean(media.error);
                    }"""
                )
                if source_media_failed and not media_error:
                    source_failures.append(f"{source}: media element failed")
                if modal_open:
                    page.locator("#modalClose").click()

            # Capture the stable page state rather than a fragment mid-transition.
            page.wait_for_timeout(520)

            image_failures = page.evaluate(
                """() => [...document.images]
                .filter(img => !img.complete || img.naturalWidth === 0)
                .map(img => img.getAttribute('src') || '')"""
            )
            overflow = page.evaluate(OVERFLOW_CHECK)
            rhythm_failures = page.evaluate(RHYTHM_CHECK)
            canvas_coverage = page.evaluate(CANVAS_COVERAGE_CHECK)
            text_collisions = [
                {"state": state["state"], **collision}
                for state in text_collision_states
                for collision in state["collisions"]
            ]
            opt_out_records = {
                (item["selector"], item["reason"], item["text"]): item
                for state in text_collision_states
                for item in state["opt_outs"]
            }
            invalid_opt_outs = {
                (item["selector"], item["text"]): item
                for state in text_collision_states
                for item in state["invalid_opt_outs"]
            }
            normal_flow_metric_exclusions = {
                (
                    item["first"]["selector"],
                    item["second"]["selector"],
                    item["reason"],
                ): item
                for state in text_collision_states
                for item in state["normal_flow_metric_exclusions"]
            }
            ancestor_clipping = [
                {
                    "page": i + 1,
                    "state": state["state"],
                    **clipping,
                }
                for state in ancestor_clipping_states
                for clipping in state["clips"]
            ]
            screenshot = args.output_dir / f"page-{i + 1:02d}.png"
            page.screenshot(path=str(screenshot), full_page=False)
            current_console_errors = console_errors[console_start:]
            current_page_errors = page_errors[page_error_start:]

            page_result = {
                "page": i + 1,
                "title": active.get_attribute("data-title") if active_count == 1 else None,
                "screenshot": str(screenshot),
                "route_ok": route_ok,
                "fragments": {
                    "total": fragment_count,
                    "steps": step_count,
                    "visible": visible_fragments,
                    "rewound": rewound_fragments,
                },
                "source_failures": source_failures,
                "image_failures": image_failures,
                "offscreen_elements": overflow,
                "rhythm_failures": rhythm_failures,
                "canvas_coverage": canvas_coverage,
                "text_collision_states": text_collision_states,
                "text_collisions": text_collisions,
                "text_collision_opt_outs": list(opt_out_records.values()),
                "invalid_text_collision_opt_outs": list(invalid_opt_outs.values()),
                "normal_flow_text_metric_exclusions": list(
                    normal_flow_metric_exclusions.values()
                ),
                "ancestor_clipping_states": ancestor_clipping_states,
                "ancestor_clipping": ancestor_clipping,
                "editable_region_capacity_states": [],
                "editable_region_capacity_failures": [],
                "console_errors": current_console_errors,
                "page_errors": current_page_errors,
            }
            results["pages"].append(page_result)

            if not route_ok:
                failures.append(f"Page {i + 1}: hash route did not activate the expected slide.")
            if visible_fragments != fragment_count:
                failures.append(
                    f"Page {i + 1}: only {visible_fragments}/{fragment_count} fragments became visible."
                )
            if rewound_fragments != 0:
                failures.append(
                    f"Page {i + 1}: {rewound_fragments}/{fragment_count} fragments remained after rewind."
                )
            if source_failures:
                failures.append(f"Page {i + 1}: source modal failures: {source_failures}")
            if image_failures:
                failures.append(f"Page {i + 1}: image failed to load: {image_failures}")
            if overflow:
                failures.append(f"Page {i + 1}: visible content exceeds slide bounds: {overflow[:3]}")
            if rhythm_failures:
                failures.append(
                    f"Page {i + 1}: semantic rhythm differs from declared tokens: {rhythm_failures[:3]}"
                )
            if not canvas_coverage["valid"]:
                failures.append(
                    f"Page {i + 1}: active slide does not cover the deck canvas: "
                    f"deck={canvas_coverage.get('deck')}, slide={canvas_coverage.get('slide')}, "
                    f"deltas={canvas_coverage.get('deltas')}, tolerance={canvas_coverage.get('tolerance')}."
                )
            for invalid in invalid_opt_outs.values():
                failures.append(
                    f"Page {i + 1}: text-collision opt-out requires a local reason: "
                    f"{invalid['text']!r} ({invalid['selector']})."
                )
            for collision in text_collisions:
                failures.append(
                    f"Page {i + 1} state {collision['state']}: text collision between "
                    f"{collision['first']['text']!r} ({collision['first']['selector']}) and "
                    f"{collision['second']['text']!r} ({collision['second']['selector']}): "
                    f"overlap={collision['overlap']['x']}px x {collision['overlap']['y']}px; "
                    f"clearance={collision['clearance']['x']}px x {collision['clearance']['y']}px; "
                    f"required_gap={collision['safety_gap']}px."
                )
            for clipping in ancestor_clipping:
                clipped = ", ".join(
                    f"{direction}={clipping['clipped_pixels'][direction]}px"
                    for direction in clipping["directions"]
                )
                failures.append(
                    f"Page {i + 1} state {clipping['state']}: readable content "
                    f"{clipping['content']['text']!r} ({clipping['content']['selector']}) "
                    f"is clipped by ancestor {clipping['clipping_ancestor']['selector']} "
                    f"on {', '.join(clipping['directions'])}: {clipped}; "
                    f"overflow-x={clipping['clipping_ancestor']['overflow_x']}, "
                    f"overflow-y={clipping['clipping_ancestor']['overflow_y']}."
                )
            if current_console_errors:
                failures.append(f"Page {i + 1}: console errors: {current_console_errors}")
            if current_page_errors:
                failures.append(f"Page {i + 1}: page errors: {current_page_errors}")

        capacity_viewport = {
            "width": DESIGN_CANVAS_WIDTH,
            "height": DESIGN_CANVAS_HEIGHT,
        }
        results["canonical_capacity_probe"] = {
            "basis": "canonical_design_canvas_render",
            "viewport": capacity_viewport,
            "pages_checked": slide_count,
        }
        if runtime_contract["available"]:
            page.set_viewport_size(capacity_viewport)
            page.wait_for_timeout(150)
            for i, page_result in enumerate(results["pages"]):
                page.evaluate("index => window.TaoHtmlRuntime.showPage(index)", i)
                page.evaluate("() => window.TaoHtmlRuntime.setMode('reading')")
                page.wait_for_timeout(40)
                active = page.locator(".slide.active")
                fragment_count = active.locator(CONTROLLED_STEP_SELECTOR).count()
                step_count = active.locator(CONTROLLED_STEP_SELECTOR).evaluate_all(
                    "els => Math.max(0, ...els.map(el => "
                    "Number.parseInt(el.dataset.taohtmlStep || '0', 10)))"
                )
                capacity_states: list[dict[str, object]] = []

                def capture_capacity_state(label: str) -> None:
                    capacity_states.append(
                        {
                            "state": label,
                            "probe_viewport": capacity_viewport,
                            **page.evaluate(ANCESTOR_CLIPPING_CHECK),
                        }
                    )

                capture_capacity_state("reading-initial")
                if fragment_count:
                    page.evaluate("() => window.TaoHtmlRuntime.setMode('presentation')")
                    page.wait_for_timeout(40)
                    capture_capacity_state("presentation-step-0")
                    for step_index in range(step_count):
                        page.evaluate("() => window.TaoHtmlRuntime.nextStep()")
                        page.wait_for_timeout(40)
                        capture_capacity_state(
                            f"presentation-step-{step_index + 1}"
                        )

                capacity_failures = aggregate_editable_region_capacity_failures(
                    i + 1,
                    capacity_states,
                )
                page_result["editable_region_capacity_states"] = capacity_states
                page_result["editable_region_capacity_failures"] = capacity_failures
                for capacity_failure in capacity_failures:
                    samples = capacity_failure["clipped_content"]["samples"]
                    sample = samples[0]
                    clipped = ", ".join(
                        f"{direction}="
                        f"{capacity_failure['clipped_pixels'][direction]}px"
                        for direction in capacity_failure["directions"]
                    )
                    failures.append(
                        f"Page {i + 1} state {capacity_failure['state']}: "
                        f"canonical {DESIGN_CANVAS_WIDTH}x{DESIGN_CANVAS_HEIGHT} "
                        f"editable-region capacity clips readable content "
                        f"{sample['text']!r} ({sample['selector']}) inside "
                        f"{capacity_failure['editable_region']['selector']} on "
                        f"{', '.join(capacity_failure['directions'])}: {clipped}. "
                        "Reflow, choose a suitable shell, split, or reduce load."
                    )
        browser.close()

    clipping_states = [
        state
        for page_result in results["pages"]
        for state in page_result["ancestor_clipping_states"]
    ]
    capacity_states = [
        state
        for page_result in results["pages"]
        for state in page_result["editable_region_capacity_states"]
    ]
    results["ancestor_clipping_performance"] = {
        "pages_checked": len(results["pages"]),
        "states_checked": len(clipping_states),
        "candidate_evaluations": sum(
            state["candidate_count"] for state in clipping_states
        ),
        "text_rect_evaluations": sum(
            state["text_rect_count"] for state in clipping_states
        ),
        "clipping_ancestor_checks": sum(
            state["clipping_ancestor_checks"] for state in clipping_states
        ),
        "editable_region_capacity_checks": sum(
            state["editable_region_capacity_checks"] for state in clipping_states
        ),
        "browser_evaluation_ms": round(
            sum(state["duration_ms"] for state in clipping_states), 2
        ),
        "clipping_records": sum(
            len(page_result["ancestor_clipping"])
            for page_result in results["pages"]
        ),
        "editable_region_capacity_failures": sum(
            len(page_result["editable_region_capacity_failures"])
            for page_result in results["pages"]
        ),
        "canonical_capacity_probe": {
            "states_checked": len(capacity_states),
            "candidate_evaluations": sum(
                state["candidate_count"] for state in capacity_states
            ),
            "text_rect_evaluations": sum(
                state["text_rect_count"] for state in capacity_states
            ),
            "clipping_ancestor_checks": sum(
                state["clipping_ancestor_checks"] for state in capacity_states
            ),
            "browser_evaluation_ms": round(
                sum(state["duration_ms"] for state in capacity_states), 2
            ),
        },
    }
    results["passed"] = not failures
    results["failures"] = failures
    report = args.output_dir / "qa-report.json"
    report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        print("HTML_DECK_QA_FAILED")
        for failure in failures:
            print(failure)
        print(report)
        return 1
    print("HTML_DECK_QA_OK")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
