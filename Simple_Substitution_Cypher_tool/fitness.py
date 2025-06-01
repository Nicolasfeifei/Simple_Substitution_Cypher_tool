# fitness.py
# 评估解密文本质量的适应度函数，用于自动破译

import math
import re
import os

# --- 全局变量定义 (与上一版相同) ---
MONOGRAM_SCORES = {}
BIGRAM_SCORES = {}
TRIGRAM_SCORES = {}
QUADGRAM_SCORES = {}
ENGLISH_DICTIONARY_FITNESS = set()

MONOGRAMS_LOADED = False
BIGRAMS_LOADED = False
TRIGRAMS_LOADED = False
QUADGRAMS_LOADED = False
FITNESS_DICTIONARY_LOADED = False

MIN_MONOGRAM_LOG_PROB = -12.0
MIN_BIGRAM_LOG_PROB = -18.0
MIN_TRIGRAM_LOG_PROB = -22.0
MIN_QUADGRAM_LOG_PROB = -25.0

DEFAULT_FITNESS_WORDS = {"THE", "AND", "ING", "HER", "WAS", "FOR", "THAT", "THIS"}

# --- _load_ngrams_from_file, load_monograms, load_bigrams, etc. (与上一版相同) ---
def _load_ngrams_from_file(filepath, n, scores_dict_ref, loaded_flag_setter, min_log_prob_setter, ngram_type_name):
    """通用N-gram加载函数，从文件读取N-gram及其计数，计算对数概率并存储。"""
    if globals()[f"{ngram_type_name.upper()}S_LOADED"]:
        return
    raw_counts = {}; total_ngram_count = 0
    very_low_log_prob_fallback = math.log(1e-9) 
    try:
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0: raise FileNotFoundError 
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or not line: continue
                parts = line.split()
                if len(parts) == 2:
                    ngram_str = parts[0].upper()
                    try:
                        count = int(parts[1])
                        if len(ngram_str) == n and count > 0:
                            raw_counts[ngram_str] = count
                            total_ngram_count += count
                    except ValueError: pass 
        if not raw_counts or total_ngram_count == 0:
            print(f"适应度警告：未能从 '{filepath}' 加载有效的 {ngram_type_name} 计数。将使用极低备用值。")
            scores_dict_ref.clear(); scores_dict_ref["DEFAULT_FALLBACK"] = very_low_log_prob_fallback 
            min_log_prob_setter(very_low_log_prob_fallback - math.log(10))
        else:
            scores_dict_ref.clear()
            for ngram_str, count in raw_counts.items():
                scores_dict_ref[ngram_str] = math.log(count / total_ngram_count)
            min_prob_val = math.log(0.1 / total_ngram_count)
            min_log_prob_setter(min_prob_val)
            print(f"适应度函数：成功加载并处理 {len(scores_dict_ref)} 个 {ngram_type_name}。总计数: {total_ngram_count}。最小对数概率: {min_prob_val:.4f}")
    except FileNotFoundError:
        print(f"适应度错误：{ngram_type_name.capitalize()} 文件 '{filepath}' 未找到或为空。{ngram_type_name.capitalize()} 适应度将受严重影响，使用极低备用值。")
        scores_dict_ref.clear(); scores_dict_ref["DEFAULT_FALLBACK"] = very_low_log_prob_fallback
        min_log_prob_setter(very_low_log_prob_fallback - math.log(10))
    except Exception as e:
        print(f"适应度错误：加载 {ngram_type_name} 时发生意外错误：{e}。使用极低备用值。")
        scores_dict_ref.clear(); scores_dict_ref["DEFAULT_FALLBACK"] = very_low_log_prob_fallback
        min_log_prob_setter(very_low_log_prob_fallback - math.log(10))
    loaded_flag_setter()

def load_monograms(filepath="english_monograms.txt"):
    def set_loaded_flag(): global MONOGRAMS_LOADED; MONOGRAMS_LOADED = True
    def set_min_log_prob_value(val): global MIN_MONOGRAM_LOG_PROB; MIN_MONOGRAM_LOG_PROB = val
    _load_ngrams_from_file(filepath, 1, MONOGRAM_SCORES, set_loaded_flag, set_min_log_prob_value, "monogram")

def load_bigrams(filepath="english_bigrams.txt"):
    def set_loaded_flag(): global BIGRAMS_LOADED; BIGRAMS_LOADED = True
    def set_min_log_prob_value(val): global MIN_BIGRAM_LOG_PROB; MIN_BIGRAM_LOG_PROB = val
    _load_ngrams_from_file(filepath, 2, BIGRAM_SCORES, set_loaded_flag, set_min_log_prob_value, "bigram")

def load_trigrams(filepath="english_trigrams.txt"):
    def set_loaded_flag(): global TRIGRAMS_LOADED; TRIGRAMS_LOADED = True
    def set_min_log_prob_value(val): global MIN_TRIGRAM_LOG_PROB; MIN_TRIGRAM_LOG_PROB = val
    _load_ngrams_from_file(filepath, 3, TRIGRAM_SCORES, set_loaded_flag, set_min_log_prob_value, "trigram")

def load_quadgrams(filepath="english_quadgrams.txt"):
    def set_loaded_flag(): global QUADGRAMS_LOADED; QUADGRAMS_LOADED = True
    def set_min_log_prob_value(val): global MIN_QUADGRAM_LOG_PROB; MIN_QUADGRAM_LOG_PROB = val
    _load_ngrams_from_file(filepath, 4, QUADGRAM_SCORES, set_loaded_flag, set_min_log_prob_value, "quadgram")

def load_dictionary_for_fitness(filepath="common_words.txt"): # (与上一版相同)
    global ENGLISH_DICTIONARY_FITNESS, FITNESS_DICTIONARY_LOADED
    if FITNESS_DICTIONARY_LOADED: return
    try:
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0: raise FileNotFoundError
        with open(filepath, 'r', encoding='utf-8') as f:
            ENGLISH_DICTIONARY_FITNESS = set(word.strip().upper() for word in f if word.strip().isalpha())
        if not ENGLISH_DICTIONARY_FITNESS:
             print(f"适应度警告：词典文件 '{filepath}' 内容为空或无效。将使用内置的默认词典。")
             ENGLISH_DICTIONARY_FITNESS = DEFAULT_FITNESS_WORDS
    except FileNotFoundError:
        print(f"适应度警告：词典文件 '{filepath}' 未找到。将使用内置的默认词典。")
        ENGLISH_DICTIONARY_FITNESS = DEFAULT_FITNESS_WORDS
    FITNESS_DICTIONARY_LOADED = True

def _get_ngram_text_score(text, n, scores_dict, min_log_prob_val, loaded_checker_func): # (与上一版相同)
    if not loaded_checker_func():
        if n == 1 and not MONOGRAMS_LOADED: load_monograms()
        elif n == 2 and not BIGRAMS_LOADED: load_bigrams()
        elif n == 3 and not TRIGRAMS_LOADED: load_trigrams()
        elif n == 4 and not QUADGRAMS_LOADED: load_quadgrams()
    text_upper = ''.join(filter(str.isalpha, text.upper()))
    if len(text_upper) < n: return min_log_prob_val * (n + (n - len(text_upper))) 
    current_score_sum = 0.0; num_ngrams_in_text = 0
    for i in range(len(text_upper) - n + 1):
        ngram = text_upper[i:i+n]
        current_score_sum += scores_dict.get(ngram, min_log_prob_val)
        num_ngrams_in_text += 1
    return current_score_sum / num_ngrams_in_text if num_ngrams_in_text > 0 else min_log_prob_val * n

def get_monogram_score(text): return _get_ngram_text_score(text, 1, MONOGRAM_SCORES, MIN_MONOGRAM_LOG_PROB, lambda: MONOGRAMS_LOADED)
def get_bigram_score(text): return _get_ngram_text_score(text, 2, BIGRAM_SCORES, MIN_BIGRAM_LOG_PROB, lambda: BIGRAMS_LOADED)
def get_trigram_score(text): return _get_ngram_text_score(text, 3, TRIGRAM_SCORES, MIN_TRIGRAM_LOG_PROB, lambda: TRIGRAMS_LOADED)
def get_quadgram_score(text): return _get_ngram_text_score(text, 4, QUADGRAM_SCORES, MIN_QUADGRAM_LOG_PROB, lambda: QUADGRAMS_LOADED)

# --- 更新 get_dictionary_score ---
def get_dictionary_score(text, weighting_scheme='linear'):
    """
    基于在文本中找到的词典词及其长度计算得分。
    参数:
        text (str): 需要评估的文本。
        weighting_scheme (str): 权重方案。
            'count': 简单地计算找到的词占总词数的百分比 (旧行为)。
            'linear': 找到的词的得分贡献与其长度成正比。
            'quadratic': 找到的词的得分贡献与其长度的平方成正比。
    返回:
        float: 规范化后的词典得分 (0-100范围)。
    """
    if not FITNESS_DICTIONARY_LOADED:
        load_dictionary_for_fitness()

    words = re.findall(r'[a-zA-Z]+', text.upper()) # 提取所有单词
    if not words: 
        return 0.0

    achieved_score = 0.0
    total_potential_score = 0.0

    for word in words:
        word_len = len(word)
        current_word_potential_score = 0.0
        
        if weighting_scheme == 'linear':
            current_word_potential_score = word_len
        elif weighting_scheme == 'quadratic':
            current_word_potential_score = word_len ** 2
        elif weighting_scheme == 'count':
            current_word_potential_score = 1.0 # 每个词的潜在贡献是1
        else: # 默认为线性
            current_word_potential_score = word_len

        total_potential_score += current_word_potential_score

        if word in ENGLISH_DICTIONARY_FITNESS:
            achieved_score += current_word_potential_score
            
    if total_potential_score == 0: # 避免除以零 (例如，如果所有词长度为0或权重方案导致0)
        return 0.0
        
    return (achieved_score / total_potential_score) * 100.0


# --- 更新 calculate_fitness ---
def calculate_fitness(text, 
                      mono_weight=0.8,
                      bi_weight=0.12,
                      tri_weight=0.21,
                      quad_weight=0.38,
                      dict_weight=0.31, # 词典得分的整体权重
                      dictionary_weighting_scheme='linear'): # 新增：词典内部单词长度的加权方案
    """
    计算给定文本的综合适应度分数。分数越高，代表文本越像自然英文。
    参数:
        dictionary_weighting_scheme (str): 传递给 get_dictionary_score 的词长加权方案。
                                           可选 'count', 'linear', 'quadratic'。
    """
    m_score = get_monogram_score(text)
    b_score = get_bigram_score(text)
    t_score = get_trigram_score(text)
    q_score = get_quadgram_score(text)
    # 使用新的词典计分方法
    d_score_normalized_percent = get_dictionary_score(text, weighting_scheme=dictionary_weighting_scheme)
    
    # N-gram得分是平均对数概率 (负数，越接近0越好)
    # d_score_normalized_percent 是0-100的规范化百分比 (越高越好)
    # 仍然将词典得分除以10.0进行缩放，使其贡献与N-gram得分大致平衡
    fitness_score = (mono_weight * m_score) + \
                    (bi_weight * b_score) + \
                    (tri_weight * t_score) + \
                    (quad_weight * q_score) + \
                    (dict_weight * (d_score_normalized_percent / 6)) 
                    
    return fitness_score