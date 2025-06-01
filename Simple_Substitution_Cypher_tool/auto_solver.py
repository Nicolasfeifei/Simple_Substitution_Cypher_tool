# auto_solver.py
# 实现模拟退火算法进行自动破译，支持用户锁定的部分密钥映射

import random
import string
import math
from cipher_logic import decrypt, PLAINTEXT_ALPHABET, validate_key
from fitness import calculate_fitness

def generate_random_key():
    """生成一个完全随机的、有效的26字母密钥字符串 (密文序列对应a-z)。"""
    alphabet_list = list(PLAINTEXT_ALPHABET)
    random.shuffle(alphabet_list)
    return "".join(alphabet_list)

def generate_initial_key_with_locks(user_locked_mappings):
    """根据用户锁定的映射 {密文大写: 明文小写} 生成初始密钥字符串。"""
    key_list_for_plain_order = [''] * 26
    plain_to_locked_cipher = {v.lower(): k.upper() for k, v in user_locked_mappings.items()}
    all_cipher_chars_available = set(string.ascii_uppercase)
    used_cipher_chars_by_locks = set()

    for plain_idx in range(26):
        current_plain_char = PLAINTEXT_ALPHABET[plain_idx]
        if current_plain_char in plain_to_locked_cipher:
            locked_cipher_for_plain = plain_to_locked_cipher[current_plain_char]
            key_list_for_plain_order[plain_idx] = locked_cipher_for_plain
            used_cipher_chars_by_locks.add(locked_cipher_for_plain)

    remaining_available_cipher_chars = list(all_cipher_chars_available - used_cipher_chars_by_locks)
    random.shuffle(remaining_available_cipher_chars)
    
    current_remaining_cipher_idx = 0
    for plain_idx in range(26):
        if key_list_for_plain_order[plain_idx] == '':
            if current_remaining_cipher_idx < len(remaining_available_cipher_chars):
                key_list_for_plain_order[plain_idx] = remaining_available_cipher_chars[current_remaining_cipher_idx]
                current_remaining_cipher_idx += 1
            else:
                key_list_for_plain_order[plain_idx] = '?' # 标记生成问题
                # print(f"自动求解警告：生成初始密钥时缺少可用密文字母 (明文索引: {plain_idx})。") # 控制台调试信息

    initial_key_str = "".join(key_list_for_plain_order)
    if '?' in initial_key_str or len(set(initial_key_str)) != 26:
        # print("自动求解错误：根据锁定映射生成的初始密钥无效，将使用完全随机密钥。") # 控制台调试信息
        return generate_random_key()
    return initial_key_str

def modify_key_with_locks(current_key_list, locked_plain_char_indices):
    """修改密钥列表，仅交换那些未被用户锁定的明文字母的映射。"""
    unlocked_indices = [i for i in range(26) if i not in locked_plain_char_indices]
    if len(unlocked_indices) < 2: return current_key_list 
    idx1, idx2 = random.sample(unlocked_indices, 2)
    current_key_list[idx1], current_key_list[idx2] = current_key_list[idx2], current_key_list[idx1]
    return current_key_list

def solve_simulated_annealing(ciphertext,
                              user_locked_mappings=None, 
                              initial_temperature=10.0,
                              cooling_rate=0.997, 
                              min_temperature=0.01,
                              max_iterations_per_run=100000, # 单轮运行的迭代次数
                              status_callback=None):      # 移除了 stop_event
    """执行单轮模拟退火算法。"""
    if not PLAINTEXT_ALPHABET: _ = validate_key("abcdefghijklmnopqrstuvwxyz")

    if user_locked_mappings is None: user_locked_mappings = {}

    locked_plain_indices = []
    if user_locked_mappings:
        for plain_char_value in user_locked_mappings.values():
            try: locked_plain_indices.append(PLAINTEXT_ALPHABET.index(plain_char_value.lower()))
            except ValueError: pass # 无效的锁定明文字母在GUI层面已校验

    current_key_str = generate_initial_key_with_locks(user_locked_mappings)
    current_key_list_mutable = list(current_key_str)
    current_decrypted_text = decrypt(ciphertext, current_key_str)
    current_score = calculate_fitness(current_decrypted_text, dictionary_weighting_scheme='linear') 

    run_best_key_str = current_key_str
    run_best_score = current_score
    run_best_decrypted_text = current_decrypted_text

    temperature = initial_temperature
    last_reported_iteration_for_gui = 0 
    status_message_on_stop_for_run = "已完成 (单轮)" # 默认的单轮停止原因

    if status_callback: 
        status_callback(run_best_key_str, run_best_decrypted_text, run_best_score, 0, False, "单轮初始化完成, 开始迭代...")
        last_reported_iteration_for_gui = 0 

    for i in range(max_iterations_per_run): # 模拟退火主循环
        # 移除了 stop_event 检查
        if temperature < min_temperature: status_message_on_stop_for_run = f"温度已达最低 (单轮 T={temperature:.3f})"; break

        candidate_key_list_mutable = list(current_key_list_mutable)
        candidate_key_list_mutable = modify_key_with_locks(candidate_key_list_mutable, locked_plain_indices)
        candidate_key_str = "".join(candidate_key_list_mutable)
        
        candidate_decrypted_text = decrypt(ciphertext, candidate_key_str)
        candidate_score = calculate_fitness(candidate_decrypted_text, dictionary_weighting_scheme='linear')

        delta_score = candidate_score - current_score
        current_status_msg_for_callback = "探索中..."

        if delta_score > 0: 
            current_key_list_mutable = candidate_key_list_mutable
            current_score = candidate_score
            current_decrypted_text = candidate_decrypted_text
            current_status_msg_for_callback = "接受更优解..."
            if current_score > run_best_score: 
                run_best_score = current_score
                run_best_key_str = "".join(current_key_list_mutable)
                run_best_decrypted_text = current_decrypted_text
                current_status_msg_for_callback = "发现本轮更优!" 
                if status_callback: 
                    status_callback(run_best_key_str, run_best_decrypted_text, run_best_score, i + 1, False, current_status_msg_for_callback)
                    last_reported_iteration_for_gui = i + 1
        else: 
            acceptance_probability = math.exp(delta_score / temperature)
            if random.random() < acceptance_probability:
                current_key_list_mutable = candidate_key_list_mutable
                current_score = candidate_score
                current_decrypted_text = candidate_decrypted_text
                current_status_msg_for_callback = f"概率接受差解 (P={acceptance_probability:.3f})"
        
        temperature *= cooling_rate
        
        if status_callback and ((i + 1) % 500 == 0 or i == max_iterations_per_run - 1) and (i + 1) > last_reported_iteration_for_gui:
            status_callback(run_best_key_str, run_best_decrypted_text, run_best_score, i + 1, False, f"T:{temperature:.3f} {current_status_msg_for_callback}")
            last_reported_iteration_for_gui = i + 1

        if i == max_iterations_per_run - 1: status_message_on_stop_for_run = "达到最大迭代次数 (单轮)"
    
    final_score_for_assessment = run_best_score 
    qualitative_assessment = "" 
    if final_score_for_assessment > -7: qualitative_assessment = "统计特性良好"
    elif final_score_for_assessment > -12: qualitative_assessment = "统计特性尚可"
    elif final_score_for_assessment > -18: qualitative_assessment = "统计特性一般"
    else: qualitative_assessment = "统计特性较差"

    final_status_for_gui_run = f"{status_message_on_stop_for_run} ({qualitative_assessment})"

    if status_callback: 
        status_callback(run_best_key_str, run_best_decrypted_text, run_best_score, i + 1, True, final_status_for_gui_run)
    
    return run_best_key_str, run_best_decrypted_text, run_best_score