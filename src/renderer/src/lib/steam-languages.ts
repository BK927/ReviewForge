export const STEAM_LANGUAGES: Record<string, string> = {
  english: 'English',
  koreana: '한국어',
  japanese: '日本語',
  schinese: '简体中文',
  tchinese: '繁體中文',
  russian: 'Русский',
  spanish: 'Español (ES)',
  latam: 'Español (LA)',
  french: 'Français',
  german: 'Deutsch',
  portuguese: 'Português',
  brazilian: 'Português (BR)',
  italian: 'Italiano',
  polish: 'Polski',
  turkish: 'Türkçe',
  thai: 'ไทย',
  vietnamese: 'Tiếng Việt',
  ukrainian: 'Українська',
  czech: 'Čeština',
  dutch: 'Nederlands',
  hungarian: 'Magyar',
  romanian: 'Română',
  swedish: 'Svenska',
  finnish: 'Suomi',
  danish: 'Dansk',
  norwegian: 'Norsk',
  indonesian: 'Bahasa Indonesia',
  arabic: 'العربية',
  greek: 'Ελληνικά',
  bulgarian: 'Български'
}

export function getLanguageDisplayName(code: string): string {
  return STEAM_LANGUAGES[code] ?? code
}
