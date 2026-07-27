import type { Lang } from "../i18n";
import { useSetLang, useT } from "../i18n";

const OPTIONS: Lang[] = ["de", "en"];

/** Segmented DE/EN toggle. Switching relabels the app, and the generated
 *  report and offline bundle follow the same choice. */
export function LanguageSwitch() {
  const { lang, t } = useT();
  const setLang = useSetLang();

  return (
    <div
      className="flex overflow-hidden rounded-md border border-edge bg-black/30"
      role="group"
      aria-label={t("app.language")}
    >
      {OPTIONS.map((option) => (
        <button
          key={option}
          onClick={() => setLang(option)}
          aria-pressed={option === lang}
          className={`px-2.5 py-1 text-xs font-semibold uppercase transition ${
            option === lang
              ? "bg-edge text-gray-100"
              : "text-gray-500 hover:bg-edge/60 hover:text-gray-300"
          }`}
        >
          {option}
        </button>
      ))}
    </div>
  );
}
