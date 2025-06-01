# analysis_helpers.py
# 手动破译模式下的辅助函数

import collections
import string
import re
from english_stats import SORTED_ENGLISH_FREQUENCIES

ENGLISH_DICTIONARY_ANALYSIS = set()
ANALYSIS_DICTIONARY_LOADED = False
DEFAULT_ANALYSIS_WORDS = {"A", "I", "IS", "IT", "OF", "TO", "IN", "ON", "AT", "AS", "BE", "HE", "WE", "OR", "BY", "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "ANY", "HAS", "HAD", "WAS", "ITS", "HER", "HIM", "HIS"}

def load_dictionary_for_analysis(filepath="common_words.txt"):
    """为手动分析助手加载词典文件。"""
    global ENGLISH_DICTIONARY_ANALYSIS, ANALYSIS_DICTIONARY_LOADED
    if ANALYSIS_DICTIONARY_LOADED: return
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ENGLISH_DICTIONARY_ANALYSIS = set(word.strip().upper() for word in f if word.strip().isalpha())
        if not ENGLISH_DICTIONARY_ANALYSIS:
            print(f"分析助手警告：词典文件 '{filepath}' 为空，使用默认词典。")
            ENGLISH_DICTIONARY_ANALYSIS = DEFAULT_ANALYSIS_WORDS
    except FileNotFoundError:
        print(f"分析助手警告：词典文件 '{filepath}' 未找到，使用默认词典。")
        ENGLISH_DICTIONARY_ANALYSIS = DEFAULT_ANALYSIS_WORDS
    ANALYSIS_DICTIONARY_LOADED = True

def get_letter_frequencies(text):
    """计算文本中字母的出现频率（%）。"""
    text_alpha_only = ''.join(filter(str.isalpha, text.upper()))
    if not text_alpha_only: return collections.Counter()
    counts = collections.Counter(text_alpha_only); total = len(text_alpha_only)
    return {char: (count / total) * 100 for char, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)}

def get_ngram_frequencies(text, n=2):
    """计算文本中N-gram的出现次数。"""
    text_alpha_only = ''.join(filter(str.isalpha, text.upper()))
    ngrams = collections.Counter()
    for i in range(len(text_alpha_only) - n + 1): ngrams[text_alpha_only[i:i+n]] += 1
    return {ngram: count for ngram, count in sorted(ngrams.items(), key=lambda item: item[1], reverse=True) if count > 0}

def apply_partial_key(ciphertext, partial_key_map):
    """应用部分密钥进行解密，未知字母用'_'表示。"""
    decrypted_text = ""
    for char_original_case in ciphertext:
        char_upper = char_original_case.upper()
        if char_upper.isalpha():
            decrypted_text += partial_key_map.get(char_upper, "_") # 已映射则用小写明文，否则用"_"
        else: decrypted_text += char_original_case
    return decrypted_text

def generate_frequency_suggestions_data(ciphertext_freq):
    """根据频率生成初步的密钥替换建议数据。"""
    suggestions_data = []
    sorted_cipher_freq_list = sorted(ciphertext_freq.items(), key=lambda item: item[1], reverse=True)
    for i, (cipher_char, freq) in enumerate(sorted_cipher_freq_list):
        if i < len(SORTED_ENGLISH_FREQUENCIES):
            eng_char, eng_freq = SORTED_ENGLISH_FREQUENCIES[i]
            suggestions_data.append({'cipher': cipher_char, 'plain': eng_char, 'cipher_freq': freq, 'plain_freq': eng_freq})
    return suggestions_data

def suggest_patterns_from_partially_decrypted(partially_decrypted_text, current_key_map):
    """(高级功能占位符) 根据部分解密文本中的模式和词典给出建议。"""
    if not ANALYSIS_DICTIONARY_LOADED: load_dictionary_for_analysis()
    suggestions = [] # 此处可添加更复杂的模式匹配逻辑
    return suggestions