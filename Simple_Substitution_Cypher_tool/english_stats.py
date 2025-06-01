# english_stats.py
# 存储英文的统计特性数据

LETTER_FREQUENCIES = { # 标准英文字母频率 (%)
    'E': 12.70, 'T': 9.06, 'A': 8.17, 'O': 7.51, 'I': 6.97, 'N': 6.75,
    'S': 6.33, 'H': 6.09, 'R': 5.99, 'D': 4.25, 'L': 4.03, 'C': 2.78,
    'U': 2.76, 'M': 2.41, 'W': 2.36, 'F': 2.23, 'G': 2.02, 'Y': 1.97,
    'P': 1.93, 'B': 1.29, 'V': 0.98, 'K': 0.77, 'J': 0.15, 'X': 0.15,
    'Q': 0.10, 'Z': 0.07
}
SORTED_ENGLISH_FREQUENCIES = sorted(LETTER_FREQUENCIES.items(), key=lambda item: item[1], reverse=True)

COMMON_BIGRAMS = [ # 常见英文二元组
    "TH", "HE", "IN", "ER", "AN", "RE", "ES", "ON", "ST", "NT",
    "EN", "AT", "ED", "TO", "OR", "EA", "HI", "IS", "OU", "AR", "AS", "DE", "RT", "VE"
]
COMMON_TRIGRAMS = [ # 常见英文三元组
    "THE", "ING", "AND", "HER", "ERE", "ENT", "THA", "NTH", "WAS", "ETH",
    "FOR", "DTH", "HIS", "OFT", "STH", "ITH"
]
DEFAULT_COMMON_WORDS_LIST = { # 默认常用短词 (备用)
    1: ["A", "I"],
    2: ["OF", "TO", "IN", "IT", "IS", "BE", "AS", "AT", "SO", "WE", "HE", "BY", "OR", "ON", "DO", "IF", "ME", "MY", "UP", "AN", "GO", "NO"],
    3: ["THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "ANY", "CAN", "HAD", "HER", "WAS", "ONE", "OUR", "OUT", "DAY", "GET", "HAS", "HIM", "HIS", "HOW", "MAN", "NEW", "NOW", "OLD", "SEE", "TWO", "WAY", "WHO", "BOY", "DID", "ITS", "LET", "PUT", "SAY", "SHE", "TOO", "USE"]
}