import os
import uuid
import re
from typing import List, Tuple, Optional
from docx.text.paragraph import Paragraph
from docx.table import Table
from .preprocessor import Q_PATTERN

FORCE_DELETE_LINES = {'故', '故。', '故本题选', '故正确答案'}

class PostProcessor:
    def __init__(self, media_dir: str):
        self.media_dir = media_dir
        if not os.path.exists(media_dir):
            os.makedirs(media_dir)

    def _save_image_from_blip(self, doc, blip_rId, sub_dir=None) -> Optional[str]:
        try:
            if not blip_rId: return None
            
            if blip_rId not in doc.part.related_parts:
                return None
                
            image_part = doc.part.related_parts[blip_rId]
            try:
                ext = image_part.content_type.split('/')[-1]
                if ext == 'jpeg': ext = 'jpg'
            except:
                ext = 'png'
            
            filename = f"{uuid.uuid4().hex}.{ext}"
            
            target_dir = self.media_dir
            if sub_dir:
                target_dir = os.path.join(self.media_dir, sub_dir)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
            
            filepath = os.path.join(target_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(image_part.blob)
            
            return filename
        except Exception as e:
            print(f"Error saving image {blip_rId}: {e}")
            return None

    def get_block_images(self, doc, block, sub_dir=None) -> List[str]:
        images = []
        try:
            if isinstance(block, Paragraph):
                ns = block._element.nsmap
                if 'a' not in ns:
                    ns['a'] = 'http://schemas.openxmlformats.org/drawingml/2006/main'
                
                try:
                    blips = block._element.findall('.//a:blip', ns)
                except KeyError:
                    blips = []

                for blip in blips:
                    rId = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                    if rId:
                        fname = self._save_image_from_blip(doc, rId, sub_dir=sub_dir)
                        if fname: images.append(fname)
                        
                imagedatas = block._element.findall('.//v:imagedata', ns)
                for idata in imagedatas:
                    rId = idata.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                    if rId:
                        fname = self._save_image_from_blip(doc, rId, sub_dir=sub_dir)
                        if fname: images.append(fname)
                        
            elif isinstance(block, Table):
                for row in block.rows:
                    for cell in row.cells:
                        for p in cell.paragraphs:
                            images.extend(self.get_block_images(doc, p, sub_dir=sub_dir))
        except Exception as e:
            pass
            
        return images

    def block_to_html(self, doc, block, skip_images=False, sub_dir=None) -> Tuple[str, List[str]]:
        images = [] if skip_images else self.get_block_images(doc, block, sub_dir=sub_dir)
        html = ""
        
        if isinstance(block, Paragraph):
            text = block.text.strip()
            html = f"<p>{text}</p>" if text else ""
        elif isinstance(block, Table):
            rows = []
            for row in block.rows:
                cells = []
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    cells.append(f"<td>{cell_text}</td>")
                rows.append(f"<tr>{''.join(cells)}</tr>")
            html = f"<table border='1' cellspacing='0' cellpadding='5'>{''.join(rows)}</table>"
        
        for img in images:
            path = f"{sub_dir}/{img}" if sub_dir else img
            html += f'<div class="img-container"><img src="/media/{path}" class="question-img" /></div>'
                
        return html, images

    def blocks_to_html_str(self, doc, blks, is_stem=False, skip_images=False, sub_dir=None):
        htmls = []
        imgs = []
        for i_idx, b in enumerate(blks):
            if isinstance(b, Paragraph):
                text = b.text.strip()
                if text in FORCE_DELETE_LINES:
                    continue
            
            if is_stem and i_idx == 0 and isinstance(b, Paragraph):
                text = b.text.strip()
                match = Q_PATTERN.match(text)
                if match:
                    cleaned_text = text[match.end():].strip()
                    block_imgs = [] if skip_images else self.get_block_images(doc, b, sub_dir=sub_dir)
                    imgs.extend(block_imgs)
                    
                    h = f"<p>{cleaned_text}</p>" if cleaned_text else ""
                    
                    for img in block_imgs:
                        path = f"{sub_dir}/{img}" if sub_dir else img
                        h += f'<div class="img-container"><img src="/media/{path}" class="question-img" /></div>'
                    
                    htmls.append(h)
                    continue
            
            h, i = self.block_to_html(doc, b, skip_images=skip_images, sub_dir=sub_dir)
            htmls.append(h)
            
            # Remove image duplication if block_to_html already added them to strings, 
            # BUT we return list of images for file management.
            imgs.extend(i)
        return "".join(htmls), imgs
