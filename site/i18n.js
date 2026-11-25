// Shared language handling for every page.
const I18N = {
  lang: localStorage.getItem("lang") || ((navigator.language || "es").startsWith("es") ? "es" : "en"),
  dict: {},
  async load(lang) {
    this.lang = lang;
    localStorage.setItem("lang", lang);
    document.documentElement.lang = lang;
    this.dict = await (await fetch(`i18n/${lang}.json`)).json();
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = this.t(el.dataset.i18n);
    });
    document.querySelectorAll("[data-lang]").forEach((el) => {
      el.hidden = el.dataset.lang !== lang;
    });
    document.title = this.t(document.body.dataset.titleKey || "title");
  },
  t(key, params = {}) {
    const s = this.dict[key] ?? key;
    return s.replace(/\{(\w+)\}/g, (_, k) => params[k] ?? "");
  },
  toggle() {
    return this.load(this.lang === "es" ? "en" : "es");
  },
};
