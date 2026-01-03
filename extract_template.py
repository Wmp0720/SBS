import xml.etree.ElementTree as ET
import re
import os

def extract_text(xml_path):
    # 读取XML文件
    with open(xml_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    # 解析XML
    root = ET.fromstring(xml_content)
    
    # 定义命名空间
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    
    # 提取所有文本节点
    text_nodes = root.findall('.//w:t', ns)
    
    # 拼接所有文本
    full_text = ''
    for node in text_nodes:
        text = node.text if node.text else ''
        full_text += text
    
    # 去除多余的空白字符
    full_text = re.sub(r'\s+', ' ', full_text)
    
    return full_text

if __name__ == "__main__":
    # 提取专利草稿文本
    os.makedirs('/tmp/docx_work/templates', exist_ok=True)
    
    # 提取模板1
    print("=== 提取模板1: 一种多模态交互的AI绘画方法v4 ===")
    os.system("unzip -p '/Users/wmyu/Desktop/SBS论文/SBS/模板/一种多模态交互的AI绘画方法v4.docx' word/document.xml > /tmp/docx_work/templates/template1.xml")
    template1 = extract_text('/tmp/docx_work/templates/template1.xml')
    print(template1[:1000])
    
    # 提取模板2
    print("\n=== 提取模板2: 一种多人会议同声传译的方法-v2 ===")
    os.system("unzip -p '/Users/wmyu/Desktop/SBS论文/SBS/模板/一种多人会议同声传译的方法-v2.docx' word/document.xml > /tmp/docx_work/templates/template2.xml")
    template2 = extract_text('/tmp/docx_work/templates/template2.xml')
    print(template2[:1000])
