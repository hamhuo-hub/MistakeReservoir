import re
from copy import deepcopy
from docx.text.paragraph import Paragraph
from docx.table import Table

# Unified Answer Regex
ANSWER_REGEX = re.compile(
    r'(【\s*答案\s*】|【\s*解析\s*】|【\s*拓展\s*】|【\s*来源\s*】|正确\s*答案|参考\s*答案|答案\s*[:：]?|解析\s*[:：]?)'
)
# Option Pattern
OPTION_PATTERN = re.compile(r'^\s*\(?[A-DＡ-Ｄ]\)?[\.．、\s]')

def process_buffer_as_question(doc, buffer, q_num, post_processor, current_type, material_content, skip_images=False, sub_dir=None):
    """
    Convert a buffer of blocks into structured Question data.
    Separates Stem, Options, and Analysis.
    """
    stem_blocks = []
    option_blocks = []
    analysis_blocks = []
    
    # State: 0=Stem, 1=Options, 2=Analysis
    state = 0
    
    for block in buffer:
        text = ""
        if isinstance(block, Paragraph):
            text = block.text.strip()
        elif isinstance(block, Table):
            # Extract text from table for keyword checking
            cell_texts = []
            for row in block.rows:
                for cell in row.cells:
                    cell_texts.append(cell.text.strip())
            text = " ".join(cell_texts)
        
        if state < 2:
            # Direct regex check for options
            if OPTION_PATTERN.match(text):
                state = 1

        # Check Switch to Analysis using Regex
        ans_match = ANSWER_REGEX.search(text)
        
        if ans_match:
            start_idx = ans_match.start()
            
            if start_idx == 0:
                state = 2
            else:
                if isinstance(block, Paragraph):
                    part1_text = text[:start_idx].strip()
                    part2_text = text[start_idx:].strip()
                    
                    try:
                        elem_copy = deepcopy(block._element)
                        block_part2 = Paragraph(elem_copy, block._parent)
                        block_part2.text = part2_text
                        
                        block.text = part1_text
                        
                        if state == 1:
                            option_blocks.append(block)
                        elif state == 2:
                            analysis_blocks.append(block)
                        else:
                            stem_blocks.append(block)
                            
                        state = 2
                        analysis_blocks.append(block_part2)
                        
                        continue 
                        
                    except Exception as e:
                        print(f"Wrapper Split Error: {e}")
                        state = 2 
                else:
                    state = 2 
        
        
        if state == 2:
            analysis_blocks.append(block)
        elif state == 1:
            option_blocks.append(block)
        else:
            stem_blocks.append(block)
    
    # Use PostProcessor to generate HTML
    stem_html, stem_imgs = post_processor.blocks_to_html_str(doc, stem_blocks, is_stem=True, skip_images=skip_images, sub_dir=sub_dir)
    opt_html, opt_imgs = post_processor.blocks_to_html_str(doc, option_blocks, skip_images=skip_images, sub_dir=sub_dir)
    ana_html, ana_imgs = post_processor.blocks_to_html_str(doc, analysis_blocks, skip_images=skip_images, sub_dir=sub_dir)
    
    return {
        "original_num": q_num,
        "content_html": stem_html,
        "options_html": opt_html,
        "answer_html": ana_html, 
        "images": stem_imgs + opt_imgs + ana_imgs,
        "type": current_type,
        "material_content": material_content if material_content else None
    }
