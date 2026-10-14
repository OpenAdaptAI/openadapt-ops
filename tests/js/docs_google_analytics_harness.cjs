"use strict";

// Run the Google Analytics scripts of a built docs page against a stub
// browser and print what they did as JSON.
//
// Usage: node docs_google_analytics_harness.cjs PAGE.html SIGNALS_JSON
// SIGNALS_JSON sets Do-Not-Track, for example {"navigator.doNotTrack": "1"}.
//
// It runs every inline <script> in <head> that mentions __md_analytics, in
// page order: Material's definition (or this repo's override of it) and the
// call that Material emits, then fires DOMContentLoaded, one instant
// navigation, and one search (the search box loses focus holding SEARCH_QUERY).
// It reports the script URLs the page inserted and the gtag commands it queued.

const { readFileSync } = require("node:fs");
const vm = require("node:vm");

const [page, signalsJson] = process.argv.slice(2);
const signals = JSON.parse(signalsJson || "{}");
const head = readFileSync(page, "utf8").split("</head>")[0];
const scripts = [...head.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)]
  .map((match) => match[1])
  .filter((source) => source.includes("__md_analytics"));

// A query a reader might type. Google Analytics must never receive its text.
const SEARCH_QUERY = "private search words";

const inserted = [];
const loaded = [];
const blurred = [];
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
  forms: {
    search: {
      query: {
        addEventListener: (type, listener) => type === "blur" && blurred.push(listener),
      },
    },
  },
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
for (const listener of blurred) {
  listener.call({ value: SEARCH_QUERY });
}

process.stdout.write(
  JSON.stringify({
    scripts: scripts.length,
    searchQuery: SEARCH_QUERY,
    inserted,
    dataLayer: (context.dataLayer || []).map((entry) => Array.from(entry)),
  }),
);
