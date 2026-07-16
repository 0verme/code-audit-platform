//#region src/graph/adjacency.ts
function e(e, t) {
	let n = /* @__PURE__ */ new Map(), r = /* @__PURE__ */ new Map(), i = /* @__PURE__ */ new Map();
	for (let t of e) n.set(t.id, t), r.set(t.id, []), i.set(t.id, []);
	for (let e of t) r.get(e.target)?.push(e), i.get(e.source)?.push(e);
	return {
		nodeById: n,
		incomingByNodeId: r,
		outgoingByNodeId: i
	};
}
//#endregion
//#region src/graph/cycle-detection.ts
function t(e, t) {
	let a = n(e), o = n(e), s = /* @__PURE__ */ new Set();
	for (let e of t) a.get(e.source)?.push(e.target), o.get(e.target)?.push(e.source), e.source === e.target && s.add(e.source);
	for (let e of a.values()) e.sort((e, t) => e.localeCompare(t));
	for (let e of o.values()) e.sort((e, t) => e.localeCompare(t));
	let c = r([...e].sort((e, t) => e.localeCompare(t)), a), l = /* @__PURE__ */ new Set(), u = [];
	for (let e of [...c].reverse()) {
		if (l.has(e)) continue;
		let t = i(e, o, l).sort((e, t) => e.localeCompare(t));
		(t.length > 1 || s.has(e)) && u.push(t);
	}
	return u.sort((e, t) => e.join("\0").localeCompare(t.join("\0")));
}
function n(e) {
	return new Map(e.map((e) => [e, []]));
}
function r(e, t) {
	let n = /* @__PURE__ */ new Set(), r = [];
	for (let i of e) {
		if (n.has(i)) continue;
		n.add(i);
		let e = [{
			nodeId: i,
			nextIndex: 0
		}];
		for (; e.length > 0;) {
			let i = e[e.length - 1];
			if (i === void 0) continue;
			let a = t.get(i.nodeId) ?? [];
			if (i.nextIndex < a.length) {
				let t = a[i.nextIndex];
				i.nextIndex += 1, t !== void 0 && !n.has(t) && (n.add(t), e.push({
					nodeId: t,
					nextIndex: 0
				}));
			} else r.push(i.nodeId), e.pop();
		}
	}
	return r;
}
function i(e, t, n) {
	let r = [], i = [e];
	for (n.add(e); i.length > 0;) {
		let e = i.pop();
		if (e !== void 0) {
			r.push(e);
			for (let r of t.get(e) ?? []) n.has(r) || (n.add(r), i.push(r));
		}
	}
	return r;
}
//#endregion
//#region src/schema/diagnostics.ts
var a = {
	error: 0,
	warning: 1,
	info: 2
};
function o(e) {
	return [...e].sort((e, t) => {
		let n = a[e.level] - a[t.level];
		if (n !== 0) return n;
		let r = e.code.localeCompare(t.code);
		if (r !== 0) return r;
		let i = (e.nodeId ?? "").localeCompare(t.nodeId ?? "");
		if (i !== 0) return i;
		let o = (e.edgeId ?? "").localeCompare(t.edgeId ?? "");
		return o === 0 ? e.message.localeCompare(t.message) : o;
	});
}
//#endregion
//#region src/schema/validate.ts
var s = [
	"table",
	"view",
	"field",
	"job",
	"dataset",
	"custom"
], c = [
	"default",
	"success",
	"warning",
	"error",
	"muted"
], l = [
	"lineage",
	"dependency",
	"reference",
	"custom"
];
function u(e) {
	if (typeof e != "object" || !e || Array.isArray(e)) return !1;
	let t = Reflect.getPrototypeOf(e);
	return t === Object.prototype || t === null;
}
function d(e) {
	return typeof e == "string" && s.includes(e);
}
function f(e) {
	return typeof e == "string" && c.includes(e);
}
function p(e) {
	return typeof e == "string" && l.includes(e);
}
function m(e) {
	return typeof e == "string" && e.trim().length > 0;
}
function h(e) {
	return u(e) ? e.schemaVersion !== void 0 && e.schemaVersion !== "1.0" ? [g("schemaVersion must be \"1.0\" when provided.")] : Array.isArray(e.nodes) ? Array.isArray(e.edges) ? [] : [g("edges must be an array.")] : [g("nodes must be an array.")] : [g("Input must be a plain object.")];
}
function g(e, t, n) {
	return {
		level: "error",
		code: "INVALID_GRAPH_DATA",
		message: e,
		...t === void 0 ? {} : { nodeId: t },
		...n === void 0 ? {} : { edgeId: n }
	};
}
//#endregion
//#region src/graph/normalize.ts
function _(n, r = {}) {
	let i = h(n);
	if (i.length > 0 || !u(n) || !Array.isArray(n.nodes) || !Array.isArray(n.edges)) return v(null, i);
	let a = [], s = /* @__PURE__ */ new Map();
	for (let e of n.nodes) {
		let t = ee(e, a);
		if (t !== null) {
			if (s.has(t.id)) {
				a.push({
					level: "error",
					code: "DUPLICATE_NODE_ID",
					nodeId: t.id,
					message: `Duplicate node id "${t.id}"; first valid occurrence wins.`
				});
				continue;
			}
			s.set(t.id, t);
		}
	}
	let c = /* @__PURE__ */ new Map();
	for (let e of n.edges) {
		let t = te(e, s, a);
		if (t !== null) {
			if (t.source === t.target && r.showSelfLoops !== !0) {
				a.push({
					level: "warning",
					code: "SELF_LOOP_HIDDEN",
					message: `Self-loop at "${t.source}" was hidden.`,
					...t.id === void 0 ? {} : { edgeId: t.id }
				});
				continue;
			}
			if (c.has(t.key)) {
				a.push({
					level: "warning",
					code: "DUPLICATE_EDGE",
					message: `Duplicate edge "${t.key}" was removed; first valid occurrence wins.`,
					...t.id === void 0 ? {} : { edgeId: t.id }
				});
				continue;
			}
			c.set(t.key, t);
		}
	}
	let l = [...s.values()].sort(re), d = [...c.values()].sort(ie);
	l.length === 0 && a.push({
		level: "info",
		code: "EMPTY_GRAPH",
		message: "The graph contains no valid nodes."
	});
	let f = e(l, d), p = t(l.map((e) => e.id), d);
	for (let e of p) a.push({
		level: "warning",
		code: "CYCLE_DETECTED",
		nodeId: e[0] ?? "",
		message: `Cycle detected: ${e.join(", ")}.`
	});
	let m = {
		schemaVersion: "1.0",
		nodes: l,
		edges: d,
		...f,
		cycleGroups: p
	}, g = o(a);
	return g.some((e) => e.level === "error") && r.validationMode === "strict" ? v(null, g) : v(m, g);
}
function v(e, t) {
	let n = o(t);
	return {
		graph: e,
		diagnostics: n,
		hasErrors: n.some((e) => e.level === "error")
	};
}
function ee(e, t) {
	if (!u(e)) return t.push(g("A node must be a plain object.")), null;
	let n = y(e.id), r = y(e.label);
	if (n === null || r === null || e.type !== void 0 && !d(e.type) || e.status !== void 0 && !f(e.status) || e.metadata !== void 0 && !u(e.metadata)) return t.push(g("A node has invalid required or typed fields.", n ?? void 0)), null;
	let i = {
		id: n,
		label: r
	};
	return x(e, i, "layer"), x(e, i, "subtitle"), e.type !== void 0 && (i.type = e.type), e.status !== void 0 && (i.status = e.status), e.metadata !== void 0 && (i.metadata = e.metadata), i;
}
function te(e, t, n) {
	if (!u(e)) return n.push(g("An edge must be a plain object.")), n.push({
		level: "error",
		code: "MISSING_EDGE_SOURCE",
		message: "Edge source is missing or invalid."
	}), n.push({
		level: "error",
		code: "MISSING_EDGE_TARGET",
		message: "Edge target is missing or invalid."
	}), null;
	let r = y(e.source), i = y(e.target), a = b(e.id), o = a === null || e.label !== void 0 && typeof e.label != "string" || e.type !== void 0 && !p(e.type) || e.metadata !== void 0 && !u(e.metadata);
	a === null && n.push(g("An edge id must be a non-empty string when provided.")), o && a !== null && n.push(g("An edge has invalid typed fields.", void 0, a));
	let s = r !== null && t.has(r), c = i !== null && t.has(i);
	if (s || n.push({
		level: "error",
		code: "MISSING_EDGE_SOURCE",
		message: "Edge source is missing, invalid, or does not reference a valid node.",
		...typeof a == "string" ? { edgeId: a } : {}
	}), c || n.push({
		level: "error",
		code: "MISSING_EDGE_TARGET",
		message: "Edge target is missing, invalid, or does not reference a valid node.",
		...typeof a == "string" ? { edgeId: a } : {}
	}), r === null || i === null || o || !s || !c) return null;
	let l = e.type ?? "lineage", d = e.label ?? "", f = {
		source: r,
		target: i,
		type: l,
		label: d,
		key: ne(r, i, l, d)
	};
	return a !== void 0 && (f.id = a), e.metadata !== void 0 && (f.metadata = e.metadata), f;
}
function y(e) {
	return m(e) ? e.trim() : null;
}
function b(e) {
	return e === void 0 ? void 0 : y(e);
}
function x(e, t, n) {
	e[n] !== void 0 && typeof e[n] == "string" && (t[n] = e[n]);
}
function ne(e, t, n, r) {
	return JSON.stringify([
		e,
		t,
		n,
		r
	]);
}
function re(e, t) {
	return e.id.localeCompare(t.id);
}
function ie(e, t) {
	return e.source.localeCompare(t.source) || e.target.localeCompare(t.target) || e.type.localeCompare(t.type) || e.label.localeCompare(t.label) || (e.id ?? "").localeCompare(t.id ?? "");
}
//#endregion
//#region src/graph/traversal.ts
function S(e, t) {
	return T(e, t, "incomingByNodeId", "source");
}
function C(e, t) {
	return T(e, t, "outgoingByNodeId", "target");
}
function w(e, t) {
	return [.../* @__PURE__ */ new Set([...S(e, t), ...C(e, t)])].sort((e, t) => e.localeCompare(t));
}
function T(e, t, n, r) {
	if (!e.nodeById.has(t)) return [];
	let i = /* @__PURE__ */ new Set([t]), a = [t];
	for (; a.length > 0;) {
		let t = a.pop();
		if (t === void 0) continue;
		let o = e[n].get(t) ?? [];
		for (let e of o) {
			let t = e[r];
			i.has(t) || (i.add(t), a.push(t));
		}
	}
	return i.delete(t), [...i].sort((e, t) => e.localeCompare(t));
}
//#endregion
//#region src/interactions/highlight-state.ts
function E(e, t, n) {
	if (e === null || t === null || !e.nodeById.has(t)) return D();
	if (n === "none") return {
		...D(),
		selectedNodeId: t
	};
	let r = n === "upstream" ? S(e, t) : n === "downstream" ? C(e, t) : w(e, t), i = /* @__PURE__ */ new Set([t, ...r]), a = new Set(r), o = new Set(e.edges.filter((e) => i.has(e.source) && i.has(e.target)).map((e) => e.key));
	return {
		selectedNodeId: t,
		highlightedNodeIds: a,
		dimmedNodeIds: new Set(e.nodes.map((e) => e.id).filter((e) => !i.has(e))),
		highlightedEdgeKeys: o,
		dimmedEdgeKeys: new Set(e.edges.filter((e) => !o.has(e.key)).map((e) => e.key))
	};
}
function D() {
	return {
		selectedNodeId: null,
		highlightedNodeIds: /* @__PURE__ */ new Set(),
		dimmedNodeIds: /* @__PURE__ */ new Set(),
		highlightedEdgeKeys: /* @__PURE__ */ new Set(),
		dimmedEdgeKeys: /* @__PURE__ */ new Set()
	};
}
//#endregion
//#region src/interactions/viewport-math.ts
var O = .1, k = {
	scale: 1,
	translateX: 0,
	translateY: 0
};
function ae(e) {
	let t = e.filter(L);
	if (t.length === 0) return null;
	let n = Math.min(...t.map((e) => e.x)), r = Math.min(...t.map((e) => e.y)), i = Math.max(...t.map((e) => e.x + e.width)), a = Math.max(...t.map((e) => e.y + e.height));
	return {
		x: n,
		y: r,
		width: i - n,
		height: a - r
	};
}
function A(e, t, n = 24) {
	return j(e, t, { padding: n });
}
function j(e, t, n = {}) {
	if (!L(e) || !I(t)) return null;
	let r = P(n.padding) ? n.padding : 24, i = t.width - r * 2, a = t.height - r * 2;
	if (i <= 0 || a <= 0) return null;
	let o = le(Math.min(i / e.width, a / e.height), n);
	return M({
		scale: o,
		translateX: (t.width - e.width * o) / 2 - e.x * o,
		translateY: (t.height - e.height * o) / 2 - e.y * o
	});
}
function oe(e, t, n) {
	return M({
		...e,
		translateX: e.translateX + t,
		translateY: e.translateY + n
	});
}
function se(e, t, n) {
	if (!Number.isFinite(t.x) || !Number.isFinite(t.y) || !Number.isFinite(n) || n <= 0) return M(e);
	let r = N(e.scale * n), i = (t.x - e.translateX) / e.scale, a = (t.y - e.translateY) / e.scale;
	return M({
		scale: r,
		translateX: t.x - i * r,
		translateY: t.y - a * r
	});
}
function ce(e, t, n) {
	return !I(t) || !Number.isFinite(n.x) || !Number.isFinite(n.y) ? null : M({
		scale: e.scale,
		translateX: t.width / 2 - n.x * e.scale,
		translateY: t.height / 2 - n.y * e.scale
	});
}
function M(e) {
	return {
		scale: N(e.scale),
		translateX: Number.isFinite(e.translateX) ? e.translateX : 0,
		translateY: Number.isFinite(e.translateY) ? e.translateY : 0
	};
}
function N(e) {
	return Math.min(4, Math.max(O, Number.isFinite(e) ? e : 1));
}
function le(e, t) {
	let n = Math.max(O, F(t.minScale) ? t.minScale : O), r = Math.max(n, Math.min(4, F(t.maxScale) ? t.maxScale : 4));
	return Math.min(r, Math.max(n, e));
}
function P(e) {
	return e !== void 0 && Number.isFinite(e) && e >= 0;
}
function F(e) {
	return e !== void 0 && Number.isFinite(e) && e > 0;
}
function I(e) {
	return Number.isFinite(e.width) && Number.isFinite(e.height) && e.width > 0 && e.height > 0;
}
function L(e) {
	return Number.isFinite(e.x) && Number.isFinite(e.y) && Number.isFinite(e.width) && Number.isFinite(e.height) && e.width > 0 && e.height > 0;
}
//#endregion
//#region src/interactions/viewport-controller.ts
var R = class {
	apply;
	transform = k;
	baseline = k;
	viewport = {
		width: 0,
		height: 0
	};
	scene = null;
	userInteracted = !1;
	constructor(e) {
		this.apply = e;
	}
	setScene(e, t, n) {
		this.scene = e, this.viewport = t, this.userInteracted = !1;
		let r = n && e !== null ? A(e, t) : k;
		this.baseline = r ?? k, this.setTransform(this.baseline);
	}
	resize(e, t) {
		let n = this.viewport;
		if (this.viewport = e, this.scene !== null) {
			if (!this.userInteracted && t) {
				let t = A(this.scene, e);
				t && (this.baseline = t, this.setTransform(t));
				return;
			}
			if (this.userInteracted && n.width > 0 && n.height > 0 && e.width > 0 && e.height > 0) {
				let t = (n.width / 2 - this.transform.translateX) / this.transform.scale, r = (n.height / 2 - this.transform.translateY) / this.transform.scale;
				this.setTransform({
					...this.transform,
					translateX: e.width / 2 - t * this.transform.scale,
					translateY: e.height / 2 - r * this.transform.scale
				});
			}
		}
	}
	getTransform() {
		return { ...this.transform };
	}
	fit() {
		if (this.scene) {
			let e = A(this.scene, this.viewport);
			e && this.setTransform(e);
		}
	}
	fitBounds(e, t) {
		let n = j(e, this.viewport, t);
		n && this.setTransform(n);
	}
	reset() {
		this.scene && (this.userInteracted = !1, this.setTransform(this.baseline));
	}
	focus(e) {
		let t = ce(this.transform, this.viewport, e);
		t && (this.userInteracted = !0, this.setTransform(t));
	}
	pan(e, t) {
		this.userInteracted = !0, this.setTransform(oe(this.transform, e, t));
	}
	zoom(e, t) {
		this.userInteracted = !0, this.setTransform(se(this.transform, e, t));
	}
	destroy() {
		this.scene = null;
	}
	setTransform(e) {
		this.transform = M(e), this.apply(this.transform);
	}
}, z = 32, B = (e, t) => e.localeCompare(t);
function V(e, t) {
	let n = H(e), r = new Map(n.map((e) => [e.key, e])), i = /* @__PURE__ */ new Map();
	for (let e of n) for (let t of e.nodeIds) i.set(t, e);
	for (let t of e.edges) {
		let e = i.get(t.source), n = i.get(t.target);
		e !== void 0 && n !== void 0 && e !== n && (e.outgoing.add(n.key), n.incoming.add(e.key));
	}
	let a = U(n, r), o = t.direction === "TB" || t.direction === "BT", s = o ? t.nodeHeight : t.nodeWidth, c = o ? t.nodeWidth : t.nodeHeight, l = Math.max(t.nodeGap * 2, 64), u = [], d = 0, f = s;
	for (let e of a) {
		let n = W(e), r = [], i = 0;
		for (let e = 0; e < n.length; e += 1) r[e] = i, i += s + t.layerGap;
		f = Math.max(f, Math.max(0, i - t.layerGap));
		let a = 0;
		for (let e of n) {
			let n = 0;
			for (let i of e) {
				let e = i.nodeIds.length, a = e * c + Math.max(0, e - 1) * t.nodeGap;
				for (let a = 0; a < e; a += 1) {
					let e = i.nodeIds[a];
					e !== void 0 && u.push({
						id: e,
						primary: r[i.rank] ?? 0,
						cross: d + n + a * (c + t.nodeGap),
						rank: i.rank,
						componentKey: i.key
					});
				}
				n += a + t.nodeGap;
			}
			a = Math.max(a, Math.max(0, n - t.nodeGap));
		}
		d += a + l;
	}
	let p = Math.max(c, Math.max(0, d - l));
	return {
		nodes: u.sort((e, t) => B(e.id, t.id)).map((e) => ue(e, t, f)),
		width: Math.max(1, (o ? p : f) + z * 2),
		height: Math.max(1, (o ? f : p) + z * 2)
	};
}
function H(e) {
	let t = e.cycleGroups.map((e) => [...e].sort(B)), n = new Set(t.flat());
	for (let r of e.nodes) n.has(r.id) || t.push([r.id]);
	return t.map((t) => ({
		key: t.join("\0"),
		nodeIds: t,
		cyclic: t.length > 1 || e.edges.some((e) => e.source === t[0] && e.target === t[0]),
		incoming: /* @__PURE__ */ new Set(),
		outgoing: /* @__PURE__ */ new Set(),
		rank: 0
	})).sort((e, t) => B(e.key, t.key));
}
function U(e, t) {
	let n = /* @__PURE__ */ new Set(), r = [];
	for (let i of e) {
		if (n.has(i.key)) continue;
		let e = [i], a = [];
		for (n.add(i.key); e.length > 0;) {
			let r = e.pop();
			if (r !== void 0) {
				a.push(r);
				for (let i of [...r.incoming, ...r.outgoing].sort(B)) {
					let r = t.get(i);
					r !== void 0 && !n.has(i) && (n.add(i), e.push(r));
				}
			}
		}
		a.sort((e, t) => B(e.key, t.key)), r.push({
			components: a,
			key: a[0]?.key ?? ""
		});
	}
	return r.sort((e, t) => B(e.key, t.key));
}
function W(e) {
	let t = new Map(e.components.map((e) => [e.key, e])), n = new Map(e.components.map((e) => [e.key, e.incoming.size])), r = e.components.filter((e) => (n.get(e.key) ?? 0) === 0).sort((e, t) => B(e.key, t.key)), i = [];
	for (; r.length > 0;) {
		let e = r.shift();
		if (e !== void 0) {
			i.push(e);
			for (let i of [...e.outgoing].sort(B)) {
				let e = (n.get(i) ?? 1) - 1;
				if (n.set(i, e), e === 0) {
					let e = t.get(i);
					e !== void 0 && (r.push(e), r.sort((e, t) => B(e.key, t.key)));
				}
			}
		}
	}
	for (let e of i) e.rank = Math.max(0, ...[...e.incoming].map((e) => (t.get(e)?.rank ?? 0) + 1));
	let a = [];
	for (let e of i) (a[e.rank] ??= []).push(e);
	for (let e of a) e.sort((e, t) => B(e.key, t.key));
	for (let e = 0; e < 4; e += 1) {
		let t = e % 2 == 0, n = /* @__PURE__ */ new Map(), r = t ? [...a.keys()] : [...a.keys()].reverse();
		for (let e of r) {
			if (t && e === 0 || !t && e === a.length - 1) continue;
			let r = a[e] ?? [];
			(a[t ? e - 1 : e + 1] ?? []).forEach((e, t) => n.set(e.key, t));
			let i = new Map(r.map((e, t) => [e.key, t]));
			r.sort((e, r) => G(e, n, t) - G(r, n, t) || (i.get(e.key) ?? 0) - (i.get(r.key) ?? 0) || B(e.key, r.key));
		}
	}
	return a;
}
function G(e, t, n) {
	let r = [...n ? e.incoming : e.outgoing].filter((e) => t.has(e));
	return r.length === 0 ? Infinity : r.reduce((e, n) => e + (t.get(n) ?? 0), 0) / r.length;
}
function ue(e, t, n) {
	let r = t.direction === "TB" || t.direction === "BT", i = t.direction === "RL" || t.direction === "BT", a = r ? t.nodeHeight : t.nodeWidth, o = i ? n - e.primary - a : e.primary;
	return {
		id: e.id,
		x: z + (r ? e.cross : o),
		y: z + (r ? o : e.cross),
		width: t.nodeWidth,
		height: t.nodeHeight,
		rank: e.rank,
		componentKey: e.componentKey
	};
}
//#endregion
//#region src/render/create-render-scene.ts
function de(e, t) {
	let n = V(e, t), r = n.nodes.map((t) => ({
		...t,
		node: e.nodeById.get(t.id)
	})), i = new Map(r.map((e) => [e.id, e])), a = e.edges.flatMap((e) => {
		let n = i.get(e.source), r = i.get(e.target);
		return n === void 0 || r === void 0 ? [] : [{
			key: e.key,
			edge: e,
			...fe(n, r, t.direction, e.key)
		}];
	});
	return {
		width: n.width,
		height: n.height,
		nodes: r,
		edges: a
	};
}
function fe(e, t, n, r) {
	if (e.id === t.id) return me(e, n);
	let i = n === "TB" || n === "BT", a = n === "LR" || n === "TB";
	if (e.rank === t.rank) return pe(e, t, i, r);
	if (i) {
		let n = {
			x: e.x + e.width / 2,
			y: e.y + (a ? e.height : 0)
		}, r = {
			x: t.x + t.width / 2,
			y: t.y + (a ? 0 : t.height)
		}, i = (n.y + r.y) / 2;
		return K(n, {
			x: n.x,
			y: i
		}, {
			x: r.x,
			y: i
		}, r);
	}
	let o = {
		x: e.x + (a ? e.width : 0),
		y: e.y + e.height / 2
	}, s = {
		x: t.x + (a ? 0 : t.width),
		y: t.y + t.height / 2
	}, c = (o.x + s.x) / 2;
	return K(o, {
		x: c,
		y: o.y
	}, {
		x: c,
		y: s.y
	}, s);
}
function pe(e, t, n, r) {
	let i = 28 + he(r) % 3 * 12;
	if (n) {
		let n = e.x + e.width / 2, r = t.x + t.width / 2, a = Math.min(e.y, t.y) - i;
		return K({
			x: n,
			y: e.y
		}, {
			x: n,
			y: a
		}, {
			x: r,
			y: a
		}, {
			x: r,
			y: t.y
		});
	}
	let a = e.y + e.height / 2, o = t.y + t.height / 2, s = Math.min(e.x, t.x) - i;
	return K({
		x: e.x,
		y: a
	}, {
		x: s,
		y: a
	}, {
		x: s,
		y: o
	}, {
		x: t.x,
		y: o
	});
}
function me(e, t) {
	if (t === "TB" || t === "BT") {
		let t = e.x + e.width / 2, n = e.y;
		return K({
			x: t,
			y: n
		}, {
			x: t + 40,
			y: n - 36
		}, {
			x: t - 40,
			y: n - 36
		}, {
			x: t,
			y: n
		});
	}
	let n = e.x + e.width, r = e.y + e.height / 2;
	return K({
		x: n,
		y: r
	}, {
		x: n + 40,
		y: r - 36
	}, {
		x: n + 40,
		y: r + 36
	}, {
		x: n,
		y: r + 1
	});
}
function K(e, t, n, r) {
	let i = (i) => (e[i] + 3 * t[i] + 3 * n[i] + r[i]) / 8;
	return {
		path: `M ${e.x} ${e.y} C ${t.x} ${t.y}, ${n.x} ${n.y}, ${r.x} ${r.y}`,
		labelX: i("x"),
		labelY: i("y")
	};
}
function he(e) {
	let t = 0;
	for (let n = 0; n < e.length; n += 1) t = t * 31 + e.charCodeAt(n) >>> 0;
	return t;
}
//#endregion
//#region src/render/svg-renderer.ts
var ge = "http://www.w3.org/2000/svg", _e = 0, ve = class {
	svg;
	viewportGroup;
	sceneGroup;
	viewportWidth = 0;
	viewportHeight = 0;
	markerId = `lineage-viewer-arrow-${++_e}`;
	destroyed = !1;
	constructor(e) {
		this.svg = Y("svg"), this.svg.setAttribute("part", "svg"), this.svg.setAttribute("width", "100%"), this.svg.setAttribute("height", "100%"), this.svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
		let t = Y("defs"), n = Y("marker");
		n.setAttribute("id", this.markerId), n.setAttribute("viewBox", "0 0 10 10"), n.setAttribute("refX", "9"), n.setAttribute("refY", "5"), n.setAttribute("markerWidth", "7"), n.setAttribute("markerHeight", "7"), n.setAttribute("orient", "auto-start-reverse");
		let r = Y("path");
		r.setAttribute("d", "M 0 0 L 10 5 L 0 10 z"), r.setAttribute("class", "arrow"), n.append(r), t.append(n), this.viewportGroup = Y("g"), this.viewportGroup.setAttribute("class", "viewport"), this.sceneGroup = Y("g"), this.sceneGroup.setAttribute("class", "scene"), this.viewportGroup.append(this.sceneGroup), this.svg.append(t, this.viewportGroup), e.append(this.svg);
	}
	render(e, t) {
		if (this.destroyed) return;
		this.clear();
		let n = Y("g");
		n.setAttribute("class", "edges");
		let r = Y("g");
		r.setAttribute("class", "nodes");
		for (let r of e.edges) {
			let e = Y("path");
			if (e.setAttribute("class", "edge"), e.setAttribute("d", r.path), e.setAttribute("marker-end", `url(#${this.markerId})`), e.setAttribute("data-edge-key", r.key), e.setAttribute("data-edge-source", r.edge.source), e.setAttribute("data-edge-target", r.edge.target), n.append(e), t.showEdgeLabels && r.edge.label) {
				let e = Y("text");
				e.setAttribute("class", "edge-label"), e.setAttribute("x", String(r.labelX)), e.setAttribute("y", String(r.labelY)), e.setAttribute("dy", "-6"), e.setAttribute("text-anchor", "middle"), e.textContent = r.edge.label, n.append(e);
			}
		}
		for (let [t, n] of e.nodes.entries()) {
			let e = Y("g");
			e.setAttribute("class", "node"), e.setAttribute("transform", `translate(${n.x} ${n.y})`), e.setAttribute("data-node-id", n.id), n.rank !== void 0 && e.setAttribute("data-node-layer", String(n.rank)), n.node.type && e.setAttribute("data-node-type", n.node.type), n.node.status && e.setAttribute("data-node-status", n.node.status);
			let i = Y("rect");
			i.setAttribute("width", String(n.width)), i.setAttribute("height", String(n.height)), i.setAttribute("rx", "8");
			let a = `${this.markerId}-node-text-${t}`, o = Y("clipPath");
			o.setAttribute("id", a);
			let s = Y("rect");
			s.setAttribute("x", "16"), s.setAttribute("width", String(Math.max(0, n.width - 32))), s.setAttribute("height", String(n.height)), o.append(s);
			let c = Y("title"), l = J(n.node.metadata, "fullLabel") ?? n.node.label, u = J(n.node.metadata, "fullSubtitle") ?? n.node.subtitle;
			c.textContent = u ? `${l}\n${u}` : l;
			let d = Y("text");
			if (d.setAttribute("class", "node-title"), d.setAttribute("x", "16"), d.setAttribute("y", "30"), d.setAttribute("clip-path", `url(#${a})`), d.textContent = n.node.label, e.append(o, c, i, d), n.node.subtitle) {
				let t = Y("text");
				t.setAttribute("class", "node-subtitle"), t.setAttribute("x", "16"), t.setAttribute("y", "52"), t.setAttribute("clip-path", `url(#${a})`), t.textContent = n.node.subtitle, e.append(t);
			}
			r.append(e);
		}
		this.sceneGroup.append(n, r);
	}
	clear() {
		this.sceneGroup.replaceChildren();
	}
	setViewportSize(e, t) {
		e > 0 && t > 0 && Number.isFinite(e) && Number.isFinite(t) && (e !== this.viewportWidth || t !== this.viewportHeight) && (this.viewportWidth = e, this.viewportHeight = t, this.svg.setAttribute("viewBox", `0 0 ${e} ${t}`));
	}
	setViewportTransform(e) {
		this.viewportGroup.setAttribute("transform", `translate(${e.translateX} ${e.translateY}) scale(${e.scale})`);
	}
	setInteractionState(e) {
		for (let t of this.sceneGroup.querySelectorAll(".node")) {
			let n = t.dataset.nodeId;
			q(t, "selected", n === e.selectedNodeId), q(t, "highlighted", n !== void 0 && e.highlightedNodeIds.has(n)), q(t, "dimmed", n !== void 0 && e.dimmedNodeIds.has(n));
		}
		for (let t of this.sceneGroup.querySelectorAll(".edge")) {
			let n = t.dataset.edgeKey;
			q(t, "highlighted", n !== void 0 && e.highlightedEdgeKeys.has(n)), q(t, "dimmed", n !== void 0 && e.dimmedEdgeKeys.has(n));
		}
	}
	destroy() {
		this.destroyed ||= (this.clear(), this.svg.remove(), !0);
	}
};
function q(e, t, n) {
	n ? e.setAttribute(`data-${t}`, "") : e.removeAttribute(`data-${t}`);
}
function J(e, t) {
	let n = e?.[t];
	return typeof n == "string" ? n : void 0;
}
function Y(e) {
	return document.createElementNS(ge, e);
}
//#endregion
//#region src/public-api/options.ts
var ye = {
	direction: "LR",
	fitOnLoad: !0,
	readonly: !0,
	showSelfLoops: !1,
	showEdgeLabels: !1,
	validationMode: "lenient",
	nodeWidth: 180,
	nodeHeight: 72,
	layerGap: 72,
	nodeGap: 32,
	highlightMode: "connected"
};
function be(e, t) {
	if (typeof t != "object" || !t || Array.isArray(t)) return e;
	let n = t;
	return {
		direction: xe(n.direction) ? n.direction : e.direction,
		fitOnLoad: typeof n.fitOnLoad == "boolean" ? n.fitOnLoad : e.fitOnLoad,
		readonly: typeof n.readonly == "boolean" ? n.readonly : e.readonly,
		showSelfLoops: typeof n.showSelfLoops == "boolean" ? n.showSelfLoops : e.showSelfLoops,
		showEdgeLabels: typeof n.showEdgeLabels == "boolean" ? n.showEdgeLabels : e.showEdgeLabels,
		validationMode: n.validationMode === "strict" || n.validationMode === "lenient" ? n.validationMode : e.validationMode,
		nodeWidth: X(n.nodeWidth, e.nodeWidth),
		nodeHeight: X(n.nodeHeight, e.nodeHeight),
		layerGap: X(n.layerGap, e.layerGap),
		nodeGap: X(n.nodeGap, e.nodeGap),
		highlightMode: Se(n.highlightMode) ? n.highlightMode : e.highlightMode
	};
}
function X(e, t) {
	return typeof e == "number" && Number.isFinite(e) && e > 0 ? e : t;
}
function xe(e) {
	return e === "LR" || e === "RL" || e === "TB" || e === "BT";
}
function Se(e) {
	return e === "connected" || e === "upstream" || e === "downstream" || e === "none";
}
//#endregion
//#region src/element/styles.ts
var Z = ":host { position:relative; display:block; width:100%; height:100%; min-width:0; min-height:0; overflow:hidden; --lineage-background:#fff; --lineage-node-background:#fff; --lineage-node-border:#d7dce3; --lineage-node-success-background:#f0fdf4; --lineage-node-success-border:#16a34a; --lineage-node-warning-background:#fffbeb; --lineage-node-warning-border:#d97706; --lineage-node-error-background:#fef2f2; --lineage-node-error-border:#dc2626; --lineage-node-muted-background:#f8fafc; --lineage-node-muted-border:#94a3b8; --lineage-node-selected-border:#2563eb; --lineage-node-selected-shadow:#93c5fd; --lineage-node-text:#172033; --lineage-node-subtitle:#6b7280; --lineage-edge-color:#718096; --lineage-edge-highlight-color:#2563eb; --lineage-dimmed-opacity:.28; --lineage-font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif; } .root { position:relative; width:100%; height:100%; min-width:0; min-height:0; background:var(--lineage-background); overflow:hidden; } svg { position:absolute; inset:0; display:block; width:100%; height:100%; background:var(--lineage-background); font-family:var(--lineage-font-family); cursor:grab; touch-action:none; } svg[data-panning] { cursor:grabbing; } .edge { fill:none; stroke:var(--lineage-edge-color); stroke-width:1.5; } .arrow { fill:var(--lineage-edge-color); } .node { cursor:pointer; } .node rect { fill:var(--lineage-node-background); stroke:var(--lineage-node-border); filter:drop-shadow(0 1px 1px rgb(15 23 42 / 8%)); } .node[data-node-status=\"success\"] rect { fill:var(--lineage-node-success-background); stroke:var(--lineage-node-success-border); } .node[data-node-status=\"warning\"] rect { fill:var(--lineage-node-warning-background); stroke:var(--lineage-node-warning-border); } .node[data-node-status=\"error\"] rect { fill:var(--lineage-node-error-background); stroke:var(--lineage-node-error-border); } .node[data-node-status=\"muted\"] rect { fill:var(--lineage-node-muted-background); stroke:var(--lineage-node-muted-border); } .node[data-selected] rect { stroke:var(--lineage-node-selected-border); stroke-width:3; filter:drop-shadow(0 0 4px var(--lineage-node-selected-shadow)); } .node[data-highlighted] rect,.edge[data-highlighted] { stroke:var(--lineage-edge-highlight-color); } .edge[data-highlighted] { stroke-width:2.25; } .edge[data-dimmed],.node[data-dimmed] { opacity:var(--lineage-dimmed-opacity); } .node-title { fill:var(--lineage-node-text); font-size:14px; font-weight:600; } .node-subtitle,.edge-label { fill:var(--lineage-node-subtitle); font-size:12px; } .edge-label { pointer-events:none; paint-order:stroke; stroke:var(--lineage-background); stroke-width:4px; stroke-linejoin:round; } .state { position:absolute; inset:0; display:grid; place-content:center; gap:8px; padding:24px; text-align:center; color:#64748b; font-family:var(--lineage-font-family); } .state[data-kind=\"invalid\"] { color:#b42318; } .state p { margin:0; } @media (prefers-reduced-motion: no-preference) { .edge,.node { transition:opacity 120ms ease,stroke 120ms ease; } }", Ce = typeof HTMLElement > "u" ? class {} : HTMLElement, Q = class extends Ce {
	root;
	renderer = null;
	viewport = null;
	resizeObserver = null;
	state = "idle";
	graph = null;
	scene = null;
	diagnostics = [];
	input = null;
	resolvedOptions = ye;
	selectedId = null;
	initialized = !1;
	readyDispatched = !1;
	hasObservedViewport = !1;
	drag = null;
	suppressClick = !1;
	constructor() {
		super(), this.root = this.attachShadow({ mode: "open" });
	}
	get data() {
		return this.graph === null ? null : {
			schemaVersion: this.graph.schemaVersion,
			nodes: this.graph.nodes.map((e) => ({ ...e })),
			edges: this.graph.edges.map(we)
		};
	}
	set data(e) {
		this.setData(e);
	}
	get options() {
		return { ...this.resolvedOptions };
	}
	set options(e) {
		this.setOptions(e);
	}
	get selectedNodeId() {
		return this.state === "destroyed" ? null : this.selectedId;
	}
	connectedCallback() {
		this.state !== "destroyed" && (this.ensureInitialized(), this.observe(), this.process(!1));
	}
	disconnectedCallback() {
		this.stopObserving(), this.renderer?.clear();
	}
	setData(e) {
		this.state !== "destroyed" && (this.input = e, this.process(!0));
	}
	setOptions(e) {
		if (this.state === "destroyed") return;
		let t = this.resolvedOptions;
		this.resolvedOptions = be(t, e);
		let n = t.validationMode !== this.resolvedOptions.validationMode || t.showSelfLoops !== this.resolvedOptions.showSelfLoops, r = t.direction !== this.resolvedOptions.direction || t.nodeWidth !== this.resolvedOptions.nodeWidth || t.nodeHeight !== this.resolvedOptions.nodeHeight || t.layerGap !== this.resolvedOptions.layerGap || t.nodeGap !== this.resolvedOptions.nodeGap;
		n ? this.process(!0) : r && this.initialized ? this.renderCurrent(!0) : t.fitOnLoad !== this.resolvedOptions.fitOnLoad && this.resolvedOptions.fitOnLoad && this.scene ? this.viewport?.setScene($(this.scene), this.size(), !0) : t.showEdgeLabels !== this.resolvedOptions.showEdgeLabels && this.initialized && this.renderCurrent(!1), this.applyInteractionState();
	}
	getDiagnostics() {
		return [...this.diagnostics];
	}
	fitView() {
		this.state !== "destroyed" && this.viewport?.fit();
	}
	fitBounds(e, t) {
		this.state !== "destroyed" && this.viewport?.fitBounds(e, t);
	}
	fitNodes(e, t) {
		if (this.state === "destroyed" || e.length === 0) return;
		let n = e.map((e) => this.findSceneNode(e)).filter((e) => e !== void 0);
		if (n.length === 0) return;
		let r = ae(n.map((e) => e));
		r && this.viewport?.fitBounds(r, t);
	}
	resetView() {
		this.state !== "destroyed" && this.viewport?.reset();
	}
	focusNode(e) {
		let t = this.findSceneNode(e);
		t && this.viewport?.focus({
			x: t.x + t.width / 2,
			y: t.y + t.height / 2
		});
	}
	zoomBy(e) {
		let t = this.size();
		this.viewport?.zoom({
			x: t.width / 2,
			y: t.height / 2
		}, e);
	}
	selectNode(e) {
		let t = e.trim();
		this.graph?.nodeById.has(t) && this.updateSelection(t, "api");
	}
	clearSelection() {
		this.updateSelection(null, "api");
	}
	destroy() {
		this.state !== "destroyed" && (this.stopObserving(), this.renderer?.destroy(), this.renderer = null, this.viewport?.destroy(), this.viewport = null, this.root.replaceChildren(), this.graph = null, this.scene = null, this.selectedId = null, this.diagnostics = [], this.state = "destroyed");
	}
	ensureInitialized() {
		if (this.initialized) return;
		let e = document.createElement("style");
		e.textContent = Z;
		let t = document.createElement("div");
		t.className = "root", this.root.append(e, t), this.renderer = new ve(this.root), this.viewport = new R((e) => this.renderer?.setViewportTransform(e)), this.renderer.svg.addEventListener("wheel", this.onWheel, { passive: !1 }), this.renderer.svg.addEventListener("pointerdown", this.onPointerDown), this.renderer.svg.addEventListener("pointermove", this.onPointerMove), this.renderer.svg.addEventListener("pointerup", this.onPointerEnd), this.renderer.svg.addEventListener("pointercancel", this.onPointerEnd), this.renderer.svg.addEventListener("click", this.onClick), this.initialized = !0;
	}
	process(e) {
		if (this.state === "destroyed") return;
		if (this.input === null) {
			this.graph = null, this.diagnostics = [], this.state = "idle", this.clearForData(), this.renderCurrent(!0);
			return;
		}
		let t = _(this.input, {
			validationMode: this.resolvedOptions.validationMode,
			showSelfLoops: this.resolvedOptions.showSelfLoops
		});
		this.graph = t.graph, this.diagnostics = t.diagnostics, this.state = t.graph === null ? "invalid" : t.graph.nodes.length === 0 ? "empty" : "rendered", this.selectedId !== null && !this.graph?.nodeById.has(this.selectedId) && this.updateSelection(null, "data"), this.renderCurrent(!0), e && this.isConnected && this.emitDiagnostics(), this.dispatchReadyIfPossible();
	}
	clearForData() {
		this.selectedId !== null && this.updateSelection(null, "data");
	}
	renderCurrent(e) {
		if (!this.initialized || this.renderer === null) return;
		if (this.renderer.clear(), this.root.querySelector(".state")?.remove(), this.scene = null, this.state === "rendered" && this.graph !== null) {
			this.scene = de(this.graph, this.resolvedOptions), this.renderer.render(this.scene, this.resolvedOptions);
			let t = this.size();
			this.renderer.setViewportSize(t.width, t.height), e && this.viewport?.setScene($(this.scene), t, this.resolvedOptions.fitOnLoad), this.applyInteractionState();
			return;
		}
		this.viewport?.setScene(null, this.size(), !1);
		let t = document.createElement("div");
		t.className = "state", t.dataset.kind = this.state;
		let n = document.createElement("p");
		if (n.textContent = this.state === "empty" ? "No lineage nodes" : this.state === "invalid" ? "Unable to render lineage data" : "No lineage data", t.append(n), this.state === "invalid") {
			let e = this.diagnostics.find((e) => e.level === "error");
			if (e) {
				let n = document.createElement("p");
				n.textContent = e.message, t.append(n);
			}
		}
		this.root.append(t);
	}
	applyInteractionState() {
		this.renderer?.setInteractionState(E(this.graph, this.selectedId, this.resolvedOptions.highlightMode));
	}
	updateSelection(e, t) {
		if (e === this.selectedId) return;
		let n = this.selectedId;
		this.selectedId = e, this.applyInteractionState();
		let r = e === null ? null : this.graph?.nodeById.get(e) ?? null;
		this.dispatchEvent(new CustomEvent("lineage-selection-change", {
			detail: {
				selectedNodeId: e,
				previousSelectedNodeId: n,
				node: r === null ? null : { ...r },
				source: t
			},
			bubbles: !0,
			composed: !0
		}));
	}
	findSceneNode(e) {
		let t = e.trim();
		return t ? this.scene?.nodes.find((e) => e.id === t) : void 0;
	}
	onWheel = (e) => {
		if (this.state !== "rendered") return;
		e.preventDefault();
		let t = this.eventPoint(e);
		this.viewport?.zoom(t, Math.exp(-e.deltaY * .002));
	};
	onPointerDown = (e) => {
		e.button !== 0 || this.state !== "rendered" || e.target instanceof Element && e.target.closest(".node") || (this.drag = {
			pointerId: e.pointerId,
			x: e.clientX,
			y: e.clientY,
			moved: !1
		}, this.renderer?.svg.setPointerCapture(e.pointerId), this.renderer?.svg.setAttribute("data-panning", ""));
	};
	onPointerMove = (e) => {
		if (!this.drag || e.pointerId !== this.drag.pointerId) return;
		let t = e.clientX - this.drag.x, n = e.clientY - this.drag.y;
		Math.abs(t) + Math.abs(n) > 3 && (this.drag.moved = !0), this.drag.x = e.clientX, this.drag.y = e.clientY, this.viewport?.pan(t, n);
	};
	onPointerEnd = (e) => {
		!this.drag || e.pointerId !== this.drag.pointerId || (this.suppressClick = this.drag.moved, this.renderer?.svg.hasPointerCapture(e.pointerId) && this.renderer.svg.releasePointerCapture(e.pointerId), this.drag = null, this.renderer?.svg.removeAttribute("data-panning"));
	};
	onClick = (e) => {
		if (this.suppressClick) {
			this.suppressClick = !1;
			return;
		}
		let t = (e.target instanceof Element ? e.target.closest(".node") : null)?.dataset.nodeId;
		if (t && this.graph) {
			let e = this.graph.nodeById.get(t);
			if (!e) return;
			this.dispatchEvent(new CustomEvent("lineage-node-click", {
				detail: {
					nodeId: t,
					node: { ...e }
				},
				bubbles: !0,
				composed: !0
			})), this.updateSelection(t, "pointer");
		} else this.updateSelection(null, "pointer");
	};
	eventPoint(e) {
		let t = this.renderer?.svg.getBoundingClientRect(), n = this.size();
		return t && t.width > 0 && t.height > 0 ? {
			x: (e.clientX - t.left) * n.width / t.width,
			y: (e.clientY - t.top) * n.height / t.height
		} : {
			x: 0,
			y: 0
		};
	}
	size() {
		let e = this.renderer?.svg.getBoundingClientRect();
		return {
			width: e?.width ?? 0,
			height: e?.height ?? 0
		};
	}
	observe() {
		if (this.resizeObserver || typeof ResizeObserver > "u") {
			typeof ResizeObserver > "u" && (this.hasObservedViewport = !0, this.dispatchReadyIfPossible());
			return;
		}
		this.resizeObserver = new ResizeObserver((e) => {
			let t = e[0];
			if (!t || this.state === "destroyed") return;
			let { width: n, height: r } = t.contentRect;
			this.renderer?.setViewportSize(n, r), this.viewport?.resize({
				width: n,
				height: r
			}, this.resolvedOptions.fitOnLoad), this.hasObservedViewport = n > 0 && r > 0, this.dispatchReadyIfPossible();
		}), this.resizeObserver.observe(this);
	}
	stopObserving() {
		this.resizeObserver?.disconnect(), this.resizeObserver = null;
	}
	dispatchReadyIfPossible() {
		this.readyDispatched || !this.hasObservedViewport || !this.isConnected || this.state !== "empty" && this.state !== "rendered" || (this.readyDispatched = !0, this.dispatchEvent(new CustomEvent("lineage-ready", {
			detail: {
				nodeCount: this.graph?.nodes.length ?? 0,
				edgeCount: this.graph?.edges.length ?? 0,
				state: this.state
			},
			bubbles: !0,
			composed: !0
		})));
	}
	emitDiagnostics() {
		let e = this.diagnostics.filter((e) => e.level === "error"), t = this.diagnostics.filter((e) => e.level === "warning");
		this.emit("lineage-error", e, !0), this.emit("lineage-warning", t, !1);
	}
	emit(e, t, n) {
		t.length !== 0 && this.dispatchEvent(new CustomEvent(e, {
			detail: {
				diagnostics: t.map((e) => ({ ...e })),
				hasErrors: n
			},
			bubbles: !0,
			composed: !0
		}));
	}
};
function $(e) {
	return {
		x: 0,
		y: 0,
		width: e.width,
		height: e.height
	};
}
function we(e) {
	return {
		source: e.source,
		target: e.target,
		...e.id === void 0 ? {} : { id: e.id },
		...e.label === "" ? {} : { label: e.label },
		...e.type === "lineage" ? {} : { type: e.type },
		...e.metadata === void 0 ? {} : { metadata: e.metadata }
	};
}
//#endregion
//#region src/registration.ts
function Te() {
	return typeof customElements < "u" && !customElements.get("lineage-viewer") && customElements.define("lineage-viewer", Q), Q;
}
//#endregion
export { Q as n, Te as t };

//# sourceMappingURL=registration-C_mWQXsE.js.map