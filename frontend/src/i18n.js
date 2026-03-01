/**
 * i18n.js — Internationalization for English ↔ Arabic
 * =====================================================
 * Simple key-based translation system. No heavy library needed.
 */

const translations = {
  en: {
    // Status bar
    sentinel: 'SENTINEL',
    connecting: 'Connecting…',
    backtest: 'BACKTEST',
    danger: 'DANGER',
    warning: 'WARNING',
    hexes: 'hexes',
    live: 'live',
    backtestBtn: '⏪ BACKTEST',

    // Launch page
    tagline: 'Conflict Risk Intelligence · Levant',
    monitoredHexes: 'Monitored Hexes',
    modelAuc: 'Model AUC',
    updateCycle: 'Update Cycle',
    enter: 'ENTER',
    disclaimer: 'For situational awareness only · Not a substitute for official advisories',

    // HexSidebar
    loading: 'Loading…',
    noData: 'No data for this hex.',
    activeTriggers: 'Active triggers',
    intelSummary: 'Intelligence Summary',
    webGrounded: 'web-grounded',
    noIntel: 'No recent intelligence available for this area.',
    mlProbability: 'ML escalation probability',
    tacticalScore: 'Tactical score',
    gdeltSignals: 'GDELT news signals (latest week)',
    hostility: 'Hostility',
    avgTone: 'Avg tone',
    minGoldstein: 'Min Goldstein',
    articles: 'Articles',
    firmsThermal: 'NASA FIRMS thermal (latest week)',
    hotspots: 'Hotspots',
    maxFrp: 'Max FRP',
    spikeFlag: 'Spike flag',
    yes: 'Yes',
    no: 'No',
    recentEvents: 'Recent ACLED events',
    fatalities: 'fatalities',
    scoredAt: 'Scored at',
    hexCluster: 'hexes in cluster',

    // Area briefing
    areaBriefing: 'AREA BRIEFING',
    updating: 'updating…',
    panMap: 'Pan the map to generate a conflict briefing for the visible area.',
    sitOverview: 'Situation Overview',
    threatDist: 'Threat Distribution',
    activeSignals: 'Active Signals',
    hexesInView: 'hexes in view',
    scored: 'scored',

    // Backtest slider
    red: 'RED',
    orange: 'ORANGE',
    yellow: 'YELLOW',
    exitBacktest: 'EXIT BACKTEST',

    // Evacuation
    evacuate: 'EVACUATE',
    evacRoute: 'Evacuation Route',
    findingSafe: 'Finding safest route…',
    routeDistance: 'Route distance',
    safetyScore: 'Safety score',
    dangerAvoided: 'Danger zones avoided',
    nearestShelter: 'Nearest safe facility',
    closeRoute: 'CLOSE ROUTE',
    clickToEvac: 'Click any point on the map to find a safe evacuation route',

    // Shelters
    showShelters: 'Shelters',
    hospitals: 'Hospitals',
    unShelters: 'UN Shelters',
    redCross: 'Red Cross',
    evacPoints: 'Evacuation Points',
    borderCrossings: 'Border Crossings',

    // Backtest events
    evtOct7: 'Hamas attack on Israel',
    evtOct17: 'Al-Ahli hospital blast',
    evtOct27: 'IDF ground incursion',
    evtNov24: 'Israel-Hamas truce begins',
    evtJan2: 'Al-Arouri assassinated',
    evtApr1: 'Strike on Iran consulate',
    evtApr13: 'Iran retaliatory attack',
    evtSep17: 'Lebanon pager attacks',
    evtSep23: 'Massive strikes on Lebanon',
    evtOct1_24: 'Israel invades Lebanon',
    evtNov27: 'Israel-Lebanon ceasefire',

    // Language
    langToggle: 'عربي',
  },
  ar: {
    // Status bar
    sentinel: 'سِنتينِل',
    connecting: 'جارٍ الاتصال…',
    backtest: 'محاكاة',
    danger: 'خطر',
    warning: 'تحذير',
    hexes: 'منطقة',
    live: 'مباشر',
    backtestBtn: '⏪ محاكاة',

    // Launch page
    tagline: 'استخبارات مخاطر النزاع · المشرق',
    monitoredHexes: 'مناطق مراقبة',
    modelAuc: 'دقة النموذج',
    updateCycle: 'دورة التحديث',
    enter: 'ادخل',
    disclaimer: 'للتوعية الظرفية فقط · لا يُغني عن الاستشارات الرسمية',

    // HexSidebar
    loading: 'جارٍ التحميل…',
    noData: 'لا توجد بيانات لهذه المنطقة.',
    activeTriggers: 'المؤشرات النشطة',
    intelSummary: 'ملخص استخباراتي',
    webGrounded: 'مصادر حية',
    noIntel: 'لا تتوفر معلومات استخباراتية حديثة لهذه المنطقة.',
    mlProbability: 'احتمالية التصعيد',
    tacticalScore: 'الدرجة التكتيكية',
    gdeltSignals: 'إشارات الأخبار (آخر أسبوع)',
    hostility: 'العدائية',
    avgTone: 'متوسط النبرة',
    minGoldstein: 'أدنى غولدشتاين',
    articles: 'المقالات',
    firmsThermal: 'الاستشعار الحراري (آخر أسبوع)',
    hotspots: 'نقاط ساخنة',
    maxFrp: 'أقصى طاقة إشعاعية',
    spikeFlag: 'ارتفاع مفاجئ',
    yes: 'نعم',
    no: 'لا',
    recentEvents: 'أحداث حديثة',
    fatalities: 'ضحايا',
    scoredAt: 'تم التقييم في',
    hexCluster: 'منطقة في المجموعة',

    // Area briefing
    areaBriefing: 'إحاطة المنطقة',
    updating: 'جارٍ التحديث…',
    panMap: 'حرّك الخريطة لإنشاء إحاطة عن منطقة النزاع المرئية.',
    sitOverview: 'نظرة عامة على الوضع',
    threatDist: 'توزيع التهديدات',
    activeSignals: 'الإشارات النشطة',
    hexesInView: 'منطقة مراقبة',
    scored: 'تم التقييم',

    // Backtest slider
    red: 'أحمر',
    orange: 'برتقالي',
    yellow: 'أصفر',
    exitBacktest: 'إنهاء المحاكاة',

    // Evacuation
    evacuate: 'إخلاء',
    evacRoute: 'مسار الإخلاء',
    findingSafe: 'جارٍ البحث عن أسلم طريق…',
    routeDistance: 'مسافة المسار',
    safetyScore: 'درجة الأمان',
    dangerAvoided: 'مناطق خطر تم تجنبها',
    nearestShelter: 'أقرب مرفق آمن',
    closeRoute: 'إغلاق المسار',
    clickToEvac: 'اضغط على أي نقطة على الخريطة لإيجاد طريق إخلاء آمن',

    // Shelters
    showShelters: 'الملاجئ',
    hospitals: 'المستشفيات',
    unShelters: 'ملاجئ الأمم المتحدة',
    redCross: 'الصليب الأحمر',
    evacPoints: 'نقاط الإخلاء',
    borderCrossings: 'المعابر الحدودية',

    // Backtest events
    evtOct7: 'هجوم حماس على إسرائيل',
    evtOct17: 'انفجار مستشفى الأهلي',
    evtOct27: 'التوغل البري الإسرائيلي',
    evtNov24: 'بدء الهدنة بين إسرائيل وحماس',
    evtJan2: 'اغتيال العاروري',
    evtApr1: 'ضرب القنصلية الإيرانية',
    evtApr13: 'الهجوم الإيراني الانتقامي',
    evtSep17: 'هجمات أجهزة النداء في لبنان',
    evtSep23: 'ضربات واسعة على لبنان',
    evtOct1_24: 'إسرائيل تغزو لبنان',
    evtNov27: 'وقف إطلاق النار بين إسرائيل ولبنان',

    // Language
    langToggle: 'EN',
  },
}

// Global state
let currentLang = 'en'
const listeners = new Set()

export function t(key) {
  return translations[currentLang]?.[key] || translations.en[key] || key
}

export function getLang() {
  return currentLang
}

export function setLang(lang) {
  currentLang = lang
  listeners.forEach(fn => fn(lang))
}

export function toggleLang() {
  setLang(currentLang === 'en' ? 'ar' : 'en')
}

export function isRTL() {
  return currentLang === 'ar'
}

export function onLangChange(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}
