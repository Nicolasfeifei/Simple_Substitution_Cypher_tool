# cipher_logic.py
# 单表代换密码的加密与解密核心逻辑

import string

PLAINTEXT_ALPHABET = string.ascii_lowercase  # 标准26个小写英文字母

def validate_key(key):
    """验证密钥是否为包含26个不同小写英文字母的有效字符串。"""
    if not isinstance(key, str) or len(key) != 26 or \
       not all(char in PLAINTEXT_ALPHABET for char in key.lower()) or \
       len(set(key.lower())) != 26:
        return False
    return True

def encrypt(plaintext, key):
    """使用单表代换加密明文。"""
    if not validate_key(key):
        raise ValueError("无效密钥。密钥必须是26个不同的小写字母的排列。")
    key_map = {plain_char: cipher_char for plain_char, cipher_char in zip(PLAINTEXT_ALPHABET, key.lower())}
    ciphertext = ""
    for char in plaintext:
        char_lower = char.lower()
        if char_lower in key_map:
            cipher_char = key_map[char_lower]
            ciphertext += cipher_char.upper() if char.isupper() else cipher_char
        else:
            ciphertext += char
    return ciphertext

def decrypt(ciphertext, key):
    """使用单表代换解密密文。"""
    if not validate_key(key):
        raise ValueError("无效密钥。密钥必须是26个不同的小写字母的排列。")
    inv_key_map = {cipher_char: plain_char for plain_char, cipher_char in zip(PLAINTEXT_ALPHABET, key.lower())}
    plaintext = ""
    for char in ciphertext:
        char_lower = char.lower()
        if char_lower in inv_key_map:
            plain_char = inv_key_map[char_lower]
            plaintext += plain_char.upper() if char.isupper() else plain_char
        else:
            plaintext += char
    return plaintext