// ESLint flat config for the browser scripts in app/static (run: npx eslint app/static).
export default [
  {
    files: ["app/static/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: {
        window: "readonly", document: "readonly", fetch: "readonly", location: "readonly", navigator: "readonly",
        console: "readonly", setTimeout: "readonly", clearTimeout: "readonly", localStorage: "readonly",
        URLSearchParams: "readonly", FormData: "readonly", Intl: "readonly", L: "readonly", alert: "readonly",
        confirm: "readonly", prompt: "readonly", history: "readonly", Blob: "readonly", URL: "readonly",
        requestAnimationFrame: "readonly", setInterval: "readonly", clearInterval: "readonly", getComputedStyle: "readonly", Event: "readonly",
        Draw3V: "readonly", Draw3VParts: "readonly", Draw3VFamilies: "readonly", Blueprint: "readonly",
        $: "readonly", esc: "readonly",
      },
    },
    rules: {
      // page scripts expose top-level functions to inline HTML handlers, so only locals must be used
      "no-unused-vars": ["error", { vars: "local", args: "none", caughtErrors: "none" }],
      "no-undef": "error",
      "no-redeclare": "error",
      "no-dupe-keys": "error",
      "no-unreachable": "error",
      "eqeqeq": ["error", "smart"],
      "prefer-const": "error",
      "no-var": "error",
    },
  },
  {
    // common.js is where the shared page helpers are defined
    files: ["app/static/js/common.js"],
    languageOptions: { globals: { $: "off", esc: "off" } },
  },
];
