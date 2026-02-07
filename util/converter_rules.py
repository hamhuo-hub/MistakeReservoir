import re

# ==================== 配置区域 ====================

# 1. 自定义【开始删除】关键字 (Regex)
# 遇到这些词，脚本进入“删除模式”
# 用户指定: 【\s*答案\s*】| 正确\s*答案 | 参考\s*答案 | 答案\s*[:：]
START_KEYWORD_REGEX = re.compile(
    r'(【\s*答案\s*】|正确\s*答案|参考\s*答案|答案\s*[:：])'
)

# 2. 自定义【结束删除】关键字 (Regex List)
# 遇到这些行（通常是新的一题或大标题），停止删除
END_KEYWORD_PATTERNS = [
    # 2.1 题号 (需要配合逻辑判断递增)
    re.compile(r'^\s*\(?(\d+)\)?[\.．、\s]'),
    
    # 2.2 部分小标题 r'^\s*第[一二三四五]+部分|'
    re.compile(r'^\s*第[一二三四五]+部分'),
    
    # 2.3 材料 r'^\s*(根据|阅读).*(材料|回答|短文|资料)'
    re.compile(r'^\s*(根据|阅读).*(材料|回答|短文|资料)'),
    
    # 2.4 大写数字标题 r'^\s*[一二三四五六七八九十]+、'
    re.compile(r'^\s*[一二三四五六七八九十]+、'),
    
    # 2.5 复合标题 (兼容 "四、根据...")
    re.compile(r'^\s*[一二三四五六七八九十]+[、\.]\s*根据')
]

# (保留旧的配置以防其他模块引用，但主要逻辑将使用上面两个)

# 兼容旧代码引用
ANSWER_REGEX = START_KEYWORD_REGEX 
Q_PATTERN = END_KEYWORD_PATTERNS[0]
HEADER_PATTERN = re.compile(r'|'.join([p.pattern for p in END_KEYWORD_PATTERNS[1:]]))

FORCE_DELETE_PREFIXES = [
    '因此，选择', '因此选择', '故本题选', '故正确答案',
    '第一步，', '第二步，', '第三步，', '第四步，',
    'A项：', 'B项：', 'C项：', 'D项：', 'A项 ', 'B项 '
]
STRONG_DELETE_CONTAIN = [
    '故本题选', '故正确答案', '故本题正确答案'
]
