import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import hi from "./locales/hi.json";
import gu from "./locales/gu.json";

export const LANGUAGES = [
  ["en", "English"],
  ["hi", "हिन्दी"],
  ["gu", "ગુજરાતી"],
];

const STORAGE_KEY = "crimegpt_lang";
const saved = localStorage.getItem(STORAGE_KEY);
const initial = LANGUAGES.some(([c]) => c === saved) ? saved : "en";

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    hi: { translation: hi },
    gu: { translation: gu },
  },
  lng: initial,
  fallbackLng: "en",
  interpolation: { escapeValue: false }, // React already escapes
});

// Persist the choice so it survives reloads / next sign-in.
i18n.on("languageChanged", (lng) => localStorage.setItem(STORAGE_KEY, lng));

export default i18n;
