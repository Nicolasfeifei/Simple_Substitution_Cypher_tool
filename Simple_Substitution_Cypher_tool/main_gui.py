# main_gui.py
# 单表代换辅助工具的主程序，包含图形用户界面

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import string
import os
import re
import collections

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MONOGRAM_FILE_PATH = os.path.join(BASE_DIR, "english_monograms.txt")
BIGRAM_FILE_PATH = os.path.join(BASE_DIR, "english_bigrams.txt")
TRIGRAM_FILE_PATH = os.path.join(BASE_DIR, "english_trigrams.txt")
QUADGRAM_FILE_PATH = os.path.join(BASE_DIR, "english_quadgrams.txt")
COMMON_WORDS_FILE_PATH = os.path.join(BASE_DIR, "common_words.txt")

from cipher_logic import encrypt, decrypt, validate_key, PLAINTEXT_ALPHABET
from analysis_helpers import (
    get_letter_frequencies, apply_partial_key,
    generate_frequency_suggestions_data,
    load_dictionary_for_analysis, ANALYSIS_DICTIONARY_LOADED
)
from fitness import (
    calculate_fitness,
    load_monograms, load_bigrams, load_trigrams, load_quadgrams,
    load_dictionary_for_fitness,
    MONOGRAMS_LOADED, BIGRAMS_LOADED, TRIGRAMS_LOADED, QUADGRAMS_LOADED,
    FITNESS_DICTIONARY_LOADED
)
from auto_solver import solve_simulated_annealing, generate_random_key # 导入 generate_random_key

DEFAULT_WORDS_CONTENT = ["THE", "BE", "TO", "OF", "AND", "A", "IN", "THAT", "HAVE", "I",
                         "IT", "FOR", "NOT", "ON", "WITH", "HE", "AS", "YOU", "DO", "AT",
                         "THIS", "BUT", "HIS", "BY", "FROM", "ANSWER", "QUESTION", "SECRET", "MESSAGE"]

class CipherApp:
    """主应用程序类。"""
    def __init__(self, root_tk):
        self.root = root_tk
        self.root.title("单表代换辅助工具 (多轮模拟退火)")
        self.root.geometry("950x950")

        self.ensure_data_files() 

        if not MONOGRAMS_LOADED: load_monograms(MONOGRAM_FILE_PATH)
        if not BIGRAMS_LOADED: load_bigrams(BIGRAM_FILE_PATH)
        if not TRIGRAMS_LOADED: load_trigrams(TRIGRAM_FILE_PATH)
        if not QUADGRAMS_LOADED: load_quadgrams(QUADGRAM_FILE_PATH)
        if not FITNESS_DICTIONARY_LOADED: load_dictionary_for_fitness(COMMON_WORDS_FILE_PATH)
        if not ANALYSIS_DICTIONARY_LOADED: load_dictionary_for_analysis(COMMON_WORDS_FILE_PATH)

        self.current_manual_key_map = {}
        self.user_locked_mappings_for_auto = {} 
        self.overall_best_key_str = ""
        self.overall_best_score = -float('inf')
        self.overall_best_decrypted_text = ""
        self.auto_solver_master_thread = None 
        # self.auto_solver_stop_event = None # 停止事件已移除
        self.current_sa_run_best_score_log = -float('inf') 

        self.tabControl = ttk.Notebook(self.root)
        self.tab_crypt = ttk.Frame(self.tabControl)
        self.tab_manual_break = ttk.Frame(self.tabControl)
        self.tab_auto_break = ttk.Frame(self.tabControl)
        self.tabControl.add(self.tab_crypt, text='加密与解密')
        self.tabControl.add(self.tab_manual_break, text='手动辅助破译')
        self.tabControl.add(self.tab_auto_break, text='自动辅助破译 (多轮)')
        self.tabControl.pack(expand=1, fill="both")

        self.create_crypt_tab(self.tab_crypt)
        self.create_manual_break_tab(self.tab_manual_break)
        self.create_auto_break_tab(self.tab_auto_break)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def ensure_data_files(self):
        """检查数据文件，若common_words.txt缺失则创建默认，N-gram文件缺失则警告。"""
        if not os.path.exists(COMMON_WORDS_FILE_PATH) or os.path.getsize(COMMON_WORDS_FILE_PATH) == 0:
            try:
                with open(COMMON_WORDS_FILE_PATH, 'w', encoding='utf-8') as f:
                    for word in DEFAULT_WORDS_CONTENT: f.write(word + "\n")
                print(f"提示：词典文件 '{COMMON_WORDS_FILE_PATH}' 未找到或为空，已创建默认版本。")
            except Exception as e:
                messagebox.showerror("文件错误", f"无法创建默认词典文件 '{os.path.basename(COMMON_WORDS_FILE_PATH)}':\n{e}")
        ngram_files_to_check = {
            "单字母": MONOGRAM_FILE_PATH, "双字母": BIGRAM_FILE_PATH,
            "三字母": TRIGRAM_FILE_PATH, "四字母": QUADGRAM_FILE_PATH,
        }
        missing_ngram_files_info = []
        for name, path in ngram_files_to_check.items():
            if not os.path.exists(path) or os.path.getsize(path) == 0:
                missing_ngram_files_info.append(f"- {name} 数据文件 '{os.path.basename(path)}'")
        if missing_ngram_files_info:
            warning_message = "以下N-gram数据文件未找到或为空：\n" + "\n".join(missing_ngram_files_info) + \
                              "\n\n程序将使用极简备用数据，自动破译效果可能不佳。\n" + \
                              f"请确保文件位于程序目录:\n{BASE_DIR}"
            messagebox.showwarning("数据文件缺失警告", warning_message)

    def on_closing(self):
        """处理窗口关闭事件。"""
        # 由于移除了外部停止事件，如果线程在运行，关闭窗口会更直接，可能不会等待线程优雅退出。
        if self.auto_solver_master_thread and self.auto_solver_master_thread.is_alive():
            if messagebox.askokcancel("退出确认", "自动破译仍在进行中，直接退出可能导致当前轮次未完成。\n确定要退出吗？"):
                self.root.destroy() # 直接销毁窗口，线程将作为守护线程结束
        else:
            self.root.destroy()

    def create_crypt_tab(self, tab):
        """创建“加密与解密”选项卡。"""
        crypt_frame = ttk.LabelFrame(tab, text="加解密操作", padding=10)
        crypt_frame.pack(padx=10, pady=10, fill="x", expand=False)
        ttk.Label(crypt_frame, text="输入文本:").grid(row=0, column=0, padx=5, pady=5, sticky="nw")
        self.crypt_text_input = scrolledtext.ScrolledText(crypt_frame, height=8, width=80, relief=tk.SOLID, borderwidth=1, state="normal")
        self.crypt_text_input.grid(row=0, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        
        key_input_frame = ttk.Frame(crypt_frame) # 用于密钥输入和随机生成按钮的Frame
        key_input_frame.grid(row=1, column=1, columnspan=3, padx=0, pady=5, sticky="ew")

        self.crypt_key_entry = ttk.Entry(key_input_frame, width=38, font=('Consolas', 10)) # 调整宽度给按钮留空间
        self.crypt_key_entry.pack(side="left", fill="x", expand=True, padx=(0,5))
        self.crypt_key_entry.insert(0, "qwertyuiopasdfghjklzxcvbnm")
        
        random_key_button = ttk.Button(key_input_frame, text="随机生成", command=self.generate_and_set_random_key_for_crypt)
        random_key_button.pack(side="left")

        ttk.Label(crypt_frame, text="密钥 (26字母):").grid(row=1, column=0, padx=5, pady=5, sticky="nw") # 标签移到Entry旁边

        btn_frame = ttk.Frame(crypt_frame); btn_frame.grid(row=2, column=1, columnspan=2, pady=10, sticky="ew")
        encrypt_button = ttk.Button(btn_frame, text="加密", command=self.perform_encrypt); encrypt_button.pack(side="left", padx=10)
        decrypt_button = ttk.Button(btn_frame, text="解密", command=self.perform_decrypt); decrypt_button.pack(side="left", padx=10)
        
        ttk.Label(crypt_frame, text="输出结果:").grid(row=3, column=0, padx=5, pady=5, sticky="nw")
        self.crypt_result_text = scrolledtext.ScrolledText(crypt_frame, height=8, width=80, state="disabled", relief=tk.SOLID, borderwidth=1)
        self.crypt_result_text.grid(row=3, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        crypt_frame.columnconfigure(1, weight=1)

    def generate_and_set_random_key_for_crypt(self):
        """为加密解密选项卡生成随机密钥并设置到输入框。"""
        random_key = generate_random_key() # 调用 auto_solver 中的函数
        self.crypt_key_entry.delete(0, tk.END)
        self.crypt_key_entry.insert(0, random_key)

    def perform_encrypt(self):
        """执行加密操作。"""
        plaintext = self.crypt_text_input.get("1.0", tk.END).strip(); key = self.crypt_key_entry.get().strip().lower()
        if not validate_key(key): messagebox.showerror("密钥错误", "无效密钥！\n密钥必须是26个不同的小写英文字母。"); return
        try:
            result = encrypt(plaintext, key)
            self.crypt_result_text.configure(state="normal"); self.crypt_result_text.delete("1.0", tk.END); self.crypt_result_text.insert("1.0", result); self.crypt_result_text.configure(state="disabled")
        except ValueError as e: messagebox.showerror("加密错误", str(e))

    def perform_decrypt(self):
        """执行解密操作。"""
        ciphertext = self.crypt_text_input.get("1.0", tk.END).strip(); key = self.crypt_key_entry.get().strip().lower()
        if not validate_key(key): messagebox.showerror("密钥错误", "无效密钥！\n密钥必须是26个不同的小写英文字母。"); return
        try:
            result = decrypt(ciphertext, key)
            self.crypt_result_text.configure(state="normal"); self.crypt_result_text.delete("1.0", tk.END); self.crypt_result_text.insert("1.0", result); self.crypt_result_text.configure(state="disabled")
        except ValueError as e: messagebox.showerror("解密错误", str(e))

    def create_manual_break_tab(self, tab):
        """创建“手动辅助破译”选项卡。"""
        top_frame = ttk.Frame(tab); top_frame.pack(padx=10, pady=10, fill="x")
        ttk.Label(top_frame, text="输入待破译密文:").pack(side="left", anchor="nw", pady=5)
        load_cipher_button = ttk.Button(top_frame, text="开始分析 / 重置", command=self.manual_load_ciphertext); load_cipher_button.pack(side="right", padx=10)
        self.manual_cipher_input = scrolledtext.ScrolledText(tab, height=8, relief=tk.SOLID, borderwidth=1, state="normal")
        self.manual_cipher_input.pack(padx=10, fill="x", expand=False)
        main_analysis_frame = ttk.PanedWindow(tab, orient=tk.HORIZONTAL); main_analysis_frame.pack(padx=10, pady=10, fill="both", expand=True)
        left_panel = ttk.Frame(main_analysis_frame, width=350); main_analysis_frame.add(left_panel, weight=2)
        freq_frame = ttk.LabelFrame(left_panel, text="统计与建议", padding=10); freq_frame.pack(fill="both", expand=True, pady=5)
        self.manual_freq_display = scrolledtext.ScrolledText(freq_frame, height=15, width=45, relief=tk.SOLID, borderwidth=1, state="disabled"); self.manual_freq_display.pack(fill="both", expand=True)
        right_panel = ttk.Frame(main_analysis_frame, width=400); main_analysis_frame.add(right_panel, weight=3)
        import_key_frame = ttk.LabelFrame(right_panel, text="导入完整密钥进行微调", padding=10); import_key_frame.pack(fill="x", pady=(10,5))
        ttk.Label(import_key_frame, text="完整密钥 (a-z对应密文):").grid(row=0, column=0, padx=2, pady=5, sticky="w")
        self.manual_full_key_entry = ttk.Entry(import_key_frame, width=30, font=('Consolas', 10)); self.manual_full_key_entry.grid(row=0, column=1, padx=2, pady=5, sticky="ew")
        import_key_button = ttk.Button(import_key_frame, text="导入此密钥", command=self.manual_import_full_key); import_key_button.grid(row=0, column=2, padx=5, pady=5)
        import_key_frame.columnconfigure(1, weight=1)
        key_entry_frame = ttk.LabelFrame(right_panel, text="单个密钥指定/微调 (密文 -> 明文)", padding=10); key_entry_frame.pack(fill="x", pady=5)
        input_key_frame = ttk.Frame(key_entry_frame); input_key_frame.pack(pady=5)
        ttk.Label(input_key_frame, text="密文字母:").pack(side="left", padx=2); self.manual_cipher_char_entry = ttk.Entry(input_key_frame, width=4, font=('Consolas', 10)); self.manual_cipher_char_entry.pack(side="left", padx=2)
        ttk.Label(input_key_frame, text="-> 明文字母:").pack(side="left", padx=2); self.manual_plain_char_entry = ttk.Entry(input_key_frame, width=4, font=('Consolas', 10)); self.manual_plain_char_entry.pack(side="left", padx=2)
        set_key_button = ttk.Button(input_key_frame, text="设置", command=self.manual_set_key_char); set_key_button.pack(side="left", padx=(10,2))
        unset_key_button = ttk.Button(input_key_frame, text="取消该映射", command=self.manual_unset_key_char); unset_key_button.pack(side="left", padx=2)
        self.manual_key_status_display = scrolledtext.ScrolledText(right_panel, height=8, width=45, state="disabled", relief=tk.SOLID, borderwidth=1); self.manual_key_status_display.pack(fill="x", pady=5)
        decrypted_frame = ttk.LabelFrame(right_panel, text="部分解密结果", padding=10); decrypted_frame.pack(fill="both", expand=True, pady=5)
        self.manual_decrypted_text = scrolledtext.ScrolledText(decrypted_frame, height=10, width=45, wrap=tk.WORD, relief=tk.SOLID, borderwidth=1, state="disabled"); self.manual_decrypted_text.pack(fill="both", expand=True)

    def manual_import_full_key(self):
        """从输入框导入完整密钥并更新手动密钥映射。"""
        full_key_str = self.manual_full_key_entry.get().strip().lower()
        if not validate_key(full_key_str): messagebox.showerror("密钥导入错误", "无效的完整密钥！\n密钥必须是26个不同的小写英文字母的排列。"); return
        self.current_manual_key_map.clear()
        for i in range(26): self.current_manual_key_map[full_key_str[i].upper()] = PLAINTEXT_ALPHABET[i]
        self.manual_full_key_entry.delete(0, tk.END); self.update_manual_decryption_and_key_status()
        messagebox.showinfo("密钥导入成功", "完整密钥已成功导入并应用！您现在可以进行微调。")

    def manual_load_ciphertext(self):
        """加载密文进行手动分析。"""
        self.manual_full_key_entry.delete(0, tk.END); self.current_manual_key_map.clear()
        self.manual_cipher_char_entry.delete(0, tk.END); self.manual_plain_char_entry.delete(0, tk.END)
        ciphertext = self.manual_cipher_input.get("1.0", tk.END).strip().upper()
        if not ciphertext: messagebox.showinfo("提示", "请输入要分析的密文。"); return
        self.manual_freq_display.configure(state="normal"); self.manual_freq_display.delete("1.0", tk.END)
        self.manual_freq_display.insert(tk.END, "--- 密文字母频率 ---\n")
        cipher_freq = get_letter_frequencies(ciphertext)
        for char, freq_val in cipher_freq.items(): self.manual_freq_display.insert(tk.END, f"{char}: {freq_val:.2f}%\n")
        self.manual_freq_display.insert(tk.END, "\n--- 基于频率的初步建议 (密文->明文) ---\n")
        suggestions_data = generate_frequency_suggestions_data(cipher_freq)
        for i, sug in enumerate(suggestions_data):
            self.manual_freq_display.insert(tk.END, f"  密'{sug['cipher']}' ({sug['cipher_freq']:.1f}%) -> 明'{sug['plain'].lower()}' (英 {sug['plain_freq']:.1f}%)\n")
            if i >= 9: break
        self.manual_freq_display.configure(state="disabled"); self.update_manual_decryption_and_key_status()

    def manual_set_key_char(self):
        """设置单个密文到明文的映射。"""
        cipher_char = self.manual_cipher_char_entry.get().strip().upper(); plain_char = self.manual_plain_char_entry.get().strip().lower()
        if not (len(cipher_char) == 1 and cipher_char.isalpha() and len(plain_char) == 1 and plain_char.isalpha()): messagebox.showerror("输入错误", "请输入单个密文字母和单个明文字母进行映射。"); return
        if plain_char in self.current_manual_key_map.values():
            conflicting_cipher = [k for k, v in self.current_manual_key_map.items() if v == plain_char][0]
            if conflicting_cipher != cipher_char:
                if not messagebox.askyesno("映射冲突警告",f"明文字母 '{plain_char}' 已被密文字母 '{conflicting_cipher}' 映射。\n是否要取消 '{conflicting_cipher}' -> '{plain_char}' 的映射，\n并设置 '{cipher_char}' -> '{plain_char}' ？"): return
                else: del self.current_manual_key_map[conflicting_cipher]
        if cipher_char in self.current_manual_key_map and self.current_manual_key_map[cipher_char] != plain_char:
             if not messagebox.askyesno("覆盖警告",f"密文字母 '{cipher_char}' 当前已映射到 '{self.current_manual_key_map[cipher_char]}'.\n是否要将其更改为映射到 '{plain_char}'？"): return
        self.current_manual_key_map[cipher_char] = plain_char; self.manual_cipher_char_entry.delete(0, tk.END); self.manual_plain_char_entry.delete(0, tk.END)
        self.manual_cipher_char_entry.focus(); self.update_manual_decryption_and_key_status()

    def manual_unset_key_char(self):
        """取消指定密文字母的映射。"""
        cipher_char_to_unset = self.manual_cipher_char_entry.get().strip().upper()
        if not (len(cipher_char_to_unset) == 1 and cipher_char_to_unset.isalpha()): messagebox.showerror("输入错误", "请在“密文字母”框中输入要取消映射的单个字母。"); return
        if cipher_char_to_unset in self.current_manual_key_map:
            del self.current_manual_key_map[cipher_char_to_unset]; self.manual_cipher_char_entry.delete(0, tk.END); self.manual_plain_char_entry.delete(0, tk.END)
            self.update_manual_decryption_and_key_status(); messagebox.showinfo("操作成功", f"密文字母 '{cipher_char_to_unset}' 的映射已取消。")
        else: messagebox.showinfo("提示", f"密文字母 '{cipher_char_to_unset}' 当前未被映射。")

    def update_manual_decryption_and_key_status(self):
        """更新手动破译界面的密钥状态和部分解密文本。"""
        ciphertext = self.manual_cipher_input.get("1.0", tk.END).strip().upper()
        self.manual_key_status_display.configure(state="normal"); self.manual_key_status_display.delete("1.0", tk.END)
        if not ciphertext and not self.current_manual_key_map:
            self.manual_key_status_display.insert("1.0", "请先输入密文并开始分析，或设置/导入密钥映射。")
            self.manual_decrypted_text.configure(state="normal"); self.manual_decrypted_text.delete("1.0", tk.END); self.manual_decrypted_text.insert("1.0", "待部分解密的文本显示在此。"); self.manual_decrypted_text.configure(state="disabled")
            self.manual_key_status_display.configure(state="disabled"); return
        if self.current_manual_key_map:
            self.manual_key_status_display.insert(tk.END, "当前密钥映射 (密文 -> 明文):\n")
            for c, p in sorted(self.current_manual_key_map.items()): self.manual_key_status_display.insert(tk.END, f"  {c} -> {p}\n")
        else: self.manual_key_status_display.insert(tk.END, "当前无密钥映射。\n")
        mapped_cipher_chars = set(self.current_manual_key_map.keys()); mapped_plain_chars = set(self.current_manual_key_map.values())
        unmapped_cipher_gui = sorted(list(set(string.ascii_uppercase) - mapped_cipher_chars)); unmapped_plain_gui = sorted(list(set(string.ascii_lowercase) - mapped_plain_chars))
        self.manual_key_status_display.insert(tk.END, f"\n未映射密文字母: {', '.join(unmapped_cipher_gui) or '无'}\n")
        self.manual_key_status_display.insert(tk.END, f"未用明文字母: {', '.join(unmapped_plain_gui) or '无'}\n")
        self.manual_key_status_display.configure(state="disabled")
        self.manual_decrypted_text.configure(state="normal"); self.manual_decrypted_text.delete("1.0", tk.END)
        if ciphertext: self.manual_decrypted_text.insert("1.0", apply_partial_key(ciphertext, self.current_manual_key_map))
        else: self.manual_decrypted_text.insert("1.0", "请输入密文以查看部分解密结果。")
        self.manual_decrypted_text.configure(state="disabled")
    
    def create_auto_break_tab(self, tab):
        """创建“自动辅助破译”选项卡，包含多轮运行和日志。"""
        top_controls_frame = ttk.Frame(tab); top_controls_frame.pack(padx=10, pady=(10,0), fill="x")
        input_cipher_frame = ttk.LabelFrame(top_controls_frame, text="输入密文", padding=5); input_cipher_frame.pack(side="left", fill="x", expand=True, padx=(0,5))
        self.auto_cipher_input = scrolledtext.ScrolledText(input_cipher_frame, height=4, width=60, relief=tk.SOLID, borderwidth=1, state="normal"); self.auto_cipher_input.pack(fill="x", expand=True)
        locked_mappings_frame = ttk.LabelFrame(top_controls_frame, text="手动锁定密钥 (例如 C=m)", padding=5); locked_mappings_frame.pack(side="left", fill="x", expand=True, padx=(5,0))
        self.auto_locked_mappings_input = scrolledtext.ScrolledText(locked_mappings_frame, height=4, width=30, relief=tk.SOLID, borderwidth=1, state="normal"); self.auto_locked_mappings_input.pack(fill="x", expand=True)
        self.auto_locked_mappings_input.insert("1.0", "# X=e\n# Q=t\n")

        main_buttons_frame = ttk.Frame(tab); main_buttons_frame.pack(padx=10, pady=5, fill="x")
        run_params_frame = ttk.Frame(main_buttons_frame); run_params_frame.pack(side="left", padx=(0,10))
        ttk.Label(run_params_frame, text="执行轮次:").grid(row=0, column=0, sticky="w"); self.auto_num_reruns_entry = ttk.Entry(run_params_frame, width=5); self.auto_num_reruns_entry.grid(row=0, column=1, sticky="w"); self.auto_num_reruns_entry.insert(0, "10") # 默认10轮
        self.auto_start_button = ttk.Button(main_buttons_frame, text="开始自动破译 (多轮)", command=self.start_master_solver_loop); self.auto_start_button.pack(side="left", padx=5)
        # self.auto_stop_button 已被移除
        self.auto_clear_task_button = ttk.Button(main_buttons_frame, text="清空当前任务结果和日志", command=self.clear_auto_decryption_task); self.auto_clear_task_button.pack(side="left", padx=15)
        self.auto_progress_label = ttk.Label(main_buttons_frame, text="状态: 空闲", width=50); self.auto_progress_label.pack(side="left", padx=10, fill="x", expand=True)

        overall_best_frame = ttk.LabelFrame(tab, text="全程最优解 (当前解密任务)", padding=10); overall_best_frame.pack(padx=10, pady=5, fill="x", expand=False)
        key_score_frame = ttk.Frame(overall_best_frame); key_score_frame.pack(fill="x", pady=2)
        ttk.Label(key_score_frame, text="全程最佳密钥:").grid(row=0, column=0, sticky="w", padx=(0,5)); self.overall_best_key_display = ttk.Entry(key_score_frame, width=40, state="readonly", font=('Consolas', 10)); self.overall_best_key_display.grid(row=0, column=1, sticky="ew", padx=(0,10))
        ttk.Label(key_score_frame, text="全程最佳分数:").grid(row=1, column=0, sticky="w", padx=(0,5), pady=(5,0)); self.overall_best_score_display = ttk.Entry(key_score_frame, width=20, state="readonly"); self.overall_best_score_display.grid(row=1, column=1, sticky="w", pady=(5,0))
        key_score_frame.columnconfigure(1, weight=1)
        ttk.Label(overall_best_frame, text="全程最佳解密文本 (蓝色粗体为手动锁定部分):").pack(anchor="w", pady=(5,2))
        self.overall_best_decrypted_text_display = scrolledtext.ScrolledText(overall_best_frame, height=7, width=80, wrap=tk.WORD, state="disabled", relief=tk.SOLID, borderwidth=1); self.overall_best_decrypted_text_display.pack(fill="x", expand=True, pady=5)
        self.overall_best_decrypted_text_display.tag_config("locked_mapping", foreground="blue", font=('TkDefaultFont', 9, "bold"))
        self.overall_best_decrypted_text_display.tag_config("auto_mapping", foreground="black")

        current_run_info_frame = ttk.Frame(tab); current_run_info_frame.pack(padx=10, pady=0, fill="x")
        ttk.Label(current_run_info_frame, text="当前轮次迭代:").pack(side="left", padx=(0,5)); self.current_run_iteration_display = ttk.Entry(current_run_info_frame, width=15, state="readonly"); self.current_run_iteration_display.pack(side="left")

        log_frame = ttk.LabelFrame(tab, text="破译日志 (记录找到更优解的时刻)", padding=10); log_frame.pack(padx=10, pady=5, fill="both", expand=True)
        self.auto_log_display = scrolledtext.ScrolledText(log_frame, height=5, width=80, wrap=tk.WORD, state="disabled", relief=tk.SOLID, borderwidth=1); self.auto_log_display.pack(fill="both", expand=True, pady=5)

    def clear_auto_decryption_task(self):
        """清空当前自动解密任务的结果和日志，但保留用户已输入的锁定密钥。"""
        if self.auto_solver_master_thread and self.auto_solver_master_thread.is_alive():
            messagebox.showwarning("操作警告", "请等待当前自动破译任务完成或结束后再清空。"); return

        self.overall_best_key_str = ""
        self.overall_best_score = -float('inf')
        self.overall_best_decrypted_text = ""
        # self.user_locked_mappings_for_auto 不清空
        # self.auto_locked_mappings_input.delete("1.0", tk.END) 也不清空其内容

        self.current_sa_run_best_score_log = -float('inf')

        for widget in [self.overall_best_key_display, self.overall_best_score_display, self.current_run_iteration_display]:
            widget.config(state="normal"); widget.delete(0, tk.END); widget.config(state="readonly")
        for text_widget in [self.overall_best_decrypted_text_display, self.auto_log_display]:
            text_widget.config(state="normal"); text_widget.delete("1.0", tk.END); text_widget.config(state="disabled")
        
        self.auto_progress_label.config(text="状态: 空闲 (任务结果已清空，锁定映射保留)")
        self.auto_start_button.config(state="normal")
        # self.auto_stop_button 已移除
        messagebox.showinfo("任务结果已清空", "自动破译任务的结果和日志已被清空。\n手动锁定的密钥信息已保留，您可以基于此开始新的多轮尝试。")

    def parse_locked_mappings(self):
        """从GUI输入框解析用户定义的锁定映射。"""
        locked_map = {}
        raw_text = self.auto_locked_mappings_input.get("1.0", tk.END).strip()
        if not raw_text: return {} 
        lines = raw_text.splitlines()
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith("#"): continue
            match = re.fullmatch(r"([a-zA-Z])\s*=\s*([a-zA-Z])", line, re.IGNORECASE)
            if match:
                cipher_char, plain_char = match.group(1).upper(), match.group(2).lower()
                if plain_char in locked_map.values() and not any(c.upper()==cipher_char and p.lower()==plain_char for c,p in locked_map.items()):
                    conflicting_cipher = [c for c, p in locked_map.items() if p.lower() == plain_char][0]
                    messagebox.showerror("锁定映射冲突", f"第 {i+1} 行: 明文 '{plain_char}' 已被密文 '{conflicting_cipher}' 锁定。"); return None 
                if cipher_char in locked_map and locked_map[cipher_char].lower() != plain_char:
                    messagebox.showerror("锁定映射冲突", f"第 {i+1} 行: 密文 '{cipher_char}' 已被锁定到明文 '{locked_map[cipher_char]}'"); return None
                locked_map[cipher_char] = plain_char
            else: messagebox.showerror("锁定映射格式错误", f"第 {i+1} 行格式错误: '{line}'.\n请使用 '密文=明文'。"); return None
        value_counts = collections.Counter(locked_map.values())
        for plain_val, count in value_counts.items():
            if count > 1: messagebox.showerror("锁定映射严重冲突", f"明文 '{plain_val}' 被多个不同密文锁定。"); return None
        return locked_map

    def start_master_solver_loop(self):
        """启动主控循环，该循环将多次运行模拟退火算法。"""
        if self.auto_solver_master_thread and self.auto_solver_master_thread.is_alive(): messagebox.showwarning("操作警告", "自动破译任务已在进行中！"); return
        ciphertext = self.auto_cipher_input.get("1.0", tk.END).strip().upper()
        if not ciphertext: messagebox.showinfo("输入提示", "请输入用于自动破译的密文。"); return
        try:
            num_reruns = int(self.auto_num_reruns_entry.get())
            if num_reruns <= 0: raise ValueError
        except ValueError: messagebox.showerror("输入错误", "执行轮次必须是一个正整数。"); return

        parsed_locked_mappings = self.parse_locked_mappings()
        if parsed_locked_mappings is None: return 
        self.user_locked_mappings_for_auto = parsed_locked_mappings 
        
        self.auto_start_button.config(state="disabled")
        # self.auto_stop_button.config(state="normal") # 停止按钮已移除
        self.auto_locked_mappings_input.config(state="disabled") # 运行时不允许修改锁定映射
        # self.auto_solver_stop_event = threading.Event() # 停止事件已移除

        self.auto_master_thread = threading.Thread(
            target=self._master_solver_loop_thread_target,
            args=(num_reruns, ciphertext, self.user_locked_mappings_for_auto), daemon=True )
        self.auto_master_thread.start()

    def _master_solver_loop_thread_target(self, num_reruns, ciphertext, locked_mappings_for_task):
        """在单独线程中执行多轮模拟退火的主控逻辑。"""
        # 此处不检查 stop_event，因为已移除
        for run_num in range(1, num_reruns + 1):
            self.current_sa_run_best_score_log = -float('inf')
            self.root.after(0, lambda rn=run_num, nr=num_reruns: self.auto_progress_label.config(text=f"状态: 第 {rn}/{nr} 轮运行中..."))
            self.root.after(0, lambda: self.current_run_iteration_display.config(state="normal"))
            self.root.after(0, lambda: self.current_run_iteration_display.delete(0,tk.END))
            self.root.after(0, lambda: self.current_run_iteration_display.config(state="readonly"))

            run_key, _, run_score = solve_simulated_annealing(
                ciphertext, locked_mappings_for_task, 
                initial_temperature=10.0, cooling_rate=0.997, min_temperature=0.01,
                max_iterations_per_run=100000, 
                status_callback=self.update_single_sa_run_gui) # 移除了 stop_event
            
            # 移除了对 stop_event 的检查
            if run_score > self.overall_best_score:
                self.overall_best_score = run_score; self.overall_best_key_str = run_key
                self.root.after(0, self._update_overall_best_gui_display)
                log_msg = f"轮次 {run_num}/{num_reruns}: 发现新的全程最优！分数: {run_score:.4f}, 密钥: {run_key[:20]}...\n"
                self.root.after(0, self._add_to_auto_log, log_msg)
            else:
                log_msg = f"轮次 {run_num}/{num_reruns} 完成。分数: {run_score:.4f} (未超越最优: {self.overall_best_score:.4f})\n"
                self.root.after(0, self._add_to_auto_log, log_msg)
        self.root.after(0, self._update_gui_after_all_runs_stopped, f"完成全部 {num_reruns} 轮自动破译")

    def _update_overall_best_gui_display(self):
        """在主线程中更新显示全程最优解的GUI组件。"""
        if not hasattr(self, 'overall_best_key_display'): return 
        self.overall_best_key_display.config(state="normal"); self.overall_best_key_display.delete(0, tk.END); self.overall_best_key_display.insert(0, self.overall_best_key_str); self.overall_best_key_display.config(state="readonly")
        self.overall_best_score_display.config(state="normal"); self.overall_best_score_display.delete(0, tk.END); self.overall_best_score_display.insert(0, f"{self.overall_best_score:.6f}"); self.overall_best_score_display.config(state="readonly")
        
        self.overall_best_decrypted_text_display.config(state="normal"); self.overall_best_decrypted_text_display.delete("1.0", tk.END)
        current_full_key_map_cipher_to_plain = {}
        if len(self.overall_best_key_str) == 26:
            for i_map in range(26):
                if self.overall_best_key_str[i_map].isalpha(): current_full_key_map_cipher_to_plain[self.overall_best_key_str[i_map].upper()] = PLAINTEXT_ALPHABET[i_map]
        original_ciphertext_for_display = self.auto_cipher_input.get("1.0", tk.END).strip()
        for char_cipher_original_case in original_ciphertext_for_display:
            char_cipher_upper = char_cipher_original_case.upper()
            if char_cipher_upper.isalpha():
                if char_cipher_upper in current_full_key_map_cipher_to_plain:
                    plain_char = current_full_key_map_cipher_to_plain[char_cipher_upper]
                    tag_to_apply = "auto_mapping"
                    if char_cipher_upper in self.user_locked_mappings_for_auto and self.user_locked_mappings_for_auto[char_cipher_upper] == plain_char:
                        tag_to_apply = "locked_mapping"
                    self.overall_best_decrypted_text_display.insert(tk.END, plain_char.lower(), (tag_to_apply,))
                else: self.overall_best_decrypted_text_display.insert(tk.END, "_", ("auto_mapping",))
            else: self.overall_best_decrypted_text_display.insert(tk.END, char_cipher_original_case, ("auto_mapping",))
        self.overall_best_decrypted_text_display.config(state="disabled")

    def _add_to_auto_log(self, message):
        """在主线程中向自动破译日志区添加消息。"""
        if not hasattr(self, 'auto_log_display'): return
        self.auto_log_display.config(state="normal"); self.auto_log_display.insert(tk.END, message); self.auto_log_display.see(tk.END); self.auto_log_display.config(state="disabled")

    def _update_gui_after_all_runs_stopped(self, final_status_message):
        """当所有自动破译轮次完成后，在主线程中更新GUI。"""
        if not hasattr(self, 'auto_start_button'): return
        self.auto_start_button.config(state="normal")
        # self.auto_stop_button 已移除，无需操作
        self.auto_locked_mappings_input.config(state="normal") 
        self.auto_progress_label.config(text=f"状态: {final_status_message}")
        self._update_overall_best_gui_display() 
        messagebox.showinfo("自动破译任务结束", f"自动破译任务已处理完毕。\n最终状态：{final_status_message}")

    def update_single_sa_run_gui(self, key_str_run, decrypted_text_run, score_run, iteration_run, is_final_for_run, status_message_run):
        """模拟退火单轮运行的回调函数。"""
        self.root.after(0, self._update_single_sa_run_gui_threadsafe, key_str_run, decrypted_text_run, score_run, iteration_run, is_final_for_run, status_message_run)

    def _update_single_sa_run_gui_threadsafe(self, key_str_run, decrypted_text_run, score_run, iteration_run, is_final_for_run, status_message_run):
        """在GUI主线程中实际执行单轮SA运行的界面更新。"""
        if not hasattr(self, 'current_run_iteration_display'): return 
        self.current_run_iteration_display.config(state="normal")
        self.current_run_iteration_display.delete(0, tk.END); self.current_run_iteration_display.insert(0, str(iteration_run))
        self.current_run_iteration_display.config(state="readonly")
        
        if status_message_run == "发现本轮更优!" or (status_message_run == "单轮初始化完成, 开始迭代..." and iteration_run == 0) :
            if score_run > self.current_sa_run_best_score_log or iteration_run == 0:
                self.current_sa_run_best_score_log = score_run
                log_message = f"  当前轮次迭代 {iteration_run}: 本轮新最佳分数 {score_run:.4f}, 密钥: {key_str_run[:20]}...\n"
                self._add_to_auto_log(log_message)
        
        if is_final_for_run: self.current_sa_run_best_score_log = -float('inf')


if __name__ == '__main__':
    app_root = tk.Tk()
    style = ttk.Style(app_root); available_themes = style.theme_names()
    if 'vista' in available_themes: style.theme_use('vista')        
    elif 'clam' in available_themes: style.theme_use('clam')       
    elif 'aqua' in available_themes: style.theme_use('aqua')       
    elif 'alt' in available_themes: style.theme_use('alt')
    elif 'default' in available_themes: style.theme_use('default')
    app = CipherApp(app_root)
    app_root.mainloop()