import os
import re
from typing import List, Dict, Optional
from docx import Document
# from docx.document import Document as _Document # Not strictly needed if only passing to preprocessor
from docx.text.paragraph import Paragraph
from docx.table import Table

from parsing import preprocessor
from parsing import core
from parsing.postprocessor import PostProcessor, FORCE_DELETE_LINES

class QuestionExtractor:
    def __init__(self, media_dir: str):
        self.media_dir = media_dir
        self.post_processor = PostProcessor(media_dir)
        
        # Current State
        self.current_material_id = None
        self.current_material_content = ""
        self.current_type = "Unknown"
        
        # Expose Patterns for main loop usage
        self.Q_PATTERN = preprocessor.Q_PATTERN
        self.HEADER_PATTERN = preprocessor.HEADER_PATTERN
        self.IGNORE_PATTERN = preprocessor.IGNORE_PATTERN
        self.FORCE_DELETE_LINES = FORCE_DELETE_LINES

    def extract_from_file(self, docx_path: str, target_ids: List[int] = None, skip_images: bool = False, sub_dir: str = None) -> List[Dict]:
        """
        Main Entry: Parse file and return list of Question Dicts.
        If target_ids is None, return all.
        """
        doc = Document(docx_path)
        blocks = list(preprocessor.iter_block_items(doc))
        
        extracted_questions = []
        buffer = []
        last_q_num = 0 
        current_q_num = 0
        
        for block in blocks:
            text = ""
            if isinstance(block, Paragraph):
                text = block.text.strip()
            elif isinstance(block, Table):
                 pass

            # 1. Check Header (Material / Type Change)
            if self.HEADER_PATTERN.match(text):
                if buffer and current_q_num > 0:
                    # Delegate to core
                    q = core.process_buffer_as_question(
                        doc, buffer, current_q_num, self.post_processor, 
                        self.current_type, self.current_material_content, 
                        skip_images=skip_images, sub_dir=sub_dir
                    )
                    if target_ids is None or current_q_num in target_ids:
                         extracted_questions.append(q)
                    
                    buffer = []
                
                # Identify Type
                is_material_header = text.strip().startswith("根据") or text.strip().startswith("阅读")
                if not is_material_header:
                    if "常识" in text: self.current_type = "常识"
                    elif "言语" in text: self.current_type = "言语"
                    elif "数量" in text: self.current_type = "数量"
                    elif "资料" in text: self.current_type = "资料"
                    elif "判断" in text: self.current_type = "判断" 
                    
                    if "图形" in text and "推理" in text: self.current_type = "图形"
                    elif "定义" in text and "判断" in text: self.current_type = "定义"
                    elif "类比" in text and "推理" in text: self.current_type = "类比"
                    elif "逻辑" in text and "判断" in text: self.current_type = "逻辑"
                
                # Material Handling
                if current_q_num > 0:
                    last_q_num = current_q_num
                
                current_q_num = 0
                self.current_material_content = "" 
                
                if "根据" in text or "材料" in text or "阅读" in text:
                     h, _ = self.post_processor.block_to_html(doc, block, skip_images=skip_images, sub_dir=sub_dir)
                     self.current_material_content += h
                
                continue

            # 2. Check Question Start
            match = self.Q_PATTERN.match(text)
            is_new_q = False
            found_num = 0
            
            if match:
                try:
                    nums = re.findall(r'\d+', text)
                    if nums:
                        found_num = int(nums[0])
                        # Sanity Check
                        if found_num < 500: # Years like 2016 filtered
                            if current_q_num == 0:
                                # Check against LAST q_num if current is 0
                                if last_q_num == 0:
                                    is_new_q = True # Start of file
                                elif (found_num == last_q_num + 1) or (found_num > last_q_num and found_num - last_q_num < 20):
                                     is_new_q = True
                            elif (found_num == current_q_num + 1) or (found_num > current_q_num and found_num - current_q_num < 20):
                                is_new_q = True
                except:
                    pass
            
            if is_new_q:
                # Process previous
                if buffer:
                    if current_q_num > 0:
                        q = core.process_buffer_as_question(
                            doc, buffer, current_q_num, self.post_processor, 
                            self.current_type, self.current_material_content, 
                            skip_images=skip_images, sub_dir=sub_dir
                        )
                        if target_ids is None or current_q_num in target_ids:
                            extracted_questions.append(q)
                    else:
                        for b in buffer:
                            h, imgs = self.post_processor.block_to_html(doc, b, skip_images=skip_images, sub_dir=sub_dir)
                            self.current_material_content += h
                
                # Start new
                current_q_num = found_num
                buffer = [block]
                
            else:
                if current_q_num > 0:
                    should_skip = False
                    if isinstance(block, Paragraph) and text in self.FORCE_DELETE_LINES:
                        should_skip = True
                    
                    if not should_skip:
                        buffer.append(block)
                else:
                    # check ignore
                    if self.IGNORE_PATTERN.match(text):
                        continue
                        
                    h, imgs = self.post_processor.block_to_html(doc, block, skip_images=skip_images, sub_dir=sub_dir)
                    if text or imgs:
                        self.current_material_content += h

        if buffer and current_q_num > 0:
            q = core.process_buffer_as_question(
                doc, buffer, current_q_num, self.post_processor, 
                self.current_type, self.current_material_content, 
                skip_images=skip_images, sub_dir=sub_dir
            )
            if target_ids is None or current_q_num in target_ids:
                extracted_questions.append(q)
                
        return extracted_questions

if __name__ == "__main__":
    extractor = QuestionExtractor(media_dir="media")
