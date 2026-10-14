"use strict";

// Run the Google Analytics scripts of a built docs page against a stub
// browser and print what they did as JSON.
//
// Usage: node docs_google_analytics_harness.cjs PAGE.html SIGNALS_JSON
// SIGNALS_JSON sets Do-Not-Track, for example {"navigator.doNotTrack": "1"}.
//
// It runs every inline <script> in <head> that mentions __md_analytics, in
// page order: Material's definition (or this repo's override of it) and the
// call that Material emits, then fires DOMContentLoaded and one instant
// navigation. It reports the script URLs the page inserted and the gtag
// commands it queued.

const { readFileSync } = require("node:fs");
const vm = require("node:vm");

const [page, signalsJson] = process.argv.slice(2);
const signals = JSON.parse(signalsJson || "{}");
const head = readFileSync(page, "utf8").split("</head>")[0];
const scripts = [...head.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)]
  .map((match) => match[1])
  .filter((source) => source.includes("__md_analytics"));

const inserted = [];
const loaded = [];
function element() {
  return {
    insertAdjacentElement(_position, node) {
      inserted.push(node.src);
    },
  };
}
const document = {
  createElement: () => ({}),
  getElementById: () => element(),
  getElementsByTagName: () => [{ parentNode: { insertBefore: (node) => inserted.push(node.src) } }],
  addEventListener: (type, listener) => type === "DOMContentLoaded" && loaded.push(listener),
  forms: {},
};
const navigator = {};
const context = { document, navigator, location: { pathname: "/" }, console };
context.window = context;
for (const [path, value] of Object.entries(signals)) {
  const [owner, name] = path.split(".");
  (owner === "navigator" ? navigator : context)[name] = value;
}
vm.createContext(context);
for (const source of scripts) {
  vm.runInContext(source, context);
}
// Material's observables for instant navigation: one page load, one page.
context.document$ = { subscribe: (next) => next() };
context.location$ = { subscribe: (next) => next({ pathname: "/evaluate/" }) };
for (const listener of loaded) {
  listener();
}

process.stdout.write(
  JSON.stringify({
    scripts: scripts.length,
    inserted,
    dataLayer: (context.dataLayer || []).map((entry) => Array.from(entry)),
  }),
);
