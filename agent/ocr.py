"""
DashScope OCR - 使用 qwen-vl-ocr 模型对图片/PDF扫描页进行文字识别
"""
import os
import base64
from io import BytesIO
from pathlib import Path
from typing import List

import dashscope
from dashscope import MultiModalConversation


def image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def ocr_image_file(image_path: str, api_key: str) -> str:
    """对图片文件进行 OCR，返回识别文字"""
    if not os.path.exists(image_path):
        return ""

    with open(image_path, "rb") as f:
        img_bytes = f.read()

    b64 = image_to_base64(img_bytes)
    image_url = f"data:image/png;base64,{b64}"

    dashscope.api_key = api_key
    resp = MultiModalConversation.call(
        model="qwen-vl-ocr",
        messages=[{
            "role": "user",
            "content": [
                {"image": image_url},
                {"text": "请识别图片中的所有文字，只返回文字内容，不要其他说明。"}
            ]
        }]
    )

    if resp.status_code != 200:
        print(f"  [OCR API error] {resp.message}")
        return ""

    try:
        content = resp.output["choices"][0]["message"]["content"]
        # 处理 ocr_result 格式
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and "ocr_result" in item:
                    return item["ocr_result"].get("processed_text", "")
        elif isinstance(content, str):
            return content
    except Exception as e:
        print(f"  [OCR parse error] {e}")

    return ""


def ocr_pdf_page(pixmap_bytes: bytes, api_key: str) -> str:
    """对 PDF 页面渲染图进行 OCR"""
    b64 = image_to_base64(pixmap_bytes)
    image_url = f"data:image/png;base64,{b64}"

    dashscope.api_key = api_key
    resp = MultiModalConversation.call(
        model="qwen-vl-ocr",
        messages=[{
            "role": "user",
            "content": [
                {"image": image_url},
                {"text": "请识别图片中的所有文字，只返回文字内容。"}
            ]
        }]
    )

    if resp.status_code != 200:
        return ""

    try:
        content = resp.output["choices"][0]["message"]["content"]
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and "ocr_result" in item:
                    return item["ocr_result"].get("processed_text", "")
        elif isinstance(content, str):
            return content
    except Exception:
        return ""

    return ""
