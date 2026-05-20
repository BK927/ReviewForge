from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Any

import duckdb
import httpx

from .db import connect, utcnow
from .repository import rows_to_dicts


DEFAULT_SEMANTIC_EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
DEFAULT_EMBEDDING_MODEL = DEFAULT_SEMANTIC_EMBEDDING_MODEL
LOCAL_HASH_EMBEDDING_MODEL = "local-hash-v1"
LM_STUDIO_OPENAI_BASE_URL = "http://127.0.0.1:1234/v1"
LM_STUDIO_NATIVE_BASE_URL = "http://127.0.0.1:1234/api/v1"
ISSUE_VERIFIER_BATCH_SIZE = 6
MAX_LMSTUDIO_ISSUE_CARDS = 12


@dataclass(frozen=True)
class Theme:
    key: str
    label: str
    pattern: str
    summary: str


@dataclass(frozen=True)
class ThemeMatch:
    theme: Theme
    source: str
    count: int
    support_review_count: int
    coverage: float
    matched_terms: list[str]
    confidence: str
    warnings: list[str]
    accepted: bool


@dataclass(frozen=True)
class AnalysisPipelineResult:
    reviews_analyzed: int
    clusters_created: int
    evidence_created: int
    clusterer: str
    message: str
    issues_created: int = 0
    issue_evidence_created: int = 0
    axis_suggestions_created: int = 0


@dataclass(frozen=True)
class ReviewQuality:
    review_id: str
    normalized_text: str
    text_hash: str
    quality_score: float
    quality_flags: list[str]
    duplicate_count: int


@dataclass(frozen=True)
class ClusterInsight:
    title: str
    summary: str
    praise: str
    pain_point: str
    planner_action: str
    marketing_angle: str
    confidence: float
    warnings: list[str]
    source: str = "deterministic"
    model: str | None = None


@dataclass(frozen=True)
class IssueAspect:
    key: str
    label: str
    pattern: str
    summary: str
    recommended_action: str


@dataclass(frozen=True)
class ClaimAxisRule:
    key: str
    label: str
    terms: tuple[str, ...]
    target_axis_keys: tuple[str, ...]
    definition: str
    include_criteria: tuple[str, ...]
    exclude_criteria: tuple[str, ...]
    why_actionable: str
    min_terms: int = 2


THEMES = [
    Theme(
        "late_loop",
        "후반 반복성과 보상 밀도",
        r"late|repeat|repetitive|reward|loop|grind|endgame|보상|반복|후반|루프|recompensa|repetir|報酬|繰り返",
        "후반 플레이에서 반복감, 보상 변화, 장기 동기 문제가 함께 언급됩니다.",
    ),
    Theme(
        "combat",
        "전투 손맛과 보스전 긴장감",
        r"combat|boss|fight|rhythm|weapon feel|전투|보스|손맛|타격|戦闘|ボス",
        "전투 감각, 무기별 리듬, 보스전 압박감이 핵심 경험으로 반복됩니다.",
    ),
    Theme(
        "balance",
        "무기 밸런스와 빌드 선택지",
        r"balance|build|weapon choice|weapons fall|narrow|밸런스|빌드|무기|选择|構成|ビルド|平衡",
        "패치나 성장 구조 이후 무기 밸런스와 빌드 다양성에 대한 반응이 모입니다.",
    ),
    Theme(
        "presentation",
        "아트와 캐릭터 매력",
        r"art|character|atmosphere|illustration|music|visual|아트|캐릭터|분위기|음악|美術|キャラクター",
        "캐릭터 표현, 시각 연출, 음악, 분위기가 강점으로 언급됩니다.",
    ),
    Theme(
        "performance",
        "성능과 안정성",
        r"performance|crash|fps|stutter|bug|loading|성능|버그|튕김|프레임|クラッシュ|卡顿",
        "성능, 충돌, 프레임, 버그처럼 플레이 안정성과 관련된 신호가 묶입니다.",
    ),
    Theme(
        "ui",
        "UI와 가독성",
        r"ui|menu|readability|text|font|interface|가독성|메뉴|인터페이스|글자|읽기|界面",
        "메뉴, 텍스트, 가독성, 조작 흐름에 대한 사용성 의견이 나타납니다.",
    ),
]

GAME_THEMES: dict[str, list[Theme]] = {
    "730": [
        Theme("cheaters", "치터/VAC 신뢰", r"cheat|cheater|hacker|vac|spinbot|aimbot|wallhack|читер|читер", "치터, 핵, VAC 대응 신뢰도에 대한 반응입니다."),
        Theme("servers", "서버와 연결 안정성", r"server|tick|ping|lag|packet|disconnect|서버|핑|랙|тик|пинг", "서버 품질, 지연, 접속 안정성 문제가 함께 언급됩니다."),
        Theme("matchmaking", "매치메이킹과 랭크", r"matchmaking|rank|premier|elo|teammate|mmr|매치|랭크|рейтин", "매치 품질, 랭크, 팀 구성에 대한 의견입니다."),
        Theme("performance", "성능과 프레임", r"fps|frame|stutter|crash|freeze|performance|프레임|성능|卡顿", "프레임 드랍, 튕김, 끊김 같은 성능 신호입니다."),
        Theme("csgo_compare", "CS:GO와 변화 비교", r"csgo|cs:go|cs 2|cs2|old cs|source|글옵", "이전 버전과 비교해 달라진 점에 대한 반응입니다."),
        Theme("ui", "UI와 가독성", r"ui|interface|menu|hud|readability|font|메뉴|가독성|интерфейс", "UI, HUD, 메뉴, 가독성에 대한 사용성 의견입니다."),
    ],
    "413150": [
        Theme("cozy", "힐링감과 몰입", r"cozy|relax|chill|comfort|힐링|농장|relaxing|уют", "편안함, 몰입감, 장기 플레이 만족에 대한 반응입니다."),
        Theme("content", "콘텐츠 볼륨", r"content|update|quest|event|festival|콘텐츠|업데이트", "즐길 거리, 업데이트, 이벤트 볼륨에 대한 의견입니다."),
        Theme("multiplayer", "멀티플레이와 협동", r"multiplayer|coop|co-op|friend|친구|멀티", "친구와 함께 하는 플레이 경험에 대한 신호입니다."),
        Theme("mods", "모드와 커뮤니티", r"mod|mods|workshop|community|모드", "모드 친화성과 커뮤니티 확장성에 대한 반응입니다."),
    ],
    "2379780": [
        Theme("addictive", "중독성 있는 반복 플레이", r"addictive|again|one more|replay|중독|한판|もう一回", "계속 다시 하게 만드는 루프에 대한 호평입니다."),
        Theme("deckbuilding", "카드 조합과 덱빌딩", r"deck|card|poker|hand|blind|joker|build|combo|synergy|카드|덱|포커|조커|시너지|组合|卡牌", "카드 조합, 조커 시너지, 덱빌딩 선택지에 대한 반응입니다."),
        Theme("jimbo_meme", "Jimbo와 밈 반응", r"jimbo|clown|meme|mémé|밈|광대", "Jimbo, 광대 캐릭터, 밈성 반응처럼 커뮤니티 농담에 가까운 의견입니다."),
        Theme("rng", "운과 밸런스", r"rng|luck|random|balance|joker|seed|운빨|밸런스", "랜덤성, 조커 조합, 밸런스에 대한 의견입니다."),
        Theme("difficulty", "난이도와 진척", r"difficulty|hard|ante|stake|progress|난이도|어려", "난이도 곡선과 진행 체감에 대한 반응입니다."),
    ],
    "1859910": [
        Theme("update_completion", "업데이트와 완성도 기대", r"update|unfinished|incomplete|early access|route|ending|chapter|更新|画饼|文本|未完成|路线|结局|업데이트|미완성|루트|엔딩|분기|텍스트|회차", "업데이트 약속, 완성도, 분기/엔딩/텍스트 추가 기대가 함께 언급됩니다."),
        Theme("route_guidance", "분기와 공략 의존", r"hint|guide|walkthrough|choice|choices|route|ending|gallery|힌트|공략|선택지|분기|루트|엔딩|도감|暗示|攻略|选择|路线|结局|图鉴", "분기 조건, 힌트 부족, 공략 의존, 엔딩 접근성 의견이 모입니다."),
        Theme("martial_story", "무협 서사와 인물 매력", r"martial|wuxia|heroine|character|story|route|무협|협객|히로인|캐릭터|스토리|서사|剧情|武侠|侠客|女主|角色|人设|故事", "무협 분위기, 인물 매력, 루트별 서사에 대한 반응입니다."),
    ],
    "3101040": [
        Theme("mystery_logic", "추리/재판/마법 규칙", r"mystery|deduction|logic|trick|magic|case|danganronpa|trial|reasoning|추리|논리|트릭|마법|재판|단간|개연성|억지|推理|逻辑|诡计|魔法|审判|弹丸|裁判", "추리 파트, 재판 전개, 마법 규칙, 트릭 납득감이 주요 평가 포인트로 반복됩니다."),
        Theme("chapter_replay", "챕터/회차 편의", r"chapter|chapter select|replay|skip|save|one more|周目|チャプター|もう一周|챕터|회차|스킵|저장|다시", "챕터 선택, 재플레이, 회상/스킵 같은 장문 서사 게임의 반복 플레이 편의 신호입니다."),
        Theme("character_voice", "캐릭터/연출/더빙", r"character|voice|acting|design|cg|art|캐릭터|캐디|더빙|성우|디자인|일러|연출|角色|配音|人设|立绘|演出|キャラ|ボイス", "캐릭터 디자인, 더빙, 연출이 만족도와 구매 이유로 언급됩니다."),
    ],
    "1456820": [
        Theme("short_content", "짧은 분량과 엔딩 반복", r"short|too short|content|volume|ending|endings|replay|less than|hour|분량|짧|컨텐츠|콘텐츠|볼륨|엔딩|다회차|1시간|ボリューム|短い|エンディング|结局|内容少", "짧은 플레이타임, 엔딩 반복, 콘텐츠 볼륨에 대한 반응입니다."),
        Theme("weapon_card_rng", "무기/카드 RNG", r"weapon|weapons|card|cards|rng|random|luck|durability|shotgun|grenade|무기|카드|운|랜덤|내구도|샷건|유탄|武器|カード|運|ランダム|耐久|霰弹枪", "무기 카드, 랜덤 제시, 내구도, 빌드 선택의 운 의존 신호입니다."),
        Theme("bleak_ending_tone", "엔딩 톤과 구원감", r"ending|endings|bad end|good end|救い|虚無|暗い|엔딩|배드엔딩|굿엔딩|구원|허무|우울|结局|坏结局", "엔딩의 어두운 톤, 구원감 부족, 결말 만족도에 대한 반응입니다."),
    ],
}

ACTION_THEME_KEYS = {"combat", "balance"}
APP_BLOCKED_GLOBAL_THEME_KEYS: dict[str, set[str]] = {
    "3101040": ACTION_THEME_KEYS,
}
APP_BLOCKED_GENERIC_ASPECT_KEYS: dict[str, set[str]] = {
    "3101040": {"balance"},
}

GENERIC_ISSUE_ASPECTS = [
    IssueAspect(
        "performance",
        "성능/안정성",
        r"crash|bug|bugs|broken|freeze|low fps|fps drop|fps issue|frame drop|frame rate|stutter|lag|loading|performance|optimization|disconnect|튕김|튕|버그|프레임|렉|랙|끊김|멈춤|최적화|クラッシュ|バグ|卡顿|崩溃",
        "성능, 충돌, 버그, 지연처럼 플레이 안정성을 직접 해치는 신호입니다.",
        "재현 가능한 환경, 플랫폼, 최근 패치 이후 증가 여부를 먼저 확인하세요.",
    ),
    IssueAspect(
        "balance",
        "밸런스/RNG",
        r"balance|balanced|unbalanced|rng|luck|random|unfair|overpowered|op|nerf|buff|밸런스|운빨|운|랜덤|불공평|사기|너프|버프|ランダム|運|平衡",
        "무작위성, 난이도 체감, 선택지 효율 차이에 대한 신호입니다.",
        "불만이 집중되는 빌드/구간/조건을 분리해 수치 조정 후보로 검토하세요.",
    ),
    IssueAspect(
        "progression",
        "난이도/진척",
        r"difficulty|hard|easy|progress|progression|grind|unlock|level|rank|reward|난이도|어려|쉬움|진행|진척|해금|노가다|보상|레벨",
        "진행 속도, 해금, 보상, 난이도 곡선에 대한 신호입니다.",
        "초반/중반/후반 어느 구간에서 막히는지 플레이타임별로 다시 확인하세요.",
    ),
    IssueAspect(
        "content_repetition",
        "반복성/콘텐츠",
        r"repetitive|repeat|same|boring|bored|content|endgame|late game|loop|variety|반복|지루|콘텐츠|컨텐츠|후반|엔드게임|다양성|飽き|繰り返",
        "콘텐츠 다양성, 반복감, 장기 플레이 동기에 대한 신호입니다.",
        "새 목표, 변주, 보상 밀도 중 무엇이 부족한지 근거 리뷰를 나눠 보세요.",
    ),
    IssueAspect(
        "ui_onboarding",
        "UI/가독성/온보딩",
        r"\bui\b|\bux\b|\binterface\b|\bmenu\b|\bhud\b|\breadability\b|\bfont\b|\btext\b|\btutorial\b|\bexplain|confusing|\bcontrols?\b|\bcontroller\b|키설정|조작|가독성|메뉴|인터페이스|글자|튜토리얼|설명|헷갈|읽기|界面|文字",
        "메뉴, 조작, 설명, 가독성처럼 이해와 반복 사용을 방해하는 신호입니다.",
        "첫 플레이와 장기 플레이를 나눠, 설명 부족인지 조작 피로인지 분리하세요.",
    ),
    IssueAspect(
        "content_missing",
        "누락/비교",
        r"missing|removed|less than|worse than|compared|where is|bring back|lack|lacks|없어|빠졌|부족|돌려|비교|以前|戻して",
        "이전작/경쟁작/기대치와 비교해 빠졌다고 느끼는 요소입니다.",
        "실제 누락 기능인지 기대 관리 문제인지 패치 노트와 함께 확인하세요.",
    ),
    IssueAspect(
        "story_logic",
        "스토리/세계관/엔딩",
        r"story|plot|logic|deduction|mystery|twist|foreshadow|case|trick|character|route|ending|스토리|서사|개연성|논리|추리|트릭|반전|떡밥|캐릭터|루트|엔딩|剧情|逻辑|推理|诡计|伏笔|角色|路线|结局|ストーリー|推理|伏線|キャラ",
        "스토리 전개, 세계관, 캐릭터 서사, 엔딩 납득감에 대한 신호입니다.",
        "불만이면 개연성/힌트/회수 문제로 쪼개고, 강점이면 후속작과 홍보의 핵심 약속으로 써도 되는지 확인하세요.",
    ),
    IssueAspect(
        "content_volume",
        "분량/완성도",
        r"short|too short|length|volume|content|incomplete|unfinished|early access|update|chapter|route|ending|replay|분량|볼륨|짧|컨텐츠|콘텐츠|미완성|업데이트|챕터|루트|엔딩|다회차|周目|ボリューム|短い|未完成|更新|章节|路线|结局|画饼|文本",
        "플레이 분량, 업데이트 기대, 미완성감, 다회차 동기에 대한 신호입니다.",
        "가격/분량 기대와 실제 플레이 루프를 나눠, 로드맵·DLC·패치 우선순위 후보로 검토하세요.",
    ),
    IssueAspect(
        "localization_readability",
        "번역/가독성",
        r"translation|localization|typo|subtitle|korean|english|japanese|chinese|readability|번역|한글화|오역|자막|가독성|텍스트|翻译|本地化|字幕|错字|読みづら|日本語|한국어",
        "번역, 자막, 텍스트 가독성, 언어 지원 품질에 대한 신호입니다.",
        "언어별 원문을 비교해 번역 품질 문제인지 텍스트 UI 문제인지 분리하세요.",
    ),
]

GAME_ISSUE_ASPECTS: dict[str, list[IssueAspect]] = {
    "730": [
        IssueAspect(
            "cheating",
            "치터/안티치트",
            r"cheat|cheater|hacker|hackers|vac|aimbot|wallhack|spinbot|anti cheat|anticheat|ban system|overwatch|치터|핵|해커|안티치트|월핵|에임핵|читер|читеры",
            "치터와 안티치트 신뢰가 직접적으로 언급되는 경쟁 품질 이슈입니다.",
            "치터 신고, 매치 품질, VAC 신뢰 언급을 분리해 우선순위를 높게 검토하세요.",
        ),
        IssueAspect(
            "matchmaking",
            "매치메이킹/랭크",
            r"matchmaking|match making|premier|rank|ranking|elo|mmr|teammate|team mate|smurf|bot lobby|bot lobbies|lobby|lobbies|매치|매칭|랭크|프리미어|팀원|смурф",
            "랭크, 프리미어, 팀 구성, 실력 매칭에 대한 신호입니다.",
            "불만이 솔로큐, 프리미어, 특정 랭크대에 몰리는지 확인하세요.",
        ),
        IssueAspect(
            "toxicity",
            "팀원/소통/독성",
            r"toxic|toxicity|racial slur|slurs|grief|griefing|troll|trolling|microphone|voice comm|voice chat|russian|turkish|team kill|팀킬|욕설|트롤|소통|마이크",
            "팀원 소통, 욕설, 트롤링, 지역/언어 갈등처럼 매치 경험을 해치는 커뮤니티 신호입니다.",
            "매치메이킹 문제와 분리해 신고/차단/음성 소통 UX 또는 커뮤니티 운영 이슈로 검토하세요.",
        ),
        IssueAspect(
            "server_netcode",
            "서버/서브틱/히트레지",
            r"server|servers|subtick|tick|hitreg|hit registration|ping|packet|rubberband|lag|서버|서브틱|틱|핑|랙|렉|히트|판정",
            "서버 품질, 지연, 탄 판정, 서브틱 체감에 대한 신호입니다.",
            "지역/시간대/핑과 함께 묶어 네트워크 문제인지 체감 문제인지 분리하세요.",
        ),
        IssueAspect(
            "csgo_regression",
            "CS:GO 대비 퇴보",
            r"csgo|cs:go|cs 2|cs2|source 2|old cs|bring back|missing maps|workshop|글옵|카스글옵",
            "CS:GO와 비교해 기능, 맵, 느낌이 줄었다는 신호입니다.",
            "비교 대상이 기능 누락인지 감각 변화인지 나눠 로드맵 후보로 정리하세요.",
        ),
    ],
    "2379780": [
        IssueAspect(
            "deck_synergy",
            "조커/덱 시너지",
            r"joker|jokers|deck|card|combo|synergy|build|hand|blind|조커|덱|카드|콤보|시너지|블라인드|포커|手札|カード",
            "조커, 카드 조합, 덱빌딩 선택지에 대한 신호입니다.",
            "특정 조커/카드 조합이 너무 강하거나 약하다는 근거를 분리하세요.",
        ),
        IssueAspect(
            "rng_luck",
            "RNG/운 의존",
            r"rng|luck|lucky|random|seed|reroll|운빨|운|랜덤|시드|리롤|運|ランダム",
            "런 성패가 실력보다 운에 좌우된다고 느끼는 신호입니다.",
            "실패 구간, 리롤 수단, 보상 선택지의 불만 근거를 우선 확인하세요.",
        ),
        IssueAspect(
            "stakes_progression",
            "스테이크/앤티 진행",
            r"stake|stakes|ante|difficulty|unlock|gold stake|orange stake|스테이크|앤티|난이도|해금",
            "스테이크, 앤티, 해금 구간에서 압박이 커진다는 신호입니다.",
            "어느 난이도 단계부터 불만이 증가하는지 패치 전후로 비교하세요.",
        ),
        IssueAspect(
            "mobile_platform",
            "플랫폼/휴대성",
            r"mobile|phone|ios|android|switch|steam deck|deck verified|portable|모바일|휴대|스위치|스팀덱|폰",
            "모바일, 스팀덱, 휴대 플레이 기대와 플랫폼 품질 신호입니다.",
            "플랫폼별 조작/저장/가격/성능 이슈를 따로 확인하세요.",
        ),
        IssueAspect(
            "gambling_framing",
            "도박/중독 프레이밍",
            r"gambling|casino|addiction|addictive|crack|drug|도박|중독|카지노|마약|ギャンブル",
            "게임 루프를 도박성/중독성으로 표현하는 반응입니다.",
            "호평 밈인지 실제 피로/우려인지 추천 여부와 문맥으로 분리하세요.",
        ),
    ],
    "1859910": [
        IssueAspect(
            "update_completion",
            "업데이트/완성도",
            r"update|unfinished|incomplete|early access|route|ending|chapter|更新|画饼|文本|未完成|路线|结局|업데이트|미완성|루트|엔딩|분기|텍스트|회차",
            "업데이트 약속, 완성도, 분기/엔딩/텍스트 추가 기대가 섞인 신호입니다.",
            "불만이면 로드맵 신뢰와 실제 추가 콘텐츠를 분리하고, 강점이면 업데이트로 다시 플레이할 이유가 되는지 확인하세요.",
        ),
        IssueAspect(
            "route_guidance",
            "분기/힌트/공략 의존",
            r"hint|guide|walkthrough|choice|choices|route|ending|gallery|힌트|공략|선택지|분기|루트|엔딩|도감|暗示|攻略|选择|路线|结局|图鉴",
            "분기 조건, 힌트 부족, 공략 의존, 엔딩 접근성에 대한 신호입니다.",
            "선택지 피드백, 실패 후 힌트, 도감/회상 UI를 개선 후보로 검토하세요.",
        ),
        IssueAspect(
            "martial_story",
            "무협 서사/인물 매력",
            r"martial|wuxia|heroine|character|story|route|무협|협객|히로인|캐릭터|스토리|서사|剧情|武侠|侠客|女主|角色|人设|故事",
            "무협 분위기, 인물 매력, 루트별 서사에 대한 신호입니다.",
            "강점이면 스토어 문구와 후속 콘텐츠의 핵심 약속으로 쓰고, 불만이면 특정 루트/인물의 서사 납득감을 점검하세요.",
        ),
    ],
    "3101040": [
        IssueAspect(
            "mystery_logic",
            "추리/재판/마법 규칙",
            r"mystery|deduction|logic|trick|magic|case|danganronpa|trial|reasoning|추리|논리|트릭|마법|재판|단간|개연성|억지|推理|逻辑|诡计|魔法|审判|弹丸|裁判",
            "추리 파트, 재판 전개, 마법 규칙, 트릭 납득감, 단간론파식 기대와의 비교 신호입니다.",
            "불만이면 추리 난이도보다 '힌트-증거-마법 규칙-결론'의 납득성 문제로 우선 확인하세요.",
        ),
        IssueAspect(
            "chapter_replay",
            "챕터/회차 편의",
            r"chapter|chapter select|replay|skip|save|one more|周目|チャプター|もう一周|챕터|회차|스킵|저장|다시",
            "챕터 선택, 재플레이, 회상/스킵처럼 장문 서사 게임의 반복 플레이 편의 신호입니다.",
            "재감상·분기 회수·추리 재검토를 돕는 기능 후보로 검토하세요.",
        ),
        IssueAspect(
            "character_voice",
            "캐릭터/연출/더빙",
            r"character|voice|acting|design|cg|art|캐릭터|캐디|더빙|성우|디자인|일러|연출|角色|配音|人设|立绘|演出|キャラ|ボイス",
            "캐릭터 디자인, 더빙, 연출이 구매 만족을 만드는 강점 신호입니다.",
            "강점이면 홍보 소재와 팬덤 확장 포인트로 쓰고, 불만이면 특정 캐릭터/연출의 설득력을 점검하세요.",
        ),
    ],
    "1456820": [
        IssueAspect(
            "short_content",
            "짧은 분량/엔딩 반복",
            r"short|too short|content|volume|ending|endings|replay|less than|hour|분량|짧|컨텐츠|콘텐츠|볼륨|엔딩|다회차|1시간|ボリューム|短い|エンディング|结局|内容少",
            "짧은 플레이타임, 엔딩 반복, 콘텐츠 볼륨에 대한 신호입니다.",
            "가격 기대, 엔딩 수집 동기, 반복 플레이 보상을 분리해 후속 패치/후속작 범위를 정하세요.",
        ),
        IssueAspect(
            "weapon_card_rng",
            "무기/카드 RNG",
            r"weapon|weapons|card|cards|rng|random|luck|durability|shotgun|grenade|무기|카드|운|랜덤|내구도|샷건|유탄|武器|カード|運|ランダム|耐久|霰弹枪",
            "무기 카드, 랜덤 제시, 내구도, 빌드 선택의 운 의존 신호입니다.",
            "런 다양성의 장점인지 통제감 부족인지 추천/비추천 근거를 나눠 보세요.",
        ),
        IssueAspect(
            "bleak_ending_tone",
            "엔딩 톤/구원감",
            r"ending|endings|bad end|good end|救い|虚無|暗い|엔딩|배드엔딩|굿엔딩|구원|허무|우울|结局|坏结局",
            "엔딩의 어두운 톤, 구원감 부족, 결말 만족도에 대한 신호입니다.",
            "이 톤이 의도된 정체성인지, 기대 불일치로 비추천을 만드는지 분리하세요.",
        ),
    ],
}

NEGATIVE_CUE_PATTERN = re.compile(
    r"bad|worse|worst|boring|bored|annoy|frustrat|hate|broken|problem|issue|unfair|too hard|too easy|too short|not enough|lack|lacks|missing|"
    r"shallow|repetitive|repeat|little content|short content|lack depth|"
    r"crash|bug|lag|cheat|hacker|비추천|별로|나쁘|망|문제|불만|아쉬|짜증|지루|부족|없어|짧|반복|질리|버그|튕|랙|렉|핵|치터|불공평|어려",
    re.IGNORECASE,
)
REQUEST_CUE_PATTERN = re.compile(
    r"please|pls|should|need to|needs to|must|add|fix|hope|wish|would like|bring back|"
    r"제발|추가|고쳐|고쳐줘|개선|필요|바람|원함|돌려",
    re.IGNORECASE,
)
PRAISE_CUE_PATTERN = re.compile(
    r"love|great|good|amazing|awesome|fun|best|excellent|addictive|recommend|"
    r"추천|재밌|재미|좋|훌륭|최고|갓겜|명작",
    re.IGNORECASE,
)
BUG_CUE_PATTERN = re.compile(
    r"crash|bug|bugs|broken|freeze|low fps|fps drop|fps issue|stutter|lag|disconnect|softlock|save|cloud save|"
    r"버그|튕|프레임|멈춤|렉|랙|세이브|저장",
    re.IGNORECASE,
)
PRAISE_CONFLICT_CUE_PATTERN = re.compile(
    r"too short|not enough|lack|lacks|missing|boring|bored|repetitive|repeat|shallow|frustrat|disappoint|"
    r"부족|불만|비판|실망|지루|반복|피로|질리|짧|아쉬|허술|납득하기 어렵",
    re.IGNORECASE,
)

LOW_INFORMATION_PHRASES = {
    "good",
    "great",
    "nice",
    "fun",
    "bad",
    "trash",
    "gg",
    "ez",
    "ok",
    "yes",
    "no",
    "nb",
    "lol",
    "10/10",
    "11/10",
    "추천",
    "비추천",
    "재밌음",
    "재밌다",
    "최고",
    "별로",
}

SUGGESTION_STOPWORDS = {
    "game",
    "games",
    "good",
    "great",
    "best",
    "love",
    "like",
    "fun",
    "really",
    "very",
    "still",
    "played",
    "play",
    "게임",
    "게임이",
    "게임은",
    "게임을",
    "재미",
    "재밌",
    "좋아",
    "좋은",
    "최고",
    "최고의",
    "무조건",
    "갓겜",
    "갓겜이",
    "아직",
    "정말",
    "매우",
    "비주얼",
}

AXIS_TOKEN_BLOCKLIST = {
    "중심",
    "의견",
    "중심 의견",
    "ㅋㅋㅋ",
    "ㅎㅎㅎ",
    "lgbt",
    "joguei",
    "leia",
    "adv",
    "everyone",
    "people",
    "player",
    "players",
    "レビュー",
    "遊戲",
    "游戏",
}

CLAIM_AXIS_RULES = [
    ClaimAxisRule(
        key="route_guidance",
        label="루트/선택지 안내와 세이브 편의",
        terms=(
            "route",
            "routes",
            "choice",
            "choices",
            "branch",
            "guide",
            "walkthrough",
            "hint",
            "save",
            "gallery",
            "루트",
            "선택지",
            "분기",
            "공략",
            "힌트",
            "세이브",
            "도감",
            "路线",
            "选择",
            "攻略",
            "存档",
            "セーブ",
            "攻略",
        ),
        target_axis_keys=("route_guidance", "chapter_replay", "story_logic", "content_volume"),
        definition="분기 조건, 선택지 피드백, 저장/되돌리기, 공략 의존성이 플레이 이해와 반복 플레이에 미치는 평가입니다.",
        include_criteria=("분기나 루트 진입 조건이 불명확하다는 주장", "세이브/챕터 선택/회상 기능이 부족하다는 주장", "공략 없이 엔딩이나 수집 요소를 회수하기 어렵다는 주장"),
        exclude_criteria=("스토리 취향만 말하는 리뷰", "단순히 엔딩이 좋거나 싫다는 감상", "조작감이나 전투 UI 불만"),
        why_actionable="힌트, 선택지 피드백, 세이브 슬롯, 챕터 선택 같은 구체적인 UX 개선 후보로 이어집니다.",
    ),
    ClaimAxisRule(
        key="mystery_logic",
        label="추리/재판 공정성과 납득감",
        terms=(
            "mystery",
            "deduction",
            "logic",
            "trial",
            "case",
            "evidence",
            "trick",
            "reasoning",
            "magic rule",
            "danganronpa",
            "추리",
            "논리",
            "재판",
            "증거",
            "트릭",
            "마법",
            "단간",
            "개연성",
            "억지",
            "推理",
            "逻辑",
            "诡计",
            "审判",
            "裁判",
            "証拠",
        ),
        target_axis_keys=("mystery_logic", "story_logic"),
        definition="추리 과정, 증거 제시, 재판 전개, 규칙 설명이 플레이어에게 공정하고 납득 가능하게 받아들여지는지에 대한 평가입니다.",
        include_criteria=("정답 도출 과정이 억지스럽거나 힌트가 부족하다는 주장", "증거와 결론의 연결이 약하다는 주장", "추리/재판 파트가 장점이라는 주장"),
        exclude_criteria=("캐릭터 호감만 말하는 리뷰", "분량이나 가격 불만", "순수 번역 품질 문제"),
        why_actionable="힌트 배치, 증거 설명, 반론 흐름, 규칙 튜토리얼을 조정할 우선순위로 바로 연결됩니다.",
    ),
    ClaimAxisRule(
        key="update_completion",
        label="완성도와 업데이트 신뢰",
        terms=(
            "update",
            "updates",
            "patch",
            "roadmap",
            "unfinished",
            "incomplete",
            "early access",
            "complete",
            "업데이트",
            "패치",
            "로드맵",
            "미완성",
            "완성도",
            "텍스트",
            "追加",
            "更新",
            "未完成",
            "画饼",
        ),
        target_axis_keys=("update_completion", "content_volume", "content_missing"),
        definition="현재 빌드가 충분히 완성되어 보이는지, 약속된 업데이트와 추가 콘텐츠를 신뢰할 수 있는지에 대한 평가입니다.",
        include_criteria=("미완성감, 업데이트 대기, 로드맵 신뢰 문제", "패치 후 개선 또는 악화 언급", "추가 텍스트/루트/챕터 요구"),
        exclude_criteria=("일반적인 스토리 감상", "플레이어가 직접 만든 모드 요구", "일회성 버그 제보"),
        why_actionable="로드맵 문구, 패치 우선순위, 출시/얼리액세스 기대 관리의 판단 근거가 됩니다.",
    ),
    ClaimAxisRule(
        key="ending_afterstory",
        label="엔딩 후속/후일담 요구",
        terms=(
            "ending",
            "endings",
            "true ending",
            "afterstory",
            "after story",
            "epilogue",
            "sequel",
            "엔딩",
            "후일담",
            "후속",
            "에필로그",
            "결말",
            "结局",
            "后日谈",
            "エンディング",
            "後日談",
        ),
        target_axis_keys=("bleak_ending_tone", "content_volume", "story_logic"),
        definition="엔딩의 만족도, 후일담 요구, 결말 톤과 후속 콘텐츠 기대가 어떻게 형성되는지에 대한 평가입니다.",
        include_criteria=("결말이 허무하거나 더 설명이 필요하다는 주장", "후일담·후속작·에필로그 요구", "엔딩 톤이 강점이라는 주장"),
        exclude_criteria=("루트 진입 조건만 말하는 리뷰", "초반 스토리만 말하는 리뷰", "순수 플레이타임 불만"),
        why_actionable="후일담 DLC, 엔딩 보강, 스토어 기대 관리, 후속작 훅을 검토할 수 있습니다.",
    ),
    ClaimAxisRule(
        key="character_art",
        label="캐릭터/아트/연출 매력",
        terms=(
            "character",
            "characters",
            "art",
            "visual",
            "cg",
            "sprite",
            "voice",
            "acting",
            "music",
            "캐릭터",
            "캐디",
            "아트",
            "일러",
            "성우",
            "더빙",
            "연출",
            "음악",
            "角色",
            "人设",
            "立绘",
            "配音",
            "キャラ",
            "ボイス",
        ),
        target_axis_keys=("character_voice", "martial_story", "story_logic"),
        definition="캐릭터 디자인, 일러스트, 보이스, 음악, 장면 연출이 구매 만족과 팬덤 반응에 기여하는 정도입니다.",
        include_criteria=("캐릭터·일러스트·성우·음악을 강점으로 언급", "특정 캐릭터나 연출이 만족/불만의 핵심이라는 주장", "아트 방향성이 구매 이유라는 주장"),
        exclude_criteria=("UI 가독성 문제", "추리 논리 불만", "분량이나 가격 불만"),
        why_actionable="스토어 소재, 캐릭터 상품성, 후속 콘텐츠 우선순위, 연출 보강 포인트로 활용할 수 있습니다.",
    ),
    ClaimAxisRule(
        key="localization_readability",
        label="번역/텍스트 가독성",
        terms=(
            "translation",
            "localization",
            "subtitle",
            "typo",
            "font",
            "readability",
            "번역",
            "한글화",
            "오역",
            "자막",
            "텍스트",
            "가독성",
            "翻译",
            "本地化",
            "字幕",
            "読みづら",
        ),
        target_axis_keys=("localization_readability", "ui_onboarding"),
        definition="번역 품질, 자막/텍스트 표시, 폰트와 문장 가독성이 이해와 몰입에 미치는 평가입니다.",
        include_criteria=("번역 오류나 어색함", "자막·폰트·텍스트 가독성 문제", "언어 지원 품질에 대한 칭찬"),
        exclude_criteria=("스토리 내용 자체의 호불호", "UI 조작 흐름 불만", "일반 성능 문제"),
        why_actionable="언어별 QA, 폰트/자막 UI 개선, 번역 검수 우선순위로 바로 이어집니다.",
    ),
]

STOPWORDS = {
    "the",
    "and",
    "but",
    "for",
    "to",
    "with",
    "this",
    "that",
    "game",
    "games",
    "balatro",
    "all",
    "any",
    "around",
    "at",
    "back",
    "be",
    "been",
    "being",
    "big",
    "by",
    "it",
    "is",
    "in",
    "of",
    "on",
    "or",
    "so",
    "some",
    "such",
    "my",
    "we",
    "he",
    "she",
    "them",
    "there",
    "their",
    "these",
    "those",
    "good",
    "great",
    "fun",
    "best",
    "better",
    "well",
    "hours",
    "play",
    "played",
    "playing",
    "still",
    "feel",
    "feels",
    "after",
    "every",
    "new",
    "same",
    "again",
    "about",
    "also",
    "are",
    "can",
    "cant",
    "could",
    "did",
    "didnt",
    "dont",
    "don't",
    "does",
    "doesnt",
    "because",
    "before",
    "ever",
    "even",
    "first",
    "from",
    "go",
    "going",
    "get",
    "got",
    "had",
    "has",
    "have",
    "having",
    "how",
    "if",
    "into",
    "isnt",
    "its",
    "it's",
    "ive",
    "i've",
    "ill",
    "i'll",
    "im",
    "i'm",
    "just",
    "know",
    "like",
    "lot",
    "make",
    "makes",
    "more",
    "most",
    "many",
    "much",
    "need",
    "not",
    "nothing",
    "now",
    "one",
    "only",
    "other",
    "out",
    "over",
    "pretty",
    "really",
    "see",
    "stuff",
    "while",
    "than",
    "then",
    "they",
    "think",
    "too",
    "try",
    "up",
    "very",
    "was",
    "were",
    "what",
    "when",
    "way",
    "which",
    "who",
    "why",
    "will",
    "would",
    "wouldnt",
    "you",
    "youre",
    "you're",
    "your",
    "ve",
    "want",
    "without",
    "review",
    "recommend",
    "recommended",
    "recommendation",
    "steam",
    "10",
    "100",
    "01",
    "2024",
    "2025",
    "2026",
    "de",
    "del",
    "des",
    "du",
    "el",
    "en",
    "es",
    "esse",
    "est",
    "et",
    "eu",
    "il",
    "je",
    "la",
    "las",
    "le",
    "les",
    "lo",
    "los",
    "me",
    "mi",
    "no",
    "pas",
    "por",
    "que",
    "qui",
    "se",
    "un",
    "una",
    "une",
    "juego",
    "juegos",
    "muy",
    "pero",
    "este",
    "esta",
    "como",
    "con",
    "com",
    "do",
    "si",
    "sin",
    "para",
    "te",
    "todo",
    "tudo",
    "mas",
    "mais",
    "muito",
    "na",
    "al",
    "horas",
    "jugar",
    "jogo",
    "jeu",
    "das",
    "der",
    "die",
    "ein",
    "eine",
    "ich",
    "ist",
    "mit",
    "nicht",
    "und",
    "zu",
    "den",
    "dem",
    "einfach",
    "на",
    "не",
    "что",
    "это",
    "как",
    "좋지만",
    "조금",
    "아직",
    "최근",
}


def run_local_analysis(
    *,
    analysis_run_id: int,
    app_id: str | None,
    scope: str,
    embedding_model: str | None,
    min_cluster_size: int,
    generate_ai_summary: bool,
    llm_provider: str | None,
    llm_model: str | None = None,
    min_quality_score: float = 0.25,
    exclude_duplicate_evidence: bool = True,
    use_lmstudio_labels: bool = True,
    max_clusters: int = 60,
    evidence_per_claim: int = 3,
) -> AnalysisPipelineResult:
    model_name = embedding_model or DEFAULT_EMBEDDING_MODEL
    with connect() as conn:
        reviews = _load_reviews(conn, app_id, scope)

    if not reviews:
        return AnalysisPipelineResult(
            reviews_analyzed=0,
            clusters_created=0,
            evidence_created=0,
            clusterer="none",
            message="No reviews matched the requested analysis scope.",
        )

    quality_rows = _score_review_quality(reviews)
    quality_by_id = {row.review_id: row for row in quality_rows}
    clustering_reviews = _select_cluster_candidates(reviews, quality_by_id, min_quality_score)
    issue_units, issue_cards, issue_stats, axis_suggestions = _build_issue_outputs(reviews, quality_by_id, app_id)

    embedding_rows: list[list[float]] | None = None
    try:
        groups, embedding_rows, device = _cluster_with_semantic_embeddings(
            clustering_reviews,
            model_name,
            min_cluster_size,
            app_id,
            max_clusters,
            quality_by_id,
        )
        clusterer = f"sentence_transformers_minibatch_kmeans_{device}"
        message = f"Analysis completed with GPU-ready semantic embeddings ({model_name}) on {device}."
    except Exception as exc:
        try:
            groups = _cluster_with_sklearn(clustering_reviews, min_cluster_size, app_id, max_clusters, quality_by_id)
            clusterer = "sklearn_tfidf_kmeans"
            message = (
                "Semantic embedding path unavailable; completed with local TF-IDF clustering "
                f"({exc.__class__.__name__})."
            )
        except Exception as fallback_exc:
            groups = _cluster_with_keywords(clustering_reviews, app_id, quality_by_id)
            clusterer = "keyword_fallback"
            message = (
                "Semantic and TF-IDF clustering failed; used keyword fallback "
                f"({exc.__class__.__name__}, {fallback_exc.__class__.__name__})."
            )

    groups = _apply_ctfidf_keywords(groups)

    if generate_ai_summary and llm_provider in {"lmstudio", "lm_studio"}:
        groups = _enrich_cluster_insights(groups, app_id, False, llm_model)
        issue_cards, issue_message = _enrich_issue_cards_with_lmstudio(issue_cards, app_id, llm_model, use_lmstudio_labels)
        if issue_message:
            message += f" {issue_message}"
    else:
        groups = _enrich_cluster_insights(groups, app_id, False, llm_model)

    axis_suggestions = _build_axis_suggestions(issue_units, issue_cards, _active_issue_aspects(app_id))

    with connect() as conn:
        _store_review_quality(conn, analysis_run_id, quality_rows)
        _store_embeddings(conn, clustering_reviews, model_name, embedding_rows)
        clusters_created, evidence_created = _store_analysis_outputs(
            conn,
            analysis_run_id,
            groups,
            evidence_per_claim=evidence_per_claim,
            exclude_duplicate_evidence=exclude_duplicate_evidence,
        )
        issues_created, issue_evidence_created = _store_issue_outputs(
            conn,
            analysis_run_id,
            app_id,
            issue_units,
            issue_cards,
        )
        axis_suggestions_created = _store_axis_suggestions(
            conn,
            analysis_run_id,
            app_id,
            axis_suggestions,
        )
        _store_analysis_report(conn, analysis_run_id, app_id, reviews, clusters_created, clusterer)

    coverage = issue_stats.get("issue_coverage")
    coverage_text = f" 이슈 커버리지는 {coverage:.0%}입니다." if isinstance(coverage, float) else ""
    suggestion_text = f" 새 평가축 후보 {axis_suggestions_created}개를 제안했습니다." if axis_suggestions_created else ""
    message += f" Issue board created {issues_created} cards with {issue_evidence_created} evidence quotes.{coverage_text}{suggestion_text}"
    return AnalysisPipelineResult(
        reviews_analyzed=len(reviews),
        clusters_created=clusters_created,
        evidence_created=evidence_created,
        clusterer=clusterer,
        message=message,
        issues_created=issues_created,
        issue_evidence_created=issue_evidence_created,
        axis_suggestions_created=axis_suggestions_created,
    )


async def model_settings_status() -> dict[str, Any]:
    lm_status = await _lm_studio_status()
    providers = [
        {
            "id": "local_gpu",
            "label": "Local GPU embeddings",
            "available": True,
            "default": True,
            "notes": "Uses SentenceTransformers on CUDA when available; falls back to CPU/TF-IDF.",
            "default_embedding_model": DEFAULT_SEMANTIC_EMBEDDING_MODEL,
        },
        {
            "id": "lmstudio",
            "label": "LM Studio",
            "available": lm_status["available"],
            "default": False,
            "base_url": LM_STUDIO_NATIVE_BASE_URL,
            "openai_base_url": LM_STUDIO_OPENAI_BASE_URL,
            "models": lm_status["models"],
            "embedding_models": lm_status.get("embedding_models", []),
        },
    ]
    return {
        "default_provider": "local_gpu",
        "default_embedding_model": DEFAULT_SEMANTIC_EMBEDDING_MODEL,
        "providers": providers,
        "lm_studio": lm_status,
    }


async def _lm_studio_status() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(f"{LM_STUDIO_NATIVE_BASE_URL}/models")
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                response = await client.get(f"{LM_STUDIO_OPENAI_BASE_URL}/models")
                response.raise_for_status()
                payload = response.json()
        except Exception as fallback_exc:
            return {
                "available": False,
                "base_url": LM_STUDIO_NATIVE_BASE_URL,
                "openai_base_url": LM_STUDIO_OPENAI_BASE_URL,
                "models": [],
                "embedding_models": [],
                "default_model": None,
                "message": f"{exc}; OpenAI-compatible fallback failed: {fallback_exc}",
            }

        models = [str(item.get("id")) for item in payload.get("data", []) if item.get("id")]
        return {
            "available": True,
            "base_url": LM_STUDIO_OPENAI_BASE_URL,
            "models": models,
            "embedding_models": [model for model in models if "embed" in model.lower()],
            "default_model": models[0] if models else None,
            "message": "LM Studio OpenAI-compatible endpoint is reachable.",
        }

    rows = payload.get("models") or []
    models = [str(item.get("key")) for item in rows if item.get("key")]
    embedding_models = [str(item.get("key")) for item in rows if item.get("type") == "embedding" and item.get("key")]
    llm_models = [str(item.get("key")) for item in rows if item.get("type") == "llm" and item.get("key")]
    return {
        "available": True,
        "base_url": LM_STUDIO_NATIVE_BASE_URL,
        "openai_base_url": LM_STUDIO_OPENAI_BASE_URL,
        "models": models,
        "embedding_models": embedding_models,
        "default_model": llm_models[0] if llm_models else models[0] if models else None,
        "message": "LM Studio native v1 endpoint is reachable.",
    }


def _load_reviews(conn: duckdb.DuckDBPyConnection, app_id: str | None, scope: str) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if app_id:
        clauses.append("r.app_id = ?")
        params.append(app_id)
    if scope == "new":
        clauses.append(
            """
            NOT EXISTS (
                SELECT 1
                FROM review_clusters rc
                JOIN clusters c ON c.id = rc.cluster_id
                WHERE rc.review_id = r.recommendation_id
                  AND c.analysis_run_id IS NOT NULL
            )
            """
        )
    where_sql = "WHERE " + " AND ".join(clauses) if clauses else ""
    return rows_to_dicts(
        conn.execute(
            f"""
            SELECT
                r.recommendation_id,
                r.app_id,
                r.language,
                r.review,
                r.voted_up,
                r.votes_up,
                r.weighted_vote_score,
                r.playtime_at_review,
                r.steam_created_at,
                r.collected_at
            FROM reviews r
            {where_sql}
            ORDER BY coalesce(r.steam_created_at, r.collected_at) DESC, r.recommendation_id
            """,
            params,
        )
    )


def _score_review_quality(reviews: list[dict[str, Any]]) -> list[ReviewQuality]:
    base_rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for row in reviews:
        normalized = _normalize_review_text(str(row.get("review") or ""))
        text_hash = hashlib.blake2b(normalized.encode("utf-8"), digest_size=12).hexdigest()
        counts[text_hash] += 1
        base_rows.append({**row, "_normalized_text": normalized, "_text_hash": text_hash})

    scored: list[ReviewQuality] = []
    for row in base_rows:
        text = str(row.get("review") or "")
        normalized = str(row["_normalized_text"])
        tokens = _tokens(text)
        unique_tokens = set(tokens)
        flags: list[str] = []
        if len(normalized) < 12 or len(tokens) <= 1:
            flags.append("very_short")
        if normalized in LOW_INFORMATION_PHRASES or _looks_like_low_information(normalized, tokens):
            flags.append("low_information")
        duplicate_count = counts[str(row["_text_hash"])]
        if duplicate_count > 1:
            flags.append("duplicate")
        if not re.search(r"[A-Za-z가-힣ぁ-んァ-ン一-龥]", normalized):
            flags.append("no_words")

        weighted = max(0.0, min(float(row.get("weighted_vote_score") or 0), 1.0))
        length_score = min(len(normalized) / 260, 0.38)
        diversity_score = min(len(unique_tokens) / 14, 0.28)
        vote_score = min(math.log1p(int(row.get("votes_up") or 0)) / 8, 0.08)
        score = 0.16 + length_score + diversity_score + weighted * 0.16 + vote_score
        if "very_short" in flags:
            score -= 0.28
        if "low_information" in flags:
            score -= 0.28
        if "duplicate" in flags:
            score -= min(0.18, 0.04 * math.log2(duplicate_count + 1))
        if "no_words" in flags:
            score -= 0.18
        score = max(0.0, min(score, 1.0))
        scored.append(
            ReviewQuality(
                review_id=str(row["recommendation_id"]),
                normalized_text=normalized,
                text_hash=str(row["_text_hash"]),
                quality_score=score,
                quality_flags=flags,
                duplicate_count=duplicate_count,
            )
        )
    return scored


def _select_cluster_candidates(
    reviews: list[dict[str, Any]],
    quality_by_id: dict[str, ReviewQuality],
    min_quality_score: float,
) -> list[dict[str, Any]]:
    best_by_hash: dict[str, dict[str, Any]] = {}
    for row in reviews:
        quality = quality_by_id.get(str(row["recommendation_id"]))
        if not quality or quality.quality_score < min_quality_score:
            continue
        current = best_by_hash.get(quality.text_hash)
        if current is None:
            best_by_hash[quality.text_hash] = row
            continue
        current_quality = quality_by_id.get(str(current["recommendation_id"]))
        if not current_quality or quality.quality_score > current_quality.quality_score:
            best_by_hash[quality.text_hash] = row

    candidates = list(best_by_hash.values())
    minimum = max(10, min(50, len(reviews) // 10))
    if len(candidates) >= minimum:
        return candidates
    return reviews


def _build_issue_outputs(
    reviews: list[dict[str, Any]],
    quality_by_id: dict[str, ReviewQuality],
    app_id: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    aspects = _active_issue_aspects(app_id)
    units = _extract_issue_units(reviews, quality_by_id, app_id, aspects)
    issue_units = [unit for unit in units if not unit["is_quarantined"]]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for unit in issue_units:
        if unit["intent"] == "other" or unit["aspect"] == "general":
            continue
        issue_intent = unit["intent"] if unit["intent"] in {"bug", "praise", "request"} else "complaint"
        grouped[(unit["aspect"], issue_intent)].append(unit)

    cards = [
        _build_issue_card(aspect, intent, members, app_id, len(reviews), aspects)
        for (aspect, intent), members in grouped.items()
        if members
    ]
    cards = sorted(cards, key=lambda item: item["priority_score"], reverse=True)
    stats = {
        "unit_count": len(units),
        "quarantined_units": sum(1 for unit in units if unit["is_quarantined"]),
        "assigned_units": sum(len(card["units"]) for card in cards),
        "issue_coverage": _issue_coverage(reviews, cards),
    }
    suggestions = _build_axis_suggestions(units, cards, aspects)
    return units, cards, stats, suggestions


def _extract_issue_units(
    reviews: list[dict[str, Any]],
    quality_by_id: dict[str, ReviewQuality],
    app_id: str | None,
    aspects: list[IssueAspect] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for review in reviews:
        review_id = str(review["recommendation_id"])
        review_quality = quality_by_id.get(review_id)
        for unit_index, unit_text in enumerate(_split_review_units(str(review.get("review") or ""))):
            normalized = _normalize_review_text(unit_text)
            tokens = _tokens(unit_text)
            intent = _issue_intent(unit_text, bool(review.get("voted_up")))
            aspect = _issue_aspect(unit_text, app_id, aspects)
            quality_flags = list(review_quality.quality_flags if review_quality else [])
            if len(normalized) < 18 or len(tokens) <= 2:
                quality_flags.append("short_unit")
            if _looks_like_low_information(normalized, tokens):
                quality_flags.append("low_information_unit")

            base_quality = review_quality.quality_score if review_quality else 0.5
            length_score = min(len(normalized) / 220, 0.25)
            specificity_score = min(len(set(tokens)) / 18, 0.2)
            cue_score = 0.12 if intent in {"complaint", "request", "bug"} else 0.06 if intent == "praise" else 0.0
            quality_score = max(0.0, min(base_quality * 0.62 + length_score + specificity_score + cue_score, 1.0))

            quarantine_reason = _issue_quarantine_reason(intent, aspect, quality_score, quality_flags)
            rows.append(
                {
                    "review": review,
                    "review_id": review_id,
                    "unit_index": unit_index,
                    "unit_text": _quote(unit_text),
                    "language": review.get("language"),
                    "voted_up": bool(review.get("voted_up")),
                    "intent": intent,
                    "aspect": aspect,
                    "sentiment": "positive" if review.get("voted_up") else "negative",
                    "quality_score": quality_score,
                    "quality_flags": sorted(set(quality_flags)),
                    "is_quarantined": quarantine_reason is not None,
                    "quarantine_reason": quarantine_reason,
                    "text_hash": _text_hash(unit_text),
                }
            )
    return rows


def _split_review_units(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", str(text or "")).strip()
    if not compact:
        return []
    parts = re.split(r"(?<=[.!?。！？])\s+|\n+|[•●]|(?:\s+-\s+)", compact)
    cleaned = [part.strip(" \t\r\n\"'“”‘’") for part in parts if part.strip()]
    if not cleaned:
        cleaned = [compact]
    merged: list[str] = []
    for part in cleaned:
        if len(part) < 24 and merged:
            merged[-1] = f"{merged[-1]} {part}".strip()
        else:
            merged.append(part)
    return [part[:420] for part in merged[:8]]


def _issue_intent(text: str, voted_up: bool) -> str:
    lowered = text.casefold()
    has_negative = bool(NEGATIVE_CUE_PATTERN.search(lowered))
    has_request = bool(REQUEST_CUE_PATTERN.search(lowered))
    has_praise = bool(PRAISE_CUE_PATTERN.search(lowered))
    has_bug = bool(BUG_CUE_PATTERN.search(lowered))
    if has_bug and (has_negative or has_request or not voted_up):
        return "bug"
    if has_request and (has_negative or not voted_up):
        return "request"
    if has_negative or (not voted_up and len(_tokens(text)) >= 4):
        return "complaint"
    if has_praise and voted_up:
        return "praise"
    return "other"


def _issue_aspect(text: str, app_id: str | None, aspects: list[IssueAspect] | None = None) -> str:
    aspects = aspects or _active_issue_aspects(app_id)
    matches = [
        (aspect.key, _safe_pattern_count(aspect.pattern, text))
        for aspect in aspects
    ]
    key, count = max(matches, key=lambda item: item[1])
    return key if count > 0 else "general"


def _issue_quarantine_reason(
    intent: str,
    aspect: str,
    quality_score: float,
    quality_flags: list[str],
) -> str | None:
    if "no_words" in quality_flags:
        return "no_words"
    if "very_short" in quality_flags or "short_unit" in quality_flags:
        return "too_short"
    if "low_information" in quality_flags or "low_information_unit" in quality_flags:
        return "low_information"
    if quality_score < 0.2:
        return "low_quality"
    if intent == "other" and aspect == "general":
        return "no_actionable_signal"
    return None


def _active_issue_aspects(app_id: str | None) -> list[IssueAspect]:
    resolved_app_id = str(app_id or "")
    try:
        with connect() as conn:
            rows = rows_to_dicts(
                conn.execute(
                    """
                    SELECT key, label, pattern, description, recommended_action
                         , scope
                    FROM analysis_axes
                    WHERE status = 'active'
                      AND (scope IN ('common', 'genre') OR app_id = ?)
                    ORDER BY
                        CASE scope WHEN 'game' THEN 1 WHEN 'genre' THEN 2 ELSE 3 END,
                        id
                    """,
                    [resolved_app_id],
                )
            )
    except Exception:
        rows = []
    db_aspects = [
        IssueAspect(
            key=str(row["key"]),
            label=str(row["label"]),
            pattern=str(row["pattern"]),
            summary=str(row["description"]),
            recommended_action=str(row["recommended_action"]),
        )
        for row in rows
        if _issue_aspect_allowed(resolved_app_id, str(row["key"]), str(row.get("scope") or "common"))
    ]
    seen = {aspect.key for aspect in db_aspects}
    fallback: list[IssueAspect] = []
    for aspect in GAME_ISSUE_ASPECTS.get(resolved_app_id, []):
        if aspect.key not in seen:
            fallback.append(aspect)
    for aspect in GENERIC_ISSUE_ASPECTS:
        if aspect.key not in seen and _issue_aspect_allowed(resolved_app_id, aspect.key, "common"):
            fallback.append(aspect)
    return [*db_aspects, *fallback]


def _issue_aspect_allowed(app_id: str, aspect_key: str, scope: str) -> bool:
    if scope == "game":
        return True
    return aspect_key not in APP_BLOCKED_GENERIC_ASPECT_KEYS.get(app_id, set())


def _safe_pattern_count(pattern: str, text: str) -> int:
    try:
        return len(re.findall(pattern, text, flags=re.IGNORECASE))
    except re.error:
        return 0


def _build_issue_card(
    aspect: str,
    intent: str,
    members: list[dict[str, Any]],
    app_id: str | None,
    total_reviews: int,
    aspects: list[IssueAspect] | None = None,
) -> dict[str, Any]:
    unique_review_ids = {unit["review_id"] for unit in members}
    positive_ratio = sum(1 for unit in members if unit["voted_up"]) / len(members)
    intent_counts = Counter(unit["intent"] for unit in members)
    language_counts = Counter(str(unit.get("language") or "unknown") for unit in members)
    avg_quality = sum(float(unit["quality_score"]) for unit in members) / len(members)
    evidence_units = _select_issue_evidence_units(members, intent)
    evidence_count = len(evidence_units)
    support_score = min(math.log1p(len(unique_review_ids)) / math.log(81), 1.0)
    evidence_score = min(evidence_count / 5, 1.0)
    negative_weight = 1.0 - positive_ratio if intent != "praise" else positive_ratio
    specificity_score = 1.0 if aspect != "general" else 0.3
    confidence = max(
        0.0,
        min(
            support_score * 0.38
            + evidence_score * 0.24
            + avg_quality * 0.2
            + negative_weight * 0.12
            + specificity_score * 0.06,
            0.96,
        ),
    )
    priority_score = max(
        0.0,
        min(
            support_score * 0.45
            + negative_weight * 0.22
            + avg_quality * 0.18
            + min(len(members) / 80, 1.0) * 0.15,
            1.0,
        ),
    )
    status, confidence_band, warnings = _issue_status(
        aspect,
        intent,
        confidence,
        len(unique_review_ids),
        evidence_count,
        total_reviews,
        positive_ratio,
    )
    aspect_spec = _issue_aspect_spec(aspect, app_id, aspects)
    top_terms = _issue_top_terms(members)
    title = _issue_title(aspect_spec, intent)
    summary = _issue_summary(aspect_spec, intent, members, positive_ratio)
    return {
        "title": title,
        "summary": summary,
        "intent": intent,
        "aspect": aspect,
        "status": status,
        "confidence_band": confidence_band,
        "confidence": confidence,
        "priority_score": priority_score,
        "review_count": len(unique_review_ids),
        "unique_review_count": len(unique_review_ids),
        "unit_count": len(members),
        "complaint_count": intent_counts["complaint"],
        "praise_count": intent_counts["praise"],
        "request_count": intent_counts["request"],
        "bug_count": intent_counts["bug"],
        "positive_ratio": positive_ratio,
        "language_counts": dict(language_counts),
        "top_terms": top_terms,
        "why_it_matters": _issue_why_it_matters(aspect_spec, intent, len(unique_review_ids), top_terms),
        "recommended_action": aspect_spec.recommended_action,
        "warnings": warnings,
        "source": "deterministic_issue_rules",
        "model": None,
        "units": members,
        "evidence_units": evidence_units,
    }


def _enrich_issue_cards_with_lmstudio(
    cards: list[dict[str, Any]],
    app_id: str | None,
    llm_model: str | None,
    enabled: bool,
) -> tuple[list[dict[str, Any]], str | None]:
    if not enabled or not cards:
        return cards, None

    enriched: list[dict[str, Any]] = []
    verified_count = 0
    failed_count = 0
    model_used: str | None = None
    candidates = sorted(cards, key=_lmstudio_issue_candidate_score, reverse=True)
    for index, card in enumerate(candidates):
        current = {**card, "evidence_units": list(card.get("evidence_units") or [])}
        if index < MAX_LMSTUDIO_ISSUE_CARDS and current["evidence_units"]:
            try:
                verified_card, model_name = _lmstudio_issue_card(current, app_id, llm_model)
            except Exception:
                failed_count += 1
            else:
                if verified_card and _verified_issue_match_count(verified_card) >= 3:
                    current = verified_card
                    model_used = model_name or model_used
                    verified_count += 1
                    enriched.append(current)
                else:
                    failed_count += 1

    if verified_count == 0:
        return cards, "Issue verifier skipped or unavailable."
    enriched = sorted(enriched, key=lambda item: item["priority_score"], reverse=True)
    message = f"Issue verifier checked {verified_count} cards"
    if failed_count:
        message += f" and skipped {failed_count} cards"
    if model_used:
        message += f" with {model_used}"
    return enriched, message + "."


def _lmstudio_issue_candidate_score(card: dict[str, Any]) -> float:
    aspect = str(card.get("aspect") or "")
    intent = str(card.get("intent") or "")
    score = float(card.get("priority_score") or 0.0)
    score += min(float(card.get("unique_review_count") or 0) / 120, 0.35)
    if aspect in {"balance", "progression", "ui_onboarding", "performance"}:
        score -= 0.2
    if aspect.startswith(("mystery_", "story_", "content_", "chapter_", "route_", "update_", "short_", "weapon_", "bleak_", "character_")):
        score += 0.22
    if intent in {"complaint", "bug", "request"}:
        score += 0.16
    elif intent == "praise":
        score -= 0.05
    return score


def _verified_issue_match_count(card: dict[str, Any]) -> int:
    return sum(1 for unit in card.get("evidence_units") or [] if unit.get("verifier_verdict") == "match")


def _lmstudio_issue_card(
    card: dict[str, Any],
    app_id: str | None,
    llm_model: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    with httpx.Client(timeout=75) as client:
        model = _lmstudio_openai_model_sync(client, llm_model)
        if not model:
            return None, None
        verified_units: list[dict[str, Any]] = []
        evidence_units = list(card.get("evidence_units") or [])
        for offset in range(0, len(evidence_units), ISSUE_VERIFIER_BATCH_SIZE):
            batch = evidence_units[offset : offset + ISSUE_VERIFIER_BATCH_SIZE]
            verdicts = _lmstudio_issue_verifier_batch(client, model, card, batch, app_id)
            for local_index, unit in enumerate(batch, start=1):
                verdict = verdicts.get(local_index, {})
                summary_ko = str(verdict.get("summary_ko") or "").strip()[:600]
                verified_units.append(
                    {
                        **unit,
                        "verifier_verdict": _consistent_issue_verdict(unit, card, _clean_verdict(verdict.get("verdict")), summary_ko),
                        "summary_ko": summary_ko,
                        "subissue": str(verdict.get("subissue") or "").strip()[:120],
                        "verifier_reason": str(verdict.get("reason") or "").strip()[:600],
                    }
                )

        match_units = [unit for unit in verified_units if unit.get("verifier_verdict") == "match"]
        partial_units = [unit for unit in verified_units if unit.get("verifier_verdict") == "partial"]
        reject_units = [unit for unit in verified_units if unit.get("verifier_verdict") == "reject"]
        usable_units = match_units or partial_units
        if not usable_units:
            card["warnings"] = [*card.get("warnings", []), "LLM 근거 검증에서 확정 근거가 나오지 않았습니다."]
            card["evidence_units"] = verified_units
            card["source"] = "lm_studio_issue_verifier"
            card["model"] = model
            card["status"] = "diagnostic"
            card["confidence_band"] = "low"
            card["confidence"] = min(float(card.get("confidence") or 0.5), 0.42)
            return card, model

        summary = _lmstudio_issue_card_summary(client, model, card, match_units, partial_units)
        if summary:
            card["title"] = _polish_issue_copy(str(summary.get("issue_title") or card["title"]))[:100]
            card["summary"] = _polish_issue_copy(str(summary.get("one_line") or card["summary"]))[:1200]
            card["why_it_matters"] = _polish_issue_copy(str(summary.get("why_it_matters") or card.get("why_it_matters") or ""))[:1400]
            card["recommended_action"] = _polish_issue_copy(str(summary.get("design_decision") or card.get("recommended_action") or ""))[:1400]
            risk = str(summary.get("evidence_risk") or "").strip()
            note = str(summary.get("confidence_note") or "").strip()
            extra = [value for value in (risk, note) if value]
            if extra:
                card["warnings"] = [*card.get("warnings", []), *extra]
            if str(card.get("intent")) == "praise" and PRAISE_CONFLICT_CUE_PATTERN.search(f"{card['title']} {card['summary']} {card['why_it_matters']}"):
                card["status"] = "needs_review"
                card["confidence_band"] = "medium"
                card["warnings"] = [
                    *card.get("warnings", []),
                    "강점 카드에 부정 신호가 섞여 활용 포인트로 확정하지 않았습니다.",
                ]

        match_ratio = len(match_units) / max(len(verified_units), 1)
        card["confidence"] = max(
            0.0,
            min(float(card.get("confidence") or 0.5) * 0.82 + match_ratio * 0.18, 0.96),
        )
        if len(match_units) >= 5 and card["status"] == "diagnostic":
            card["status"] = "needs_review"
            card["confidence_band"] = "medium"
        if len(match_units) < 3 and card["status"] in {"confirmed", "strength"}:
            card["status"] = "needs_review"
            card["confidence_band"] = "medium"
        card["warnings"] = [
            *card.get("warnings", []),
            f"LLM 근거 검증: match {len(match_units)}개, partial {len(partial_units)}개, reject {len(reject_units)}개.",
        ]
        card["evidence_units"] = sorted(
            verified_units,
            key=lambda unit: (
                {"match": 0, "partial": 1, "reject": 2}.get(str(unit.get("verifier_verdict")), 3),
                -float(unit.get("quality_score") or 0),
            ),
        )
        card["source"] = "lm_studio_issue_verifier"
        card["model"] = model
        return card, model


def _polish_issue_copy(text: str) -> str:
    replacements = {
        "호평이 관측됨": "강점으로 반복 언급됩니다",
        "호평이 관측됩니다": "강점으로 반복 언급됩니다",
        "호평이 관측된다": "강점으로 반복 언급됩니다",
        "불만이 관측됨": "불만 근거가 반복됩니다",
        "불만이 관측됩니다": "불만 근거가 반복됩니다",
        "불만이 관측된다": "불만 근거가 반복됩니다",
        "관련 의견이 관측됨": "관련 근거가 확인됩니다",
        "관련 의견이 관측됩니다": "관련 근거가 확인됩니다",
    }
    polished = text.strip()
    for before, after in replacements.items():
        polished = polished.replace(before, after)
    return polished


def _lmstudio_issue_verifier_batch(
    client: httpx.Client,
    model: str,
    card: dict[str, Any],
    units: list[dict[str, Any]],
    app_id: str | None,
) -> dict[int, dict[str, Any]]:
    issue_definition = _issue_aspect_spec(str(card.get("aspect") or ""), app_id)
    sample_text = "\n".join(
        "\n".join(
            [
                f"ID {index}",
                f"언어={unit.get('language') or 'unknown'} 평가={'추천' if unit.get('voted_up') else '비추천'} 현재={unit.get('aspect')}/{unit.get('intent')}",
                f"문장={_quote(unit.get('unit_text') or '')}",
                f"원문맥락={_quote((unit.get('review') or {}).get('review') or '')}",
            ]
        )
        for index, unit in enumerate(units, start=1)
    )
    prompt = (
        "아래 Steam 리뷰 문장이 목표 이슈의 근거로 맞는지 판정하세요. "
        "반드시 JSON 객체만 출력하고 마크다운 코드블록은 쓰지 마세요. "
        "verdict는 match, partial, reject 중 하나입니다. "
        "match는 목표 이슈를 직접 뒷받침할 때, partial은 관련은 있지만 다른 이슈가 섞였을 때, "
        "reject는 다른 이슈/칭찬/잡음일 때 사용하세요. "
        f"목표 신호 유형은 {card.get('intent')}입니다. complaint/bug/request 이슈에서 순수 칭찬은 reject 또는 partial입니다. "
        "praise 이슈에서 순수 불만은 reject 또는 partial입니다. "
        "summary_ko는 원문 의미를 한국어 1문장으로 요약하세요.\n"
        f"Steam app_id={app_id}. 목표 이슈={card.get('title')}. "
        f"정의={issue_definition.summary}. 기획 액션={issue_definition.recommended_action}.\n"
        f"{sample_text}\n"
        '출력 형식: {"items":[{"id":1,"verdict":"match","summary_ko":"...","subissue":"...","reason":"..."}]}'
    )
    for _attempt in range(2):
        data = _lmstudio_openai_chat_json(client, model, prompt, max_tokens=2000, temperature=0.0)
        items = data.get("items") if isinstance(data, dict) else None
        if isinstance(items, list):
            parsed: dict[int, dict[str, Any]] = {}
            for item in items:
                if not isinstance(item, dict):
                    continue
                try:
                    item_id = int(item.get("id"))
                except (TypeError, ValueError):
                    continue
                parsed[item_id] = item
            if parsed:
                return parsed
    return {}


def _lmstudio_issue_card_summary(
    client: httpx.Client,
    model: str,
    card: dict[str, Any],
    match_units: list[dict[str, Any]],
    partial_units: list[dict[str, Any]],
) -> dict[str, Any] | None:
    evidence_lines = "\n".join(
        f"{index}. 언어={unit.get('language') or 'unknown'} 평가={'추천' if unit.get('voted_up') else '비추천'} "
        f"요약={unit.get('summary_ko') or _quote(unit.get('unit_text') or '')} "
        f"하위이슈={unit.get('subissue') or '미분류'} review_id={unit.get('review_id')}"
        for index, unit in enumerate(match_units[:8], start=1)
    )
    partial_text = ""
    if partial_units:
        partial_text = "\npartial 참고: " + " / ".join(
            str(unit.get("summary_ko") or unit.get("unit_text") or "")[:120]
            for unit in partial_units[:3]
        )
    prompt = (
        "검증된 match 근거만 사용해 게임 기획자용 이슈 카드 1개를 한국어 JSON으로 작성하세요. "
        "원문에 없는 주장을 만들지 말고, '호평이 관측된다', '불만이 반복된다', '관련 의견이 있다' 같은 빈 표현은 금지합니다. "
        "issue_title은 구체적인 문제/강점명으로 쓰고, design_decision은 기획자가 다음에 판단할 액션으로 쓰세요. "
        "praise 카드라면 문제처럼 쓰지 말고 유지할 강점, 확장 포인트, 마케팅/후속작에 쓸 수 있는 활용 포인트로 쓰세요.\n"
        f"기존 이슈명={card.get('title')}. 기존 요약={card.get('summary')}.\n"
        f"match 근거:\n{evidence_lines}{partial_text}\n"
        '출력 형식: {"issue_title":"...","one_line":"...","why_it_matters":"...","design_decision":"...","evidence_risk":"...","confidence_note":"..."}'
    )
    data = _lmstudio_openai_chat_json(client, model, prompt, max_tokens=1300, temperature=0.1)
    return data if data else None


def _lmstudio_openai_chat_json(
    client: httpx.Client,
    model: str,
    prompt: str,
    *,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    response = client.post(
        f"{LM_STUDIO_OPENAI_BASE_URL}/chat/completions",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "Return valid JSON only. Korean text values are allowed."},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    )
    response.raise_for_status()
    raw = _extract_lmstudio_text(response.json())
    data = _parse_json_object(str(raw))
    if not data:
        raise ValueError("LM Studio returned non-JSON issue verifier output")
    return data


def _clean_verdict(value: Any) -> str:
    normalized = str(value or "").strip().casefold()
    if normalized in {"match", "partial", "reject"}:
        return normalized
    return "partial" if normalized else "missing"


def _consistent_issue_verdict(unit: dict[str, Any], card: dict[str, Any], verdict: str, summary_ko: str = "") -> str:
    if verdict != "match":
        return verdict
    target_intent = str(card.get("intent") or "")
    unit_intent = str(unit.get("intent") or "")
    text = str(unit.get("unit_text") or "")
    positive_summary = bool(re.search(r"긍정|호평|좋|만족|강점|뛰어|훌륭|추천|매력", summary_ko))
    negative_summary = bool(re.search(r"불만|비판|문제|부족|아쉽|어렵|저하|부정|실망|불편", summary_ko))
    if target_intent == "praise":
        if negative_summary and not positive_summary:
            return "partial"
        if not bool(unit.get("voted_up")) and not PRAISE_CUE_PATTERN.search(text):
            return "partial"
        return "match"
    if target_intent in {"complaint", "bug", "request"}:
        if positive_summary and not negative_summary:
            return "partial"
        if unit_intent == "praise" and bool(unit.get("voted_up")) and not NEGATIVE_CUE_PATTERN.search(text):
            return "partial"
        if target_intent == "bug" and not BUG_CUE_PATTERN.search(text):
            return "partial"
        if target_intent == "request" and not REQUEST_CUE_PATTERN.search(text):
            return "partial"
    return "match"


def _select_issue_evidence_units(members: list[dict[str, Any]], intent: str, limit: int = 8) -> list[dict[str, Any]]:
    def preferred(unit: dict[str, Any]) -> bool:
        if intent == "praise":
            return unit["intent"] == "praise" and bool(unit["voted_up"])
        return unit["intent"] in {"complaint", "request", "bug"}

    candidates = [unit for unit in members if preferred(unit)] or members
    candidates = sorted(
        candidates,
        key=lambda unit: (
            0 if unit["intent"] == intent else 1,
            0 if intent != "praise" and not bool(unit.get("voted_up")) else 1,
            -float(unit["quality_score"]),
            -len(str(unit["unit_text"])),
            -float(unit["review"].get("weighted_vote_score") or 0),
        ),
        reverse=False,
    )
    selected: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    seen_reviews: set[str] = set()
    language_counts: Counter[str] = Counter()
    for unit in candidates:
        text_hash = str(unit.get("text_hash") or _text_hash(str(unit.get("unit_text") or "")))
        if text_hash in seen_hashes or unit["review_id"] in seen_reviews:
            continue
        language = str(unit.get("language") or "unknown")
        if language_counts[language] >= max(2, limit // 3) and len(selected) < limit - 2:
            continue
        selected.append(unit)
        seen_hashes.add(text_hash)
        seen_reviews.add(unit["review_id"])
        language_counts[language] += 1
        if len(selected) >= limit:
            break
    if len(selected) < min(limit, 5):
        for unit in candidates:
            text_hash = str(unit.get("text_hash") or _text_hash(str(unit.get("unit_text") or "")))
            if text_hash in seen_hashes or unit["review_id"] in seen_reviews:
                continue
            selected.append(unit)
            seen_hashes.add(text_hash)
            seen_reviews.add(unit["review_id"])
            if len(selected) >= limit:
                break
    return selected


def _issue_status(
    aspect: str,
    intent: str,
    confidence: float,
    unique_reviews: int,
    evidence_count: int,
    total_reviews: int,
    positive_ratio: float,
) -> tuple[str, str, list[str]]:
    warnings: list[str] = []
    if total_reviews < 1000:
        warnings.append("리뷰 수가 1,000개 미만이라 탐색 결과로만 보세요.")
    if unique_reviews < 20:
        warnings.append("서로 다른 리뷰 수가 적어 확정 이슈로 보기 어렵습니다.")
    if evidence_count < 3:
        warnings.append("근거 문장이 3개 미만입니다.")
    if intent != "praise" and positive_ratio > 0.7:
        warnings.append("추천 리뷰 비중이 높아 실제 불만인지 문맥 확인이 필요합니다.")
    if intent != "praise" and aspect in {"balance", "ui_onboarding"} and unique_reviews < 80:
        warnings.append("일반 분류라서 확정 전에 근거 리뷰 확인이 필요합니다.")
        confidence = min(confidence, 0.68)

    if intent == "praise" and unique_reviews >= 20 and evidence_count >= 3 and confidence >= 0.68:
        return "strength", "high", warnings
    if total_reviews >= 1000 and unique_reviews >= 20 and evidence_count >= 3 and confidence >= 0.7:
        return "confirmed", "high", warnings
    if confidence >= 0.5 and evidence_count >= 2:
        return "needs_review", "medium", warnings
    return "diagnostic", "low", warnings


def _issue_aspect_spec(aspect: str, app_id: str | None, aspects: list[IssueAspect] | None = None) -> IssueAspect:
    aspects = aspects or _active_issue_aspects(app_id)
    for spec in aspects:
        if spec.key == aspect:
            return spec
    return IssueAspect(
        "general",
        "일반 의견",
        r".*",
        "특정 측면으로 분류되지 않은 의견입니다.",
        "근거 리뷰를 직접 읽고 새 분류 규칙을 추가할지 판단하세요.",
    )


def _issue_title(aspect: IssueAspect, intent: str) -> str:
    suffix = {
        "bug": "문제",
        "complaint": "불만",
        "request": "개선 요청",
        "praise": "강점",
    }.get(intent, "신호")
    return f"{aspect.label} {suffix}"


def _issue_summary(aspect: IssueAspect, intent: str, members: list[dict[str, Any]], positive_ratio: float) -> str:
    intent_label = {
        "bug": "버그/성능 문제",
        "complaint": "불만",
        "request": "개선 요청",
        "praise": "호평",
    }.get(intent, "의견")
    return (
        f"{len({unit['review_id'] for unit in members})}개 리뷰의 {len(members)}개 문장에서 "
        f"{aspect.label} 관련 {intent_label}이 반복됩니다. 추천 비율은 {positive_ratio:.0%}입니다."
    )


def _issue_why_it_matters(aspect: IssueAspect, intent: str, unique_reviews: int, top_terms: list[str]) -> str:
    terms = ", ".join(top_terms[:4]) if top_terms else "반복 표현 부족"
    if intent == "praise":
        return f"{aspect.summary} {unique_reviews}개 리뷰에서 강점으로 반복되며, 대표 표현은 {terms}입니다."
    return f"{aspect.summary} {unique_reviews}개 리뷰에서 반복되며, 대표 표현은 {terms}입니다."


def _issue_top_terms(members: list[dict[str, Any]], limit: int = 8) -> list[str]:
    counter: Counter[str] = Counter()
    for unit in members:
        counter.update(token for token in _tokens(str(unit.get("unit_text") or "")) if token not in STOPWORDS and len(token) > 2)
    return [token for token, _ in counter.most_common(limit)]


def _issue_coverage(reviews: list[dict[str, Any]], cards: list[dict[str, Any]]) -> float | None:
    negative_ids = {str(row["recommendation_id"]) for row in reviews if not row.get("voted_up")}
    if not negative_ids:
        return None
    assigned_ids = {
        unit["review_id"]
        for card in cards
        if card["intent"] != "praise"
        for unit in card["units"]
    }
    return len(negative_ids & assigned_ids) / len(negative_ids)


def _build_axis_suggestions(
    units: list[dict[str, Any]],
    cards: list[dict[str, Any]],
    aspects: list[IssueAspect],
    limit: int = 8,
) -> list[dict[str, Any]]:
    aspects_by_key = {aspect.key: aspect for aspect in aspects}
    persisted_axis_keys = _persisted_axis_keys()
    target_aspects_by_key = {
        key: aspect
        for key, aspect in aspects_by_key.items()
        if key in persisted_axis_keys
    }
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for card in cards:
        card_units = list(card.get("evidence_units") or card.get("units") or [])
        if not card_units:
            continue
        rule = _claim_axis_rule_for_members(card_units, strict=True)
        if not rule:
            continue
        target_axis_key = _target_axis_key(rule, target_aspects_by_key)
        if target_axis_key and target_axis_key == str(card.get("aspect") or ""):
            continue
        grouped[f"rule:{rule.key}"].extend(card_units)

    for unit in units:
        if unit.get("is_quarantined") or unit.get("intent") not in {"complaint", "request", "bug", "praise"}:
            continue
        rule = _claim_axis_rule_for_members([unit], strict=False)
        if rule:
            target_axis_key = _target_axis_key(rule, target_aspects_by_key)
            if target_axis_key and target_axis_key == str(unit.get("aspect") or ""):
                continue
            grouped[f"rule:{rule.key}"].append(unit)
            continue
        if unit.get("aspect") == "general" or str(unit.get("aspect") or "") not in aspects_by_key:
            token = _raw_signal_key(unit)
            if token:
                grouped[f"raw:{token}"].append(unit)

    suggestions: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for group_key, members in grouped.items():
        if not members:
            continue
        suggestion = _claim_axis_suggestion(members, target_aspects_by_key)
        if not suggestion:
            continue
        dedupe_key = f"{suggestion['kind']}:{suggestion.get('canonical_label_ko') or suggestion['label']}"
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        suggestions.append(suggestion)

    return sorted(
        suggestions,
        key=lambda item: (
            0 if item.get("quality_gate") == "pass" else 1,
            0 if item.get("kind") == "merge_candidate" else 1,
            -int(item.get("evidence_count") or 0),
            str(item.get("label") or ""),
        ),
    )[:limit]


def _claim_axis_suggestion(
    members: list[dict[str, Any]],
    aspects_by_key: dict[str, IssueAspect],
) -> dict[str, Any] | None:
    unique_ids = _unique_review_ids(members)
    if len(unique_ids) < 3:
        return None
    language_counts = Counter(str(unit.get("language") or "unknown") for unit in members)
    intent_counts = Counter(str(unit.get("intent") or "other") for unit in members)
    top_terms = _claim_top_terms(members, 8)
    examples = _axis_example_review_ids(members)
    rule = _claim_axis_rule_for_members(members, strict=True)
    if not rule:
        return {
            "label": "원문 신호 검토 필요",
            "rationale": (
                f"{len(unique_ids)}개 리뷰에서 비슷한 표현이 반복됐지만, 한국어 평가축으로 만들 만큼 "
                "의미 단위가 안정적이지 않습니다."
            ),
            "suggested_pattern": "|".join(re.escape(term) for term in top_terms[:6]) or "",
            "evidence_count": len(unique_ids),
            "language_counts": dict(language_counts),
            "example_review_ids": examples,
            "kind": "raw_signal",
            "canonical_label_ko": None,
            "definition": None,
            "include_criteria": [],
            "exclude_criteria": [],
            "evidence_claim_ids": examples,
            "why_actionable": None,
            "quality_gate": "fail",
            "failure_reason": "반복 토큰은 있으나 기획 판단 단위로 해석할 충분한 주장 구조가 없습니다.",
        }

    target_axis_key = _target_axis_key(rule, aspects_by_key)
    matched_terms = _matched_rule_terms(rule, members)
    quality_gate, failure_reason = _axis_candidate_gate(rule, matched_terms, len(unique_ids), top_terms)
    kind = "merge_candidate" if target_axis_key else "axis_candidate"
    if quality_gate != "pass":
        kind = "raw_signal"
    target_label = aspects_by_key[target_axis_key].label if target_axis_key else None
    action = "기존 평가축에 병합할 수 있습니다" if target_label else "게임별 평가축 후보로 검토할 수 있습니다"
    return {
        "label": rule.label if quality_gate == "pass" else "원문 신호 검토 필요",
        "rationale": (
            f"{len(unique_ids)}개 리뷰에서 {rule.label} 관련 주장이 반복됩니다. "
            f"주요 언어는 {', '.join(language_counts.keys()) or 'unknown'}이고, "
            f"주요 성격은 {intent_counts.most_common(1)[0][0]}입니다. {action}."
        ),
        "suggested_pattern": "|".join(re.escape(term) for term in matched_terms[:12]) or "|".join(
            re.escape(term) for term in rule.terms[:8]
        ),
        "evidence_count": len(unique_ids),
        "language_counts": dict(language_counts),
        "example_review_ids": examples,
        "kind": kind,
        "canonical_label_ko": rule.label if quality_gate == "pass" else None,
        "definition": rule.definition if quality_gate == "pass" else None,
        "include_criteria": list(rule.include_criteria) if quality_gate == "pass" else [],
        "exclude_criteria": list(rule.exclude_criteria) if quality_gate == "pass" else [],
        "evidence_claim_ids": examples,
        "why_actionable": rule.why_actionable if quality_gate == "pass" else None,
        "quality_gate": quality_gate,
        "failure_reason": failure_reason,
        "target_axis_key": target_axis_key,
    }


def _claim_axis_rule_for_members(members: list[dict[str, Any]], strict: bool) -> ClaimAxisRule | None:
    scored: list[tuple[int, ClaimAxisRule]] = []
    for rule in CLAIM_AXIS_RULES:
        matches = _matched_rule_terms(rule, members)
        required = rule.min_terms if strict else 1
        if len(matches) >= required:
            scored.append((len(matches), rule))
    if not scored:
        return None
    return sorted(scored, key=lambda item: (-item[0], item[1].key))[0][1]


def _matched_rule_terms(rule: ClaimAxisRule, members: list[dict[str, Any]]) -> list[str]:
    text = _claim_text_blob(members)
    matched = []
    for term in rule.terms:
        normalized = term.casefold()
        if normalized and normalized in text:
            matched.append(term)
    return matched


def _claim_text_blob(members: list[dict[str, Any]]) -> str:
    return " ".join(
        str(unit.get("summary_ko") or unit.get("subissue") or unit.get("unit_text") or "")
        for unit in members
    ).casefold()


def _target_axis_key(rule: ClaimAxisRule, aspects_by_key: dict[str, IssueAspect]) -> str | None:
    for axis_key in rule.target_axis_keys:
        if axis_key in aspects_by_key:
            return axis_key
    return None


def _persisted_axis_keys() -> set[str]:
    try:
        with connect() as conn:
            rows = conn.execute("SELECT key FROM analysis_axes WHERE status = 'active'").fetchall()
    except Exception:
        return set()
    return {str(row[0]) for row in rows}


def _axis_candidate_gate(
    rule: ClaimAxisRule,
    matched_terms: list[str],
    evidence_count: int,
    top_terms: list[str],
) -> tuple[str, str | None]:
    if evidence_count < 5:
        return "fail", "서로 다른 리뷰 5개 이상의 근거가 필요합니다."
    if len(matched_terms) < rule.min_terms:
        return "fail", "같은 의미의 표현이 충분히 반복되지 않았습니다."
    if not _valid_axis_label(rule.label):
        return "fail", "한국어 평가축 라벨로 쓰기 어렵습니다."
    if any(_looks_like_axis_noise(term) for term in top_terms[:3]):
        return "fail", "대표 표현이 닉네임, 숫자, 저정보 토큰에 가깝습니다."
    return "pass", None


def _valid_axis_label(label: str) -> bool:
    if not re.search(r"[가-힣]", label):
        return False
    if re.search(r"\d", label):
        return False
    if "중심 의견" in label:
        return False
    return 4 <= len(label.strip()) <= 80


def _raw_signal_key(unit: dict[str, Any]) -> str:
    for token in _claim_top_terms([unit], 4):
        if not _looks_like_axis_noise(token):
            return token
    return ""


def _claim_top_terms(members: list[dict[str, Any]], limit: int = 8) -> list[str]:
    counter: Counter[str] = Counter()
    for unit in members:
        text = str(unit.get("summary_ko") or unit.get("unit_text") or "")
        counter.update(
            token
            for token in _tokens(text)
            if token not in STOPWORDS
            and token not in SUGGESTION_STOPWORDS
            and not _looks_like_axis_noise(token)
            and len(token) > 2
        )
    return [token for token, _ in counter.most_common(limit)]


def _looks_like_axis_noise(token: str) -> bool:
    normalized = str(token or "").casefold().strip()
    if not normalized or normalized in AXIS_TOKEN_BLOCKLIST:
        return True
    if re.fullmatch(r"[\d\W_]+", normalized):
        return True
    if re.fullmatch(r"\d+[a-z가-힣]*", normalized):
        return True
    if len(normalized) <= 2:
        return True
    return False


def _axis_example_review_ids(members: list[dict[str, Any]], limit: int = 6) -> list[str]:
    examples: list[str] = []
    seen: set[str] = set()
    for unit in sorted(members, key=lambda item: (-float(item.get("quality_score") or 0), str(item.get("review_id")))):
        review_id = str(unit["review_id"])
        if review_id in seen:
            continue
        examples.append(review_id)
        seen.add(review_id)
        if len(examples) >= limit:
            break
    return examples


def _unique_review_ids(members: list[dict[str, Any]]) -> set[str]:
    return {str(unit.get("review_id")) for unit in members if unit.get("review_id") is not None}


def _normalize_review_text(text: str) -> str:
    compact = re.sub(r"\s+", " ", text.casefold()).strip()
    compact = re.sub(r"https?://\S+", "", compact)
    compact = re.sub(r"[\u200b-\u200f]", "", compact)
    compact = re.sub(r"([!?.,~])\1{2,}", r"\1\1", compact)
    return compact.strip()


def _looks_like_low_information(normalized: str, tokens: list[str]) -> bool:
    if not normalized:
        return True
    if len(tokens) <= 2 and len(normalized) <= 18:
        return True
    if len(set(normalized.replace(" ", ""))) <= 3 and len(normalized) <= 24:
        return True
    if re.fullmatch(r"[\W_0-9]+", normalized):
        return True
    return False


def _cluster_with_semantic_embeddings(
    reviews: list[dict[str, Any]],
    model_name: str,
    min_cluster_size: int,
    app_id: str | None,
    max_clusters: int,
    quality_by_id: dict[str, ReviewQuality],
) -> tuple[list[dict[str, Any]], list[list[float]], str]:
    if model_name == LOCAL_HASH_EMBEDDING_MODEL:
        raise RuntimeError("local hash embeddings are only used as a storage fallback")

    import numpy as np
    import torch
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import MiniBatchKMeans

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(model_name, device=device)
    texts = [_embedding_text(model_name, str(row.get("review") or "")) for row in reviews]
    batch_size = 96 if device == "cuda" else 24
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    embeddings = np.asarray(embeddings, dtype=np.float32)
    cluster_count = max(1, min(max_clusters, len(reviews) // max(min_cluster_size, 1)))
    if cluster_count == 1:
        labels = np.zeros(len(reviews), dtype=np.int32)
        scores = np.ones(len(reviews), dtype=np.float32)
    else:
        model_batch_size = max(1024, cluster_count * 96)
        clusterer = MiniBatchKMeans(
            n_clusters=cluster_count,
            random_state=13,
            batch_size=model_batch_size,
            n_init=10,
            reassignment_ratio=0.01,
        )
        labels = clusterer.fit_predict(embeddings)
        centers = np.asarray(clusterer.cluster_centers_, dtype=np.float32)
        norms = np.linalg.norm(centers, axis=1, keepdims=True)
        centers = centers / np.maximum(norms, 1e-12)
        scores = np.sum(embeddings * centers[labels], axis=1)

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row, label, score in zip(reviews, labels, scores, strict=True):
        grouped[int(label)].append({
            "row": row,
            "score": max(0.0, min(float(score), 1.0)),
            "quality": quality_by_id.get(str(row["recommendation_id"])),
        })
    return [_describe_group(members, app_id, quality_by_id) for members in grouped.values()], embeddings.tolist(), device


def _embedding_text(model_name: str, text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if "e5" in model_name.lower() and not compact.lower().startswith(("query:", "passage:")):
        return f"passage: {compact}"
    return compact


def _cluster_with_sklearn(
    reviews: list[dict[str, Any]],
    min_cluster_size: int,
    app_id: str | None,
    max_clusters: int,
    quality_by_id: dict[str, ReviewQuality],
) -> list[dict[str, Any]]:
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    texts = [row["review"] or "" for row in reviews]
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, max_features=8000)
    matrix = vectorizer.fit_transform(texts)
    cluster_count = max(1, min(max_clusters, len(reviews) // max(min_cluster_size, 1)))
    if cluster_count == 1:
        labels = [0 for _ in reviews]
        scores = [1.0 for _ in reviews]
    else:
        model = KMeans(n_clusters=cluster_count, random_state=13, n_init=10)
        labels = model.fit_predict(matrix)
        similarities = cosine_similarity(matrix, model.cluster_centers_)
        scores = [float(similarities[index, labels[index]]) for index in range(len(reviews))]

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row, label, score in zip(reviews, labels, scores, strict=True):
        grouped[int(label)].append({
            "row": row,
            "score": max(0.0, min(score, 1.0)),
            "quality": quality_by_id.get(str(row["recommendation_id"])),
        })
    return [_describe_group(members, app_id, quality_by_id) for members in grouped.values()]


def _theme_candidates_for_app(app_id: str | None) -> list[tuple[Theme, str]]:
    app_id_str = str(app_id or "")
    blocked_global_keys = APP_BLOCKED_GLOBAL_THEME_KEYS.get(app_id_str, set())
    candidates: list[tuple[Theme, str]] = []
    seen_keys: set[str] = set()
    for theme in GAME_THEMES.get(app_id_str, []):
        candidates.append((theme, "game_theme"))
        seen_keys.add(theme.key)
    for theme in THEMES:
        if theme.key in seen_keys or theme.key in blocked_global_keys:
            continue
        candidates.append((theme, "common_theme"))
        seen_keys.add(theme.key)
    return candidates


def _theme_pattern_matches(theme: Theme, text: str) -> list[str]:
    matches = re.findall(theme.pattern, text, flags=re.IGNORECASE)
    terms: list[str] = []
    for match in matches:
        raw = " ".join(str(part) for part in match if part) if isinstance(match, tuple) else str(match)
        cleaned = _clean_keyword(raw)
        if cleaned:
            terms.append(cleaned)
    return terms


def _cluster_with_keywords(
    reviews: list[dict[str, Any]],
    app_id: str | None,
    quality_by_id: dict[str, ReviewQuality],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    themes = _theme_candidates_for_app(app_id)
    for row in reviews:
        text = str(row.get("review") or "").lower()
        matches = [
            (theme, source, len(_theme_pattern_matches(theme, text)))
            for theme, source in themes
        ]
        theme, source, count = max(matches, key=lambda item: item[2])
        if count <= 0:
            grouped["misc"].append({"row": row, "score": 0.55, "quality": quality_by_id.get(str(row["recommendation_id"]))})
        else:
            grouped[f"{source}:{theme.key}"].append({
                "row": row,
                "score": min(1.0, 0.62 + count * 0.12),
                "quality": quality_by_id.get(str(row["recommendation_id"])),
            })
    return [_describe_group(members, app_id, quality_by_id) for members in grouped.values() if members]


def _describe_group(
    members: list[dict[str, Any]],
    app_id: str | None,
    quality_by_id: dict[str, ReviewQuality],
) -> dict[str, Any]:
    rows = [member["row"] for member in members]
    sentiment = _sentiment(rows)
    theme_match = _best_theme(rows, app_id)
    keywords = _keywords(rows)
    language = _dominant_language(rows)
    positive_ratio = _positive_ratio(rows)
    quality_warning = _quality_warning(rows, quality_by_id)
    label_warnings = list(theme_match.warnings) if theme_match else []
    if quality_warning:
        label_warnings.append(quality_warning)
    matched_terms = theme_match.matched_terms if theme_match else []
    matched_theme_key = theme_match.theme.key if theme_match else None
    if theme_match and theme_match.accepted:
        label = theme_match.theme.label
        label_source = theme_match.source
        label_confidence = theme_match.confidence
        summary = (
            f"{len(rows)}개 리뷰 중 {theme_match.support_review_count}개에서 "
            f"{theme_match.theme.summary} 추천 비율은 {positive_ratio:.0%}입니다."
        )
    else:
        if sentiment == "positive":
            label = "긍정 경험 묶음"
        elif sentiment == "negative":
            label = "개선 요청 묶음"
        else:
            label = "혼합 의견 묶음"
        if keywords:
            label = f"{keywords[0]} 중심 의견"
        label_source = "keyword" if keywords else "fallback"
        label_confidence = "low"
        label_warnings.append("테마 확정이 아니라 키워드 기반 진단 라벨입니다. 기획 판단은 인사이트 보드와 근거 리뷰를 우선 확인하세요.")
        keyword_text = ", ".join(keywords[:4]) if keywords else "공통 표현 부족"
        summary = f"{len(rows)}개 리뷰가 유사한 표현으로 묶였습니다. 주요 단어는 {keyword_text}이며 긍정 비율은 {_positive_ratio(rows):.0%}입니다."
    label_warnings = _unique_strings(label_warnings)
    return {
        "label": label,
        "summary": summary,
        "sentiment": sentiment,
        "language": language,
        "reviews": members,
        "keywords": keywords,
        "keyword_method": "frequency",
        "label_source": label_source,
        "label_confidence": label_confidence,
        "label_warnings": label_warnings,
        "matched_theme_key": matched_theme_key,
        "matched_terms": matched_terms,
        "positive_ratio": positive_ratio,
        "quality_warning": quality_warning,
    }


def _apply_ctfidf_keywords(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(groups) < 2:
        return groups

    try:
        import numpy as np
        from sklearn.feature_extraction.text import CountVectorizer

        documents = [_cluster_keyword_document(group) for group in groups]
        if sum(1 for document in documents if document.strip()) < 2:
            return groups

        vectorizer = CountVectorizer(
            lowercase=True,
            ngram_range=(1, 3),
            min_df=1,
            max_df=0.85 if len(groups) < 4 else 0.55,
            max_features=8000,
            stop_words=sorted(STOPWORDS),
            token_pattern=r"(?u)\b[A-Za-z가-힣ぁ-んァ-ン一-龥0-9][A-Za-z가-힣ぁ-んァ-ン一-龥0-9']+\b",
        )
        matrix = vectorizer.fit_transform(documents).astype(float)
        if matrix.shape[1] == 0:
            return groups

        counts = matrix.toarray()
        row_totals = np.maximum(counts.sum(axis=1, keepdims=True), 1.0)
        term_cluster_counts = np.maximum((counts > 0).sum(axis=0), 1)
        idf = np.log((1 + len(groups)) / (1 + term_cluster_counts)) + 1.0
        scores = (counts / row_totals) * idf
        terms = vectorizer.get_feature_names_out()
    except Exception:
        return groups

    for group_index, group in enumerate(groups):
        ranked: list[tuple[str, float]] = []
        for index in np.argsort(scores[group_index])[::-1][:160]:
            count = float(counts[group_index, index])
            if count < 2:
                continue
            term = str(terms[index])
            length_penalty = 1 + 0.18 * max(0, len(term.split()) - 1)
            ranked.append((term, float(scores[group_index, index]) / length_penalty))
        ranked.sort(key=lambda item: item[1], reverse=True)
        keywords = _distinct_keywords(ranked, limit=8)
        if not keywords:
            continue
        group["keywords"] = keywords
        group["keyword_method"] = "ctfidf"
        rows = [member["row"] for member in group["reviews"]]
        if group.get("label_source") == "keyword":
            group["label"] = f"{keywords[0]} 중심 의견"
            keyword_text = ", ".join(keywords[:4])
            group["summary"] = (
                f"{len(rows)}개 리뷰가 유사한 표현으로 묶였습니다. "
                f"주요 표현은 {keyword_text}이며 긍정 비율은 {_positive_ratio(rows):.0%}입니다."
            )
    return groups


def _cluster_keyword_document(group: dict[str, Any]) -> str:
    reviews = []
    for member in group.get("reviews", []):
        row = member.get("row", {})
        text = _normalize_review_text(str(row.get("review") or ""))
        if text:
            reviews.append(text)
    return " ".join(reviews)


def _distinct_keywords(ranked_terms: list[tuple[str, float]], limit: int) -> list[str]:
    selected: list[str] = []
    for term, score in ranked_terms:
        cleaned = _clean_keyword(term)
        if not cleaned or score <= 0:
            continue
        if _keyword_is_noise(cleaned):
            continue
        if any(_keywords_overlap(cleaned, existing) for existing in selected):
            continue
        selected.append(cleaned)
        if len(selected) >= limit:
            break
    return selected


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique


def _clean_keyword(term: str) -> str:
    compact = re.sub(r"\s+", " ", term.casefold()).strip(" '\".,!?;:()[]{}")
    return compact


def _keyword_is_noise(keyword: str) -> bool:
    parts = keyword.split()
    if not parts:
        return True
    if len(parts) > 2:
        return True
    if len(parts) > 1 and (parts[0] in STOPWORDS or parts[-1] in STOPWORDS):
        return True
    if all(part in STOPWORDS for part in parts):
        return True
    if len(parts) == 1 and parts[0] in STOPWORDS:
        return True
    if len(keyword) <= 2 and not re.search(r"[가-힣ぁ-んァ-ン一-龥]", keyword):
        return True
    if re.fullmatch(r"[\d_]+", keyword):
        return True
    return False


def _keywords_overlap(candidate: str, existing: str) -> bool:
    candidate_parts = set(candidate.split())
    existing_parts = set(existing.split())
    if not candidate_parts or not existing_parts:
        return False
    if candidate in existing or existing in candidate:
        return True
    overlap = len(candidate_parts & existing_parts)
    return overlap >= min(len(candidate_parts), len(existing_parts)) and overlap > 0


def _enrich_cluster_insights(
    groups: list[dict[str, Any]],
    app_id: str | None,
    use_lmstudio: bool,
    llm_model: str | None,
) -> list[dict[str, Any]]:
    enriched = []
    for group in groups:
        insight = _deterministic_cluster_insight(group, app_id)
        if use_lmstudio:
            insight = _lmstudio_cluster_insight(group, insight, app_id, llm_model) or insight
        enriched.append({**group, "insight": insight})
    return enriched


def _deterministic_cluster_insight(group: dict[str, Any], app_id: str | None) -> ClusterInsight:
    rows = [member["row"] for member in group["reviews"]]
    positive_ratio = float(group.get("positive_ratio") or _positive_ratio(rows))
    title = str(group["label"])
    warning = group.get("quality_warning")
    keyword_text = ", ".join(group.get("keywords") or [])
    label_warnings = list(group.get("label_warnings") or [])
    summary = str(group.get("summary") or "").strip()
    if not summary:
        summary = f"{len(rows)}개 리뷰가 {title} 라벨로 묶였습니다. 추천 비율은 {positive_ratio:.0%}입니다."
    if keyword_text and "주요" not in summary:
        summary += f" 주요 표현은 {keyword_text}입니다."
    if group.get("label_source") in {"keyword", "fallback"}:
        summary += " 이 라벨은 진단용이므로 실제 기획 판단은 인사이트 보드와 원문 근거를 우선하세요."

    praise = f"{title}을 긍정적으로 언급한 리뷰가 있습니다." if positive_ratio > 0 else ""
    pain_point = f"{title}에 대한 불만 또는 주의 신호가 있습니다." if positive_ratio < 1 else ""
    planner_action = _planner_action_for(title, positive_ratio, app_id)
    marketing_angle = f"{title} 관련 호평은 스토어 문구나 패치 노트에서 강점 근거로 검토할 수 있습니다."
    warnings = _unique_strings(([warning] if warning else []) + label_warnings)
    confidence = 0.7
    if warnings:
        confidence -= 0.15
    if len(rows) < 30:
        confidence -= 0.1
    return ClusterInsight(
        title=title,
        summary=summary,
        praise=praise,
        pain_point=pain_point,
        planner_action=planner_action,
        marketing_angle=marketing_angle,
        confidence=max(0.3, min(confidence, 0.9)),
        warnings=warnings,
    )


def _planner_action_for(title: str, positive_ratio: float, app_id: str | None) -> str:
    if positive_ratio <= 0.45:
        return f"{title} 불만 원문을 우선 확인하고 다음 패치/공지에서 대응 여부를 정리하세요."
    if positive_ratio < 0.65:
        return f"{title}은 호불호가 갈립니다. 언어권과 최근 기간별로 나눠 원인을 분리하세요."
    if str(app_id or "") == "730" and ("치터" in title or "서버" in title or "매치" in title):
        return f"{title} 신호는 운영 신뢰와 직접 연결되므로 최근 불만 리뷰를 별도로 추적하세요."
    return f"{title} 호평은 유지해야 할 강점으로 기록하고, 불만 샘플이 있는지 함께 점검하세요."


def _lmstudio_cluster_insight(
    group: dict[str, Any],
    fallback: ClusterInsight,
    app_id: str | None,
    llm_model: str | None,
) -> ClusterInsight | None:
    samples = _balanced_lmstudio_samples(group["reviews"], limit=10)
    keyword_text = ", ".join(group.get("keywords") or []) or "없음"
    warning_text = group.get("quality_warning") or "없음"
    sample_text = "\n".join(
        f"- {'추천' if member['row'].get('voted_up') else '비추천'} / {member['row'].get('language')} / "
        f"{_playtime_hours(member['row'].get('playtime_at_review'))}: "
        f"{_quote(member['row'].get('review') or '')}"
        for member in samples
    )
    prompt = (
        "Steam 리뷰 클러스터를 게임 기획자가 읽을 수 있게 한국어 JSON으로만 요약하세요. "
        "과장하지 말고 원문에 없는 사실을 만들지 마세요. "
        "title은 30자 안팎의 구체적인 명사구로 쓰고, summary는 원인/맥락을 1문장으로 쓰세요. "
        "planner_action은 기획자가 다음에 확인할 액션이어야 합니다.\n"
        f"Steam app_id={app_id}. 기존 라벨={group['label']}. "
        f"키워드={keyword_text}. 추천율={float(group.get('positive_ratio') or 0):.0%}. "
        f"품질 경고={warning_text}.\n"
        f"샘플:\n{sample_text}\n"
        'JSON keys: title, summary, praise, pain_point, planner_action, marketing_angle, confidence, warnings'
    )
    model: str | None = None
    try:
        with httpx.Client(timeout=45) as client:
            model = _lmstudio_default_model_sync(client, llm_model)
            body: dict[str, Any] = {
                "input": prompt,
                "context_length": 8000,
            }
            if model:
                body["model"] = model
            response = client.post(
                f"{LM_STUDIO_NATIVE_BASE_URL}/chat",
                json=body,
            )
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return None

    raw = _extract_lmstudio_text(payload)
    if isinstance(raw, dict):
        raw = json.dumps(raw)
    data = _parse_json_object(str(raw))
    if not data:
        return None
    return ClusterInsight(
        title=str(data.get("title") or fallback.title)[:80],
        summary=str(data.get("summary") or fallback.summary),
        praise=str(data.get("praise") or fallback.praise),
        pain_point=str(data.get("pain_point") or fallback.pain_point),
        planner_action=str(data.get("planner_action") or fallback.planner_action),
        marketing_angle=str(data.get("marketing_angle") or fallback.marketing_angle),
        confidence=max(0.0, min(float(data.get("confidence") or fallback.confidence), 1.0)),
        warnings=_coerce_string_list(data.get("warnings", fallback.warnings)),
        source="lm_studio",
        model=model or llm_model,
    )


def _balanced_lmstudio_samples(members: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    ranked = _rank_members(members)
    selected: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()

    def add_matching(predicate: Any, count: int) -> None:
        for member in ranked:
            if len(selected) >= limit:
                return
            if count <= 0:
                return
            if not predicate(member):
                continue
            text_hash = _text_hash(_quote(str(member["row"].get("review") or "")))
            if text_hash in seen_hashes:
                continue
            selected.append(member)
            seen_hashes.add(text_hash)
            count -= 1

    add_matching(lambda member: not bool(member["row"].get("voted_up")), max(2, limit // 3))
    add_matching(lambda member: bool(member["row"].get("voted_up")), max(2, limit // 3))
    add_matching(lambda _member: True, limit)
    return selected[:limit]


def _parse_json_object(raw: str) -> dict[str, Any] | None:
    cleaned = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE).replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _playtime_hours(value: Any) -> str:
    try:
        minutes = int(value or 0)
    except (TypeError, ValueError):
        minutes = 0
    if minutes <= 0:
        return "플레이타임 미상"
    return f"{minutes / 60:.1f}h"


def _extract_lmstudio_text(payload: dict[str, Any]) -> str:
    for key in ("output", "content", "text"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts = []
            for item in value:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("content") or item.get("message")
                    if isinstance(text, list):
                        text = " ".join(str(part.get("text") if isinstance(part, dict) else part) for part in text)
                    parts.append(str(text or ""))
                else:
                    parts.append(str(item))
            return " ".join(part for part in parts if part)
    message = payload.get("message")
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            choice_message = first.get("message")
            if isinstance(choice_message, dict) and isinstance(choice_message.get("content"), str):
                return choice_message["content"]
            if isinstance(first.get("text"), str):
                return first["text"]
    return ""


def _coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)] if str(value).strip() else []


def _lmstudio_default_model_sync(client: httpx.Client, preferred_model: str | None = None) -> str | None:
    try:
        response = client.get(f"{LM_STUDIO_NATIVE_BASE_URL}/models")
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None
    rows = payload.get("models") or []
    llm = [str(item.get("key")) for item in rows if item.get("type") == "llm" and item.get("key")]
    if preferred_model and preferred_model in llm:
        return preferred_model
    models = [str(item.get("key")) for item in rows if item.get("key")]
    return llm[0] if llm else models[0] if models else None


def _lmstudio_openai_model_sync(client: httpx.Client, preferred_model: str | None = None) -> str | None:
    preferred = str(preferred_model or "").strip()
    if preferred:
        return preferred
    try:
        response = client.get(f"{LM_STUDIO_OPENAI_BASE_URL}/models")
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None
    models = [
        str(item.get("id"))
        for item in payload.get("data", [])
        if item.get("id") and "embed" not in str(item.get("id")).lower()
    ]
    return models[0] if models else None


def _store_embeddings(
    conn: duckdb.DuckDBPyConnection,
    reviews: list[dict[str, Any]],
    model_name: str,
    embeddings: list[list[float]] | None = None,
) -> None:
    generated_at = utcnow()
    rows = []
    for index, review in enumerate(reviews):
        embedding = embeddings[index] if embeddings is not None else _hash_embedding(str(review.get("review") or ""))
        rows.append(
            (
                review["recommendation_id"],
                model_name,
                len(embedding),
                json.dumps([round(float(value), 6) for value in embedding]),
                generated_at,
            )
        )
    conn.executemany(
        """
        INSERT INTO review_embeddings (review_id, model, dimension, embedding, generated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (review_id, model) DO UPDATE SET
            dimension = excluded.dimension,
            embedding = excluded.embedding,
            generated_at = excluded.generated_at
        """,
        rows,
    )


def _store_review_quality(
    conn: duckdb.DuckDBPyConnection,
    analysis_run_id: int,
    quality_rows: list[ReviewQuality],
) -> None:
    if not quality_rows:
        return
    conn.executemany(
        """
        INSERT INTO review_quality (
            analysis_run_id, review_id, normalized_text, text_hash,
            quality_score, quality_flags, duplicate_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (analysis_run_id, review_id) DO UPDATE SET
            normalized_text = excluded.normalized_text,
            text_hash = excluded.text_hash,
            quality_score = excluded.quality_score,
            quality_flags = excluded.quality_flags,
            duplicate_count = excluded.duplicate_count
        """,
        [
            (
                analysis_run_id,
                row.review_id,
                row.normalized_text,
                row.text_hash,
                row.quality_score,
                json.dumps(row.quality_flags),
                row.duplicate_count,
            )
            for row in quality_rows
        ],
    )


def _store_issue_outputs(
    conn: duckdb.DuckDBPyConnection,
    analysis_run_id: int,
    app_id: str | None,
    units: list[dict[str, Any]],
    cards: list[dict[str, Any]],
) -> tuple[int, int]:
    if not units and not cards:
        return 0, 0

    conn.execute("DELETE FROM issue_evidence WHERE analysis_run_id = ?", [analysis_run_id])
    conn.execute("DELETE FROM issues WHERE analysis_run_id = ?", [analysis_run_id])
    conn.execute("DELETE FROM issue_units WHERE analysis_run_id = ?", [analysis_run_id])

    if units:
        conn.executemany(
            """
            INSERT INTO issue_units (
                analysis_run_id, app_id, review_id, unit_index, unit_text, language,
                voted_up, intent, aspect, sentiment, quality_score, quality_flags,
                is_quarantined, quarantine_reason, text_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    analysis_run_id,
                    app_id,
                    unit["review_id"],
                    unit["unit_index"],
                    unit["unit_text"],
                    unit.get("language"),
                    unit.get("voted_up"),
                    unit["intent"],
                    unit["aspect"],
                    unit["sentiment"],
                    unit["quality_score"],
                    json.dumps(unit["quality_flags"]),
                    unit["is_quarantined"],
                    unit["quarantine_reason"],
                    unit["text_hash"],
                )
                for unit in units
            ],
        )

    unit_ids = {
        (str(row["review_id"]), int(row["unit_index"]), str(row.get("text_hash") or "")): int(row["id"])
        for row in rows_to_dicts(
            conn.execute(
                """
                SELECT id, review_id, unit_index, text_hash
                FROM issue_units
                WHERE analysis_run_id = ?
                """,
                [analysis_run_id],
            )
        )
    }

    issues_created = 0
    evidence_created = 0
    for card in cards:
        issue_id = conn.execute(
            """
            INSERT INTO issues (
                analysis_run_id, app_id, title, summary, intent, aspect, status,
                confidence_band, confidence, priority_score, review_count,
                unique_review_count, unit_count, complaint_count, praise_count,
                request_count, bug_count, positive_ratio, language_counts,
                top_terms, why_it_matters, recommended_action, warnings, source, model
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [
                analysis_run_id,
                app_id,
                card["title"],
                card["summary"],
                card["intent"],
                card["aspect"],
                card["status"],
                card["confidence_band"],
                card["confidence"],
                card["priority_score"],
                card["review_count"],
                card["unique_review_count"],
                card["unit_count"],
                card["complaint_count"],
                card["praise_count"],
                card["request_count"],
                card["bug_count"],
                card["positive_ratio"],
                json.dumps(card["language_counts"]),
                json.dumps(card["top_terms"]),
                card["why_it_matters"],
                card["recommended_action"],
                json.dumps(card["warnings"]),
                card["source"],
                card["model"],
            ],
        ).fetchone()[0]
        issues_created += 1

        for unit in card["evidence_units"]:
            unit_id = unit_ids.get((unit["review_id"], int(unit["unit_index"]), str(unit.get("text_hash") or "")))
            conn.execute(
                """
                INSERT INTO issue_evidence (
                    issue_id, unit_id, analysis_run_id, app_id, review_id, quote,
                    evidence_role, language, voted_up, quality_score,
                    verifier_verdict, summary_ko, subissue, verifier_reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    issue_id,
                    unit_id,
                    analysis_run_id,
                    app_id,
                    unit["review_id"],
                    unit["unit_text"],
                    unit["intent"],
                    unit.get("language"),
                    unit.get("voted_up"),
                    unit["quality_score"],
                    unit.get("verifier_verdict"),
                    unit.get("summary_ko"),
                    unit.get("subissue"),
                    unit.get("verifier_reason"),
                ],
            )
            evidence_created += 1
    return issues_created, evidence_created


def _store_axis_suggestions(
    conn: duckdb.DuckDBPyConnection,
    analysis_run_id: int,
    app_id: str | None,
    suggestions: list[dict[str, Any]],
) -> int:
    conn.execute("DELETE FROM axis_suggestions WHERE analysis_run_id = ?", [analysis_run_id])
    if not suggestions:
        return 0
    conn.executemany(
        """
        INSERT INTO axis_suggestions (
            analysis_run_id, app_id, label, rationale, suggested_pattern,
            evidence_count, language_counts, example_review_ids, kind,
            canonical_label_ko, definition, include_criteria, exclude_criteria,
            evidence_claim_ids, why_actionable, quality_gate, failure_reason,
            status, target_axis_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """,
        [
            (
                analysis_run_id,
                app_id,
                suggestion["label"],
                suggestion["rationale"],
                suggestion["suggested_pattern"],
                suggestion["evidence_count"],
                json.dumps(suggestion["language_counts"]),
                json.dumps(suggestion["example_review_ids"]),
                suggestion.get("kind", "raw_signal"),
                suggestion.get("canonical_label_ko"),
                suggestion.get("definition"),
                json.dumps(suggestion.get("include_criteria") or []),
                json.dumps(suggestion.get("exclude_criteria") or []),
                json.dumps(suggestion.get("evidence_claim_ids") or []),
                suggestion.get("why_actionable"),
                suggestion.get("quality_gate", "fail"),
                suggestion.get("failure_reason"),
                _axis_id_for_key(conn, app_id, suggestion.get("target_axis_key")),
            )
            for suggestion in suggestions
        ],
    )
    return len(suggestions)


def _axis_id_for_key(conn: duckdb.DuckDBPyConnection, app_id: str | None, axis_key: Any) -> int | None:
    if not axis_key:
        return None
    row = conn.execute(
        """
        SELECT id
        FROM analysis_axes
        WHERE key = ?
          AND status = 'active'
          AND (scope IN ('common', 'genre') OR app_id = ?)
        ORDER BY CASE scope WHEN 'game' THEN 1 WHEN 'genre' THEN 2 ELSE 3 END, id
        LIMIT 1
        """,
        [str(axis_key), str(app_id or "")],
    ).fetchone()
    return int(row[0]) if row else None


def _store_analysis_outputs(
    conn: duckdb.DuckDBPyConnection,
    analysis_run_id: int,
    groups: list[dict[str, Any]],
    *,
    evidence_per_claim: int,
    exclude_duplicate_evidence: bool,
) -> tuple[int, int]:
    clusters_created = 0
    evidence_created = 0
    used_evidence_hashes: set[str] = set()
    for group in sorted(groups, key=lambda item: len(item["reviews"]), reverse=True):
        ranked_members = _rank_members(group["reviews"])
        rows = [member["row"] for member in ranked_members]
        review_count = len(rows)
        avg_score = sum(float(row.get("weighted_vote_score") or 0) for row in rows) / review_count
        exemplar = rows[0]["recommendation_id"]
        insight = group["insight"]
        cluster_id = conn.execute(
            """
            INSERT INTO clusters (
                analysis_run_id, label, summary, sentiment, language, review_count,
                avg_weighted_score, exemplar_review_id, positive_ratio, top_keywords,
                keyword_method, quality_warning, label_source, label_confidence,
                label_warnings, matched_theme_key, matched_terms
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id
            """,
            [
                analysis_run_id,
                insight.title,
                insight.summary,
                group["sentiment"],
                group["language"],
                review_count,
                avg_score,
                exemplar,
                group["positive_ratio"],
                json.dumps(group["keywords"]),
                group.get("keyword_method"),
                group["quality_warning"],
                group.get("label_source"),
                group.get("label_confidence"),
                json.dumps(group.get("label_warnings") or []),
                group.get("matched_theme_key"),
                json.dumps(group.get("matched_terms") or []),
            ],
        ).fetchone()[0]
        _insert_cluster_insight(conn, cluster_id, insight)
        clusters_created += 1
        conn.executemany(
            "INSERT INTO review_clusters (review_id, cluster_id, score) VALUES (?, ?, ?)",
            [(member["row"]["recommendation_id"], cluster_id, member["score"]) for member in ranked_members],
        )
        for claim_type, claim_text in _claim_specs_for_group(group, insight):
            claim_id = conn.execute(
                """
                INSERT INTO claims (analysis_run_id, cluster_id, claim_type, claim_text, confidence)
                VALUES (?, ?, ?, ?, ?) RETURNING id
                """,
                [analysis_run_id, cluster_id, claim_type, claim_text, insight.confidence],
            ).fetchone()[0]
            evidence_members = _select_evidence_members(
                ranked_members,
                claim_type,
                evidence_per_claim,
                used_evidence_hashes,
                exclude_duplicate_evidence,
            )
            for member in evidence_members:
                row = member["row"]
                quality = member.get("quality")
                conn.execute(
                    """
                    INSERT INTO evidence (
                        analysis_run_id, claim_id, review_id, cluster_id, quote,
                        evidence_type, evidence_role, note, quality_score
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        analysis_run_id,
                        claim_id,
                        row["recommendation_id"],
                        cluster_id,
                        _quote(row["review"]),
                        _evidence_type(claim_type),
                        claim_type,
                        f"{_evidence_role_label(claim_type)} · 품질 {member['representative_score']:.2f}",
                        quality.quality_score if quality else None,
                    ],
                )
                evidence_created += 1
    return clusters_created, evidence_created


def _insert_cluster_insight(conn: duckdb.DuckDBPyConnection, cluster_id: int, insight: ClusterInsight) -> None:
    conn.execute(
        """
        INSERT INTO cluster_insights (
            cluster_id, title, summary, praise, pain_point,
            planner_action, marketing_angle, confidence, warnings, source, model
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            cluster_id,
            insight.title,
            insight.summary,
            insight.praise,
            insight.pain_point,
            insight.planner_action,
            insight.marketing_angle,
            insight.confidence,
            json.dumps(insight.warnings),
            insight.source,
            insight.model,
        ],
    )


def _claim_specs_for_group(group: dict[str, Any], insight: ClusterInsight) -> list[tuple[str, str]]:
    rows = [member["row"] for member in group["reviews"]]
    has_praise = any(row.get("voted_up") for row in rows)
    has_complaint = any(not row.get("voted_up") for row in rows)
    claims: list[tuple[str, str]] = []
    if has_complaint:
        claims.append(("complaint", insight.pain_point or f"{insight.title} 관련 불만 신호가 있습니다."))
    if has_praise:
        claims.append(("praise", insight.praise or f"{insight.title} 관련 호평 신호가 있습니다."))
    if not claims:
        claims.append(("representative", insight.summary))
    return claims[:2]


def _select_evidence_members(
    ranked_members: list[dict[str, Any]],
    role: str,
    limit: int,
    used_hashes: set[str],
    exclude_duplicates: bool,
) -> list[dict[str, Any]]:
    def role_match(member: dict[str, Any]) -> bool:
        voted_up = bool(member["row"].get("voted_up"))
        if role == "complaint":
            return not voted_up
        if role == "praise":
            return voted_up
        return True

    selected: list[dict[str, Any]] = []
    candidates = [member for member in ranked_members if role_match(member)]
    if not candidates:
        candidates = ranked_members

    for member in candidates:
        quality = member.get("quality")
        text_hash = _text_hash(_quote(str(member["row"].get("review") or "")))
        if exclude_duplicates and text_hash in used_hashes:
            continue
        if quality and quality.quality_score < 0.2 and len(candidates) > limit:
            continue
        selected.append(member)
        used_hashes.add(text_hash)
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        for member in candidates:
            if member in selected:
                continue
            text_hash = _text_hash(_quote(str(member["row"].get("review") or "")))
            if exclude_duplicates and text_hash in used_hashes:
                continue
            selected.append(member)
            used_hashes.add(text_hash)
            if len(selected) >= limit:
                break
    if not selected and candidates:
        member = candidates[0]
        text_hash = _text_hash(_quote(str(member["row"].get("review") or "")))
        selected.append(member)
        used_hashes.add(text_hash)
    return selected


def _text_hash(text: str) -> str:
    return hashlib.blake2b(_normalize_review_text(text).encode("utf-8"), digest_size=12).hexdigest()


def _evidence_role_label(role: str) -> str:
    if role == "complaint":
        return "구체적 불만"
    if role == "praise":
        return "구체적 호평"
    if role == "recent":
        return "최근 리뷰"
    if role == "high_weight":
        return "고가중치 리뷰"
    return "대표 리뷰"


def _store_analysis_report(
    conn: duckdb.DuckDBPyConnection,
    analysis_run_id: int,
    app_id: str | None,
    reviews: list[dict[str, Any]],
    clusters_created: int,
    clusterer: str,
) -> None:
    positive_ratio = _positive_ratio(reviews)
    summary = (
        f"{len(reviews)}개 리뷰를 분석해 {clusters_created}개 클러스터를 만들었습니다. "
        f"긍정 비율은 {positive_ratio:.0%}이며 사용한 분석기는 {clusterer}입니다."
    )
    conn.execute(
        "INSERT INTO reports (analysis_run_id, title, summary, filters) VALUES (?, ?, ?, ?)",
        [
            analysis_run_id,
            "Local analysis run",
            summary,
            json.dumps({"app_id": app_id, "clusterer": clusterer}),
        ],
    )


def _hash_embedding(text: str, dimension: int = 64) -> list[float]:
    vector = [0.0] * dimension
    terms = _tokens(text)
    compact = re.sub(r"\s+", " ", text.lower())
    terms.extend(compact[index : index + 3] for index in range(max(0, len(compact) - 2)))
    for term in terms:
        digest = hashlib.blake2b(term.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def _rank_members(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for member in members:
        row = member["row"]
        quality = member.get("quality")
        length_score = min(len(str(row.get("review") or "")) / 500, 1.0)
        weighted_score = max(0.0, min(float(row.get("weighted_vote_score") or 0), 1.0))
        quality_score = quality.quality_score if quality else 0.5
        representative_score = member["score"] * 0.45 + quality_score * 0.35 + weighted_score * 0.15 + length_score * 0.05
        ranked.append({**member, "quality": quality, "representative_score": representative_score})
    return sorted(ranked, key=lambda item: item["representative_score"], reverse=True)


def _best_theme(rows: list[dict[str, Any]], app_id: str | None = None) -> ThemeMatch | None:
    if not rows:
        return None
    candidates: list[ThemeMatch] = []
    total = len(rows)
    for theme, source in _theme_candidates_for_app(app_id):
        term_counter: Counter[str] = Counter()
        support_review_count = 0
        for row in rows:
            matches = _theme_pattern_matches(theme, str(row.get("review") or "").lower())
            if not matches:
                continue
            support_review_count += 1
            term_counter.update(matches)
        count = sum(term_counter.values())
        if count <= 0:
            continue
        coverage = support_review_count / total
        accepted, confidence, warnings = _theme_acceptance(theme, source, support_review_count, coverage, total)
        candidates.append(
            ThemeMatch(
                theme=theme,
                source=source,
                count=count,
                support_review_count=support_review_count,
                coverage=coverage,
                matched_terms=[term for term, _count in term_counter.most_common(6)],
                confidence=confidence,
                warnings=warnings,
                accepted=accepted,
            )
        )
    if not candidates:
        return None
    accepted_candidates = [candidate for candidate in candidates if candidate.accepted]
    pool = accepted_candidates or candidates
    return sorted(
        pool,
        key=lambda item: (
            item.source == "game_theme",
            item.support_review_count,
            item.coverage,
            item.count,
        ),
        reverse=True,
    )[0]


def _theme_acceptance(
    theme: Theme,
    source: str,
    support_review_count: int,
    coverage: float,
    total_reviews: int,
) -> tuple[bool, str, list[str]]:
    if source == "game_theme":
        min_support = 2 if total_reviews < 50 else 3
        min_coverage = 0.05
    else:
        min_support = 2 if total_reviews < 20 else 3 if total_reviews < 80 else 5
        min_coverage = 0.10

    if source == "common_theme" and theme.key in ACTION_THEME_KEYS:
        min_support = max(min_support, 4)
        min_coverage = 0.18

    warnings: list[str] = []
    accepted = support_review_count >= min_support and coverage >= min_coverage
    if not accepted:
        warnings.append(
            f"{theme.label} 관련 표현이 {support_review_count}개 리뷰에서만 보여 확정 라벨로 쓰지 않았습니다."
        )
        return False, "low", warnings

    if source == "common_theme":
        warnings.append("공통 테마 라벨입니다. 게임 고유 맥락은 인사이트 보드의 근거로 다시 확인하세요.")
    if source == "common_theme" and theme.key in ACTION_THEME_KEYS:
        warnings.append("액션/전투 공통 테마는 직접 표현이 충분할 때만 붙인 진단 라벨입니다.")

    high_threshold = 0.18 if source == "game_theme" else 0.25
    confidence = "high" if support_review_count >= 8 and coverage >= high_threshold else "medium"
    return True, confidence, warnings


def _quality_warning(rows: list[dict[str, Any]], quality_by_id: dict[str, ReviewQuality]) -> str | None:
    if not rows:
        return None
    qualities = [quality_by_id.get(str(row["recommendation_id"])) for row in rows]
    qualities = [quality for quality in qualities if quality]
    if not qualities:
        return None
    low_info = sum(1 for quality in qualities if "low_information" in quality.quality_flags or "very_short" in quality.quality_flags)
    duplicates = sum(1 for quality in qualities if "duplicate" in quality.quality_flags)
    if low_info / len(qualities) >= 0.45:
        return "짧거나 정보량이 낮은 리뷰가 많은 묶음"
    if duplicates / len(qualities) >= 0.35:
        return "중복 표현이 많은 묶음"
    if len(rows) < 20:
        return "표본이 작은 묶음"
    return None


def _sentiment(rows: list[dict[str, Any]]) -> str:
    ratio = _positive_ratio(rows)
    if ratio >= 0.65:
        return "positive"
    if ratio <= 0.45:
        return "negative"
    return "mixed"


def _positive_ratio(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if row.get("voted_up")) / len(rows)


def _dominant_language(rows: list[dict[str, Any]]) -> str | None:
    counts = Counter(str(row.get("language") or "unknown") for row in rows)
    language, count = counts.most_common(1)[0]
    return language if count / len(rows) >= 0.8 else None


def _keywords(rows: list[dict[str, Any]]) -> list[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        counter.update(token for token in _tokens(str(row.get("review") or "")) if token not in STOPWORDS)
    return [token for token, _ in counter.most_common(8)]


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z가-힣ぁ-んァ-ン一-龥0-9]{2,}", text)]


def _quote(text: str) -> str:
    compact = re.sub(r"\s+", " ", str(text or "")).strip()
    return compact[:300]


def _evidence_type(role: str) -> str:
    if role == "praise":
        return "praise"
    if role == "complaint":
        return "pain_point"
    return "representative"
